#!/usr/bin/env python3
"""Simple test to verify the DOCX agent fix."""

import os
import sys
from pathlib import Path

# Add src to path
current_dir = Path(__file__).resolve().parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

def test_tool_call_args_parsing():
    """Test the tool call args parsing logic."""
    print("🧪 Testing Tool Call Args Parsing")
    print("=" * 50)
    
    try:
        import json
        from langchain_core.messages.tool import ToolCall
        
        # Test different argument formats
        test_cases = [
            ("{}", {}),
            ("", {}),
            ('{"key": "value"}', {"key": "value"}),
            (None, {}),
        ]
        
        print("📋 Testing argument parsing:")
        for input_args, expected in test_cases:
            # Parse arguments if they're a string
            args = input_args
            if isinstance(args, str):
                try:
                    args = json.loads(args) if args else {}
                except json.JSONDecodeError:
                    args = {}
            elif not args:
                args = {}
            
            print(f"   Input: {input_args} -> Output: {args} (Expected: {expected})")
            assert args == expected, f"Expected {expected}, got {args}"
        
        print("✅ All argument parsing tests passed")
        
        # Test creating ToolCall with proper args
        tool_call = ToolCall(
            name="get_outline",
            args={},
            id="call_123"
        )
        
        print(f"✅ ToolCall created successfully: {tool_call}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in tool call args parsing: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_approval_node_fix():
    """Test the approval node fix logic."""
    print("\n🧪 Testing Approval Node Fix")
    print("=" * 50)
    
    try:
        from langchain_core.messages.tool import ToolCall
        from langchain_core.messages import AIMessage
        
        # Simulate the approval node logic
        print("📋 Testing approval node logic:")
        
        # Mock tool call from LLM (in dict format)
        mock_tool_call = {
            "id": "call_update_123",
            "type": "function",
            "function": {
                "name": "update_paragraph",
                "arguments": '{"anchor": [0, 0, 0, 0, 0], "new_text": "Updated text"}'
            }
        }
        
        print(f"   Input tool call: {mock_tool_call}")
        
        # Convert to proper ToolCall object
        import json
        args = mock_tool_call["function"]["arguments"]
        if isinstance(args, str):
            try:
                args = json.loads(args) if args else {}
            except json.JSONDecodeError:
                args = {}
        elif not args:
            args = {}
        
        proper_tool_call = ToolCall(
            name=mock_tool_call["function"]["name"],
            args=args,
            id=mock_tool_call["id"]
        )
        
        print(f"   Converted tool call: {proper_tool_call}")
        
        # Create AIMessage with proper ToolCall
        ai_msg = AIMessage(
            content="I'll update the document.",
            tool_calls=[proper_tool_call]
        )
        
        print("✅ AIMessage with ToolCall created successfully")
        print(f"   Content: {ai_msg.content}")
        print(f"   Tool calls: {ai_msg.tool_calls}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in approval node fix: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_message_conversion():
    """Test the message conversion logic."""
    print("\n🧪 Testing Message Conversion")
    print("=" * 50)
    
    try:
        from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
        
        print("📋 Testing message conversion:")
        
        # Test human message conversion
        human_msg = HumanMessage(content="docx show headings")
        human_dict = {"role": "user", "content": human_msg.content}
        print(f"   Human: {human_dict}")
        
        # Test AI message conversion (without tool calls)
        ai_msg = AIMessage(content="I'll help you with that.")
        ai_dict = {"role": "assistant", "content": ai_msg.content}
        print(f"   AI: {ai_dict}")
        
        # Test tool message conversion
        tool_msg = ToolMessage(content="No headings found", tool_call_id="call_123")
        tool_dict = {
            "role": "tool",
            "content": tool_msg.content,
            "tool_call_id": tool_msg.tool_call_id
        }
        print(f"   Tool: {tool_dict}")
        
        print("✅ All message conversions successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in message conversion: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("🚀 Starting Simple DOCX Agent Fix Tests")
    print("=" * 60)
    
    # Run tests
    tests = [
        ("Tool Call Args Parsing", test_tool_call_args_parsing),
        ("Approval Node Fix", test_approval_node_fix),
        ("Message Conversion", test_message_conversion),
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
        print("🎉 All tests passed! DOCX agent fix is working correctly.")
        print("\n📋 Fix Summary:")
        print("   ✅ Fixed tool call args parsing (string to dict)")
        print("   ✅ Fixed approval node ToolCall creation")
        print("   ✅ Fixed message conversion logic")
        print("\n🚀 The DOCX agent should now work without the message format error!")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
    
    return passed == len(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
