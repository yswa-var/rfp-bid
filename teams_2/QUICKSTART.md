# Quick Start Guide - Teams + LangGraph Integration

Get your Teams bot up and running in 5 minutes!

## Prerequisites Checklist

- [ ] Python 3.11+ installed
- [ ] Virtual environment created
- [ ] Microsoft Teams Bot registered (for production) OR Bot Framework Emulator (for testing)

## Step 1: Install Dependencies

```bash
# Navigate to project root
cd /Users/yash/Documents/rfp/rfp-bid

# Create/activate virtual environment (if not already done)
python3 -m venv venv
source venv/bin/activate

# Install Teams bot dependencies
cd teams_2
pip install -r requirements.txt

# Install main project dependencies (for LangGraph Server)
cd ../main
pip install -r requirements.txt
```

## Step 2: Configure Environment

```bash
cd ../teams_2

# Copy environment template
cp .env.template .env

# Edit configuration
nano .env
```

**Minimum configuration for local testing:**
```bash
# Leave these empty for Bot Framework Emulator testing
MicrosoftAppId=
MicrosoftAppPassword=

# LangGraph Server (default is fine)
LANGGRAPH_SERVER_URL=http://localhost:8123
ASSISTANT_ID=agent
```

**For Teams production, add your bot credentials:**
```bash
MicrosoftAppId=your-app-id-from-azure
MicrosoftAppPassword=your-app-password-from-azure
MicrosoftAppType=MultiTenant
```

## Step 3: Start LangGraph Server

Open a **new terminal window**:

```bash
cd /Users/yash/Documents/rfp/rfp-bid/main
source ../venv/bin/activate

# Start LangGraph Server
langgraph dev
```

**Expected output:**
```
INFO:     Started server process
INFO:     Waiting for application startup
INFO:     Application startup complete
INFO:     LangGraph server running on http://localhost:8123
```

**Verify it's running:**
```bash
curl http://localhost:8123/ok
# Should return: {"ok":true}
```

## Step 4: Start Teams Bot

Open **another terminal window**:

```bash
cd /Users/yash/Documents/rfp/rfp-bid/teams_2
source ../venv/bin/activate

# Start the bot
./start.sh
```

**Expected output:**
```
Starting Teams Bot with LangGraph integration...
Activating virtual environment...
Checking LangGraph Server connection...
Starting Teams Bot server...
Server will listen on 0.0.0.0:3978
```

## Step 5: Test with Bot Framework Emulator

### Download Emulator (if you don't have it)
- Download from: https://github.com/Microsoft/BotFramework-Emulator/releases
- Install and open it

### Connect to Your Bot
1. Click "Open Bot"
2. Enter Bot URL: `http://localhost:3978/api/messages`
3. Leave App ID and Password empty (for local testing)
4. Click "Connect"

### Test Messages

**Basic conversation:**
```
You: Hello
Bot: 👋 Hello! I'm your LangGraph AI Assistant...
```

**Document query:**
```
You: What documents do you have access to?
Bot: I can help you with document operations...
```

**Approval flow (advanced):**
```
You: Edit the master.docx file and change the title to "New Title"
Bot: 🔔 Approval Required
     Edit Operation
     - Location: [Title]
     - New text: New Title
     
     Reply with /approve or /reject

You: /approve
Bot: ✅ Document updated successfully
```

## Step 6: Connect to Teams (Production)

### Prerequisites
1. Bot registered in Azure Bot Service
2. Bot credentials in your `.env` file
3. Server accessible via HTTPS (use ngrok for testing)

### Using ngrok for Testing
```bash
# In a new terminal
ngrok http 3978
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`) and:
1. Go to Azure Bot Service
2. Update Messaging endpoint to: `https://abc123.ngrok.io/api/messages`
3. Save changes
4. Add bot to Teams and start chatting!

## Troubleshooting

### "Cannot connect to LangGraph Server"
```bash
# Check if server is running
curl http://localhost:8123/ok

# If not, start it:
cd main
langgraph dev
```

### "Module not found" errors
```bash
# Ensure dependencies are installed
cd teams_2
pip install -r requirements.txt

cd ../main
pip install -r requirements.txt
```

### Bot doesn't respond in Emulator
1. Check both terminal windows for errors
2. Verify bot is listening: `curl http://localhost:3978/health`
3. Check firewall settings
4. Restart bot and try again

### "Run timed out" errors
Increase timeout in `.env`:
```bash
RUN_TIMEOUT=300  # 5 minutes
```

## What's Next?

Now that your bot is running:

1. **Read the full documentation**: `README.md`
2. **Learn about LangGraph Server**: `LANGGRAPH_SERVER_SETUP.md`
3. **Customize the graph**: Edit `main/src/agent/graph.py`
4. **Add new agents**: Extend the supervisor system
5. **Deploy to production**: See deployment guides

## Architecture Overview

```
┌─────────────┐
│ Teams Client│
└──────┬──────┘
       │ (User messages)
       ▼
┌──────────────────┐
│ Bot Framework    │
│ (teams_2/app.py) │
└──────┬───────────┘
       │ (LangGraph SDK)
       ▼
┌──────────────────┐
│ LangGraph Server │
│ (localhost:8123) │
└──────┬───────────┘
       │ (Graph execution)
       ▼
┌──────────────────┐
│ Supervisor Graph │
│ (graph.py)       │
└──────────────────┘
       │
       ├─► PDF Parser
       ├─► General Assistant
       ├─► DOCX Agent (with approvals)
       ├─► RFP Team
       └─► Image Adder
```

## Key Features

✅ **Persistent Conversations**: Each Teams chat maintains context  
✅ **Human-in-the-Loop**: Approvals for sensitive operations  
✅ **Multi-Agent System**: Access to multiple specialized agents  
✅ **Thread Management**: Automatic conversation tracking  
✅ **Error Handling**: Robust error recovery

## Support

- **Logs**: Check `teams_2/teams_bot.log`
- **Debug endpoint**: `http://localhost:3978/debug/threads`
- **Health check**: `http://localhost:3978/health`

## Common Commands

```bash
# Start LangGraph Server
cd main && langgraph dev

# Start Teams Bot
cd teams_2 && ./start.sh

# Check health
curl http://localhost:3978/health
curl http://localhost:8123/ok

# View thread mappings
curl http://localhost:3978/debug/threads

# Stop services
# Press Ctrl+C in each terminal window
```

Happy chatting! 🤖

