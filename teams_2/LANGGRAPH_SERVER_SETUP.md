# LangGraph Server Setup Guide

This document explains how to start and configure the LangGraph Server for use with the Teams bot.

## Prerequisites

- Python 3.11 or higher
- LangGraph CLI installed
- Project dependencies installed

## Installation

### Install LangGraph CLI

```bash
pip install langgraph-cli
```

Or if using pipx (recommended):
```bash
pipx install langgraph-cli
```

### Install Project Dependencies

```bash
cd main
pip install -r requirements.txt
```

## Configuration

The LangGraph Server is configured via `main/langgraph.json`:

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

Key configuration:
- **Graph**: `agent` points to the supervisor system in `./src/agent/graph.py:graph`
- **Dependencies**: Installs from current directory
- **Environment**: Loads from `.env` file

## Starting the Server

### Development Mode (Recommended for Testing)

```bash
cd main
langgraph dev
```

This starts the server with:
- Hot reload on code changes
- Default port: 8123
- Development-friendly logging
- Local file-based persistence

The server will be available at `http://localhost:8123`

### Production Mode

For production deployments:

```bash
cd main
langgraph up
```

Or with Docker:

```bash
cd main
docker-compose up
```

## Verifying the Server

### Check Health

```bash
curl http://localhost:8123/ok
```

Expected response:
```json
{"ok": true}
```

### List Assistants

```bash
curl http://localhost:8123/assistants/search -X POST \
  -H "Content-Type: application/json" \
  -d '{}'
```

You should see the `agent` assistant in the response.

### Get Graph Schema

```bash
curl http://localhost:8123/assistants/agent/graph
```

This returns the structure of your graph.

## Server Endpoints

The LangGraph Server exposes several REST endpoints:

### Core Endpoints
- `GET /ok` - Health check
- `GET /info` - Server information

### Assistants
- `POST /assistants/search` - List assistants
- `GET /assistants/{assistant_id}` - Get assistant details
- `GET /assistants/{assistant_id}/graph` - Get graph structure

### Threads
- `POST /threads` - Create thread
- `GET /threads/{thread_id}` - Get thread
- `GET /threads/{thread_id}/state` - Get thread state
- `POST /threads/{thread_id}/state` - Update thread state

### Runs
- `POST /threads/{thread_id}/runs/wait` - Create run and wait for completion
- `POST /threads/{thread_id}/runs/stream` - Create run with streaming
- `GET /threads/{thread_id}/runs/{run_id}` - Get run status

## Using with Teams Bot

The Teams bot (`teams_2/`) connects to this server via the LangGraph SDK.

Configuration in `teams_2/.env`:
```
LANGGRAPH_SERVER_URL=http://localhost:8123
ASSISTANT_ID=agent
```

## Troubleshooting

### Server won't start

**Error: Port already in use**
```bash
# Find process using port 8123
lsof -i :8123

# Kill the process
kill -9 <PID>
```

**Error: Module not found**
```bash
# Ensure you're in the main directory
cd main

# Verify dependencies are installed
pip install -r requirements.txt
```

**Error: Graph not found**
```bash
# Verify the graph can be imported
cd main
python -c "from src.agent.graph import graph; print(graph)"
```

### Server starts but bot can't connect

Check the URL:
```bash
# Test from same machine as bot
curl http://localhost:8123/ok

# If bot is on different machine, use server's IP
curl http://<server-ip>:8123/ok
```

### Graph errors during execution

Check server logs:
```bash
# Logs are printed to console when using langgraph dev
# Look for error messages and stack traces
```

Common issues:
- Missing environment variables in `main/.env`
- Missing API keys (OpenAI, etc.)
- File permissions for document operations

## Environment Variables

The graph requires certain environment variables. Create `main/.env`:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your-api-key-here

# Optional: Other LLM providers
ANTHROPIC_API_KEY=
LANGCHAIN_API_KEY=

# Document paths (if needed)
DOC_AGENT_DOCUMENT_DIRS=/path/to/docs

# Default document name
DEFAULT_DOCX_NAME=master.docx
```

## Development Workflow

1. **Start LangGraph Server**:
   ```bash
   cd main
   langgraph dev
   ```

2. **In another terminal, start Teams Bot**:
   ```bash
   cd teams_2
   ./start.sh
   ```

3. **Make changes to graph**:
   - Edit files in `main/src/agent/`
   - Server will automatically reload (with `langgraph dev`)

4. **Test changes**:
   - Send messages through Teams or Bot Framework Emulator
   - Check logs in both terminals

## Server Logs

When running `langgraph dev`, you'll see:
- Incoming requests
- Graph execution steps
- Node transitions
- Tool calls
- Errors and warnings

Example log output:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     POST /threads/123/runs/wait
INFO:     Executing graph...
INFO:     Node: supervisor
INFO:     Node: docx_agent
INFO:     Run completed successfully
```

## Performance Tuning

### Adjust Timeout

If operations take longer than expected, increase timeout in `teams_2/.env`:
```
RUN_TIMEOUT=300  # 5 minutes
```

### Enable Caching

For faster responses, configure caching in `main/.env`:
```
LANGCHAIN_CACHE_DIR=.cache
```

### Scale Workers

For production, increase worker processes:
```bash
langgraph up --workers 4
```

## Security

### Production Checklist

- [ ] Use HTTPS for server endpoint
- [ ] Implement authentication (API keys)
- [ ] Set up firewall rules
- [ ] Enable rate limiting
- [ ] Configure CORS appropriately
- [ ] Use secrets management (not `.env` files)
- [ ] Enable audit logging
- [ ] Regular security updates

### Authentication

For production, add authentication to LangGraph Server:

```python
# In main/langgraph.json, add:
{
  "auth": {
    "type": "api_key",
    "header": "X-API-Key"
  }
}
```

Then configure in Teams bot:
```python
# In teams_2/bot.py
self.langgraph_client = get_client(
    url=config.LANGGRAPH_SERVER_URL,
    api_key=config.LANGGRAPH_API_KEY
)
```

## Monitoring

### Health Checks

Set up automated health checks:
```bash
# Add to cron or monitoring service
*/5 * * * * curl -f http://localhost:8123/ok || alert-admin
```

### Metrics

LangGraph Server exposes metrics:
```bash
curl http://localhost:8123/metrics
```

### Logging

Configure structured logging in production:
```python
# Add to main/.env
LOG_LEVEL=INFO
LOG_FORMAT=json
```

## Backup and Recovery

### Thread Data

Thread state is persisted. Back up the database:
```bash
# If using SQLite (default for dev)
cp main/.langgraph/db.sqlite main/.langgraph/db.sqlite.backup

# If using PostgreSQL (production)
pg_dump langgraph > backup.sql
```

### Configuration

Keep backups of:
- `main/langgraph.json`
- `main/.env`
- `main/requirements.txt`

## Updating

To update LangGraph Server:

```bash
# Update CLI
pip install --upgrade langgraph-cli

# Update SDK
pip install --upgrade langgraph-sdk

# Restart server
cd main
langgraph dev
```

## Getting Help

- **LangGraph Documentation**: https://langchain-ai.github.io/langgraph/
- **LangGraph Server API**: https://langchain-ai.github.io/langgraph/cloud/reference/api/
- **LangGraph SDK Reference**: https://langchain-ai.github.io/langgraph/cloud/reference/sdk/python_sdk_ref/

## Next Steps

Once the server is running:
1. Test with `curl` commands above
2. Start the Teams bot (`teams_2/start.sh`)
3. Send test messages through Teams or Bot Emulator
4. Monitor logs for any issues
5. Adjust configuration as needed

