import getpass
import os
import glob
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain import hub
from langchain_community.document_loaders import PyPDFLoader
from langchain.chat_models import init_chat_model
from langchain_openai import OpenAIEmbeddings
from langchain_milvus import Milvus
from langchain_core.documents import Document

def analyze_all_metadata_fields(documents: List[Document]) -> set:
    """Analyze all documents to find all possible metadata fields."""
    all_fields = set()
    for doc in documents:
        all_fields.update(doc.metadata.keys())
    return all_fields

def clean_and_standardize_metadata(metadata: Dict[str, Any], all_fields: set) -> Dict[str, Any]:
    """Clean metadata and ensure all fields are present with default values."""
    # First clean the field names
    cleaned = {}
    for key, value in metadata.items():
        # Replace invalid characters with underscores
        clean_key = key.replace(':', '_').replace('-', '_').replace(' ', '_')
        # Remove any other special characters and keep only alphanumeric and underscores
        clean_key = ''.join(c if c.isalnum() or c == '_' else '_' for c in clean_key)
        # Ensure key starts with letter or underscore
        if clean_key and clean_key[0].isdigit():
            clean_key = '_' + clean_key
        
        # Convert value to string if it's not already
        if isinstance(value, (list, dict)):
            cleaned[clean_key] = str(value)
        else:
            cleaned[clean_key] = str(value) if value is not None else ""
    
    # Clean all field names in the set
    cleaned_all_fields = set()
    for field in all_fields:
        clean_field = field.replace(':', '_').replace('-', '_').replace(' ', '_')
        clean_field = ''.join(c if c.isalnum() or c == '_' else '_' for c in clean_field)
        if clean_field and clean_field[0].isdigit():
            clean_field = '_' + clean_field
        cleaned_all_fields.add(clean_field)
    
    # Ensure all fields are present with default values
    standardized = {}
    for field in cleaned_all_fields:
        standardized[field] = cleaned.get(field, "")
    
    return standardized

def create_simple_metadata(metadata: Dict[str, Any]) -> Dict[str, str]:
    """Create simplified metadata with only essential fields."""
    return {
        'source': str(metadata.get('source', 'Unknown')),
        'page': str(metadata.get('page', metadata.get('page_label', 'Unknown'))),
        'file_path': str(metadata.get('file_path', '')),
        'total_pages': str(metadata.get('total_pages', 0)),
        'creator': str(metadata.get('creator', '')),
        'producer': str(metadata.get('producer', '')),
    }

def process_documents_robust():
    """Process documents with robust error handling and metadata management."""
    
    print("Initializing components...")
    llm = init_chat_model("gpt-4o-mini", model_provider="openai")
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    URI = "./milvus_example.db"

# Load environment variables
load_dotenv()


llm = init_chat_model("gpt-4o-mini", model_provider="openai")

embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

