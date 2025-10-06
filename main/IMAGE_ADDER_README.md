# Image Adder Node - Intelligent Document Image Insertion

## Overview

The Image Adder Node is an AI-powered feature that intelligently analyzes your document structure and automatically places relevant images into appropriate sections based on:

- **Document headings and sections** - Extracted using the DOCX agent
- **Image descriptions** - Read from a CSV file with image metadata
- **LLM-based matching** - Uses GPT to determine the best image-to-section matches

## Architecture

### Graph Integration

The Image Adder Node is integrated as a **separate path** in the LangGraph workflow:

```
START → Supervisor → Image Adder Node → END
```

### Components

1. **`image_adder_node.py`** - Main node implementation
   - `add_images_to_document()` - Async function that executes the image addition workflow
   - `should_add_images()` - Router function (optional, currently handled by main supervisor router)

2. **`graph.py`** - Graph integration
   - Added "image_adder" node to the workflow
   - Connected to supervisor routing
   - Direct path to END after completion

3. **`router.py`** - Routing logic
   - Priority 2: Detects image-related requests
   - Keywords: "add images", "insert images", "place images", etc.

## Workflow

### Step-by-Step Process

1. **Index Document Structure**
   ```python
   docx_manager = get_docx_manager()
   await docx_manager._ensure_index_loaded()
   outline = docx_manager.get_outline()
   ```
   - Retrieves all headings from the document
   - Creates a structured outline with anchors

2. **Load Image Metadata**
   - Reads from `main/images/image_name_dicription.csv`
   - Format:
     ```csv
     Image Name,Description
     screenshot1.png,System architecture diagram
     screenshot2.png,User interface mockup
     ```
   - Validates that image files exist

3. **LLM-Based Matching**
   - Sends document outline + image list to GPT
   - LLM analyzes and returns matches:
     ```
     screenshot1.png -> 2
     screenshot2.png -> 5
     ```
   - Parses LLM response and validates matches

4. **Image Insertion**
   - Uses `docx_manager.insert_image()`
   - Inserts after the matched section heading
   - Default width: 5 inches
   - Position: "after" the heading

5. **Result Reporting**
   - Returns success count
   - Lists all inserted images with their sections
   - Reports any errors encountered

## Usage

### Basic Usage

```python
# Via the main graph
from agent.graph import graph

# Send a message requesting image addition
response = await graph.ainvoke({
    "messages": [
        {"role": "user", "content": "Add images to the document"}
    ]
})
```

### Via Agent Name

```python
response = await graph.ainvoke({
    "messages": [
        {"role": "user", "content": "Use image_adder to insert pictures"}
    ]
})
```

### Trigger Keywords

The following phrases will route to the image adder:
- "add images"
- "insert images"
- "place images"
- "add image"
- "insert image"
- "place image"
- "add pictures"
- "insert pictures"
- "add photo"
- "image_adder" (explicit agent name)

## Configuration

### Image Directory

Default: `/Users/yash/Documents/rfp/rfp-bid/main/images/`

To change, modify in `image_adder_node.py`:
```python
images_dir = Path("/your/custom/path/images")
```

### CSV Path

Default: `/Users/yash/Documents/rfp/rfp-bid/main/images/image_name_dicription.csv`

To change:
```python
csv_path = Path("/your/custom/path/images.csv")
```

### Image Size

Default width: 5 inches

To change:
```python
success = docx_manager.insert_image(
    image_path=image_info['path'],
    width=6.0,  # Change to desired width in inches
    after_anchor=section['anchor'],
    position="after"
)
```

### LLM Model

Default: `gpt-4o-mini` (from environment)

To change:
```python
llm = ChatOpenAI(
    model="gpt-4o",  # Use a different model
    temperature=0.3,
    api_key=os.getenv("OPENAI_API_KEY"),
)
```

## CSV Format

The CSV file must follow this format:

```csv
Image Name,Description
Screenshot 2025-10-06 at 4.42.31 PM.png,Network topology diagram showing security zones
Screenshot 2025-10-06 at 4.43.35 PM.png,User authentication flow
Screenshot 2025-10-06 at 4.44.34 PM.png,Database schema design
```

### Fields

- **Image Name** (required): Exact filename including extension
- **Description** (optional): Text description to help the LLM match images to sections

### Tips for Better Matching

1. **Use descriptive section headings** in your document
2. **Provide detailed image descriptions** in the CSV
3. **Match terminology** - use similar words in descriptions and headings
4. **Be specific** - "Security architecture diagram" is better than "diagram"

