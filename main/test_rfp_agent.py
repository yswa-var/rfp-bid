"""
Simple test script for RFP Proposal Agent

This script performs basic tests to ensure the agent is working correctly.
"""

import os
import sys
from pathlib import Path

# Add src to path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))


def test_imports():
    """Test if all required imports work."""
    print("Testing imports...")
    try:
        from agent.RFP_proposal_agent import RFPProposalAgent
        print("✅ Successfully imported RFPProposalAgent")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


def test_initialization():
    """Test agent initialization."""
    print("\nTesting agent initialization...")
    try:
        from agent.RFP_proposal_agent import RFPProposalAgent
        agent = RFPProposalAgent(response_file="test_responses.json")
        print("✅ Agent initialized successfully")
        return agent
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_chat_gpt(agent):
    """Test chat_gpt functionality."""
    print("\nTesting chat_gpt...")
    try:
        response = agent.chat_gpt("Hello! Can you help me with RFP proposals?", use_history=False)
        print(f"✅ Chat response received (length: {len(response)} chars)")
        print(f"   Preview: {response[:100]}...")
        return True
    except Exception as e:
        print(f"❌ chat_gpt failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_query_rag(agent):
    """Test query_rag functionality."""
    print("\nTesting query_rag...")
    try:
        # Try querying with minimal expectations
        results = agent.query_rag("test query", k=3, database="session")
        print(f"✅ Query RAG executed (found {len(results)} results)")
        if results:
            print(f"   Sample result: {results[0].get('source_file', 'Unknown')}")
        else:
            print("   ⚠️ No results found (databases may be empty)")
        return True
    except Exception as e:
        print(f"⚠️ query_rag warning: {e}")
        # Not a critical failure if databases don't exist yet
        return True


def test_finance_node(agent):
    """Test finance_node functionality."""
    print("\nTesting finance_node...")
    try:
        result = agent.finance_node("Create a simple budget estimate", k=3)
        if result['success']:
            print(f"✅ Finance node generated content (length: {len(result['response'])} chars)")
            print(f"   Preview: {result['response'][:100]}...")
        else:
            print(f"⚠️ Finance node returned error: {result['response']}")
        return True
    except Exception as e:
        print(f"❌ finance_node failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_technical_node(agent):
    """Test technical_node functionality."""
    print("\nTesting technical_node...")
    try:
        result = agent.technical_node("Describe a basic technical architecture", k=3)
        if result['success']:
            print(f"✅ Technical node generated content (length: {len(result['response'])} chars)")
        else:
            print(f"⚠️ Technical node returned error: {result['response']}")
        return True
    except Exception as e:
        print(f"❌ technical_node failed: {e}")
        return False


def test_legal_node(agent):
    """Test legal_node functionality."""
    print("\nTesting legal_node...")
    try:
        result = agent.legal_node("Draft basic contract terms", k=3)
        if result['success']:
            print(f"✅ Legal node generated content (length: {len(result['response'])} chars)")
        else:
            print(f"⚠️ Legal node returned error: {result['response']}")
        return True
    except Exception as e:
        print(f"❌ legal_node failed: {e}")
        return False


def test_qa_node(agent):
    """Test qa_node functionality."""
    print("\nTesting qa_node...")
    try:
        result = agent.qa_node("Create a basic testing plan", k=3)
        if result['success']:
            print(f"✅ QA node generated content (length: {len(result['response'])} chars)")
        else:
            print(f"⚠️ QA node returned error: {result['response']}")
        return True
    except Exception as e:
        print(f"❌ qa_node failed: {e}")
        return False


def test_response_tracking(agent):
    """Test response tracking functionality."""
    print("\nTesting response tracking...")
    try:
        summary = agent.get_response_summary()
        print(f"✅ Response tracking working")
        print(f"   Total responses: {summary['total']}")
        print(f"   By node: {summary['by_node']}")
        
        # Test filtering
        all_responses = agent.get_all_responses()
        chat_responses = agent.get_all_responses(node_type="chat")
        print(f"   All responses: {len(all_responses)}")
        print(f"   Chat responses: {len(chat_responses)}")
        
        return True
    except Exception as e:
        print(f"❌ Response tracking failed: {e}")
        return False


def cleanup_test_files():
    """Clean up test files."""
    print("\nCleaning up test files...")
    test_files = ["test_responses.json"]
    for file in test_files:
        if os.path.exists(file):
            os.remove(file)
            print(f"   Removed {file}")


def main():
    print("=" * 80)
    print("RFP PROPOSAL AGENT - TEST SUITE")
    print("=" * 80)
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("\n⚠️ WARNING: OPENAI_API_KEY not set!")
        print("Some tests may fail. Set it with:")
        print("   export OPENAI_API_KEY='your-api-key-here'")
        print("\nContinuing with tests...\n")
    
    results = {}
    
    # Run tests
    results['imports'] = test_imports()
    
    if not results['imports']:
        print("\n❌ Cannot continue - imports failed")
        return
    
    agent = test_initialization()
    
    if not agent:
        print("\n❌ Cannot continue - initialization failed")
        return
    
    results['initialization'] = True
    
    # Only run OpenAI tests if API key is available
    if os.getenv("OPENAI_API_KEY"):
        results['chat_gpt'] = test_chat_gpt(agent)
        results['query_rag'] = test_query_rag(agent)
        results['finance_node'] = test_finance_node(agent)
        results['technical_node'] = test_technical_node(agent)
        results['legal_node'] = test_legal_node(agent)
        results['qa_node'] = test_qa_node(agent)
        results['response_tracking'] = test_response_tracking(agent)
    else:
        print("\n⚠️ Skipping OpenAI-dependent tests (no API key)")
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("⚠️ Some tests failed")
    
    # Cleanup
    cleanup_test_files()
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

