"""
RFP Teams App - Flask application for Microsoft Teams integration
"""
import os
import asyncio
from flask import Flask, request, Response
from botbuilder.core import (
    BotFrameworkAdapter,
    BotFrameworkAdapterSettings,
    TurnContext,
)
from botbuilder.schema import Activity
from dotenv import load_dotenv

# Load Teams environment
load_dotenv("src/teams/.env.teams")

from bot import RFPTeamsBot
from rfp_config import RFPTeamsConfig

# Create Flask app
app = Flask(__name__)
config = RFPTeamsConfig()

# Create adapter with bot credentials
SETTINGS = BotFrameworkAdapterSettings(
    app_id=config.BOT_APP_ID,
    app_password=config.BOT_APP_PASSWORD
)
ADAPTER = BotFrameworkAdapter(SETTINGS)

# Create the RFP bot
BOT = RFPTeamsBot()

# Error handler
async def on_error(context: TurnContext, error: Exception):
    print(f"❌ Error: {error}")
    await context.send_activity(
        "Sorry, I encountered an error processing your request. Please try again or type 'help' for assistance."
    )

ADAPTER.on_turn_error = on_error

@app.route("/api/messages", methods=["POST"])
def messages():
    """Handle incoming messages from Microsoft Teams"""
    if "application/json" in request.headers.get("Content-Type", ""):
        body = request.json
    else:
        return Response(status=415)

    activity = Activity().deserialize(body)
    auth_header = request.headers.get("Authorization", "")

    try:
        # Create new event loop for this request
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Process the activity asynchronously
        task = ADAPTER.process_activity(activity, auth_header, BOT.on_turn)
        loop.run_until_complete(task)
        
        return Response(status=200)
    except Exception as e:
        print(f"❌ Error processing activity: {e}")
        return Response(status=500)
    finally:
        loop.close()

@app.route("/", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return {
        "status": "RFP Teams Bot is running!",
        "bot_type": "RFP Proposal Assistant",
        "features": [
            "Proposal Generation",
            "Memory Management", 
            "Multi-Agent Teams",
            "RAG Integration"
        ]
    }

@app.route("/health", methods=["GET"])
def detailed_health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "app": "RFP Teams Bot",
        "version": "1.0.0",
        "rfp_system": "integrated",
        "memory": "enabled",
        "teams": "ready"
    }

if __name__ == "__main__":
    print("🚀 Starting RFP Teams Bot...")
    print("🎯 RFP Proposal Assistant with Memory")
    print("📱 Teams integration active")
    print("🧠 Memory system enabled")
    print("🤖 Multi-agent RFP system integrated")
    print("")
    print("✅ Bot available at: http://localhost:3978")
    print("🔗 Health check: http://localhost:3978/health")
    print("")
    
    app.run(host="localhost", port=3978, debug=True)