# RAG System Scripts

This directory contains two separate RAG (Retrieval-Augmented Generation) systems for managing different types of documents:

1. **Template RAG** (`template_rag.py`) - For managing template documents
2. **RFP RAG** (`rfp_rag.py`) - For managing RFP example documents

Both scripts use the `milvus_ops.py` module for PDF processing, chunking, and vector operations.

## Features

### Template RAG
- Add template documents to the RAG system
- Query template database with semantic search
- Interactive query mode
- Quality statistics and chunk analysis

### RFP RAG
- Add RFP example documents to the RAG system
- Query RFP database with semantic search
- Query specific RFP documents
- List available RFP documents
- Interactive query mode with advanced features

## Installation

Make sure you have the required dependencies installed:

```bash
pip install -r requirements.txt
```

## Usage

### Template RAG

#### Add Data
```bash
python template_rag.py add_data --template_dir /path/to/template/directory
```

#### Query Data
```bash
python template_rag.py query_data --query "What are the key requirements?" --k 5
```

#### Interactive Mode
```bash
python template_rag.py interactive
```

### RFP RAG

#### Add Data
```bash
python rfp_rag.py add_data --rfp_dir /path/to/rfp/directory
```

#### Query Data
```bash
python rfp_rag.py query_data --query "What are the cybersecurity requirements?" --k 5
```

#### Query Specific RFP
```bash
python rfp_rag.py query_data --query "security requirements" --rfp_name "RFP-229-CYBER-SECURITY.pdf" --k 3
```

#### Interactive Mode
```bash
python rfp_rag.py interactive
```

## Command Line Options

### Common Options
- `--db_name`: Database name (default: template_rag.db or rfp_rag.db)
- `--chunk_size`: Chunk size in characters (default: 1000 for templates, 1200 for RFP)
- `--chunk_overlap`: Chunk overlap in characters (default: 200 for templates, 300 for RFP)
- `--k`: Number of results to return (default: 5)

### Template RAG Options
- `--template_dir`: Template directory path (required for add_data)
- `--query`: Query string (required for query_data)

### RFP RAG Options
- `--rfp_dir`: RFP directory path (required for add_data)
- `--query`: Query string (required for query_data)
- `--rfp_name`: Specific RFP name to search in (optional)

## Example Usage

### 1. Setup Template RAG
```bash
# Add template documents
python template_rag.py add_data --template_dir ../../example-PDF/Contracts --chunk_size 1000

# Query template database
python template_rag.py query_data --query "What are the contract terms?" --k 3

# Run interactive mode
python template_rag.py interactive
```

### 2. Setup RFP RAG
```bash
# Add RFP documents
python rfp_rag.py add_data --rfp_dir ../../example-PDF/Contracts --chunk_size 1200

# Query RFP database
python rfp_rag.py query_data --query "What are the technical requirements?" --k 5

# Query specific RFP
python rfp_rag.py query_data --query "security" --rfp_name "RFP-229-CYBER-SECURITY.pdf" --k 3

# Run interactive mode
python rfp_rag.py interactive
```

## Interactive Mode Commands

### Template RAG Interactive Commands
- `quit` or `exit` - Exit the program
- `info` - Show database information
- Any other text - Search query

### RFP RAG Interactive Commands
- `quit` or `exit` - Exit the program
- `info` - Show database information
- `list` - Show available RFP documents
- `search <rfp_name>` - Search specific RFP document
- Any other text - Search query

## Database Files

- Template RAG database: `template_rag.db` (default)
- RFP RAG database: `rfp_rag.db` (default)

These are Milvus vector databases that store the processed and vectorized document chunks.

## Example Script

Run the example script to see how both RAG systems work:

```bash
python rag_example.py
```

This script demonstrates the basic usage of both RAG systems with example queries.

## Troubleshooting

### Common Issues

1. **No PDF files found**: Make sure the directory contains PDF files
2. **Database not loaded**: Run `add_data` command first before querying
3. **Import errors**: Make sure you're running from the correct directory
4. **OpenAI API key**: Ensure `OPENAI_API_KEY` is set in your environment

### Error Messages

- `❌ Template directory not found` - Check the directory path
- `❌ No PDF files found` - Ensure PDF files exist in the directory
- `❌ No template database loaded` - Run add_data command first
- `❌ Error processing PDF` - Check if PDF files are corrupted or password-protected

## Advanced Usage

### Custom Chunk Sizes
For different document types, you may want to adjust chunk sizes:

```bash
# For technical documents (larger chunks)
python rfp_rag.py add_data --rfp_dir /path/to/docs --chunk_size 1500 --chunk_overlap 400

# For template documents (smaller chunks)
python template_rag.py add_data --template_dir /path/to/templates --chunk_size 800 --chunk_overlap 150
```

### Multiple Databases
You can create multiple databases for different purposes:

```bash
# Create separate databases
python template_rag.py add_data --template_dir /path/to/templates --db_name "security_templates.db"
python rfp_rag.py add_data --rfp_dir /path/to/rfp --db_name "cybersecurity_rfp.db"
```

## Integration

These RAG systems can be integrated into larger applications by importing the classes:

```python
from template_rag import TemplateRAG
from rfp_rag import RFPRAG

# Initialize RAG systems
template_rag = TemplateRAG("my_templates.db")
rfp_rag = RFPRAG("my_rfp.db")

# Add data
template_rag.add_data("/path/to/templates")
rfp_rag.add_data("/path/to/rfp")

# Query data
template_results = template_rag.query_data("query here")
rfp_results = rfp_rag.query_data("query here")
```
