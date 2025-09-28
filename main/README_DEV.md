# RFP-Bid LangGraph Development Setup

## Quick Start

### 1. Prerequisites
- Python 3.8+
- Git

### 2. Setup
```bash
# Navigate to the main directory
cd main

# Run the setup script
python setup_dev.py

# Start the development server
langgraph dev
```

### 3. Access LangGraph Studio
- Open your browser to: http://localhost:8123
- Test the RAG editor agent with: `launch rag editor`

## Project Structure
```
rfp-bid/
├── main/                    # LangGraph main directory
│   ├── src/agent/          # Agent implementations
│   ├── langgraph.json      # LangGraph configuration
│   ├── setup_dev.py        # Development setup script
│   └── requirements.txt    # Python dependencies
└── Mcp_client_word/        # RAG Editor components
    ├── launch_rag_editor.py
    └── ai_dynamic_editor_with_rag.py
```

## Available Agents

### RAG Editor Agent
- **Trigger phrases**: `launch editor`, `rag editor`, `ai editor`, `document editor`
- **Function**: Launches the AI Dynamic Editor with RAG integration
- **Features**: 
  - Dynamic path resolution
  - Environment setup
  - Process management
  - Error handling

### Other Agents
- **PDF Parser**: Parse and index PDF documents
- **Multi-RAG Setup**: Set up template and example databases
- **Proposal Supervisor**: Generate hierarchical proposals
- **General Assistant**: Query documents and provide answers

## Environment Variables
Create a `.env` file in the `main` directory:
```
OPENAI_API_KEY=your_api_key_here
LLM_MODEL=gpt-4o-mini
```

## Docker Support
```bash
# Build and run with Docker
docker build -t rfp-bid .
docker run -p 8080:8080 rfp-bid
```

## Troubleshooting

### Common Issues
1. **Mcp_client_word not found**: Ensure the directory exists in the project root
2. **Import errors**: Run `python setup_dev.py` to install dependencies
3. **Environment issues**: Check your `.env` file and API keys

### Development Tips
- Use `langgraph dev --verbose` for detailed logging
- Check the terminal output for RAG database status
- The RAG editor runs in a separate process for better isolation
