#!/usr/bin/env python3
"""
Seamless WhatsApp-RAG Bridge Setup
Keeps your existing RAG system separate and only connects WhatsApp when needed.
"""

import os
import sys
import subprocess
import shutil
import json
from pathlib import Path

class WhatsAppRAGSetup:
    def __init__(self):
        self.base_dir = Path("/home/arun/Pictures/rfp-bid")
        self.main_dir = self.base_dir / "main"
        self.whatsapp_dir = Path.cwd()  # Current directory (whatsapp-integration)
        self.env_file = self.whatsapp_dir / ".env"
        
    def check_requirements(self):
        """Check if all requirements are met"""
        print("🔍 Checking requirements...")
        
        # Check if conda environment exists
        result = subprocess.run(['conda', 'info', '--envs'], 
                              capture_output=True, text=True)
        if 'rfp-agent' not in result.stdout:
            print("❌ Conda environment 'rfp-agent' not found")
            return False
            
        # Check if main RAG system exists
        if not self.main_dir.exists():
            print("❌ Main RAG system not found")
            return False
            
        print("✅ All requirements met")
        return True
    
    def setup_environment(self):
        """Set up environment variables"""
        print("📝 Setting up environment...")
        
        if not self.env_file.exists():
            # Create .env file with template
            env_content = """# WhatsApp Integration Environment Variables
# Copy from your existing setup or add new ones

# Google Gemini API (Required for WhatsApp formatting)
GOOGLE_API_KEY=your_gemini_api_key_here

# Twilio WhatsApp API (Required for WhatsApp messaging)
TWILIO_ACCOUNT_SID=your_twilio_sid_here
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# Your phone number (for testing)
YOUR_PHONE_NUMBER=+919360011424

# Optional: LangGraph API (if using remote RAG)
LANGGRAPH_API_URL=http://localhost:2024
"""
            
            with open(self.env_file, 'w') as f:
                f.write(env_content)
                
            print(f"📄 Created .env template at {self.env_file}")
            print("⚠️  Please edit the .env file with your API keys")
            return False
        else:
            print("✅ Environment file exists")
            return True
    
    def create_isolated_bridge(self):
        """Create an isolated WhatsApp bridge that doesn't interfere with main RAG"""
        print("🔧 Creating isolated WhatsApp bridge...")
        
        bridge_content = '''#!/usr/bin/env python3
"""
Isolated WhatsApp-RAG Bridge
Connects to your existing RAG system without interfering with it.
"""

import os
import sys
import logging
import asyncio
import requests
from flask import Flask, request, jsonify
from twilio.rest import Client
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN') 
TWILIO_WHATSAPP_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
LANGGRAPH_API_URL = os.getenv('LANGGRAPH_API_URL', 'http://localhost:2024')

# Initialize clients
twilio_client = None
gemini_model = None

def initialize_clients():
    """Initialize Twilio and Gemini clients"""
    global twilio_client, gemini_model
    
    if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
        twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        logger.info("✅ Twilio client initialized")
    else:
        logger.warning("⚠️  Twilio credentials not found")
    
    if GOOGLE_API_KEY:
        genai.configure(api_key=GOOGLE_API_KEY)
        gemini_model = genai.GenerativeModel('gemini-2.0-flash-exp')
        logger.info("✅ Gemini client initialized")
    else:
        logger.warning("⚠️  Google API key not found")

def query_existing_rag(question: str) -> str:
    """Query your existing RAG system via API"""
    try:
        # This calls your existing LangGraph RAG API
        response = requests.post(
            f"{LANGGRAPH_API_URL}/runs/stream",
            json={
                "assistant_id": "agent",
                "graph_id": "agent", 
                "input": {"messages": [{"role": "user", "content": question}]},
                "stream_mode": "values"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            # Parse the streaming response
            lines = response.text.strip().split('\\n')
            for line in lines:
                if line.startswith('data: '):
                    try:
                        data = json.loads(line[6:])
                        if 'messages' in data and data['messages']:
                            last_message = data['messages'][-1]
                            if last_message.get('type') == 'ai':
                                return last_message.get('content', 'No response')
                    except:
                        continue
        
        # Fallback: try simple POST to main endpoint
        fallback_response = requests.post(
            f"{LANGGRAPH_API_URL}/query",
            json={"question": question},
            timeout=15
        )
        
        if fallback_response.status_code == 200:
            data = fallback_response.json()
            return data.get('response', 'No response available')
        
        return "Sorry, I couldn't get a response from the RAG system."
        
    except requests.exceptions.ConnectionError:
        return "RAG system is not running. Please start your main RAG system on port 2024."
    except Exception as e:
        logger.error(f"RAG query error: {e}")
        return f"Error querying RAG system: {str(e)}"

def format_for_whatsapp(response: str) -> str:
    """Format response for WhatsApp using Gemini"""
    if not gemini_model:
        # Simple fallback formatting
        if len(response) > 1400:
            response = response[:1400] + "..."
        return response
    
    try:
        prompt = f"""Format this response for WhatsApp (mobile-friendly):

Original response: {response}

Requirements:
- Keep it concise and mobile-friendly
- Use bullet points and emojis
- Maximum 1500 characters
- Maintain key information
- Make it easy to read on mobile

Formatted response:"""

        result = gemini_model.generate_content(prompt)
        formatted = result.text.strip()
        
        if len(formatted) > 1500:
            formatted = formatted[:1497] + "..."
            
        return formatted
        
    except Exception as e:
        logger.error(f"Formatting error: {e}")
        if len(response) > 1400:
            response = response[:1400] + "..."
        return response

def send_whatsapp_message(to_number: str, message: str):
    """Send WhatsApp message via Twilio"""
    if not twilio_client:
        return {"success": False, "error": "Twilio not configured"}
    
    try:
        # Fix phone number format
        if not to_number.startswith("whatsapp:"):
            if not to_number.startswith("+"):
                to_number = "+" + to_number
            to_number = f"whatsapp:{to_number}"
        
        message_obj = twilio_client.messages.create(
            body=message,
            from_=TWILIO_WHATSAPP_NUMBER,
            to=to_number
        )
        
        return {"success": True, "message_sid": message_obj.sid}
        
    except Exception as e:
        logger.error(f"WhatsApp send error: {e}")
        return {"success": False, "error": str(e)}

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "twilio": "configured" if twilio_client else "not configured",
        "gemini": "configured" if gemini_model else "not configured",
        "rag_api": LANGGRAPH_API_URL
    })

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming WhatsApp messages"""
    try:
        from_number = request.form.get('From', '')
        message_body = request.form.get('Body', '').strip()
        
        if not message_body:
            return jsonify({"status": "no message"}), 200
        
        logger.info(f"📱 WhatsApp from {from_number}: {message_body}")
        
        # Query your existing RAG system
        rag_response = query_existing_rag(message_body)
        
        # Format for WhatsApp
        formatted_response = format_for_whatsapp(rag_response)
        
        # Send response
        result = send_whatsapp_message(from_number, formatted_response)
        
        if result["success"]:
            logger.info(f"✅ Response sent to {from_number}")
        else:
            logger.error(f"❌ Failed to send: {result['error']}")
        
        return jsonify({"status": "processed"}), 200
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/test', methods=['GET'])
def test_endpoint():
    """Test endpoint"""
    question = request.args.get('q', 'What are the cybersecurity requirements?')
    
    # Test RAG query
    rag_response = query_existing_rag(question)
    formatted_response = format_for_whatsapp(rag_response)
    
    return jsonify({
        "question": question,
        "rag_response": rag_response,
        "whatsapp_formatted": formatted_response
    })

if __name__ == '__main__':
    print("🚀 Starting Isolated WhatsApp-RAG Bridge")
    initialize_clients()
    
    print(f"📍 Health check: http://localhost:5000/health")
    print(f"🧪 Test endpoint: http://localhost:5000/test?q=your_question")
    print(f"🔗 Webhook URL: http://localhost:5000/webhook")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
'''

        bridge_file = Path("isolated_whatsapp_bridge.py")
        with open(bridge_file, 'w') as f:
            f.write(bridge_content)
            
        # Make it executable
        os.chmod(bridge_file, 0o755)
        
        print(f"✅ Created isolated bridge: {bridge_file}")
        return True
    
    def install_dependencies(self):
        """Install required Python packages"""
        print("📦 Installing dependencies...")
        
        packages = [
            "flask>=3.0.0",
            "twilio>=9.0.0", 
            "google-generativeai>=0.8.0",
            "python-dotenv>=1.0.0",
            "requests>=2.31.0"
        ]
        
        try:
            import subprocess
            for package in packages:
                print(f"Installing {package}...")
                result = subprocess.run(['conda', 'run', '-n', 'rfp-agent', 'pip', 'install', package], 
                                      capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"⚠️  Warning: Failed to install {package}")
            
            print("✅ Dependencies installed")
            return True
        except Exception as e:
            print(f"❌ Error installing dependencies: {e}")
            return False
    
    def setup_ngrok(self):
        """Set up ngrok tunnel"""
        print("🌐 Setting up ngrok...")
        
        ngrok_script = '''#!/bin/bash
# ngrok tunnel setup for WhatsApp webhook

echo "🌐 Starting ngrok tunnel..."

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok not found. Please install ngrok first:"
    echo "   1. Download from: https://ngrok.com/download"
    echo "   2. Extract and move to /usr/local/bin/"
    echo "   3. Sign up and get auth token"
    echo "   4. Run: ngrok config add-authtoken <your-token>"
    exit 1
fi

# Start ngrok tunnel
echo "Starting tunnel on port 5000..."
echo "Your webhook URL will be: https://xxxxx.ngrok-free.app/webhook"
echo ""
echo "📋 Configure this URL in Twilio Console:"
echo "   1. Go to: https://console.twilio.com/"
echo "   2. Navigate: Messaging → Try it out → Send a WhatsApp message"
echo "   3. Set webhook URL in sandbox settings"
echo ""
echo "Press Ctrl+C to stop tunnel"

ngrok http 5000
'''
        
        ngrok_file = Path("start_ngrok.sh")
        with open(ngrok_file, 'w') as f:
            f.write(ngrok_script)
        
        os.chmod(ngrok_file, 0o755)
        print(f"✅ Created ngrok script: {ngrok_file}")
        return True

    def create_startup_script(self):
        """Create a complete startup script"""
        print("📜 Creating startup script...")
        
        startup_content = '''#!/bin/bash
# Complete WhatsApp-RAG Integration Startup Script

echo "🚀 Starting WhatsApp-RAG Integration"
echo "=================================="

# Check if conda environment exists
if ! conda info --envs | grep -q "rfp-agent"; then
    echo "❌ Conda environment 'rfp-agent' not found"
    echo "Please create it first: conda create -n rfp-agent python=3.11"
    exit 1
fi

# Activate conda environment
echo "🔧 Activating conda environment..."
source $(conda info --base)/etc/profile.d/conda.sh
conda activate rfp-agent

# Check if .env file is configured
ENV_FILE=".env"
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Environment file not found: $ENV_FILE"
    echo "Please run: python setup_whatsapp_rag.py first"
    exit 1
fi

# Check if required keys are set
if grep -q "your_.*_here" "$ENV_FILE"; then
    echo "⚠️  Please configure your API keys in $ENV_FILE"
    echo "Required keys:"
    echo "  - GOOGLE_API_KEY (for response formatting)"
    echo "  - TWILIO_ACCOUNT_SID (for WhatsApp)"
    echo "  - TWILIO_AUTH_TOKEN (for WhatsApp)"
    exit 1
fi

cd /home/arun/Pictures/rfp-bid/whatsapp-integration

# Check if main RAG system is running
if ! curl -s http://localhost:2024/health > /dev/null 2>&1; then
    echo "⚠️  Main RAG system not detected on port 2024"
    echo "Please start your main RAG system first:"
    echo "  cd /home/arun/Pictures/rfp-bid/main"
    echo "  conda activate rfp-agent"
    echo "  langraph dev"
    echo ""
    echo "Or continue without it (WhatsApp will use fallback responses)"
    read -p "Continue anyway? (y/N): " choice
    case "$choice" in 
        y|Y ) echo "Continuing...";;
        * ) exit 1;;
    esac
fi

echo "🌐 Starting WhatsApp bridge..."
echo "📍 Health check: http://localhost:5000/health"
echo "🧪 Test endpoint: http://localhost:5000/test"
echo ""
echo "🔗 Don't forget to start ngrok in another terminal:"
echo "   ./start_ngrok.sh"
echo ""
echo "Press Ctrl+C to stop"

python isolated_whatsapp_bridge.py
'''

        startup_file = Path("start_whatsapp_rag.sh")
        with open(startup_file, 'w') as f:
            f.write(startup_content)
            
        # Make it executable
        os.chmod(startup_file, 0o755)
        
        print(f"✅ Created startup script: {startup_file}")
        return True

