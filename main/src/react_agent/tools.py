"""This module provides tools for document management and web search functionality.

It includes:
- DOCX document management tools (create section, edit config, update content, get content)
- Basic Tavily search function

These tools enable intelligent document operations with auto-rendering capabilities.
"""

import json
import os
import csv
from datetime import datetime
from typing import Any, Callable, List, Optional, cast


from langgraph.runtime import get_runtime

from react_agent.context import Context
from react_agent.json_docx_converter import convert_json_to_docx
from react_agent.utils import load_chat_model


# Get paths from environment variables with fallback defaults
CONFIG_PATH = os.getenv("DOCX_CONFIG_PATH", "/Users/yash/json-docx/main/config.json")
CONTENT_PATH = os.getenv("DOCX_CONTENT_PATH", "/Users/yash/json-docx/main/content.json")
OUTPUT_DIR = os.getenv("DOCX_OUTPUT_DIR", "/Users/yash/json-docx/docx")


def _ensure_files_exist() -> tuple[bool, str]:
    """Ensure config.json and content.json exist with defaults.
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Ensure directories exist
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        os.makedirs(os.path.dirname(CONTENT_PATH), exist_ok=True)
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Create default config.json if missing
        if not os.path.exists(CONFIG_PATH):
            default_config = {
                "metadata": {
                    "title": "RFP Proposal Document",
                    "author": "RFP Agent",
                    "page_size": "A4",
                    "orientation": "portrait",
                    "margins": {"top": 2.54, "bottom": 2.54, "left": 2.54, "right": 2.54}
                },
                "styles": {
                    "heading": [
                        {"level": 1, "font": "Arial", "size": 18, "bold": True},
                        {"level": 2, "font": "Arial", "size": 16, "bold": True},
                        {"level": 3, "font": "Arial", "size": 14, "bold": True}
                    ],
                    "paragraph": {"font": "Arial", "size": 12},
                    "table": {"border": True, "cell_padding": 0.2, "font": "Arial", "size": 10}
                }
            }
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
        
        # Create default content.json if missing
        if not os.path.exists(CONTENT_PATH):
            default_content = {
                "Introduction": [
                    {"type": "heading", "text": "Introduction", "level": 1}
                ]
            }
            with open(CONTENT_PATH, 'w', encoding='utf-8') as f:
                json.dump(default_content, f, indent=2, ensure_ascii=False)
        
        return True, "Files initialized successfully"
    
    except Exception as e:
        return False, f"Error initializing files: {str(e)}"


def _render_docx() -> str:
    """Internal helper to render DOCX from current config and content.
    
    Creates timestamped output file in the docx directory.
    """
    try:
        # Ensure output directory exists
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Generate timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(OUTPUT_DIR, f"output_{timestamp}.docx")
        
        # Convert JSON to DOCX
        success, message = convert_json_to_docx(CONFIG_PATH, CONTENT_PATH, output_path)
        
        if success:
            return f"Document rendered successfully: {output_path}"
        else:
            return f"Failed to render document: {message}"
    
    except Exception as e:
        return f"Error rendering document: {str(e)}"


def render_document() -> str:
    """Render the current document from config.json and content.json to DOCX.
    
    This is a separate operation that should be called after making changes to
    content.json or config.json to generate the final DOCX file.
    
    The rendered document will be saved with a timestamp in the output directory.
    
    Returns:
        Success message with file path, or detailed error message if validation fails.
    
    Usage:
        Call this after creating/updating sections or configuration to generate
        the final document. This allows you to make multiple edits before rendering.
    """
    try:
        # Ensure files exist
        success, message = _ensure_files_exist()
        if not success:
            return message
        
        # Render the document
        return _render_docx()
    
    except Exception as e:
        return f"Error rendering document: {str(e)}"


def _deep_merge_dict(base: dict, updates: dict) -> dict:
    """Recursively merge updates into base dictionary.
    
    Args:
        base: Base dictionary to merge into
        updates: Updates to apply
    """
    result = base.copy()
    for key, value in updates.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge_dict(result[key], value)
        else:
            result[key] = value
    return result


async def search(query: str) -> Optional[dict[str, Any]]:
    """Search for general web results.

    This function performs a search using the Tavily search engine, which is designed
    to provide comprehensive, accurate, and trusted results. It's particularly useful
    for answering questions about current events.
    """
    runtime = get_runtime(Context)
    wrapped = TavilySearch(max_results=runtime.context.max_search_results)
    return cast(dict[str, Any], await wrapped.ainvoke({"query": query}))


def create_section(section_name: str, elements: Optional[List[dict]] = None) -> str:
    """Create a new section with content elements in the document.
    
    Adds a new section to content.json with the specified elements.
    If no elements are provided, creates a section with a default heading.
    Automatically renders the updated document to DOCX.
    
    Args:
        section_name: Name of the new section
        elements: Optional list of content element dictionaries with 'type' field.
                  If not provided, creates a heading with the section name.
    
    Examples:
        # Create section with just a heading (auto-generated)
        create_section("Technical Architecture")
        
        # Create section with custom elements
        create_section("Executive Summary", [
            {"type": "heading", "text": "Executive Summary", "level": 1},
            {"type": "paragraph", "text": "This section provides an overview..."}
        ])
    """
    try:
        # Ensure files exist with defaults
        success, message = _ensure_files_exist()
        if not success:
            return message
        
        # If no elements provided, create a default heading
        if elements is None:
            elements = [
                {"type": "heading", "text": section_name, "level": 2}
            ]
        
        # Load current content
        with open(CONTENT_PATH, 'r', encoding='utf-8') as f:
            content = json.load(f)
        
        # Check if section already exists
        if section_name in content:
            return f"Error: Section '{section_name}' already exists. Use update_content to modify it."
        
        # Validate elements structure
        for idx, element in enumerate(elements):
            if not isinstance(element, dict):
                return f"Error: Element {idx} must be a dictionary"
            if 'type' not in element:
                return f"Error: Element {idx} missing 'type' field"
        
        # Add new section
        content[section_name] = elements
        
        # Save updated content
        with open(CONTENT_PATH, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
        
        return f"Section '{section_name}' created with {len(elements)} element(s). Content saved to {CONTENT_PATH}. Call render_document() to generate the DOCX file."
    
    except FileNotFoundError:
        return f"Error: Content file not found at {CONTENT_PATH}"
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON in content file: {str(e)}"
    except Exception as e:
        return f"Error creating section: {str(e)}"


def edit_config(updates: dict) -> str:
    """Edit document configuration (metadata, styles, header, footer).
    
    Updates config.json with the provided changes. Supports nested updates
    that merge with existing configuration. Automatically renders the updated document.
    
    Args:
        updates: Dictionary with configuration updates
    """
    try:
        # Ensure files exist with defaults
        success, message = _ensure_files_exist()
        if not success:
            return message
        
        # Load current config
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Merge updates with existing config
        updated_config = _deep_merge_dict(config, updates)
        
        # Save updated config
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(updated_config, f, indent=2, ensure_ascii=False)
        
        return f"Configuration updated successfully. Config saved to {CONFIG_PATH}. Call render_document() to generate the DOCX file."
    
    except FileNotFoundError:
        return f"Error: Config file not found at {CONFIG_PATH}"
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON in config file: {str(e)}"
    except Exception as e:
        return f"Error updating config: {str(e)}"


def update_content(section_name: str, element_index: int, updated_element: dict) -> str:
    """Update a specific element within a section.
    
    Updates the element at the specified index within a section.
    Automatically renders the updated document to DOCX.
    
    Args:
        section_name: Name of the section to update
        element_index: Zero-based index of the element to update
        updated_element: New element data with 'type' field
    """
    try:
        # Ensure files exist with defaults
        success, message = _ensure_files_exist()
        if not success:
            return message
        
        # Load current content
        with open(CONTENT_PATH, 'r', encoding='utf-8') as f:
            content = json.load(f)
        
        # Check if section exists
        if section_name not in content:
            return f"Error: Section '{section_name}' not found. Available sections: {list(content.keys())}"
        
        # Check if index is valid
        section_elements = content[section_name]
        if not isinstance(section_elements, list):
            return f"Error: Section '{section_name}' does not contain a list of elements"
        
        if element_index < 0 or element_index >= len(section_elements):
            return f"Error: Invalid index {element_index}. Section has {len(section_elements)} element(s) (indices 0-{len(section_elements)-1})"
        
        # Validate updated element
        if not isinstance(updated_element, dict):
            return "Error: updated_element must be a dictionary"
        if 'type' not in updated_element:
            return "Error: updated_element missing 'type' field"
        
        # Update element
        content[section_name][element_index] = updated_element
        
        # Save updated content
        with open(CONTENT_PATH, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
        
        return f"Element {element_index} in section '{section_name}' updated successfully. Content saved to {CONTENT_PATH}. Call render_document() to generate the DOCX file."
    
    except FileNotFoundError:
        return f"Error: Content file not found at {CONTENT_PATH}"
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON in content file: {str(e)}"
    except Exception as e:
        return f"Error updating content: {str(e)}"


def get_sections() -> str:
    """List all document sections with their headings.
    
    Returns a list of all sections showing their names and primary headings.
    Useful for understanding the document structure before making changes.
    """
    try:
        # Ensure files exist with defaults
        success, message = _ensure_files_exist()
        if not success:
            return message
        
        # Load current content
        with open(CONTENT_PATH, 'r', encoding='utf-8') as f:
            content = json.load(f)
        
        sections_info = []
        for section_name, elements in content.items():
            # Find first heading in the section
            heading_text = "No heading"
            for element in elements:
                if element.get('type') == 'heading':
                    heading_text = element.get('text', 'Untitled')
                    break
            
            sections_info.append({
                "section_name": section_name,
                "heading": heading_text,
                "element_count": len(elements)
            })
        
        return json.dumps(sections_info, indent=2, ensure_ascii=False)
    
    except FileNotFoundError:
        return f"Error: Content file not found at {CONTENT_PATH}"
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON in content file: {str(e)}"
    except Exception as e:
        return f"Error listing sections: {str(e)}"


def get_content(section_name: str) -> str:
    """Get content elements from a specific section.
    
    Returns the content of the specified section as a JSON string.
    This is a read-only operation and does not trigger document rendering.
    
    Args:
        section_name: Name of the section to retrieve
    """
    try:
        # Ensure files exist with defaults
        success, message = _ensure_files_exist()
        if not success:
            return message
        
        # Load current content
        with open(CONTENT_PATH, 'r', encoding='utf-8') as f:
            content = json.load(f)
        
        # Check if section exists
        if section_name not in content:
            # Try to find section by heading
            for sec_name, elements in content.items():
                for element in elements:
                    if element.get('type') == 'heading' and section_name.lower() in element.get('text', '').lower():
                        section_name = sec_name
                        break
                if section_name in content:
                    break
            
            if section_name not in content:
                sections_list = [{"name": k, "heading": next((e.get('text') for e in v if e.get('type') == 'heading'), 'No heading')} for k, v in content.items()]
                return f"Error: Section not found. Available sections:\n{json.dumps(sections_list, indent=2)}"
        
        # Return section content as formatted JSON
        section_content = content[section_name]
        return json.dumps(section_content, indent=2, ensure_ascii=False)
    
    except FileNotFoundError:
        return f"Error: Content file not found at {CONTENT_PATH}"
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON in content file: {str(e)}"
    except Exception as e:
        return f"Error retrieving content: {str(e)}"


def get_content_by_heading(heading_text: str) -> str:
    """Get content from a section by searching for a heading.
    
    Searches for a section containing a heading that matches the given text.
    Case-insensitive partial matching is supported.
    
    Args:
        heading_text: Text to search for in section headings
    """
    try:
        # Ensure files exist with defaults
        success, message = _ensure_files_exist()
        if not success:
            return message
        
        # Load current content
        with open(CONTENT_PATH, 'r', encoding='utf-8') as f:
            content = json.load(f)
        
        # Search for matching heading
        for section_name, elements in content.items():
            for element in elements:
                if element.get('type') == 'heading':
                    if heading_text.lower() in element.get('text', '').lower():
                        return json.dumps({
                            "section_name": section_name,
                            "content": elements
                        }, indent=2, ensure_ascii=False)
        
        return f"Error: No section found with heading containing '{heading_text}'. Use get_sections() to see all available sections."
    
    except FileNotFoundError:
        return f"Error: Content file not found at {CONTENT_PATH}"
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON in content file: {str(e)}"
    except Exception as e:
        return f"Error searching for heading: {str(e)}"


def insert_content_after_heading(heading_text: str, new_element: dict) -> str:
    """Insert a content element after a specific heading.
    
    Searches for a heading by text and inserts the new element immediately after it.
    Automatically renders the updated document to DOCX.
    
    Args:
        heading_text: Text to search for in section headings (case-insensitive)
        new_element: Element dictionary to insert (must have 'type' field)
    """
    try:
        # Ensure files exist with defaults
        success, message = _ensure_files_exist()
        if not success:
            return message
        
        # Load current content
        with open(CONTENT_PATH, 'r', encoding='utf-8') as f:
            content = json.load(f)
        
        # Validate new element
        if not isinstance(new_element, dict):
            return "Error: new_element must be a dictionary"
        if 'type' not in new_element:
            return "Error: new_element missing 'type' field"
        
        # Search for matching heading
        found = False
        for section_name, elements in content.items():
            if not isinstance(elements, list):
                continue
                
            for idx, element in enumerate(elements):
                if element.get('type') == 'heading':
                    if heading_text.lower() in element.get('text', '').lower():
                        # Insert after this heading
                        content[section_name].insert(idx + 1, new_element)
                        found = True
                        break
            
            if found:
                break
        
        if not found:
            sections_list = []
            for sec_name, elems in content.items():
                for elem in elems:
                    if elem.get('type') == 'heading':
                        sections_list.append(elem.get('text', 'Untitled'))
                        break
            return f"Error: No heading found matching '{heading_text}'. Available headings: {sections_list}"
        
        # Save updated content
        with open(CONTENT_PATH, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
        
        return f"Element inserted after heading '{heading_text}'. Content saved to {CONTENT_PATH}. Call render_document() to generate the DOCX file."
    
    except FileNotFoundError:
        return f"Error: Content file not found at {CONTENT_PATH}"
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON in content file: {str(e)}"
    except Exception as e:
        return f"Error inserting content: {str(e)}"


async def add_images_from_csv() -> str:
    """Automatically match and insert images from CSV into document sections.
    
    Reads image metadata from main/images/image_name_dicription.csv and uses
    LLM-based matching to determine the best section for each image based on
    heading text and image descriptions. Inserts images after matched headings.
    
    Returns a summary of successfully inserted images and any errors encountered.
    """
    # Hardcoded paths
    CSV_PATH = "/Users/yash/json-docx/main/images/image_name_dicription.csv"
    IMAGE_DIR = "/Users/yash/json-docx/main/images"
    
    try:
        # Ensure files exist with defaults
        success, message = _ensure_files_exist()
        if not success:
            return message
        
        # Load CSV with image metadata
        if not os.path.exists(CSV_PATH):
            return f"Error: CSV file not found at {CSV_PATH}"
        
        images_data = []
        with open(CSV_PATH, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                image_name = row.get('Image Name', '').strip()
                description = row.get('Description', '').strip()
                
                if not image_name:
                    continue
                
                # Validate image file exists
                image_path = os.path.join(IMAGE_DIR, image_name)
                if not os.path.exists(image_path):
                    return f"Error: Image file not found: {image_path}"
                
                images_data.append({
                    'name': image_name,
                    'description': description,
                    'path': image_path
                })
        
        if not images_data:
            return "Error: No valid images found in CSV"
        
        # Load document sections
        with open(CONTENT_PATH, 'r', encoding='utf-8') as f:
            content = json.load(f)
        
        # Build section list with headings
        sections_info = []
        for section_name, elements in content.items():
            for element in elements:
                if element.get('type') == 'heading':
                    sections_info.append({
                        'section_name': section_name,
                        'heading': element.get('text', 'Untitled'),
                        'level': element.get('level', 1)
                    })
                    break
        
        if not sections_info:
            return "Error: No sections with headings found in document"
        
        # Build LLM prompt
        section_list_text = "\n".join([
            f"- {s['heading']}" for s in sections_info
        ])
        
        image_list_text = "\n".join([
            f"- {img['name']}: {img['description']}" for img in images_data
        ])
        
        prompt = f"""You are matching images to document sections. Match each image to the most relevant section heading based on the image description and section topic.

