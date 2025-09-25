#!/usr/bin/env python3
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
            lines = response.text.strip().split('\n')
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
