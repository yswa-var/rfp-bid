

```
python3 -m venv venv
source venv/bin/activate

cd main

pip install -r requirements.txt
pip install -e .
```
set .env keys and path as .env.example

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

## How to setup milvus?
check out rfp-rag/main/milvus_creator.py

### demo RFP docs are in example-PDF.# rfp-bid
