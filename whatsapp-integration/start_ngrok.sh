#!/bin/bash
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
