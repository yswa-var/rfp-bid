import getpass
import os
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain import hub
from langchain_community.document_loaders import PyPDFLoader
from langchain.chat_models import init_chat_model
from langchain_openai import OpenAIEmbeddings
from langchain_milvus import Milvus

# Load environment variables
load_dotenv()


llm = init_chat_model("gpt-4o-mini", model_provider="openai")

embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

URI = "./milvus_example.db"

vector_store = Milvus(
    embedding_function=embeddings,
    connection_args={"uri": URI},
    index_params={"index_type": "FLAT", "metric_type": "L2"},
)
file_path = "../example-PDF/Article-on-Green-Hydrogen-and-GOI-Policy.pdf"
loader = PyPDFLoader(file_path)
pages = loader.load()


text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,  
    chunk_overlap=200,  
    add_start_index=True, 
)
all_splits = text_splitter.split_documents(pages)

print(f"Split blog post into {len(all_splits)} sub-documents.")

document_ids = vector_store.add_documents(documents=all_splits)

print(document_ids[:3])


prompt = hub.pull("rlm/rag-prompt")


question = "what is KPMG Estimated cost of GH (Pre-policy)"

retrieved_docs = vector_store.similarity_search(question)

# Print source information for each retrieved document
print("\n=== RETRIEVED SOURCES ===")
for i, doc in enumerate(retrieved_docs):
    source_file = doc.metadata.get('source', 'Unknown')
    page_num = doc.metadata.get('page_label', doc.metadata.get('page', 'Unknown'))
    author = doc.metadata.get('author', 'Unknown')
    print(f"Source {i+1}:")
    print(f"  File: {source_file}")
    print(f"  Page: {page_num}")
    print(f"  Author: {author}")
    print(f"  Content preview: {doc.page_content[:100]}...")
    print()

# Create context with source information
docs_with_sources = []
for i, doc in enumerate(retrieved_docs):
    source_file = doc.metadata.get('source', 'Unknown').split('/')[-1]  # Get just filename
    page_num = doc.metadata.get('page_label', doc.metadata.get('page', 'Unknown'))
    content_with_source = f"[Source: {source_file}, Page {page_num}]\n{doc.page_content}"
    docs_with_sources.append(content_with_source)

docs_content = "\n\n".join(docs_with_sources)
prompt = prompt.invoke({"question": question, "context": docs_content})
answer = llm.invoke(prompt)

print("=== ANSWER WITH SOURCES ===")
print(answer)