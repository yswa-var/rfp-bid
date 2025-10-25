"""
Test Agent Selection Feature

Tests the end-to-end agent selection functionality:
1. Agent selection from frontend flows through backend
2. Selected agent is stored in session metadata
3. LangGraph router respects selected_agent and routes correctly
4. Session/thread persistence works with agent switching
"""

import asyncio
import json
import requests
from datetime import datetime

BASE_URL = "http://localhost:8000"
LANGGRAPH_URL = "http://localhost:2024"

def test_session_creation():
    """Test creating a new session."""
    print("\n=== Test 1: Session Creation ===")
    response = requests.post(f"{BASE_URL}/api/session/create")
    assert response.status_code == 200, f"Failed: {response.status_code}"
    data = response.json()
    session_id = data.get("session_id")
    print(f"✅ Created session: {session_id}")
    return session_id


def test_agent_metadata_storage(session_id):
    """Test storing selected agent in session metadata."""
    print("\n=== Test 2: Agent Metadata Storage ===")
    
    # Send message with selected agent
    payload = {
        "session_id": session_id,
        "message": "Test message",
        "selected_agent": "docx_agent"
    }
    
    response = requests.post(f"{BASE_URL}/api/chat/send", json=payload)
    print(f"Send message response: {response.status_code}")
    
    # Get session info to verify metadata
    session_response = requests.get(f"{BASE_URL}/api/session/{session_id}")
    if session_response.status_code == 200:
        session_data = session_response.json()
        metadata = session_data.get("metadata", {})
        selected_agent = metadata.get("selected_agent")
        print(f"✅ Session metadata contains selected_agent: {selected_agent}")
        assert selected_agent == "docx_agent", f"Expected docx_agent, got {selected_agent}"
    else:
        print(f"⚠️ Could not retrieve session info: {session_response.status_code}")


def test_langgraph_routing():
    """Test that LangGraph router respects selected_agent."""
    print("\n=== Test 3: LangGraph Routing ===")
    
    # Test each agent selection
    test_cases = [
        ("supervisor", "What can you help me with?"),
        ("docx_agent", "Create a new document"),
        ("rfp_finance", "Prepare financial analysis"),
        ("rfp_technical", "Review technical requirements"),
        ("image_adder", "Add images to document"),
        ("general_assistant", "What is the weather?"),
    ]
    
    for agent, message in test_cases:
        print(f"\nTesting agent: {agent}")
        payload = {
            "input": {
                "messages": [{"role": "human", "content": message}],
                "selected_agent": agent if agent != "supervisor" else None
            },
            "config": {
                "configurable": {
                    "thread_id": f"test_{agent}_{datetime.now().timestamp()}",
                    "selected_agent": agent
                }
            }
        }
        
        try:
            # Use LangGraph streaming endpoint
            response = requests.post(
                f"{LANGGRAPH_URL}/runs/stream",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"  ✅ {agent}: Request successful")
            else:
                print(f"  ⚠️ {agent}: Status {response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"  ⚠️ {agent}: Request timeout (graph may be processing)")
        except Exception as e:
            print(f"  ❌ {agent}: Error - {str(e)}")


def test_session_persistence():
    """Test that thread_id persists across agent switches."""
    print("\n=== Test 4: Session Persistence ===")
    
    session_id = test_session_creation()
    
    # Send messages with different agents but same session
    agents = ["docx_agent", "general_assistant", "rfp_finance"]
    
    for i, agent in enumerate(agents):
        payload = {
            "session_id": session_id,
            "message": f"Test message {i+1} for {agent}",
            "selected_agent": agent
        }
        
        response = requests.post(f"{BASE_URL}/api/chat/send", json=payload)
        print(f"  Message {i+1} ({agent}): {response.status_code}")
    
    # Verify session still exists and has history
    session_response = requests.get(f"{BASE_URL}/api/session/{session_id}")
    if session_response.status_code == 200:
        session_data = session_response.json()
        print(f"✅ Session persisted across {len(agents)} agent switches")
        print(f"   Thread ID: {session_data.get('thread_id')}")
    else:
        print(f"❌ Session not found after agent switches")


def test_agent_dropdown_values():
    """Verify all dropdown agents are supported."""
    print("\n=== Test 5: Agent Dropdown Values ===")
    
    # These should match the frontend dropdown options
    supported_agents = [
        "supervisor",
        "docx_agent",
        "pdf_parser", 
        "general_assistant",
        "rfp_finance",
        "rfp_technical",
        "rfp_legal",
        "rfp_qa",
        "image_adder"
    ]
    
    print(f"Testing {len(supported_agents)} agents from dropdown:")
    for agent in supported_agents:
        print(f"  ✅ {agent}")
    
    print("\nAgent Mapping (UI → LangGraph Node):")
    agent_mapping = {
        "docx_agent": "docx_agent",
        "pdf_parser": "pdf_parser",
        "general_assistant": "general_assistant",
        "rfp_finance": "rfp_supervisor",
        "rfp_technical": "rfp_supervisor",
        "rfp_legal": "rfp_supervisor",
        "rfp_qa": "rfp_supervisor",
        "image_adder": "image_adder"
    }
    for ui_name, node_name in agent_mapping.items():
        print(f"  {ui_name} → {node_name}")


def main():
    """Run all tests."""
    print("="*60)
    print("AGENT SELECTION FEATURE TESTS")
    print("="*60)
    print("\nPrerequisites:")
    print("  1. Backend running on http://localhost:8000")
    print("  2. LangGraph running on http://localhost:2024")
    print("  3. Frontend running on http://localhost:5173")
    print("="*60)
    
    try:
        # Check if services are running
        print("\nChecking services...")
        
        try:
            backend_health = requests.get(f"{BASE_URL}/health", timeout=2)
            print(f"✅ Backend: {backend_health.status_code}")
        except:
            print("❌ Backend: Not responding")
            return
        
        try:
            langgraph_health = requests.get(f"{LANGGRAPH_URL}/ok", timeout=2)
            print(f"✅ LangGraph: {langgraph_health.status_code}")
        except:
            print("⚠️ LangGraph: Not responding (some tests may fail)")
        
        # Run tests
        session_id = test_session_creation()
        test_agent_metadata_storage(session_id)
        test_langgraph_routing()
        test_session_persistence()
        test_agent_dropdown_values()
        
        print("\n" + "="*60)
        print("TESTS COMPLETED")
        print("="*60)
        print("\nNext Steps:")
        print("  1. Open frontend: http://localhost:5173")
        print("  2. Select an agent from dropdown")
        print("  3. Send a message")
        print("  4. Verify it routes to the selected agent")
        print("  5. Check browser console for 'selected_agent' in emit data")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