URI = "./milvus_example.db"

    # Process multiple PDFs
    pdf_directory = "../example-PDF/"
    pdf_files = glob.glob(os.path.join(pdf_directory, "*.pdf"))
    
    print(f"Found {len(pdf_files)} PDF files to process...")
    
    all_documents = []
    for file_path in pdf_files:
        print(f"Processing: {file_path}")
        try:
            loader = PyPDFLoader(file_path)
            pages = loader.load()
            all_documents.extend(pages)
            print(f"  Loaded {len(pages)} pages")
        except Exception as e:
            print(f"  Error loading {file_path}: {e}")
            continue

    if not all_documents:
        print("No documents loaded successfully!")
        return

    print(f"Total loaded: {len(all_documents)} pages from {len(pdf_files)} PDF files.")
    
    # Analyze all metadata fields
    print("Analyzing metadata fields...")
    all_fields = analyze_all_metadata_fields(all_documents)
    print(f"Found metadata fields: {sorted(all_fields)}")
    
    # Method 1: Try with standardized metadata (all fields present)
    print("\nMethod 1: Attempting with standardized metadata...")
    try:
        # Clean and standardize metadata for all documents
        for doc in all_documents:
            doc.metadata = clean_and_standardize_metadata(doc.metadata, all_fields)
        
        # Split documents
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,  
            chunk_overlap=200,  
            add_start_index=True, 
        )
        all_splits = text_splitter.split_documents(all_documents)
        
        # Clean metadata for splits as well
        for doc in all_splits:
            doc.metadata = clean_and_standardize_metadata(doc.metadata, all_fields)
        
        print(f"Split documents into {len(all_splits)} sub-documents.")
        
        # Create vector store
        vector_store = Milvus(
            embedding_function=embeddings,
            connection_args={"uri": URI},
            index_params={"index_type": "FLAT", "metric_type": "L2"},
        )
        
        document_ids = vector_store.add_documents(documents=all_splits)
        print(f"✅ SUCCESS: Added {len(document_ids)} documents to vector store using Method 1!")
        
        return vector_store
        
    except Exception as e:
        print(f"❌ Method 1 failed: {e}")
        print("\nMethod 2: Attempting with simplified metadata...")
        
        try:
            # Method 2: Use only simple, essential metadata
            for doc in all_documents:
                doc.metadata = create_simple_metadata(doc.metadata)
            
            # Split documents again with clean metadata
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,  
                chunk_overlap=200,  
                add_start_index=True, 
            )
            all_splits = text_splitter.split_documents(all_documents)
            
            # Clean metadata for splits
            for doc in all_splits:
                doc.metadata = create_simple_metadata(doc.metadata)
            
            print(f"Split documents into {len(all_splits)} sub-documents.")
            
            # Create new vector store
            vector_store = Milvus(
                embedding_function=embeddings,
                connection_args={"uri": URI},
                index_params={"index_type": "FLAT", "metric_type": "L2"},
            )
            
            document_ids = vector_store.add_documents(documents=all_splits)
            print(f"✅ SUCCESS: Added {len(document_ids)} documents to vector store using Method 2!")
            
            return vector_store
            
        except Exception as e2:
            print(f"❌ Method 2 failed: {e2}")
            print("\nMethod 3: Attempting with minimal metadata...")
            
            try:
                for doc in all_documents:
                    doc.metadata = {
                        'source': str(doc.metadata.get('source', 'Unknown')),
                        'page': str(doc.metadata.get('page', doc.metadata.get('page_label', 'Unknown')))
                    }
                
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1000,  
                    chunk_overlap=200,  
                    add_start_index=True, 
                )
                all_splits = text_splitter.split_documents(all_documents)

                for doc in all_splits:
                    doc.metadata = {
                        'source': str(doc.metadata.get('source', 'Unknown')),
                        'page': str(doc.metadata.get('page', 'Unknown'))
                    }
                
                print(f"Split documents into {len(all_splits)} sub-documents.")

                vector_store = Milvus(
                    embedding_function=embeddings,
                    connection_args={"uri": URI},
                    index_params={"index_type": "FLAT", "metric_type": "L2"},
                )
                
                document_ids = vector_store.add_documents(documents=all_splits)
                print(f"✅ SUCCESS: Added {len(document_ids)} documents to vector store using Method 3!")
                
                return vector_store
                
            except Exception as e3:
                print(f"❌ All methods failed!")
                print(f"Method 1 error: {e}")
                print(f"Method 2 error: {e2}")
                print(f"Method 3 error: {e3}")
                return None

def test_retrieval(vector_store):
    """Test the vector store with sample queries."""
    if not vector_store:
        print("No vector store available for testing!")
        return
    
    print("\n" + "="*50)
    print("TESTING RETRIEVAL")
    print("="*50)
    
    questions = [
        "what is KPMG Estimated cost of GH (Pre-policy)",
        "What are the key findings about smart grids?",
        "What is mentioned about distributed generation?"
    ]
    
    for question in questions:
        print(f"\nQuestion: {question}")
        print("-" * 40)
        
        try:
            retrieved_docs = vector_store.similarity_search(question, k=3)
            
            for i, doc in enumerate(retrieved_docs):
                source_file = doc.metadata.get('source', 'Unknown')
                page_num = doc.metadata.get('page', 'Unknown')
                print(f"Source {i+1}: {Path(source_file).name}, Page {page_num}")
                print(f"  Content: {doc.page_content[:150]}...")
                print()
                
        except Exception as e:
            print(f"Error during retrieval: {e}")

if __name__ == "__main__":
    # Remove existing database
    if os.path.exists("./milvus_example.db"):
        os.remove("./milvus_example.db")
        print("Removed existing database file.")

    vector_store = process_documents_robust()

    test_retrieval(vector_store)
        