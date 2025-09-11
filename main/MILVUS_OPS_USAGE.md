# MilvusOps Usage Guide

This guide explains how to use the `MilvusOps` helper functions for PDF processing and Milvus database operations.

## Features

- **PDF Parsing**: Extract text and metadata from PDF files using PyMuPDF
- **Text Chunking**: Split documents into manageable chunks for better vectorization
- **Vectorization**: Create embeddings and store them in Milvus database
- **Similarity Search**: Query the database and get top-k results with accuracy scores
- **Database Management**: Create and manage Milvus databases with custom names

## Installation

First, install the required dependencies:

```bash
pip install -r requirements.txt
```

Make sure you have the following environment variables set:

```bash
OPENAI_API_KEY=your_openai_api_key_here
```

## Quick Start

### Method 1: Using Convenience Functions

```python
from agent.milvus_ops import setup_milvus_from_pdf, query_milvus_db

# Setup database from PDF
milvus_ops = setup_milvus_from_pdf("path/to/your/document.pdf", "session.db")

# Query the database
results = query_milvus_db(milvus_ops, "What is the main topic?", k=3)

# Print results
for result in results:
    print(f"Rank {result['rank']}: Accuracy {result['accuracy']}")
    print(f"Source: {result['source_file']}, Page {result['page']}")
    print(f"Preview: {result['preview']}")
    print("-" * 50)
```

### Method 2: Using MilvusOps Class Directly

```python
from agent.milvus_ops import MilvusOps

# Initialize MilvusOps
milvus_ops = MilvusOps("session.db")

# Parse PDF
documents = milvus_ops.parse_pdf("path/to/your/document.pdf")

# Create chunks
chunks = milvus_ops.create_chunks(documents, chunk_size=1000, chunk_overlap=200)

# Vectorize and store
vector_store = milvus_ops.vectorize_and_store(chunks)

# Query database
results = milvus_ops.query_database("What is the document about?", k=3)
```

## API Reference

### MilvusOps Class

#### `__init__(db_name: str = "session.db")`
Initialize MilvusOps with a database name.

#### `parse_pdf(pdf_path: str) -> List[Document]`
Parse a PDF file and extract text with metadata.

**Parameters:**
- `pdf_path`: Path to the PDF file

**Returns:**
- List of Document objects with text content and metadata

#### `create_chunks(documents: List[Document], chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Document]`
Split documents into chunks for better vectorization.

**Parameters:**
- `documents`: List of Document objects
- `chunk_size`: Size of each chunk in characters (default: 1000)
- `chunk_overlap`: Overlap between chunks in characters (default: 200)

**Returns:**
- List of chunked Document objects

#### `vectorize_and_store(chunks: List[Document]) -> Milvus`
Vectorize chunks and store them in Milvus database.

**Parameters:**
- `chunks`: List of Document chunks to vectorize and store

**Returns:**
- Milvus vector store instance

#### `setup_milvus_db(pdf_path: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> Milvus`
Complete pipeline: parse PDF, create chunks, vectorize and store in Milvus.

**Parameters:**
- `pdf_path`: Path to the PDF file
- `chunk_size`: Size of each chunk in characters (default: 1000)
- `chunk_overlap`: Overlap between chunks in characters (default: 200)

**Returns:**
- Milvus vector store instance

#### `query_database(query: str, k: int = 3) -> List[Dict[str, Any]]`
Query the Milvus database and return top k matching results with accuracies.

**Parameters:**
- `query`: Search query string
- `k`: Number of top results to return (default: 3)

**Returns:**
- List of dictionaries containing results with content, metadata, and accuracy scores

Each result dictionary contains:
- `rank`: Rank of the result (1-based)
- `content`: Full text content of the matching chunk
- `metadata`: Metadata associated with the chunk
- `accuracy`: Similarity score (0-1, higher is better)
- `distance`: L2 distance score (lower is better)
- `source_file`: Name of the source PDF file
- `page`: Page number where the content was found
- `preview`: Short preview of the content (first 200 characters)

#### `get_database_info() -> Dict[str, Any]`
Get information about the current database.

**Returns:**
- Dictionary containing database information

### Convenience Functions

#### `setup_milvus_from_pdf(pdf_path: str, db_name: str = "session.db") -> MilvusOps`
Convenience function to setup Milvus database from PDF file.

#### `query_milvus_db(milvus_ops: MilvusOps, query: str, k: int = 3) -> List[Dict[str, Any]]`
Convenience function to query Milvus database.

## Example Usage

### Basic PDF Processing

```python
from agent.milvus_ops import MilvusOps

# Initialize
milvus_ops = MilvusOps("my_documents.db")

# Process PDF
vector_store = milvus_ops.setup_milvus_db("document.pdf")

# Query
results = milvus_ops.query_database("What are the key findings?", k=5)

# Process results
for result in results:
    print(f"Accuracy: {result['accuracy']:.3f}")
    print(f"Source: {result['source_file']}, Page {result['page']}")
    print(f"Content: {result['content'][:300]}...")
    print()
```

### Custom Chunking Parameters

```python
# Use smaller chunks for more precise matching
milvus_ops = MilvusOps("precise_search.db")
vector_store = milvus_ops.setup_milvus_db(
    "document.pdf", 
    chunk_size=500, 
    chunk_overlap=100
)
```

### Multiple Queries

```python
queries = [
    "What is the main topic?",
    "What are the key findings?",
    "What methodology was used?",
    "What are the conclusions?"
]

for query in queries:
    results = milvus_ops.query_database(query, k=2)
    print(f"\nQuery: {query}")
    for result in results:
        print(f"  {result['accuracy']:.3f}: {result['preview']}")
```

## Testing

Run the test script to verify everything works:

```bash
python test_milvus_ops.py
```

## Notes

- The database file is created in the current working directory
- If a database with the same name exists, it will be replaced
- Accuracy scores are normalized similarity scores (0-1 range)
- Distance scores are L2 distances (lower is better)
- The system uses OpenAI's `text-embedding-3-large` model for embeddings
- Milvus uses FLAT index with L2 metric for similarity search

## Troubleshooting

### Common Issues

1. **"OPENAI_API_KEY environment variable is required"**
   - Make sure you have set the `OPENAI_API_KEY` environment variable
   - Check your `.env` file or export the variable in your shell

2. **"PDF file not found"**
   - Verify the PDF file path is correct
   - Use absolute paths if relative paths don't work

3. **"No vector store available"**
   - Make sure you have called `setup_milvus_db()` or `vectorize_and_store()` before querying

4. **Import errors for PyMuPDF**
   - Install PyMuPDF: `pip install PyMuPDF`
   - Make sure you're using the correct Python environment

### Performance Tips

- Use appropriate chunk sizes (500-1500 characters work well)
- Adjust chunk overlap based on your content (100-300 characters)
- For large documents, consider processing in batches
- Use specific queries rather than very general ones for better results
