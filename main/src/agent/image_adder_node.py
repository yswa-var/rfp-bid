"""
Image Adder Node - Intelligently adds images to document sections

This node:
1. Gets document headings from content.json
2. Reads image descriptions from CSV
3. Uses LLM to match images to appropriate sections
4. Inserts images using react_agent's insert_content_after_heading
"""

import os
import sys
import csv
import json
import glob
import asyncio
import unicodedata
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage


def _resolve_images_dir() -> Path:
    """Resolve images directory robustly across environments.
    
    Priority:
    1) IMAGES_DIR or RFP_IMAGES_DIR env var if set
    2) Known absolute path
    3) Repo-relative path: <repo_root>/main/images
    """
    # 1) Env vars
    env_dir = os.getenv("IMAGES_DIR") or os.getenv("RFP_IMAGES_DIR")
    if env_dir:
        p = Path(env_dir)
        if p.exists():
            return p
    
    # 2) Dynamic absolute path resolution
    current_file = Path(__file__).resolve()
    repo_root = current_file.parents[3]  # Go up to repo root
    absolute = repo_root / "main" / "images"
    if absolute.exists():
        return absolute
    
    # 3) Repo-relative
    current_file = Path(__file__).resolve()
    # __file__ = .../main/src/agent/image_adder_node.py
    # repo_root = parents[3]
    repo_root = current_file.parents[3]
    candidate = repo_root / "main" / "images"
    return candidate


def _read_image_data_sync(images_dir: Path, csv_path: Path) -> list[dict[str, Any]]:
    """Synchronously read image data from CSV and resolve paths, with unicode-normalization tolerant matching.
    This function is intended to be executed in a background thread via asyncio.to_thread.
    """
    image_data: list[dict[str, Any]] = []

    # Build a name index of files in the directory once (avoid repeated scandir)
    normalized_name_to_path: dict[str, Path] = {}
    if images_dir.exists():
        for p in images_dir.iterdir():  # blocking scandir; safe here (called in thread)
            if not p.is_file():
                continue
            normalized = unicodedata.normalize('NFC', p.name)
            normalized_name_to_path[normalized] = p

    with open(csv_path, 'r', encoding='utf-8') as csvfile:  # blocking; safe in thread
        reader = csv.DictReader(csvfile)
        for row in reader:
            raw_name = (row.get('Image Name') or '').strip()
            description = (row.get('Description') or '').strip()
            if not raw_name:
                continue

            # Normalize filename to NFC (macOS often stores filenames in NFD)
            nfc_name = unicodedata.normalize('NFC', raw_name)
            nfd_name = unicodedata.normalize('NFD', raw_name)

            resolved_path: Path | None = None

            # Direct candidates
            for candidate_name in (nfc_name, nfd_name, raw_name):
                p = images_dir / candidate_name
                if p.exists():  # blocking; but inside thread
                    resolved_path = p
                    break

            # Fallback to index
            if resolved_path is None:
                resolved_path = normalized_name_to_path.get(nfc_name)

            if resolved_path is not None and resolved_path.exists():
                image_data.append({
                    'name': resolved_path.name,
                    'description': description if description else "No description provided",
                    'path': str(resolved_path)
                })

    return image_data


def _read_json_file(file_path: str) -> Dict[str, Any] | None:
    """Synchronously read JSON file. Intended for asyncio.to_thread execution.
    
    Args:
        file_path: Path to JSON file
        
    Returns:
        Parsed JSON data or None if error
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, Exception) as e:
        print(f"Error reading JSON file {file_path}: {e}")
        return None


def _extract_headings_from_content(content_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract all headings from content.json structure.
    
    Args:
        content_data: Parsed content.json dictionary
        
    Returns:
        List of heading dictionaries with 'text', 'level', 'section_name'
    """
    headings = []
    
    for section_name, elements in content_data.items():
        if not isinstance(elements, list):
            continue
            
        for element in elements:
            if element.get('type') == 'heading':
                headings.append({
                    'text': element.get('text', 'Untitled'),
                    'level': element.get('level', 1),
                    'section_name': section_name
                })
    
    return headings


