# Speed Up Guide for LangGraph System

## Current Issue
The LangGraph server is running with only **1 worker** (`available=1 max=1`), which bottlenecks performance.

## Quick Solutions

### Option 1: Use Backend with Multiple Workers ⚡

The FastAPI backend supports multiple workers via Gunicorn:

```bash
cd backend
# Make DEBUG=false in .env file
echo "DEBUG=false" > .env
./start.sh
```

This provides:
- **4 backend workers** for concurrent request handling
- Bypasses single-worker limitation of `langgraph dev`
- Works with local graph execution or remote LangGraph server

### Option 2: Use Local Execution (Bypass Server)

If you're running `langgraph dev`, you can use local execution to bypass the server bottleneck entirely:

1. Set environment variable to use local graph:
```bash
export USE_LOCAL_GRAPH=true
```

2. Your backend will fall back to local graph execution, which runs the graph directly without the server overhead.

### Option 3: Increase Backend Workers

Your backend can also run with multiple workers:

```bash
cd backend
# In .env, set DEBUG=false
echo "DEBUG=false" >> .env

# Then start with multiple workers
./start.sh
```

This starts the FastAPI backend with 4 workers.

## Performance Comparison

| Mode | Workers | Performance | Use Case |
|------|---------|-------------|----------|
| `langgraph dev` | 1 | Slowest | Development/Testing |
| Backend (Gunicorn) | 4 | Fast | Production (handles concurrency) |
| Local execution + backend | N/A | Fastest | Development/Bypass |

## Recommended Setup

For best performance during development:

```bash
# Terminal 1: LangGraph Server (Development mode - single worker OK)
cd main
langgraph dev

# Terminal 2: Backend with Multiple Workers (THIS speeds things up!)
cd backend
# Set DEBUG=false in .env
echo "DEBUG=false" >> .env
./start.sh

# Terminal 3: Frontend (if needed)
cd frontend
npm run dev
```

**Note**: The backend with 4 workers will handle concurrent requests even if LangGraph dev is single-threaded. Each worker maintains its own connection to LangGraph.

## Additional Speed Optimization Tips

1. **Use faster models**: Change from `gpt-5` (doesn't exist) to `gpt-4o-mini` for faster responses
2. **Reduce temperature**: Lower temperature values = faster responses
3. **Enable caching**: Set `LANGCHAIN_CACHE_DIR=.cache` to cache LLM responses
4. **Batch requests**: Group multiple operations together when possible

## Model Configuration

Currently using:
- Supervisor: `gpt-5` (⚠️ doesn't exist - should be `gpt-4o` or `gpt-4-turbo`)
- React Agent: `gpt-4o-mini` ✅
- Image Adder: `gpt-4o-mini` ✅

To change models, edit `main/src/agent/graph.py` line 34 and other agent files.