Document Sections:
{section_list_text}

Available Images:
{image_list_text}

Return matches in the exact format below, one per line:
image_name.png -> Section Heading Text

Only return valid matches where the image content clearly relates to the section. Skip images that don't fit any section well.
"""
        
        # Call LLM for matching
        runtime = get_runtime(Context)
        model = load_chat_model(runtime.context.model)
        
        response = await model.ainvoke([{"role": "user", "content": prompt}])
        llm_output = response.content if hasattr(response, 'content') else str(response)
        
        # Parse LLM response
        matches = []
        for line in llm_output.strip().split('\n'):
            line = line.strip()
            if '->' not in line:
                continue
            
            parts = line.split('->')
            if len(parts) != 2:
                continue
            
            image_name = parts[0].strip()
            heading_text = parts[1].strip()
            
            # Validate image exists in our list
            image_found = None
            for img in images_data:
                if img['name'] == image_name:
                    image_found = img
                    break
            
            if image_found:
                matches.append({
                    'image': image_found,
                    'heading': heading_text
                })
        
        if not matches:
            return f"No valid matches found. LLM response:\n{llm_output}"
        
        # Insert images
        results = []
        errors = []
        
        for match in matches:
            image_name = match['image']['name']
            heading = match['heading']
            image_path = match['image']['path']
            
            # Create image element
            image_element = {
                'type': 'image',
                'path': image_path,
                'width': 480  # 5 inches at 96 DPI
            }
            
            # Insert after heading
            result = insert_content_after_heading(heading, image_element)
            
            if result.startswith("Error"):
                errors.append(f"{image_name}: {result}")
            else:
                results.append(f"{image_name} -> {heading}")
        
        # Build summary report
        summary = f"Image insertion complete: {len(results)} successful, {len(errors)} errors.\n\n"
        
        if results:
            summary += "Successfully inserted:\n"
            for r in results:
                summary += f"  ✓ {r}\n"
        
        if errors:
            summary += "\nErrors:\n"
            for e in errors:
                summary += f"  ✗ {e}\n"
        
        return summary
    
    except FileNotFoundError as e:
        return f"Error: File not found - {str(e)}"
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON - {str(e)}"
    except Exception as e:
        return f"Error in add_images_from_csv: {str(e)}"


# List of all available tools for the agent
TOOLS: List[Callable[..., Any]] = [
    search,
    get_sections,
    get_content,
    get_content_by_heading,
    create_section,
    edit_config,
    update_content,
    insert_content_after_heading,
    add_images_from_csv,
    render_document
]