def _find_latest_versioned_file(directory: str, pattern: str) -> Optional[str]:
    """Find the latest versioned file in a directory (blocking operation for threads).
    
    Args:
        directory: Directory to search
        pattern: Glob pattern (e.g., "content_*.json")
        
    Returns:
        Path to latest file or None if not found
    """
    search_pattern = os.path.join(directory, pattern)
    files = glob.glob(search_pattern)
    
    if not files:
        return None
    
    # Extract timestamps and sort
    versioned_files = []
    for f in files:
        basename = os.path.basename(f)
        try:
            # Extract timestamp from filename (e.g., content_1234567890.json -> 1234567890)
            # Remove prefix (everything before *) and suffix (everything after *)
            prefix = pattern.split("*")[0]  # e.g., "content_"
            suffix = pattern.split("*")[1] if len(pattern.split("*")) > 1 else ""  # e.g., ".json"
            
            timestamp_str = basename
            if prefix:
                timestamp_str = timestamp_str.replace(prefix, "", 1)
            if suffix:
                timestamp_str = timestamp_str.replace(suffix, "", 1)
            
            timestamp = int(timestamp_str)
            versioned_files.append((timestamp, f))
        except (ValueError, IndexError):
            continue
    
    if not versioned_files:
        return None
    
    versioned_files.sort(reverse=True)
    return versioned_files[0][1]


def _find_latest_config_and_content(config_dir: str, content_dir: str) -> Tuple[Optional[str], Optional[str]]:
    """Find latest config and content files (blocking operation for threads).
    
    Args:
        config_dir: Directory containing config files
        content_dir: Directory containing content files
        
    Returns:
        Tuple of (config_path, content_path) or (None, None) if not found
    """
    config_path = _find_latest_versioned_file(config_dir, "config_*.json")
    content_path = _find_latest_versioned_file(content_dir, "content_*.json")
    return config_path, content_path


