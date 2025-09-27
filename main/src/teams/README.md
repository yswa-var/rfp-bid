# 🤖 RFP Teams Bot - AI-Powered Proposal Assistant

<img width="600" alt="RFP Teams Bot Demo" src="https://via.placeholder.com/600x200/4A90E2/FFFFFF?text=RFP+Teams+Bot" />

Microsoft Teams bot that generates professional RFP proposals using LangGraph multi-agent AI system with conversation memory and specialized team responses.

## 🚀 Quick Setup

```bash
# Clone and setup
git clone <repo-url>
cd rfp-bid/main/src/teams

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements-teams.txt
```

## 🔑 Environment Setup

Copy and configure your API keys:
```bash
cp .env.teams.example .env.teams
# Edit .env.teams with your OpenAI API key
```

Required in `.env.teams`:
```env
OPENAI_API_KEY=your_openai_api_key_here
MicrosoftAppId=your_bot_app_id
MicrosoftAppPassword=your_bot_password
```

## ▶️ Run the Bot From main folder

```bash
python app.py
```

Expected output:
```
🎯 RFP System successfully loaded with LangGraph workflow!
🚀 RFP Teams Bot initialized successfully
✅ Bot available at: http://localhost:3978
```

## 📱 How It Works

The bot uses a **multi-agent AI system** with specialized teams:

1. **Memory System** - Remembers client details across conversations
2. **Smart Router** - Routes queries to appropriate specialist teams
3. **LangGraph Agents** - Finance, Technical, Legal, QA teams collaborate
4. **Teams Integration** - Professional responses formatted for Microsoft Teams

## 🎯 Usage Examples

#### Store Project Info
```
Remember: Client is TechFlow Inc, budget is $400k, project is AI-powered document processing system
```

#### Generate Proposals
```
Generate proposal for AI document processing system
```

#### Get Specialized Help
```
Technical architecture for document processing
Budget breakdown for my project
Legal terms and compliance
Quality plan and testing
```

##  System Architecture

```
Teams Message → Memory Update → Query Router → LangGraph Agents → Response
```

**Core Files:**
- `app.py` - Main Flask application
- `bot.py` - Teams message handler
- `simple_rfp_agent.py` - Query routing and processing
- `rfp_bridge.py` - LangGraph integration
- `memory_management.py` - Conversation memory
- `data/memory.db` - SQLite database for context

##  Security

**Never commit API keys!**
```bash
# Verify .env.teams is in .gitignore
git status
```

##  Local Testing

```bash
# Test without Teams
python -c "
from simple_rfp_agent import SimpleRFPAgent
from memory_management import TeamsMemoryManager
print('✅ All systems working')
"
```

##  Troubleshooting

**Bot won't start?**
- Check Python 3.8+: `python --version`
- Check API key in `.env.teams`
- Install dependencies: `pip install -r requirements-teams.txt`

**LangGraph not working?**
- Verify `../agent/` directory exists
- Check: `python -c "import sys; sys.path.append('../agent'); import state, graph"`

**Memory issues?**
- Delete and recreate: `rm data/memory.db && python app.py`
