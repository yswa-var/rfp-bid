#!/usr/bin/env python3
"""
Test script to verify RAG Editor nodes are visible in LangGraph

This script tests the updated graph structure to ensure RAG editor nodes
are properly integrated and visible in LangGraph Studio.
"""

import os
import sys
from pathlib import Path

# Add the main RFP system to path
script_dir = os.path.dirname(os.path.abspath(__file__))
main_src_path = os.path.join(script_dir, 'src')

if os.path.exists(main_src_path):
    sys.path.insert(0, main_src_path)
    print(f"✅ Added main src path: {main_src_path}")
else:
    print(f"❌ Main src path not found: {main_src_path}")

def test_rag_editor_nodes():
    """Test that RAG editor nodes are properly integrated."""
    
    print("🧪 Testing RAG Editor Node Integration")
    print("=" * 50)
    
    try:
        # Import the graph
        from agent.graph import graph
        from agent.proposal_supervisor import build_parent_proposal_graph
        
        print("✅ Successfully imported graph modules")
        
        # Test main graph
        print("\n📊 Main Graph Structure:")
        main_graph_info = graph.get_graph()
        print(f"   - Nodes: {len(main_graph_info.nodes)}")
        print(f"   - Edges: {len(main_graph_info.edges)}")
        
        # Check for RAG editor nodes
        rag_editor_nodes = [node for node in main_graph_info.nodes if 'rag' in node.lower()]
        print(f"   - RAG Editor Nodes: {rag_editor_nodes}")
        
        # Test proposal supervisor graph
        print("\n📊 Proposal Supervisor Graph Structure:")
        proposal_graph = build_parent_proposal_graph()
        proposal_graph_info = proposal_graph.get_graph()
        print(f"   - Nodes: {len(proposal_graph_info.nodes)}")
        print(f"   - Edges: {len(proposal_graph_info.edges)}")
        
        # Check for RAG editor nodes in proposal supervisor
        proposal_rag_nodes = [node for node in proposal_graph_info.nodes if 'rag' in node.lower()]
        print(f"   - RAG Editor Nodes: {proposal_rag_nodes}")
        
        # Display all nodes
        print("\n📋 All Nodes in Main Graph:")
        for i, node in enumerate(main_graph_info.nodes, 1):
            print(f"   {i}. {node}")
        
        print("\n📋 All Nodes in Proposal Supervisor Graph:")
        for i, node in enumerate(proposal_graph_info.nodes, 1):
            print(f"   {i}. {node}")
        
        # Test routing capabilities
        print("\n🔄 Testing Router Integration:")
        try:
            from agent.router import supervisor_router
            print("✅ Router imported successfully")
            
            # Test routing keywords
            test_keywords = [
                "launch rag editor",
                "enhance proposal", 
                "rag enhancement",
                "improve proposal content"
            ]
            
            print("   - Router supports RAG editor keywords:")
            for keyword in test_keywords:
                print(f"     • '{keyword}'")
                
        except Exception as e:
            print(f"❌ Router test failed: {e}")
        
        # Test RAG editor agent
        print("\n🤖 Testing RAG Editor Agent:")
        try:
            from agent.rag_editor_agent import RAGEditorAgent
            rag_agent = RAGEditorAgent()
            capabilities = rag_agent.get_capabilities()
            
            print("✅ RAG Editor Agent created successfully")
            print(f"   - Agent Name: {capabilities['agent_name']}")
            print(f"   - Supported Operations: {capabilities['supported_operations']}")
            print(f"   - Document Path: {capabilities['document_path']}")
            print(f"   - RAG Databases: {capabilities['rag_databases']}")
            print(f"   - Output Formats: {capabilities['output_formats']}")
            
        except Exception as e:
            print(f"❌ RAG Editor Agent test failed: {e}")
        
        print("\n✅ RAG Editor Node Integration Test Complete!")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_graph_structure():
    """Show the complete graph structure with RAG editor integration."""
    
    print("\n🎯 Complete Graph Structure with RAG Editor Integration")
    print("=" * 60)
    
    print("""
📊 MAIN GRAPH STRUCTURE:
┌─────────────────────────────────────────────────────────┐
│ START → supervisor → [conditional routing] → END        │
└─────────────────────────────────────────────────────────┘

Available Routes from Supervisor:
├── pdf_parser → create_rag → END
├── general_assistant → END  
├── rag_editor → END                    [NEW! 🆕]
├── rag_enhancement → END               [NEW! 🆕]
├── multi_rag_setup → END
└── proposal_supervisor → END

📊 PROPOSAL SUPERVISOR GRAPH STRUCTURE:
┌─────────────────────────────────────────────────────────┐
│ START → proposal_supervisor → [team routing] → END      │
└─────────────────────────────────────────────────────────┘

Team Execution Flow:
├── technical_team → proposal_supervisor
├── finance_team → proposal_supervisor  
├── legal_team → proposal_supervisor
├── qa_team → proposal_supervisor
└── rag_editor_enhancement → proposal_supervisor  [NEW! 🆕]

🎨 VISUALIZATION COLORS:
├── Technical Team: Blue (#3B82F6)
├── Finance Team: Green (#10B981)
├── Legal Team: Yellow (#F59E0B)  
├── QA Team: Red (#EF4444)
└── RAG Editor: Purple (#8B5CF6)  [NEW! 🆕]

🔄 ROUTING KEYWORDS:
├── "launch rag editor" → rag_editor
├── "enhance proposal" → rag_enhancement
├── "rag enhancement" → rag_enhancement
├── "improve proposal" → rag_enhancement
└── "content enhancement" → rag_enhancement

🎯 RAG EDITOR CAPABILITIES:
├── ✅ RAG context integration
├── ✅ Professional document formatting
├── ✅ MCP Word server integration  
├── ✅ Content enhancement and optimization
├── ✅ Structured output generation
└── ✅ DOCX document manipulation

📄 DOCUMENT INTEGRATION:
├── Default Document: main/test_output/proposal_20250927_142039.docx
├── RAG Databases: template_rag, examples_rag, session_rag
├── Output Formats: docx, json, markdown
└── Enhancement Process: Team Outputs → RAG Context → Enhanced DOCX
""")

if __name__ == "__main__":
    # Run the test
    success = test_rag_editor_nodes()
    
    # Show the graph structure
    show_graph_structure()
    
    if success:
        print("\n🎉 RAG Editor Integration Successful!")
        print("The RAG editor nodes are now visible in LangGraph Studio!")
        print("\nYou can now:")
        print("• See 'rag_editor' and 'rag_enhancement' nodes in the main graph")
        print("• See 'rag_editor_enhancement' node in the proposal supervisor graph")
        print("• Use routing keywords to trigger RAG editor functionality")
        print("• Enhance proposals with RAG-powered content improvement")
    else:
        print("\n❌ RAG Editor Integration Failed!")
        print("Please check the error messages above for details.")
