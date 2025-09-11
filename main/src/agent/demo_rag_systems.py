#!/usr/bin/env python3
"""
RAG Systems Demo Script

This script demonstrates both Template RAG and RFP RAG systems working with sample data.

Usage:
    python3 demo_rag_systems.py
"""

import os
import sys
from pathlib import Path

# Add the current directory to the path to import the RAG modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from template_rag import TemplateRAG
from rfp_rag import RFPRAG


def demo_template_rag():
    """Demonstrate Template RAG functionality."""
    print("=" * 80)
    print("📋 TEMPLATE RAG DEMONSTRATION")
    print("=" * 80)
    
    # Initialize Template RAG
    template_rag = TemplateRAG("demo_template_rag.db")
    
    # Demo queries
    demo_queries = [
        "What are the payment terms?",
        "What are the security requirements?",
        "What is the contract duration?",
        "What are the termination conditions?",
        "What training is required?"
    ]
    
    print("🔍 Template RAG Query Examples:")
    print("-" * 50)
    
    for i, query in enumerate(demo_queries, 1):
        print(f"\n{i}. Query: '{query}'")
        results = template_rag.query_data(query, k=2)
        
        if results:
            for j, result in enumerate(results, 1):
                print(f"   Result {j}: {result['source_file']} (Page {result['page']}) - Accuracy: {result['accuracy']:.3f}")
                print(f"   Preview: {result['preview'][:100]}...")
        else:
            print("   No results found")
    
    print(f"\n📊 Template RAG Database Info:")
    info = template_rag.get_database_info()
    print(f"   Database: {info.get('database_name', 'Unknown')}")
    print(f"   Status: {info.get('status', 'Unknown')}")


def demo_rfp_rag():
    """Demonstrate RFP RAG functionality."""
    print("\n" + "=" * 80)
    print("📄 RFP RAG DEMONSTRATION")
    print("=" * 80)
    
    # Initialize RFP RAG
    rfp_rag = RFPRAG("demo_rfp_rag.db")
    
    # Demo queries
    demo_queries = [
        "What are the technical requirements?",
        "What is the budget range?",
        "What are the evaluation criteria?",
        "What is the project timeline?",
        "What are the vendor qualifications?"
    ]
    
    print("🔍 RFP RAG Query Examples:")
    print("-" * 50)
    
    for i, query in enumerate(demo_queries, 1):
        print(f"\n{i}. Query: '{query}'")
        results = rfp_rag.query_data(query, k=2)
        
        if results:
            for j, result in enumerate(results, 1):
                print(f"   Result {j}: {result['source_file']} (Page {result['page']}) - Accuracy: {result['accuracy']:.3f}")
                print(f"   Preview: {result['preview'][:100]}...")
        else:
            print("   No results found")
    
    # Demo specific RFP query
    print(f"\n🔍 Specific RFP Query Example:")
    print("-" * 50)
    rfp_list = rfp_rag.get_rfp_list()
    if rfp_list:
        specific_rfp = rfp_list[0]  # Get first RFP
        print(f"Querying specific RFP: {specific_rfp}")
        results = rfp_rag.query_specific_rfp("security requirements", specific_rfp, k=1)
        if results:
            for result in results:
                print(f"   Result: {result['source_file']} (Page {result['page']}) - Accuracy: {result['accuracy']:.3f}")
                print(f"   Preview: {result['preview'][:100]}...")
    
    print(f"\n📊 RFP RAG Database Info:")
    info = rfp_rag.get_database_info()
    print(f"   Database: {info.get('database_name', 'Unknown')}")
    print(f"   Status: {info.get('status', 'Unknown')}")


def demo_comparison():
    """Demonstrate comparison between Template and RFP RAGs."""
    print("\n" + "=" * 80)
    print("🔄 RAG SYSTEMS COMPARISON")
    print("=" * 80)
    
    # Initialize both RAGs
    template_rag = TemplateRAG("demo_template_rag.db")
    rfp_rag = RFPRAG("demo_rfp_rag.db")
    
    # Comparison queries
    comparison_queries = [
        "What are the security requirements?",
        "What is the project timeline?",
        "What are the payment terms?"
    ]
    
    print("🔍 Side-by-Side Query Comparison:")
    print("-" * 50)
    
    for query in comparison_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 30)
        
        # Template RAG results
        print("📋 Template RAG Results:")
        template_results = template_rag.query_data(query, k=1)
        if template_results:
            result = template_results[0]
            print(f"   Source: {result['source_file']} (Page {result['page']})")
            print(f"   Accuracy: {result['accuracy']:.3f}")
            print(f"   Preview: {result['preview'][:80]}...")
        else:
            print("   No results found")
        
        # RFP RAG results
        print("📄 RFP RAG Results:")
        rfp_results = rfp_rag.query_data(query, k=1)
        if rfp_results:
            result = rfp_results[0]
            print(f"   Source: {result['source_file']} (Page {result['page']})")
            print(f"   Accuracy: {result['accuracy']:.3f}")
            print(f"   Preview: {result['preview'][:80]}...")
        else:
            print("   No results found")


def main():
    """Main demo function."""
    print("🚀 RAG SYSTEMS COMPREHENSIVE DEMO")
    print("This demo shows both Template RAG and RFP RAG systems working with sample data.")
    print("\nNote: This demo assumes the databases have already been created with sample data.")
    print("If you see 'No database loaded' errors, run the setup commands first:")
    print("  python3 template_rag.py add_data --template_dir /path/to/templates")
    print("  python3 rfp_rag.py add_data --rfp_dir /path/to/rfp")
    
    # Check if databases exist
    template_db = Path("demo_template_rag.db")
    rfp_db = Path("demo_rfp_rag.db")
    
    if not template_db.exists():
        print(f"\n⚠️  Template database not found: {template_db}")
        print("   Run: python3 template_rag.py add_data --template_dir /path/to/templates")
        return
    
    if not rfp_db.exists():
        print(f"\n⚠️  RFP database not found: {rfp_db}")
        print("   Run: python3 rfp_rag.py add_data --rfp_dir /path/to/rfp")
        return
    
    # Run demonstrations
    try:
        demo_template_rag()
        demo_rfp_rag()
        demo_comparison()
        
        print("\n" + "=" * 80)
        print("✅ DEMO COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print("\nKey Features Demonstrated:")
        print("• Template RAG: Contract templates, security policies, proposal templates")
        print("• RFP RAG: Cybersecurity services, IT infrastructure, software development")
        print("• Semantic search with accuracy scores")
        print("• Document source tracking and page references")
        print("• Side-by-side comparison of different RAG systems")
        print("\nNext Steps:")
        print("• Use interactive mode: python3 template_rag.py interactive")
        print("• Use interactive mode: python3 rfp_rag.py interactive")
        print("• Add your own documents to the databases")
        print("• Integrate with your applications using the Python classes")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {str(e)}")
        print("Please check that the databases are properly set up.")


if __name__ == "__main__":
    main()
