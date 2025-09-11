#!/usr/bin/env python3
"""
Test Multi-RAG System
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.agent.multi_rag_integration import MultiRAGCoordinator

def test_database_setup():
    """Test database setup."""
    print("🔧 Testing Multi-RAG Database Setup")
    print("=" * 40)
    
    coordinator = MultiRAGCoordinator()
    coordinator.setup_databases()
    
    return coordinator

def test_multi_rag_queries(coordinator):
    """Test the multi-RAG integration."""
    print("\n🔍 Testing Multi-RAG Queries")
    print("=" * 40)
    
    test_queries = [
        "cybersecurity requirements",
        "proposal template structure", 
        "security monitoring services",
        "incident response planning"
    ]
    
    for query in test_queries:
        print(f"\n📋 Query: '{query}'")
        print("-" * 30)
        
        try:
            results = coordinator.query_all_rags(query, k=2)
            
            for rag_type, context in results.items():
                print(f"\n{rag_type.replace('_', ' ').title()}:")
                if context and len(context) > 0:
                    for i, doc in enumerate(context):
                        if hasattr(doc, 'page_content'):
                            content = doc.page_content[:100]
                            source = getattr(doc, 'metadata', {}).get('source', 'Unknown')
                            print(f"  {i+1}. [{Path(source).name if source != 'Unknown' else 'Unknown'}] {content}...")
                        else:
                            print(f"  {i+1}. {str(doc)[:100]}...")
                else:
                    print("  No results found")
        except Exception as e:
            print(f"  ❌ Error: {e}")

def test_individual_rags():
    """Test individual RAG systems."""
    print("\n🎯 Testing Individual RAG Systems")
    print("=" * 40)
    
    try:
        from src.agent.template_rag import TemplateRAG
        from src.agent.rfp_rag import RFPRAG
        
        # Test Template RAG
        print("\n📋 Template RAG:")
        template_rag = TemplateRAG("template_rag.db")
        template_results = template_rag.query_data("security policy template", k=1)
        if template_results:
            print(f"  ✅ Found {len(template_results)} results")
        else:
            print("  ⚠️  No results - may need to add data")
        
        # Test RFP RAG  
        print("\n📄 RFP Examples RAG:")
        rfp_rag = RFPRAG("rfp_rag.db")
        rfp_results = rfp_rag.query_data("cybersecurity services", k=1)
        if rfp_results:
            print(f"  ✅ Found {len(rfp_results)} results")
        else:
            print("  ⚠️  No results - may need to add data")
            
    except Exception as e:
        print(f"  ❌ Error testing individual RAGs: {e}")

def main():
    """Main test function."""
    print("🧪 Multi-RAG System Test Suite")
    print("=" * 50)
    
    # Test 1: Database Setup
    coordinator = test_database_setup()
    
    # Test 2: Individual RAG Systems
    test_individual_rags()
    
    # Test 3: Multi-RAG Queries
    test_multi_rag_queries(coordinator)
    
    print("\n" + "=" * 50)
    print("✅ Test Suite Complete!")
    print("\n📝 Next Steps:")
    print("1. If you see database errors, run: python3 src/agent/template_rag.py add_data --template_dir ../example-PDF/templates-pdf")
    print("2. If you see database errors, run: python3 src/agent/rfp_rag.py add_data --rfp_dir ../example-PDF/rfp-pdf") 
    print("3. Run the full orchestrator: python3 orchestrate_proposal.py")

if __name__ == "__main__":
    main()