
<img width="952" height="281" alt="Screenshot 2025-09-17 at 1 49 32 PM" src="https://github.com/user-attachments/assets/c351b0cc-52fe-4295-bc18-1a2e3fc6a0c9" />

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
