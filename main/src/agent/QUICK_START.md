# Quick Start Guide for RAG Scripts

## Prerequisites

1. **Install Dependencies**
   ```bash
   cd /Users/yash/Documents/rfp/rfp-bid/main
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**
   ```bash
   export OPENAI_API_KEY="your-openai-api-key-here"
   ```

## Quick Usage

### 1. Template RAG

```bash
# Navigate to the agent directory
cd /Users/yash/Documents/rfp/rfp-bid/main/src/agent

# Add template documents
python3 template_rag.py add_data --template_dir ../../example-PDF/Contracts

# Query template database
python3 template_rag.py query_data --query "What are the security requirements?" --k 5

# Interactive mode
python3 template_rag.py interactive
```

### 2. RFP RAG

```bash
# Add RFP documents
python3 rfp_rag.py add_data --rfp_dir ../../example-PDF/Contracts

# Query RFP database
python3 rfp_rag.py query_data --query "What are the technical specifications?" --k 5

# Query specific RFP
python3 rfp_rag.py query_data --query "security" --rfp_name "RFP-229-CYBER-SECURITY.pdf" --k 3

# Interactive mode
python3 rfp_rag.py interactive
```

### 3. Run Examples

```bash
# Run example script
python3 rag_example.py

# Run tests
python3 test_rag_scripts.py
```

## Available Commands

### Template RAG Commands
- `add_data` - Add template documents to database
- `query_data` - Query template database
- `interactive` - Interactive query mode

### RFP RAG Commands
- `add_data` - Add RFP documents to database
- `query_data` - Query RFP database
- `interactive` - Interactive query mode

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--db_name` | Database name | template_rag.db / rfp_rag.db |
| `--chunk_size` | Chunk size in characters | 1000 (templates) / 1200 (RFP) |
| `--chunk_overlap` | Chunk overlap in characters | 200 (templates) / 300 (RFP) |
| `--k` | Number of results to return | 5 |
| `--template_dir` | Template directory path | Required for add_data |
| `--rfp_dir` | RFP directory path | Required for add_data |
| `--query` | Query string | Required for query_data |
| `--rfp_name` | Specific RFP name | Optional for query_data |

## Example Workflows

### 1. Setup Template RAG for Contract Templates
```bash
# Add contract templates
python3 template_rag.py add_data --template_dir /path/to/contracts --chunk_size 1000

# Query for specific terms
python3 template_rag.py query_data --query "payment terms" --k 3

# Interactive mode for exploration
python3 template_rag.py interactive
```

### 2. Setup RFP RAG for RFP Analysis
```bash
# Add RFP documents
python3 rfp_rag.py add_data --rfp_dir /path/to/rfp --chunk_size 1200

# Query for requirements
python3 rfp_rag.py query_data --query "technical requirements" --k 5

# Query specific RFP
python3 rfp_rag.py query_data --query "budget" --rfp_name "RFP-2024-001.pdf" --k 3

# Interactive mode
python3 rfp_rag.py interactive
```

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError**: Install dependencies with `pip install -r requirements.txt`
2. **No PDF files found**: Check directory path and ensure PDF files exist
3. **Database not loaded**: Run `add_data` command first
4. **OpenAI API key error**: Set `OPENAI_API_KEY` environment variable

### Getting Help

- Check the full documentation in `RAG_README.md`
- Run `python3 template_rag.py --help` or `python3 rfp_rag.py --help`
- Use interactive mode to explore the databases

## Next Steps

1. **Customize chunk sizes** for your document types
2. **Create multiple databases** for different document categories
3. **Integrate with your applications** using the Python classes
4. **Set up automated workflows** for document processing
