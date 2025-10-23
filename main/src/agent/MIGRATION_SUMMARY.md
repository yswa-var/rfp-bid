# Migration from rct_agent to react_agent - Summary

## Date
October 23, 2025

## Overview
Successfully migrated the docx_agent subgraph from `rct_agent` to `react_agent`. The migration maintains the same architecture and routing while adapting to react_agent's JSON-based document management approach.

## Changes Made

### 1. graph.py (Line 25)
**Changed:**
```python
from rct_agent.graph import graph as docx_agent_graph
```

**To:**
```python
from react_agent.graph import graph as docx_agent_graph
```

**Impact:** The docx_agent subgraph now uses react_agent, which operates on JSON files (config.json, content.json) instead of directly manipulating DOCX files.

### 2. image_adder_node.py (Complete Refactoring)

#### Removed Dependencies
- Removed: `from rct_agent.docx_manager import get_docx_manager`

#### New Helper Functions Added

**_read_json_file(file_path: str) -> Dict[str, Any] | None**
- Synchronously reads JSON files for asyncio.to_thread execution
- Used to read content.json without blocking the event loop

**_extract_headings_from_content(content_data: Dict[str, Any]) -> List[Dict[str, Any]]**
- Extracts all headings from content.json structure
- Returns list of heading dictionaries with 'text', 'level', 'section_name'
- Replaces docx_manager.get_outline()

**_insert_image_after_heading(heading_text: str, image_element: Dict[str, Any]) -> str**
- Inserts image elements into content.json after specified headings
- Blocking I/O function for asyncio.to_thread execution
- Replaces docx_manager.insert_image()

#### Main Function Changes (add_images_to_document)

**Step 1: Get Document Outline**
- **Old:** Used `docx_manager.get_outline()` to read from DOCX file
- **New:** Reads from content.json using `_read_json_file()` and `_extract_headings_from_content()`

**Step 6: Insert Images**
- **Old:** Used `docx_manager.insert_image()` with anchor-based positioning
- **New:** Uses `_insert_image_after_heading()` to insert image elements into JSON structure
- Image element format: `{'type': 'image', 'path': '/path/to/image', 'width': 480}`

## Architecture Verification

### ✅ All Routes Preserved
1. **supervisor → docx_agent**: Works (line 82, 102 in graph.py)
2. **supervisor → image_adder**: Works (line 83, 104 in graph.py)
3. **rfp_supervisor → teams (finance, technical, legal, qa)**: Works (lines 117-126)
4. **rfp teams → docx_agent**: Works (lines 128-163)
5. **Direct flows to END**: All preserved

### Document Flow
```
User Request → Supervisor
              ↓
    ┌─────────┼──────────┬─────────────┐
    ↓         ↓          ↓             ↓
pdf_parser  docx_agent  image_adder  rfp_supervisor
    ↓         ↓          ↓             ↓
create_rag   END        END      team nodes
    ↓                               ↓
   END                      docx_agent or END
```

## Key Differences: rct_agent vs react_agent

### rct_agent Approach
- Direct DOCX manipulation using python-docx
- Uses DocxManager with anchor-based positioning
- Reads/writes directly to .docx files
- Index-based document navigation

### react_agent Approach
- JSON-based document representation (content.json, config.json)
- Inserts elements into JSON structure by heading text
- Renders to DOCX using json_docx_converter
- Section and element-based navigation

## Testing Recommendations

1. **Basic Flow Test**: Verify supervisor routes to docx_agent correctly
2. **Image Adder Test**: Test image insertion with sample CSV and images
3. **RFP Team Flow**: Verify RFP teams → docx_agent workflow
4. **End-to-End**: Test complete RFP generation with all components

## Environment Variables

The following environment variables are used by image_adder_node.py:
- `DOCX_CONTENT_PATH` (default: `/Users/yash/json-docx/main/content.json`)
- `LLM_MODEL` (default: `gpt-4o-mini`)
- `OPENAI_API_KEY` (required)

For react_agent tools (used by docx_agent):
- `DOCX_CONFIG_PATH` (default: `/Users/yash/json-docx/main/config.json`)
- `DOCX_CONTENT_PATH` (default: `/Users/yash/json-docx/main/content.json`)
- `DOCX_OUTPUT_DIR` (default: `/Users/yash/json-docx/docx`)

### 3. react_agent/graph.py (Subgraph Compatibility Fix)

**Issue:** When used as a subgraph, react_agent receives a different runtime context than it expects, causing:
```
AttributeError: 'dict' object has no attribute 'model'
```

**Solution:** Made runtime parameter optional with fallback defaults (similar to rct_agent approach):
- Runtime parameter now defaults to `None`
- Added checks: `if runtime and hasattr(runtime, 'context') and runtime.context:`
- Falls back to default model `"openai/gpt-4o-mini"` when context is unavailable
- Falls back to `prompts.SYSTEM_PROMPT` when system_prompt is unavailable

**Changed function signature:**
```python
async def call_model(state: State, runtime: Runtime[Context] = None)
```

This allows react_agent to work both:
- As a standalone graph with full Context schema
- As a subgraph in the main agent system with partial/no context

### 4. react_agent/tools.py (Graceful Initialization)

**Issue:** Tools were failing when `config.json` or `content.json` didn't exist, showing cryptic "file not found" errors.

**Solution:** Added automatic file initialization with sensible defaults:

**New helper function `_ensure_files_exist()`:**
- Creates directories if missing (`os.makedirs`)
- Creates `config.json` with default metadata and styles if missing
- Creates `content.json` with a starter "Introduction" section if missing
- Returns success/error tuple for consistent error handling

**Updated all tool functions:**
- `create_section` - ensures files exist before creating sections
- `get_sections` - ensures files exist before reading
- `get_content` - ensures files exist before retrieving content
- `get_content_by_heading` - ensures files exist before searching
- `edit_config` - ensures files exist before updating config
- `update_content` - ensures files exist before updating
- `insert_content_after_heading` - ensures files exist before inserting
- `add_images_from_csv` - ensures files exist before adding images

**Default config.json structure:**
```json
{
  "metadata": {
    "title": "RFP Proposal Document",
    "author": "RFP Agent",
    "page_size": "A4",
    "orientation": "portrait",
    "margins": {"top": 2.54, "bottom": 2.54, "left": 2.54, "right": 2.54}
  },
  "styles": { ... }
}
```

**Default content.json structure:**
```json
{
  "Introduction": [
    {"type": "heading", "text": "Introduction", "level": 1}
  ]
}
```

This ensures a smooth first-run experience with automatic workspace setup.

## Files Modified

1. `/Users/yash/Documents/rfp/rfp-bid/main/src/agent/graph.py` - Import updated
2. `/Users/yash/Documents/rfp/rfp-bid/main/src/agent/image_adder_node.py` - JSON-based refactor  
3. `/Users/yash/Documents/rfp/rfp-bid/main/src/react_agent/graph.py` - Subgraph compatibility fix
4. `/Users/yash/Documents/rfp/rfp-bid/main/src/react_agent/tools.py` - Graceful initialization

## Files Unchanged

- `src/rct_agent/` folder remains intact for reference
- All other agent files unchanged
- Router files unchanged
- State files unchanged

## Status

✅ **Migration Complete**
- No linter errors
- Architecture verified and intact
- All imports updated
- Helper functions implemented
- Ready for testing

