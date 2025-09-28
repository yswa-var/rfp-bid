#!/bin/bash
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