def _insert_image_after_heading(heading_text: str, image_element: Dict[str, Any]) -> str:
    """Insert an image element after a heading in content.json.
    
    This is a blocking I/O function intended for asyncio.to_thread execution.
    
    Args:
        heading_text: Text of the heading to search for
        image_element: Image element dictionary to insert
        
    Returns:
        Success or error message
    """
    try:
        # Dynamic path resolution
        _current_file = Path(__file__).resolve()
        _repo_root = _current_file.parents[3]
        _default_content = _repo_root / "main" / "test_output" / "content"
        
        # Get latest versioned content file
        content_dir = os.getenv("DOCX_CONTENT_DIR", str(_default_content))
        content_path = _find_latest_versioned_file(content_dir, "content_*.json")
        
        if not content_path:
            return "Error: No content files found. Initialize document first."
        
        # Load current content
        with open(content_path, 'r', encoding='utf-8') as f:
            content = json.load(f)
        
        # Search for matching heading and insert image
        found = False
        for section_name, elements in content.items():
            if not isinstance(elements, list):
                continue
                
            for idx, element in enumerate(elements):
                if element.get('type') == 'heading':
                    if heading_text.lower() in element.get('text', '').lower():
                        # Insert image after this heading
                        content[section_name].insert(idx + 1, image_element)
                        found = True
                        break
            
            if found:
                break
        
        if not found:
            return f"Error: Heading '{heading_text}' not found"
        
        # Save updated content
        with open(content_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
        
        return f"Successfully inserted image after '{heading_text}'"
        
    except Exception as e:
        return f"Error: {str(e)}"


async def add_images_to_document(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main image adder node function.
    
    Analyzes document structure and intelligently places images based on:
    - Section content and headings
    - Image descriptions from CSV
    - LLM-based matching
    
    Args:
        state: Current graph state containing messages
        
    Returns:
        Updated state with operation results
    """
    messages = state.get("messages", [])
    
    try:
        # Initialize LLM for intelligent matching
        llm = ChatOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            temperature=0.3,
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        
        # Step 1: Get document outline (headings) from content.json
        # Dynamic path resolution
        _current_file = Path(__file__).resolve()
        _repo_root = _current_file.parents[3]
        _default_content_dir = _repo_root / "main" / "test_output" / "content"
        
        content_dir = os.getenv("DOCX_CONTENT_DIR", str(_default_content_dir))
        
        # Get latest versioned content file (run in thread to avoid blocking)
        content_path = await asyncio.to_thread(_find_latest_versioned_file, content_dir, "content_*.json")
        
        if not content_path:
            return {
                "messages": messages + [
                    AIMessage(
                        content=f"Could not find content files in {content_dir}. Initialize document first.",
                        name="image_adder"
                    )
                ]
            }
        
        # Read content.json in a thread to avoid blocking
        content_data = await asyncio.to_thread(_read_json_file, content_path)
        
        if content_data is None:
            return {
                "messages": messages + [
                    AIMessage(
                        content=f"Could not read content file at {content_path}",
                        name="image_adder"
                    )
                ]
            }
        
        # Extract headings from all sections
        outline = _extract_headings_from_content(content_data)
        
        if not outline:
            return {
                "messages": messages + [
                    AIMessage(
                        content="No headings found in document. Cannot add images without document structure.",
                        name="image_adder"
                    )
                ]
            }
        
        # Step 2: Read image descriptions from CSV
        current_file = Path(__file__).resolve()
        repo_root = current_file.parents[3]  # Go up to repo root
        images_dir = repo_root / "main" / "images"
        csv_path = images_dir / "image_name_dicription.csv"
        
        csv_exists = await asyncio.to_thread(lambda: csv_path.exists())
        if not csv_exists:
            return {
                "messages": messages + [
                    AIMessage(
                        content=f"Image description CSV not found at {csv_path}",
                        name="image_adder"
                    )
                ]
            }
        
        # Read image data in background thread (avoid blocking event loop)
        image_data = await asyncio.to_thread(_read_image_data_sync, images_dir, csv_path)
        
        if not image_data:
            return {
                "messages": messages + [
                    AIMessage(
                        content=f"No valid images found in CSV or images directory. Checked directory: {images_dir}",
                        name="image_adder"
                    )
                ]
            }
        
        # Step 3: Format outline for LLM analysis
        outline_text = "\n".join([
            f"Section {i+1}: {heading['text']} (Level {heading.get('level', 1)})"
            for i, heading in enumerate(outline)
        ])
        
        # Format image list for LLM
        images_text = "\n".join([
            f"Image {i+1}: {img['name']} - {img['description']}"
            for i, img in enumerate(image_data)
        ])
        
        # Step 4: Use LLM to match images to sections with JSON response
        matching_prompt = f"""You are an expert document editor. Given a document outline and a list of images with descriptions, 
determine which images should be placed in which sections for maximum relevance and impact.

DOCUMENT OUTLINE:
{outline_text}

AVAILABLE IMAGES:
{images_text}

Analyze the content and provide your matches as a JSON array. Each match should be an object with:
- "image_name": the exact filename from the available images list above
- "section_number": the section number (1-based) from the document outline
- "reasoning": brief explanation of why this image fits this section

Return ONLY valid JSON in this exact format:
{{
  "matches": [
    {{
      "image_name": "image_name.png",
      "section_number": 1,
      "reasoning": "Architecture diagram fits the introduction section"
    }},
    {{
      "image_name": "image_name.png",
      "section_number": 2,
      "reasoning": "Security overview matches security section"
    }}
  ]
}}

Rules:
- Match images that are clearly relevant to a section
- Each image can only be matched to ONE section
- A section can have multiple images
- For testing purposes, try to match all available images to the most appropriate sections
- Use the exact image names from the AVAILABLE IMAGES list above
- Section numbers must be valid (1 to {len(outline)})
- Return ONLY the JSON object, no additional text
"""
        
        response = await llm.ainvoke([HumanMessage(content=matching_prompt)])
        response_content = response.content.strip()
        
        # Step 5: Parse JSON response and extract matches
        matches = []
        try:
            # Extract JSON if wrapped in markdown code blocks
            if "```json" in response_content:
                response_content = response_content.split("```json")[1].split("```")[0].strip()
            elif "```" in response_content:
                response_content = response_content.split("```")[1].split("```")[0].strip()
            
            # Parse JSON
            parsed_response = json.loads(response_content)
            match_data = parsed_response.get("matches", [])
            
            # Process each match
            for match_item in match_data:
                try:
                    image_name = (match_item.get("image_name") or "").strip()
                    section_num = int(match_item.get("section_number", 0))
                    reasoning = match_item.get("reasoning", "No reasoning provided")
                    
                    # Validate section number
                    if section_num < 1 or section_num > len(outline):
                        continue
                    
                    # Find the image data by matching the filename
                    img_info = next((img for img in image_data if img['name'] == image_name), None)
                    
                    if img_info:
                        matches.append({
                            'image': img_info,
                            'section_index': section_num - 1,  # Convert to 0-based index
                            'section_heading': outline[section_num - 1],
                            'reasoning': reasoning
                        })
                    
                except (ValueError, KeyError, TypeError) as e:
                    # Skip malformed match items
                    continue
            
        except json.JSONDecodeError as e:
            # Fallback: Try to parse as plain text if JSON parsing fails
            print(f"JSON parsing failed: {e}. Attempting fallback text parsing.")
            for line in response_content.split('\n'):
                if '->' in line:
                    try:
                        parts = line.split('->')
                        image_name = parts[0].strip().strip('"\'')
                        # Remove path if present
                        if '/' in image_name:
                            image_name = image_name.split('/')[-1]
                        section_num = int(parts[1].strip())
                        
                        if section_num > 0 and section_num <= len(outline):
                            img_info = next((img for img in image_data if img['name'] == image_name), None)
                            if img_info:
                                matches.append({
                                    'image': img_info,
                                    'section_index': section_num - 1,
                                    'section_heading': outline[section_num - 1],
                                    'reasoning': 'Fallback parsing - no reasoning provided'
                                })
                    except (ValueError, IndexError):
                        continue
        
        if not matches:
            return {
                "messages": messages + [
                    AIMessage(
                        content="No suitable image-to-section matches found by the AI.",
                        name="image_adder"
                    )
                ]
            }
        
        # Step 6: Insert images into document using JSON-based approach
        inserted_count = 0
        errors = []
        
        for match in matches:
            image_info = match['image']
            heading_info = match['section_heading']
            heading_text = heading_info['text']
            
            try:
                # Create image element for JSON structure
                # react_agent expects: {'type': 'image', 'path': '/path/to/image', 'width': pixels, 'height': pixels}
                image_element = {
                    'type': 'image',
                    'path': image_info['path'],
                    'width': 480,  # 480 pixels = ~5 inches at 96 DPI
                }
                
                # Insert image using JSON-based insertion (run in thread)
                result = await asyncio.to_thread(
                    _insert_image_after_heading,
                    heading_text,
                    image_element
                )
                
                if result.startswith("Success"):
                    inserted_count += 1
                else:
                    errors.append(f"Failed to insert {image_info['name']} after '{heading_text}': {result}")
                    
            except Exception as e:
                errors.append(f"Error inserting {image_info['name']}: {str(e)}")
        
        # Step 7: Render the document with images
        render_result = "Document not rendered"
        if inserted_count > 0:
            try:
                # Ensure react_agent is in path
                _current_dir = Path(__file__).resolve().parent
                _src_dir = _current_dir.parent
                if str(_src_dir) not in sys.path:
                    sys.path.insert(0, str(_src_dir))
                
                # Import render function
                from react_agent.json_docx_converter import convert_json_to_docx
                
                # Dynamic path resolution
                _current_file = Path(__file__).resolve()
                _repo_root = _current_file.parents[3]
                _default_test_output = _repo_root / "main" / "test_output"
                
                config_dir = os.getenv("DOCX_CONFIG_DIR", str(_default_test_output / "config"))
                content_dir = os.getenv("DOCX_CONTENT_DIR", str(_default_test_output / "content"))
                output_dir = os.getenv("DOCX_OUTPUT_DIR", str(_default_test_output / "docx"))
                
                # Get latest versioned files (run in thread to avoid blocking)
                config_path, content_path = await asyncio.to_thread(
                    _find_latest_config_and_content,
                    config_dir,
                    content_dir
                )
                
                if not config_path:
                    return {
                        "messages": messages + [
                            AIMessage(
                                content=f"No config files found in {config_dir}",
                                name="image_adder"
                            )
                        ]
                    }
                
                if not content_path:
                    return {
                        "messages": messages + [
                            AIMessage(
                                content=f"No content files found in {content_dir}",
                                name="image_adder"
                            )
                        ]
                    }
                
                # Ensure output directory exists
                await asyncio.to_thread(os.makedirs, output_dir, exist_ok=True)
                
                # Generate timestamped filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = os.path.join(output_dir, f"output_{timestamp}.docx")
                
                # Render document in background thread
                success, render_msg = await asyncio.to_thread(
                    convert_json_to_docx,
                    config_path,
                    content_path,
                    output_path
                )
                
                if success:
                    render_result = f"✅ Document rendered with images: {output_path}"
                else:
                    render_result = f"⚠️ Document rendering failed: {render_msg}"
                    
            except Exception as e:
                render_result = f"⚠️ Error rendering document: {str(e)}"
        
        # Step 8: Prepare result message
        result_parts = [
            f"✅ Image Addition Complete!",
            f"",
            f"Successfully inserted {inserted_count} out of {len(matches)} matched images.",
            f""
        ]
        
        if inserted_count > 0:
            result_parts.append("Inserted images:")
            for match in matches[:inserted_count]:
                reasoning = match.get('reasoning', 'No reasoning provided')
                heading_text = match['section_heading']['text']
                result_parts.append(
                    f"  • {match['image']['name']} → after '{heading_text}'"
                )
                result_parts.append(f"    └─ Reason: {reasoning}")
            
            # Add render result
            result_parts.append("")
            result_parts.append(render_result)
        
        # if errors:
        #     result_parts.append("")
        #     result_parts.append("Errors encountered:")
        #     for error in errors:
        #         result_parts.append(f"  ⚠️ {error}")
        
        result_message = "\n".join(result_parts)
        
        return {
            "messages": messages + [
                AIMessage(
                    content=result_message,
                    name="image_adder"
                )
            ]
        }
        
    except Exception as e:
        return {
            "messages": messages + [
                AIMessage(
                    content=f"Error in image adder node: {str(e)}",
                    name="image_adder"
                )
            ]
        }


def should_add_images(state: Dict[str, Any]) -> str:
    """
    Router function to determine if we should add images.
    
    Returns:
        "add_images" if the user request is about adding images
        "__end__" otherwise
    """
    messages = state.get("messages", [])
    
    if not messages:
        return "__end__"
    
    # Check last user message
    from langchain_core.messages import HumanMessage
    user_messages = [m for m in messages if isinstance(m, HumanMessage)]
    
    if user_messages:
        last_content = user_messages[-1].content.lower()
        
        # Keywords that trigger image addition
        if any(keyword in last_content for keyword in [
            "add images",
            "insert images", 
            "place images",
            "add pictures",
            "insert pictures",
            "image adder",
            "add image"
        ]):
            return "add_images"
    
    return "__end__"
