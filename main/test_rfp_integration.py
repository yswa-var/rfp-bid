"""
Quick Test Script for RFP Team Integration

This script runs basic tests to verify the RFP team integration is working correctly.
"""

import os
import sys
from pathlib import Path

# Add src to path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))


def test_imports():
    """Test that all necessary imports work."""
    print("Testing imports...")
    try:
        from agent.state import MessagesState
        from agent.agents import RFPProposalTeam
        from agent.router import supervisor_router, rfp_team_router, rfp_to_docx_router
        from agent.graph import graph
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


def test_rfp_team_initialization():
    """Test RFP team can be initialized."""
    print("\nTesting RFP team initialization...")
    try:
        from agent.agents import RFPProposalTeam
        team = RFPProposalTeam()
        print("✅ RFP team initialized successfully")
        print(f"   • Has finance_node: {hasattr(team, 'finance_node')}")
        print(f"   • Has technical_node: {hasattr(team, 'technical_node')}")
        print(f"   • Has legal_node: {hasattr(team, 'legal_node')}")
        print(f"   • Has qa_node: {hasattr(team, 'qa_node')}")
        print(f"   • Has rfp_supervisor: {hasattr(team, 'rfp_supervisor')}")
        return True
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_state_structure():
    """Test that state has all required fields."""
    print("\nTesting state structure...")
    try:
        from agent.state import MessagesState
        from typing import get_type_hints
        
        # Get type hints
        hints = get_type_hints(MessagesState)
        
        required_fields = [
            'messages', 'chunks', 'pdf_paths', 'task_completed',
            'rfp_content', 'current_rfp_node', 'rfp_query'
        ]
        
        print("✅ State structure:")
        for field in required_fields:
            has_field = field in hints
            status = "✓" if has_field else "✗"
            print(f"   {status} {field}: {hints.get(field, 'MISSING')}")
        
        return all(field in hints for field in required_fields)
    except Exception as e:
        print(f"❌ State structure test failed: {e}")
        return False


def test_routers():
    """Test router functions exist and are callable."""
    print("\nTesting routers...")
    try:
        from agent.router import supervisor_router, rfp_team_router, rfp_to_docx_router
        from langchain_core.messages import HumanMessage
        
        # Test supervisor router
        test_state = {
            "messages": [HumanMessage(content="Generate RFP finance content")],
            "rfp_content": {},
            "current_rfp_node": "finance"
        }
        
        result = supervisor_router(test_state)
        print(f"✅ supervisor_router works (result: {result})")
        
        # Test RFP team router
        result = rfp_team_router(test_state)
        print(f"✅ rfp_team_router works (result: {result})")
        
        # Test RFP to DOCX router
        result = rfp_to_docx_router(test_state)
        print(f"✅ rfp_to_docx_router works (result: {result})")
        
        return True
    except Exception as e:
        print(f"❌ Router test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_graph_compilation():
    """Test that the graph compiles successfully."""
    print("\nTesting graph compilation...")
    try:
        from agent.graph import graph
        print("✅ Graph compiled successfully")
        print(f"   • Graph type: {type(graph)}")
        print(f"   • Has invoke: {hasattr(graph, 'invoke')}")
        return True
    except Exception as e:
        print(f"❌ Graph compilation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_simple_invocation():
    """Test a simple graph invocation (requires API key)."""
    print("\nTesting simple graph invocation...")
    
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Skipping invocation test (no API key)")
        return True
    
    try:
        from agent.graph import graph
        from langchain_core.messages import HumanMessage
        
        print("   Invoking graph with test query...")
        result = graph.invoke({
            "messages": [HumanMessage(content="Hello, can you help with RFP?")],
            "chunks": [],
            "pdf_paths": [],
            "task_completed": False,
            "iteration_count": 0,
            "confidence_score": None,
            "follow_up_questions": [],
            "parsed_response": None,
            "rfp_content": {},
            "current_rfp_node": None,
            "rfp_query": None,
            "rfp_team_completed": False,
            "document_path": None
        })
        
        print("✅ Graph invocation successful")
        print(f"   • Returned {len(result.get('messages', []))} messages")
        print(f"   • Has rfp_content: {'rfp_content' in result}")
        
        return True
    except Exception as e:
        print(f"❌ Invocation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 80)
    print("RFP TEAM INTEGRATION - QUICK TEST SUITE")
    print("=" * 80)
    
    tests = [
        ("Imports", test_imports),
        ("RFP Team Initialization", test_rfp_team_initialization),
        ("State Structure", test_state_structure),
        ("Routers", test_routers),
        ("Graph Compilation", test_graph_compilation),
        ("Simple Invocation", test_simple_invocation),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Test '{name}' crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print("\n" + "=" * 80)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 80)
    
    if passed == total:
        print("\n🎉 All tests passed! Integration is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

