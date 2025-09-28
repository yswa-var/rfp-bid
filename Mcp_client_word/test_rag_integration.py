#!/usr/bin/env python3
"""
Test RAG Integration
Quick test to verify the RAG integration is working
"""

import sys
import os
from pathlib import Path

# Add the main RFP system to path
rfp_main_path = '/home/arun/Pictures/rfp-bid/main'
if os.path.exists(rfp_main_path):
    sys.path.append(rfp_main_path)
    sys.path.append(os.path.join(rfp_main_path, 'src'))
    print(f"✅ Added RFP system path: {rfp_main_path}")
else:
    print(f"❌ RFP system path not found: {rfp_main_path}")
    sys.exit(1)

try:
    # Test imports
    print("🔧 Testing imports...")
    from agent.proposal_rag_coordinator import ProposalRAGCoordinator
    print("✅ ProposalRAGCoordinator imported successfully")
    
    # Test RAG initialization
    print("🔧 Testing RAG initialization...")
    rag_coordinator = ProposalRAGCoordinator()
    print("✅ RAG Coordinator initialized")
    
    # Test database status
    print("🔧 Testing database status...")
    status = rag_coordinator.get_database_status()
    ready_count = sum(status.values())
    
    print(f"📊 RAG Database Status ({ready_count}/3 ready):")
    print(f"- Template RAG: {'✅ Ready' if status['template_ready'] else '❌ Not available'}")
    print(f"- Examples RAG: {'✅ Ready' if status['examples_ready'] else '❌ Not available'}")  
    print(f"- Session RAG: {'✅ Ready' if status['session_ready'] else '⚠️ No current RFP'}")
    
    if ready_count > 0:
        print("🚀 RAG integration is ready!")
        
        # Test a simple query
        print("\n🔍 Testing RAG query...")
        test_contexts = rag_coordinator.query_all_rags("technical architecture", k=2)
        
        if test_contexts:
            print("✅ RAG query successful!")
            for context_type, results in test_contexts.items():
                if results:
                    print(f"- {context_type}: {len(results)} results")
        else:
            print("⚠️ No results from RAG query")
    else:
        print("⚠️ No RAG databases available")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure the main RFP system is properly set up")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n🎯 Test completed!")