def main():
    print("🔧 WhatsApp-RAG Seamless Setup")
    print("=" * 40)
    
    setup = WhatsAppRAGSetup()
    
    # Check requirements
    if not setup.check_requirements():
        print("\n❌ Requirements not met. Please fix and try again.")
        return False
    
    # Install dependencies
    setup.install_dependencies()
    
    # Setup environment
    env_ready = setup.setup_environment()
    
    # Create isolated bridge
    setup.create_isolated_bridge()
    
    # Setup ngrok
    setup.setup_ngrok()
    
    # Create startup script
    setup.create_startup_script()
    
    print("\n🎉 Seamless Setup Complete!")
    print("=" * 40)
    
    if not env_ready:
        print("📝 Next steps:")
        print("1. Edit .env file with your API keys:")
        print(f"   nano .env")
        print("2. Start ngrok tunnel (in separate terminal):")
        print("   ./start_ngrok.sh")
        print("3. Configure webhook URL in Twilio Console")
        print("4. Start WhatsApp bridge:")
        print("   ./start_whatsapp_rag.sh")
    else:
        print("✅ Ready to start!")
        print("1. Start ngrok tunnel (in separate terminal):")
        print("   ./start_ngrok.sh")
        print("2. Start WhatsApp bridge:")
        print("   ./start_whatsapp_rag.sh")
    
    return True

if __name__ == "__main__":
    main()