## Error Handling

The node handles various error cases:

### No Headings Found
```
No headings found in document. Cannot add images without document structure.
```
**Solution**: Ensure your document has heading styles (Heading 1, Heading 2, etc.)

### CSV Not Found
```
Image description CSV not found at [path]
```
**Solution**: Create the CSV file or update the path in the code

### No Valid Images
```
No valid images found in CSV or images directory.
```
**Solution**: 
- Verify image files exist in the images directory
- Check CSV has valid entries
- Ensure image filenames match exactly

### No Matches Found
```
No suitable image-to-section matches found by the AI.
```
**Solution**:
- Add more descriptive section headings
- Improve image descriptions in CSV
- Add more images with varied descriptions

### Insertion Failures
```
Failed to insert [image] after '[section]'
```
**Solution**:
- Check document isn't corrupted
- Verify anchor points are valid
- Ensure document isn't locked

## Integration Example

Here's how the node integrates with the existing system:

```python
# graph.py
workflow = StateGraph(MessagesState)

# Add the image adder node
workflow.add_node("image_adder", add_images_to_document)

# Connect to supervisor
workflow.add_conditional_edges(
    "supervisor",
    supervisor_router,
    {
        "image_adder": "image_adder",
        # ... other routes
    }
)

# Direct path to END
workflow.add_edge("image_adder", END)
```

## State Management

### Input State

```python
{
    "messages": [
        # List of conversation messages
    ]
}
```

### Output State

```python
{
    "messages": [
        # Previous messages +
        AIMessage(
            content="✅ Image Addition Complete!\n\nSuccessfully inserted 3 out of 3 matched images...",
            name="image_adder"
        )
    ]
}
```

## Advanced Features

### Custom Matching Logic

To implement custom matching logic instead of LLM:

```python
# Replace the LLM matching section in add_images_to_document()

# Custom rule-based matching
matches = []
for img in image_data:
    for i, heading in enumerate(outline):
        # Your custom logic here
        if keyword_match(img['description'], heading['text']):
            matches.append({
                'image': img,
                'section_index': i,
                'section_heading': heading
            })
```

### Position Options

The `insert_image()` method supports different positions:

```python
# Insert before the heading
position="before"

# Insert after the heading (default)
position="after"

# Replace the heading with image
position="replace"
```

### Multiple Images Per Section

The current implementation matches one image per section, but you can modify to allow multiple:

```python
# In the matching prompt, update instructions:
matching_prompt = """
...
Rules:
- Multiple images CAN be matched to the same section
- List all relevant matches
...
"""
```

## Testing

Create a test script:

```python
# test_image_adder.py
import asyncio
from agent.graph import graph

async def test_image_addition():
    response = await graph.ainvoke({
        "messages": [
            {"role": "user", "content": "Add images to the document"}
        ]
    })
    
    print(response["messages"][-1].content)

if __name__ == "__main__":
    asyncio.run(test_image_addition())
```

Run with:
```bash
cd /Users/yash/Documents/rfp/rfp-bid/main
python test_image_adder.py
```

## Limitations

1. **Single Pass Only** - Currently runs once per invocation
2. **After-Heading Only** - Default position is after the heading
3. **CSV-Based Only** - Requires pre-populated CSV file
4. **LLM Dependency** - Matching quality depends on LLM capabilities
5. **No Image Analysis** - Doesn't analyze actual image content

## Future Enhancements

Possible improvements:

1. **Image Content Analysis** - Use vision models to understand image content
2. **Interactive Approval** - Human-in-the-loop for match confirmation
3. **Batch Processing** - Handle multiple documents
4. **Dynamic Image Discovery** - Auto-scan and catalog images
5. **Position Customization** - UI to specify exact placement
6. **Caption Generation** - Auto-generate image captions
7. **Format Options** - Support different sizes per image type

## Troubleshooting

### Images Not Inserting

1. Check DOCX file isn't open in another program
2. Verify image files are readable
3. Ensure document path is correct in `get_docx_manager()`
4. Check file permissions

### Wrong Sections Matched

1. Improve image descriptions
2. Add more context to section headings
3. Adjust LLM temperature (currently 0.3)
4. Try a different LLM model

### Performance Issues

1. Reduce number of images
2. Use smaller image files
3. Optimize LLM calls (batch if needed)
4. Cache document outline

## Support

For issues or questions:
1. Check this README
2. Review code comments in `image_adder_node.py`
3. Test with sample document and images
4. Check LangGraph logs for errors

