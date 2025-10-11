# Teams Bot with LangGraph Server Integration

This bot integrates Microsoft Teams with a self-hosted LangGraph Server, providing AI-powered assistance with human-in-the-loop approvals for sensitive operations.

## Architecture

```
Teams Client → Bot Framework → LangGraph SDK → LangGraph Server → graph.py
```

Each Teams conversation is mapped to a persistent LangGraph thread, maintaining context across messages.

## Features

- **Persistent Conversations**: Each Teams conversation maps to a LangGraph thread
- **Human-in-the-Loop Approvals**: Sensitive operations require user approval
- **Multi-Agent System**: Access to document operations, RFP generation, and general assistance
- **Thread Management**: Automatic creation and persistence of conversation threads
- **Error Handling**: Robust error handling and logging

## Prerequisites

1. **LangGraph Server** running (from `main/` directory)
2. **Microsoft Teams Bot** registered with Azure Bot Service
3. **Python 3.11+** with virtual environment

## Setup

### 1. Install Dependencies

```bash
# From project root
python3 -m venv venv
source venv/bin/activate

# Install requirements
cd teams_2
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy template
cp .env.template .env

# Edit .env with your settings
nano .env
```

Required configuration:
- `MicrosoftAppId`: Your bot's App ID from Azure
- `MicrosoftAppPassword`: Your bot's password
- `LANGGRAPH_SERVER_URL`: URL of your LangGraph Server (default: http://localhost:8123)
- `ASSISTANT_ID`: Assistant/graph ID to use (default: agent)

### 3. Start LangGraph Server

```bash
# In a separate terminal, from project root
cd main
langgraph dev
```

The server should start on http://localhost:8123

### 4. Start Teams Bot

```bash
# From teams_2 directory
chmod +x start.sh
./start.sh
```

Or manually:
```bash
source venv/bin/activate
python app.py
```

The bot will listen on `http://0.0.0.0:3978`

## Testing

### Local Testing with Bot Framework Emulator

1. Download [Bot Framework Emulator](https://github.com/Microsoft/BotFramework-Emulator/releases)
2. Open the emulator
3. Connect to `http://localhost:3978/api/messages`
4. Leave App ID and Password empty for local testing (or use your credentials)

### Testing with Teams

1. Ensure your bot is registered in Azure Bot Service
2. Configure the messaging endpoint to point to your server
3. Add the bot to Teams
4. Start a conversation

## Usage Examples

### General Queries
```
User: What can you help me with?
Bot: I can help you with document operations, RFP generation, and answer questions...
```

### Document Operations (with approval)
```
User: Edit the executive summary in project.docx
Bot: 🔔 Approval Required
     Edit Operation
     - Location: [Executive Summary]
     - New text: ...
     
     Reply with /approve or /reject

User: /approve
Bot: ✅ Document updated successfully
```

### PDF Parsing
```
User: Parse the PDF files in the contracts folder
Bot: I'll parse the PDF files and create a searchable database...
```

## File Structure

```
teams_2/
├── app.py                    # Web server with aiohttp
├── bot.py                    # Bot logic with LangGraph integration
├── config.py                 # Configuration management
├── thread_manager.py         # Thread-to-conversation mapping
├── requirements.txt          # Python dependencies
├── .env.template            # Environment variables template
├── start.sh                 # Startup script
├── README.md                # This file
├── thread_mappings.json     # Runtime: Thread storage (created automatically)
└── teams_bot.log           # Runtime: Application logs
```

## How It Works

### Thread Mapping
Each Teams conversation ID is mapped to a LangGraph thread ID. This mapping is persisted in `thread_mappings.json` so conversations maintain context even after bot restarts.

### Message Flow
1. User sends message in Teams
2. Bot receives message via Bot Framework
3. Bot gets or creates LangGraph thread for conversation
4. Bot creates a run on the thread with user's message
5. LangGraph processes the message through the graph
6. Bot sends response back to Teams

### Approval Flow
When the graph requires approval (e.g., for document edits):
1. Run returns with status "interrupted"
2. Bot detects the interrupt and extracts approval details
3. Bot sends approval request to user with action buttons
4. User responds with /approve or /reject
5. Bot updates thread state and continues execution
6. Bot sends final result to user

## Endpoints

- `POST /api/messages` - Main Teams messaging endpoint
- `GET /health` - Health check and LangGraph connection status
- `GET /debug/threads` - View all thread mappings (for debugging)

## Troubleshooting

### Bot doesn't respond
- Check if LangGraph Server is running: `curl http://localhost:8123/ok`
- Check logs in `teams_bot.log`
- Verify Bot Framework credentials in `.env`

### "Cannot connect to LangGraph Server"
- Ensure LangGraph Server is started: `cd main && langgraph dev`
- Verify `LANGGRAPH_SERVER_URL` in `.env`
- Check firewall settings

### Approval flow not working
- Check logs for interrupt detection
- Verify graph is using `interrupt()` for approvals
- Ensure thread state updates are working

### Thread mappings lost
- Check if `thread_mappings.json` exists and is writable
- Verify file permissions
- Check for file corruption

## Development

### Adding New Features

To add new capabilities:
1. Modify the graph in `main/src/agent/graph.py`
2. Restart LangGraph Server
3. Bot will automatically use the updated graph

### Custom Approval Logic

To customize approval handling, modify `bot.py`:
- `_handle_interrupt()`: Detect and parse interrupts
- `_send_approval_request()`: Format approval messages
- `_handle_approval_response()`: Process user decisions

### Logging

Adjust log level in `.env`:
```
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR
```

Logs are written to both console and `teams_bot.log`.

## Production Deployment

1. **Deploy LangGraph Server** to a production environment
2. **Update environment variables** with production URLs
3. **Configure Azure Bot Service** with your production endpoint
4. **Use HTTPS** for production (Bot Framework requires HTTPS)
5. **Set up monitoring** for logs and health checks
6. **Implement rate limiting** if needed
7. **Back up thread mappings** regularly

## Security Considerations

- Never commit `.env` file with real credentials
- Use Azure Key Vault for production secrets
- Implement authentication for debug endpoints
- Regularly rotate bot passwords
- Monitor for unusual activity

## Support

For issues:
1. Check logs in `teams_bot.log`
2. Verify LangGraph Server is running and healthy
3. Test with Bot Framework Emulator
4. Review thread mappings with `/debug/threads`

## License

[Your License Here]

