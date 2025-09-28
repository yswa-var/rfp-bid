# RFP-Bid LangGraph Agent System

## 🚀 Quick Start with `langgraph dev`

### Prerequisites
- Python 3.8+
- Git
- OpenAI API Key

### One-Command Setup
```bash
# Clone and navigate to the project
git clone <repository-url>
cd rfp-bid/main

# Run the automated setup
python setup_dev.py

# Start the development server
langgraph dev
```

### Access LangGraph Studio
- **Local**: http://localhost:8123
- **Remote**: Use `--tunnel` flag for public access

## 🏗️ Architecture

### Project Structure
```
rfp-bid/
├── main/                           # LangGraph main directory
│   ├── src/agent/                  # Agent implementations
│   │   ├── agents.py              # All agent classes
│   │   ├── graph.py               # Main workflow graph
│   │   ├── router.py              # Request routing logic
│   │   └── state.py               # State management
│   ├── langgraph.json             # LangGraph configuration
│   ├── setup_dev.py               # Automated setup script
│   ├── Dockerfile                 # Container configuration
│   └── requirements.txt           # Python dependencies
└── Mcp_client_word/               # RAG Editor components
    ├── launch_rag_editor.py       # Editor launcher
    └── ai_dynamic_editor_with_rag.py
```

### Agent System
The system uses a **supervisor pattern** with specialized worker agents:

1. **Supervisor Agent**: Routes requests to appropriate workers
2. **PDF Parser Agent**: Processes and indexes PDF documents
3. **Multi-RAG Setup Agent**: Manages template and example databases
4. **Proposal Supervisor Agent**: Generates hierarchical proposals
5. **RAG Editor Agent**: Launches AI-powered document editor
6. **General Assistant Agent**: Handles queries and document search

## 🔧 Configuration

### Environment Variables
Create `.env` file in `main/` directory:
```bash
OPENAI_API_KEY=your_api_key_here
LLM_MODEL=gpt-4o-mini
```

### LangGraph Configuration (`langgraph.json`)
```json
{
  "dependencies": ["."],
  "graphs": {
    "agent": "./src/agent/graph.py:graph"
  },
  "env": ".env",
  "image_distro": "wolfi",
  "python_version": "3.11",
  "dockerfile": "Dockerfile",
  "docker_compose": "docker-compose.yml"
}
```

## 🎯 Agent Usage

### RAG Editor Agent
**Trigger phrases**: `launch editor`, `rag editor`, `ai editor`, `document editor`

**Features**:
- Dynamic path resolution (works on any device)
- Automatic environment setup
- Process management with status reporting
- Integration with RAG databases
- Error handling with clear messages

**Example usage**:
```
User: "launch rag editor"
System: ✅ Successfully launched AI Dynamic Editor with RAG Integration!
```

### Other Agents
- **PDF Parser**: `"parse PDFs"` or provide PDF file paths
- **Multi-RAG Setup**: `"setup multi-rag"` or `"setup databases"`
- **Proposal Supervisor**: `"generate proposal"` or `"create proposal"`
- **General Assistant**: Default for queries and document search

## 🐳 Docker Support

### Local Development
```bash
# Build the container
docker build -t rfp-bid .

# Run with port mapping
docker run -p 8080:8080 rfp-bid
```

### Docker Compose
```bash
# Start with docker-compose
docker-compose up -d
```

## 🌐 Deployment Options

### 1. Local Development
```bash
cd main
python setup_dev.py
langgraph dev
```

### 2. Production Server
```bash
cd main
langgraph dev --host 0.0.0.0 --port 8080
```

### 3. Cloud Deployment
- **LangGraph Cloud**: Deploy directly to LangGraph's managed service
- **Docker**: Use provided Dockerfile for containerized deployment
- **Kubernetes**: Scale with K8s using the container image

## 🔍 Troubleshooting

### Common Issues

#### 1. Mcp_client_word Not Found
```bash
# Ensure directory structure is correct
ls -la ../Mcp_client_word/
```

#### 2. Import Errors
```bash
# Reinstall dependencies
python setup_dev.py
```

#### 3. Environment Issues
```bash
# Check .env file
cat .env
# Verify API key is set
echo $OPENAI_API_KEY
```

#### 4. RAG Database Errors
- The system includes fallback mechanisms
- Databases will auto-initialize on first use
- Check logs for specific error messages

### Debug Mode
```bash
# Enable verbose logging
langgraph dev --server-log-level DEBUG

# Enable remote debugging
langgraph dev --debug-port 5678
```

## 📊 Monitoring

### Health Checks
- **Graph Status**: Check available nodes in LangGraph Studio
- **Agent Status**: Monitor agent responses and routing
- **RAG Status**: Verify database connections and content

### Logs
- **Server Logs**: Available in terminal output
- **Agent Logs**: Embedded in agent responses
- **Error Logs**: Detailed error messages with context

## 🔄 Updates and Maintenance

### Adding New Agents
1. Create agent class in `src/agent/agents.py`
2. Add to graph in `src/agent/graph.py`
3. Update routing in `src/agent/router.py`
4. Test with `python setup_dev.py`

### Updating Dependencies
```bash
# Update requirements.txt
pip freeze > requirements.txt

# Reinstall
python setup_dev.py
```

## 🚀 Performance Optimization

### Scaling
- **Horizontal**: Multiple server instances
- **Vertical**: Increase worker processes with `--n-jobs-per-worker`
- **Caching**: RAG databases provide built-in caching

### Resource Management
- **Memory**: Monitor RAG database sizes
- **CPU**: Adjust worker processes based on load
- **Storage**: Clean up temporary files regularly

## 📚 API Reference

### Graph Endpoints
- **POST** `/runs`: Execute graph workflows
- **GET** `/runs/{run_id}`: Get run status
- **POST** `/runs/{run_id}/stream`: Stream run results

### Agent Communication
All agents communicate through the shared state system using LangChain messages.

## 🤝 Contributing

### Development Workflow
1. Fork the repository
2. Create feature branch
3. Make changes
4. Test with `python setup_dev.py`
5. Submit pull request

### Testing
```bash
# Run tests
python -m pytest tests/

# Test specific agent
python -c "from src.agent.agents import RAGEditorAgent; print('✅ Agent imported')"
```

---

**Ready to deploy?** Run `python setup_dev.py` and then `langgraph dev` to get started!
