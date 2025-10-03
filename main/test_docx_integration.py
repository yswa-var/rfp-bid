"""Test script to verify DOCX agent integration with the main supervisor graph."""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from langchain_core.messages import HumanMessage
from src.agent.graph import graph


def test_docx_routing():
    """Test that DOCX-related queries are routed to the DOCX agent."""
    
    print("=" * 80)
    print("Testing DOCX Agent Integration")
    print("=" * 80)
    
    test_cases = [
        {
            "description": "Test DOCX reading request",
            "message": "Can you read example.docx?",
            "expected_agent": "docx_agent"
        },
        {
            "description": "Test Word document editing request",
            "message": "Edit the Word document to add a title",
            "expected_agent": "docx_agent"
        },
        {
            "description": "Test document creation request",
            "message": "Create a new document with project notes",
            "expected_agent": "docx_agent"
        },
        {
            "description": "Test PDF parsing request (should not go to docx_agent)",
            "message": "Parse the PDF files in the directory",
            "expected_agent": "pdf_parser"
        },
        {
            "description": "Test general query (should not go to docx_agent)",
            "message": "What is the capital of France?",
            "expected_agent": "general_assistant"
        }
    ]
    
    print("\nRunning routing tests...\n")
    
    for i, test in enumerate(test_cases, 1):
        print(f"Test {i}: {test['description']}")
        print(f"Message: '{test['message']}'")
        print(f"Expected routing: {test['expected_agent']}")
        
        try:
            # Just test the routing, not full execution
            from src.agent.router import supervisor_router
            from src.agent.state import MessagesState
            
            state = {
                "messages": [
                    HumanMessage(content=test['message'], name="user")
                ],
                "chunks": [],
                "pdf_paths": [],
                "task_completed": False,
                "iteration_count": 0,
                "confidence_score": None,
                "follow_up_questions": [],
                "parsed_response": None,
                "teams_completed": None,
                "team_responses": None,
                "team_sequence": None,
                "next_team": None,
                "rfp_content": None
            }
            
            result = supervisor_router(state)
            
            status = "✅ PASS" if result == test['expected_agent'] else "❌ FAIL"
            print(f"Result: {result}")
            print(f"Status: {status}")
            
            if result != test['expected_agent']:
                print(f"  Expected: {test['expected_agent']}, Got: {result}")
            
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
        
        print("-" * 80)
    
    print("\n" + "=" * 80)
    print("Graph Structure Test")
    print("=" * 80)
    
    try:
        print("\nVerifying graph compilation...")
        print(f"Graph type: {type(graph)}")
        print(f"Graph name: {getattr(graph, 'name', 'N/A')}")
        
        # Get the nodes
        if hasattr(graph, 'nodes'):
            print(f"\nNodes in graph:")
            for node_name in graph.nodes:
                print(f"  - {node_name}")
        
        # Check if docx_agent is in the graph
        nodes = list(graph.nodes.keys()) if hasattr(graph, 'nodes') else []
        if 'docx_agent' in nodes:
            print("\n✅ DOCX agent successfully integrated!")
        else:
            print("\n❌ DOCX agent NOT found in graph nodes")
            
    except Exception as e:
        print(f"❌ ERROR verifying graph: {str(e)}")
    
    print("\n" + "=" * 80)
    print("Integration Test Complete")
    print("=" * 80)


if __name__ == "__main__":
    test_docx_routing()

