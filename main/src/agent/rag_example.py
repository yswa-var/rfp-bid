#!/usr/bin/env python3
"""
RAG Example Usage Script

This script demonstrates how to use both Template RAG and RFP RAG systems.

Usage:
    python rag_example.py
"""

import os
import sys
from pathlib import Path

# Add the current directory to the path to import the RAG modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from template_rag import TemplateRAG
from rfp_rag import RFPRAG


def example_template_rag():
    """Example usage of Template RAG."""
    print("=" * 60)
    print("📋 TEMPLATE RAG EXAMPLE")
    print("=" * 60)
    
    # Initialize Template RAG
    template_rag = TemplateRAG("example_template_rag.db")
    
    # Example: Add template data (uncomment to use)
    # template_dir = "../../example-PDF/Contracts"  # Update path as needed
    # if Path(template_dir).exists():
    #     print(f"Adding template data from: {template_dir}")
    #     success = template_rag.add_data(template_dir)
    #     if success:
    #         print("✅ Template data added successfully!")
    #     else:
    #         print("❌ Failed to add template data")
    #         return
    # else:
    #     print(f"❌ Template directory not found: {template_dir}")
    #     return
    
    # Example: Query template data
    print("\n🔍 Querying template database...")
    queries = [
        "What are the key requirements for security services?",
        "What is the contract duration?",
        "What are the evaluation criteria?"
    ]
    
    for query in queries:
        print(f"\nQuery: {query}")
        results = template_rag.query_data(query, k=3)
        if results:
            print(f"Found {len(results)} results")
            for i, result in enumerate(results, 1):
                print(f"  {i}. {result['source_file']} (Page {result['page']}) - Accuracy: {result['accuracy']:.3f}")
        else:
            print("  No results found")


def example_rfp_rag():
    """Example usage of RFP RAG."""
    print("\n" + "=" * 60)
    print("📄 RFP RAG EXAMPLE")
    print("=" * 60)
    
    # Initialize RFP RAG
    rfp_rag = RFPRAG("example_rfp_rag.db")
    
    # Example: Add RFP data (uncomment to use)
    # rfp_dir = "../../example-PDF/Contracts"  # Update path as needed
    # if Path(rfp_dir).exists():
    #     print(f"Adding RFP data from: {rfp_dir}")
    #     success = rfp_rag.add_data(rfp_dir)
    #     if success:
    #         print("✅ RFP data added successfully!")
    #     else:
    #         print("❌ Failed to add RFP data")
    #         return
    # else:
    #     print(f"❌ RFP directory not found: {rfp_dir}")
    #     return
    
    # Example: Query RFP data
    print("\n🔍 Querying RFP database...")
    queries = [
        "What are the cybersecurity requirements?",
        "What is the project timeline?",
        "What are the technical specifications?",
        "What is the budget range?"
    ]
    
    for query in queries:
        print(f"\nQuery: {query}")
        results = rfp_rag.query_data(query, k=3)
        if results:
            print(f"Found {len(results)} results")
            for i, result in enumerate(results, 1):
                print(f"  {i}. {result['source_file']} (Page {result['page']}) - Accuracy: {result['accuracy']:.3f}")
        else:
            print("  No results found")
    
    # Example: Query specific RFP
    print("\n🔍 Querying specific RFP...")
    rfp_list = rfp_rag.get_rfp_list()
    if rfp_list:
        print(f"Available RFP documents: {len(rfp_list)}")
        for rfp in rfp_list[:3]:  # Show first 3
            print(f"  - {rfp}")
        
        # Query specific RFP
        specific_query = "What are the security requirements?"
        specific_rfp = rfp_list[0] if rfp_list else None
        if specific_rfp:
            print(f"\nQuerying '{specific_rfp}' for: {specific_query}")
            results = rfp_rag.query_specific_rfp(specific_query, specific_rfp, k=2)
            if results:
                print(f"Found {len(results)} results in {specific_rfp}")
            else:
                print(f"No results found in {specific_rfp}")


def main():
    """Main function to run examples."""
    print("🚀 RAG System Examples")
    print("This script demonstrates how to use both Template RAG and RFP RAG systems.")
    print("\nNote: Uncomment the data loading sections to actually add data to the databases.")
    print("Make sure to update the directory paths to point to your actual PDF files.")
    
    # Run examples
    example_template_rag()
    example_rfp_rag()
    
    print("\n" + "=" * 60)
    print("✅ Examples completed!")
    print("=" * 60)
    print("\nTo use these RAG systems with your own data:")
    print("1. Update the directory paths in the example functions")
    print("2. Uncomment the data loading sections")
    print("3. Run the script again")
    print("\nOr use the command line interface:")
    print("  python template_rag.py add_data --template_dir /path/to/templates")
    print("  python template_rag.py query_data --query 'your query here'")
    print("  python rfp_rag.py add_data --rfp_dir /path/to/rfp/docs")
    print("  python rfp_rag.py query_data --query 'your query here'")


if __name__ == "__main__":
    main()
