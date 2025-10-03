
<img width="803" height="275" alt="Screenshot 2025-10-03 at 12 09 34 PM" src="https://github.com/user-attachments/assets/22f87226-b814-431b-aabf-466770f2078a" />


## 🚀 Quick Start

```
python3 -m venv venv
source venv/bin/activate

cd main

pip install -r requirements.txt
pip install -e .
```
set .env keys and path as main/.env.template

run the project 
```
langgraph dev
```

## 📱 NEW: WhatsApp Integration

Query your RFP documents directly through WhatsApp! 

### Quick Setup:
```bash
# 1. Configure API keys
cp whatsapp-integration/.env.template whatsapp-integration/.env
# Edit .env with your Twilio, Gemini, and OpenAI keys

# 2. Index your documents first
cd main && langgraph dev
# Use: "index this document /path/to/your/rfp.pdf"

# 3. Start WhatsApp integration  
./start_whatsapp_rag.sh
```

**WhatsApp Usage:**
```
User: "What are the cybersecurity requirements?"
Bot: "🔒 Cybersecurity Requirements:
- 24/7 SOC monitoring
- SIEM implementation required
- Incident response within 1 hour
- Compliance with ISO 27001

📚 Sources: MSSP-RFP.pdf p.8"
```

📖 **[Full WhatsApp Integration Guide](whatsapp-integration/README.md)**

## 🛠️ Core Systemheight="281" alt="Screenshot 2025-09-17 at 1 49 32 PM" src="https://github.com/user-attachments/assets/c351b0cc-52fe-4295-bc18-1a2e3fc6a0c9" />

```
python3 -m venv venv
source venv/bin/activate

cd main

pip install -r requirements.txt
pip install -e .
```
set .env keys and path as main/.env.template

run the project 
```
langgraph dev
```

helping libs
```
pip install -qU pypdf
pip install -qU langchain-milvus
pip install langchain-text-splitters
pip install --upgrade --quiet langchain-community langchain langchain-openai
```

**How to setup milvus?**
check out rfp-rag/main/milvus_creator.py

demo prompts

- index this document or documents `document path` (not relative path)
example:
```
index this document /Users/yash/Documents/rfp/rfp-rag/example-PDF/Contracts/Request-for-Proposal-RFP-for-Cybersecurity-Monitoring-P25-038.pdf
```
or

```
# Template RAG
python3 template_rag.py add_data --template_dir /path/to/templates
python3 template_rag.py query_data --query "What are the payment terms?" --k 3

# RFP RAG  
python3 rfp_rag.py add_data --rfp_dir /path/to/rfp
python3 rfp_rag.py query_data --query "What are the technical requirements?" --k 3

# Interactive modes
python3 template_rag.py interactive
python3 rfp_rag.py interactive

# Run demo
python3 demo_rag_systems.py
```

demo curls
```
curl --location 'http://localhost:2024/runs/stream' \
--header 'Content-Type: application/json' \
--data '{
    "assistant_id": "agent",
    "input": {
      "messages": [
        {
          "role": "human",
          "content": "Index /Users/yash/Documents/rfp/rfp-bid/example-PDF/Contracts/Request-for-proposal-for-engaging-a-Managed-Security-Services-provider-for-SOC-for-the-period-of-3-years.pdf"
        }
      ]
    },
    "stream_mode": "messages-tuple"
  }'
```

rfp/rfp-bid/example-PDF/Contracts/Request-for-proposal-for-engaging-a-Managed-Security-Services-provider-for-SOC-for-the-period-of-3-years.pdf
