#!/usr/bin/env python3
"""
Test script to run the RAG agent directly.
"""

import os
from dotenv import load_dotenv

def main():
    # Load environment variables
    load_dotenv()
    
    # Print environment variables for debugging
    print(f"OPENAI_API_KEY: {'Set' if os.getenv('OPENAI_API_KEY') else 'Not set'}")
    print(f"MILVUS_DB_PATH: {os.getenv('MILVUS_DB_PATH')}")
    print()
    
    # Check if API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not found in environment variables.")
        print("Please make sure your .env file contains the API key.")
        return
    
    # Check if Milvus path is set
    if not os.getenv("MILVUS_DB_PATH"):
        print("Error: MILVUS_DB_PATH not found in environment variables.")
        print("Please make sure your .env file contains the database path.")
        return
    
    # Import after loading environment variables
    from src.agent.graph import graph
    
    # Test question
    question = "What are the estimates for green hydrogen production cost according to KPMG?"
    
    print(f"Question: {question}")
    print("-" * 50)
    
    try:
        # Run the graph
        result = graph.invoke({
            "question": question
        })
        
        print("Answer:")
        print(result.get("answer", "No answer generated"))
        
        if result.get("error"):
            print(f"\nError: {result['error']}")
            
        print("\n" + "="*50)
        print("Agent completed successfully!")
        
    except Exception as e:
        print(f"Error running agent: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
