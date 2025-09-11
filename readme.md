

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
check this doument 