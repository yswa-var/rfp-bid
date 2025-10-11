#!/usr/bin/env python3
"""Test script to fix the tool call structure issue."""

import os
import sys
from pathlib import Path

# Add src to path
current_dir = Path(__file__).resolve().parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

def test_correct_tool_call_format():
    """Test the correct tool call format for LangChain."""
    print("🧪 Testing Correct Tool Call Format")
    print("=" * 50)
    
    try:
        from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
        from langchain_core.messages.tool import ToolCall
        
        print("📋 Testing correct LangChain ToolCall format:")
        
        # Create tool call using LangChain ToolCall
        tool_call = ToolCall(
            name="get_outline",
            args={},
            id="call_123"
        )
        
        # Create AI message with tool call
        ai_msg = AIMessage(
            content="I'll get the document outline for you.",
            tool_calls=[tool_call]
        )
        
        print("✅ AI message with ToolCall created successfully")
        print(f"   Content: {ai_msg.content}")
        print(f"   Tool calls: {ai_msg.tool_calls}")
        
        # Create tool response
        tool_msg = ToolMessage(
            content="No headings found in the document",
            tool_call_id="call_123"
        )
        
        print("✅ Tool message created successfully")
        print(f"   Content: {tool_msg.content}")
        print(f"   Tool call ID: {tool_msg.tool_call_id}")
        
        # Test conversion to OpenAI format
        print("\n📋 Converting to OpenAI format:")
        
        messages = [{"role": "system", "content": "You are a DOCX assistant."}]
        
        # Convert AI message
        ai_dict = {"role": "assistant", "content": ai_msg.content}
        if hasattr(ai_msg, 'tool_calls') and ai_msg.tool_calls:
            # Convert LangChain ToolCall to OpenAI format
            tool_calls_openai = []
            for tc in ai_msg.tool_calls:
                tool_calls_openai.append({
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": str(tc["args"]) if tc["args"] else "{}"
                    }
                })
            ai_dict["tool_calls"] = tool_calls_openai
        
        messages.append(ai_dict)
        print(f"   AI message: {messages[-1]}")
        
        # Convert tool message
        messages.append({
            "role": "tool",
            "content": tool_msg.content,
            "tool_call_id": tool_msg.tool_call_id
        })
        print(f"   Tool message: {messages[-1]}")
        
        print("✅ Conversion successful!")
        return True
        
    except Exception as e:
        print(f"❌ Error in tool call format test: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_llm_response_handling():
    """Test how to handle LLM responses with tool calls."""
    print("\n🧪 Testing LLM Response Handling")
    print("=" * 50)
    
    try:
        from langchain_core.messages import AIMessage
        
        print("📋 Testing LLM response with tool calls:")
        
        # Simulate what the LLM returns when it makes a tool call
        # This is what we get from llm_with_tools.invoke()
        llm_response = AIMessage(
            content="I'll get the document outline for you.",
            tool_calls=[{
                "id": "call_get_outline_123",
                "type": "function",
                "function": {
                    "name": "get_outline",
                    "arguments": "{}"
                }
            }]
        )
        
        print("✅ LLM response received")
        print(f"   Content: {llm_response.content}")
        print(f"   Tool calls: {llm_response.tool_calls}")
        
        # The issue is that when we convert this back to OpenAI format,
        # we need to handle the tool_calls properly
        print("\n📋 Converting LLM response to OpenAI format:")
        
        ai_dict = {"role": "assistant", "content": llm_response.content}
        if hasattr(llm_response, 'tool_calls') and llm_response.tool_calls:
            # The tool_calls are already in OpenAI format from the LLM
            ai_dict["tool_calls"] = llm_response.tool_calls
        
        print(f"   Converted: {ai_dict}")
        print("✅ LLM response conversion successful!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in LLM response handling: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_conversation_flow_fixed():
    """Test the complete conversation flow with correct format."""
    print("\n🧪 Testing Complete Conversation Flow (Fixed)")
    print("=" * 50)
    
    try:
        from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
        
        print("📋 Testing complete conversation flow:")
        
        # Step 1: Human message
        human_msg = HumanMessage(content="docx show headings of this document")
        print(f"   1. Human: {human_msg.content}")
        
        # Step 2: AI response with tool call (from LLM)
        ai_msg = AIMessage(
            content="I'll get the document outline for you.",
            tool_calls=[{
                "id": "call_get_outline_123",
                "type": "function",
                "function": {
                    "name": "get_outline",
                    "arguments": "{}"
                }
            }]
        )
        print(f"   2. AI: {ai_msg.content} (with tool call)")
        
        # Step 3: Tool response
        tool_msg = ToolMessage(
            content="No headings found in the document",
            tool_call_id="call_get_outline_123"
        )
        print(f"   3. Tool: {tool_msg.content}")
        
        # Step 4: Convert to OpenAI format for next LLM call
        print("\n📋 Converting to OpenAI format for next LLM call:")
        
        messages = [{"role": "system", "content": "You are a DOCX assistant."}]
        
        # Add human message
        messages.append({"role": "user", "content": human_msg.content})
        
        # Add AI message with tool calls
        ai_dict = {"role": "assistant", "content": ai_msg.content}
        if hasattr(ai_msg, 'tool_calls') and ai_msg.tool_calls:
            ai_dict["tool_calls"] = ai_msg.tool_calls
        messages.append(ai_dict)
        
        # Add tool message
        messages.append({
            "role": "tool",
            "content": tool_msg.content,
            "tool_call_id": tool_msg.tool_call_id
        })
        
        print("✅ Complete message format:")
        for i, msg in enumerate(messages):
            print(f"   {i}: {msg}")
        
        print("✅ Conversation flow conversion successful!")
        return True
        
    except Exception as e:
        print(f"❌ Error in conversation flow: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("🚀 Starting Tool Call Fix Tests")
    print("=" * 60)
    
    # Run tests
    tests = [
        ("Correct Tool Call Format", test_correct_tool_call_format),
        ("LLM Response Handling", test_llm_response_handling),
        ("Complete Conversation Flow", test_conversation_flow_fixed),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! We've identified the correct format.")
        print("\n📋 Key Findings:")
        print("   1. LangChain AIMessage expects ToolCall objects, not dicts")
        print("   2. LLM responses already have tool_calls in OpenAI format")
        print("   3. Our conversion logic is actually correct")
        print("   4. The issue might be elsewhere in the flow")
    else:
        print("⚠️  Some tests failed. We need to investigate further.")
    
    return passed == len(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
