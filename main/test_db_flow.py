#!/usr/bin/env python3
"""
Test script to verify database creation and querying flow.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from agent.milvus_ops import MilvusOps
from agent.agents import PDFParserAgent, CreateRAGAgent, GeneralAssistantAgent


def test_database_flow():
    """Test the complete database creation and querying flow."""
    
    print("🧪 Testing Database Creation and Querying Flow")
    print("=" * 60)
    
    # Check if we have a test PDF
    test_pdf = "../example-PDF/test.pdf"
    if not os.path.exists(test_pdf):
        print(f"❌ Test PDF not found: {test_pdf}")
        print("Please ensure there's a test PDF file available.")
        return
    
    try:
        # Step 1: Test PDF parsing
        print("\n📚 Step 1: Testing PDF Parser Agent")
        print("-" * 40)
        
        pdf_agent = PDFParserAgent()
        state = {
            "messages": [{"role": "user", "content": f"Parse this PDF: {test_pdf}"}],
            "chunks": [],
            "pdf_paths": []
        }
        
        # Convert to proper message format
        from langchain_core.messages import HumanMessage
        state["messages"] = [HumanMessage(content=f"Parse this PDF: {test_pdf}")]
        
        result = pdf_agent.parse_pdfs(state)
        print(f"PDF Parser Result: {result}")
        
        if "chunks" not in result:
            print("❌ PDF parsing failed")
            return
        
        chunks = result["chunks"]
        print(f"✅ Created {len(chunks)} chunks")
        
        # Step 2: Test RAG database creation
        print("\n🗄️ Step 2: Testing RAG Database Creation")
        print("-" * 40)
        
        create_agent = CreateRAGAgent()
        state["chunks"] = chunks
        
        result = create_agent.create_rag_database(state)
        print(f"RAG Creation Result: {result}")
        
        # Check if database was created
        milvus_ops = MilvusOps("session.db")
        if os.path.exists(milvus_ops.db_path):
            print(f"✅ Database created at: {milvus_ops.db_path}")
        else:
            print(f"❌ Database not found at: {milvus_ops.db_path}")
            return
        
        # Step 3: Test querying
        print("\n🔍 Step 3: Testing Document Querying")
        print("-" * 40)
        
        query_agent = GeneralAssistantAgent()
        state["messages"] = [HumanMessage(content="What is this document about?")]
        
        result = query_agent.query_documents(state)
        print(f"Query Result: {result}")
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Check environment variables
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY environment variable is required!")
        print("Please set it in your .env file or environment.")
        sys.exit(1)
    
    test_database_flow()
