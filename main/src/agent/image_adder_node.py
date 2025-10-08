"""
Image Adder Node - Intelligently adds images to document sections

This node:
1. Gets document headings using docx_manager
2. Reads image descriptions from CSV
3. Uses LLM to match images to appropriate sections
4. Inserts images using docx_manager
"""

import os
import csv
import json
import asyncio
import unicodedata
from pathlib import Path
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage
from rct_agent.docx_manager import get_docx_manager


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
    
    # 2) Known absolute path
    absolute = Path("/Users/yash/Documents/rfp/rfp-bid/main/images")
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
        
        # Step 1: Get document outline (headings)
        docx_manager = get_docx_manager()
        await docx_manager._ensure_index_loaded()
        outline = docx_manager.get_outline()
        
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
        images_dir = Path("/Users/yash/Documents/rfp/rfp-bid/main/images")
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
            f"Section {i+1}: {heading['text']} (Level {heading.get('heading_level', 'N/A')})"
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
        
        # Step 6: Insert images into document
        inserted_count = 0
        errors = []
        
        for match in matches:
            image_info = match['image']
            section = match['section_heading']
            
            try:
                # Insert image after the section heading (run blocking I/O in a thread)
                success = await asyncio.to_thread(
                    docx_manager.insert_image,
                    image_path=image_info['path'],
                    width=5.0,  # 5 inches width
                    after_anchor=section['anchor'],
                    position="after"
                )
                
                if success:
                    inserted_count += 1
                else:
                    errors.append(f"Failed to insert {image_info['name']} after '{section['text']}'")
                    
            except Exception as e:
                errors.append(f"Error inserting {image_info['name']}: {str(e)}")
        
        # Step 7: Prepare result message
        result_parts = [
            f"✅ Image Addition Complete!",
            f"",
            f"Successfully inserted {inserted_count} out of {len(matches)} matched images.",
            f""
        ]
        
        if inserted_count > 0:
            result_parts.append("Inserted images:")
            for i, match in enumerate(matches[:inserted_count]):
                reasoning = match.get('reasoning', 'No reasoning provided')
                result_parts.append(
                    f"  • {match['image']['name']} → after '{match['section_heading']['text']}'"
                )
                result_parts.append(f"    └─ Reason: {reasoning}")
        
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
