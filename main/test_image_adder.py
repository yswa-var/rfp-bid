#!/usr/bin/env python3
"""
Test script for the Image Adder Node

This script demonstrates how to use the image adder feature to
intelligently insert images into document sections.
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to the path
_CURRENT_DIR = Path(__file__).resolve().parent
_SRC_DIR = _CURRENT_DIR / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from agent.graph import graph


async def test_basic_image_addition():
    """Test basic image addition to document."""
    print("=" * 60)
    print("TEST 1: Basic Image Addition")
    print("=" * 60)
    
    response = await graph.ainvoke({
        "messages": [
            {"role": "user", "content": "Add images to the document"}
        ]
    })
    
    print("\nResponse:")
    print(response["messages"][-1].content)
    print()


async def test_explicit_agent_call():
    """Test explicit call to image_adder agent."""
    print("=" * 60)
    print("TEST 2: Explicit Agent Call")
    print("=" * 60)
    
    response = await graph.ainvoke({
        "messages": [
            {"role": "user", "content": "Use image_adder to insert pictures"}
        ]
    })
    
    print("\nResponse:")
    print(response["messages"][-1].content)
    print()


async def test_insert_images_phrase():
    """Test with 'insert images' phrase."""
    print("=" * 60)
    print("TEST 3: Insert Images Phrase")
    print("=" * 60)
    
    response = await graph.ainvoke({
        "messages": [
            {"role": "user", "content": "Please insert images into relevant sections"}
        ]
    })
    
    print("\nResponse:")
    print(response["messages"][-1].content)
    print()


async def test_place_pictures():
    """Test with 'place pictures' phrase."""
    print("=" * 60)
    print("TEST 4: Place Pictures Phrase")
    print("=" * 60)
    
    response = await graph.ainvoke({
        "messages": [
            {"role": "user", "content": "Can you place pictures in the document?"}
        ]
    })
    
    print("\nResponse:")
    print(response["messages"][-1].content)
    print()


async def run_all_tests():
    """Run all test cases."""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + " " * 10 + "IMAGE ADDER NODE - TEST SUITE" + " " * 18 + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "═" * 58 + "╝")
    print("\n")
    
    # Run tests
    tests = [
        test_basic_image_addition,
        test_explicit_agent_call,
        test_insert_images_phrase,
        test_place_pictures
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            await test()
            passed += 1
            print("✅ Test passed\n")
        except Exception as e:
            failed += 1
            print(f"❌ Test failed: {str(e)}\n")
    
    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print("=" * 60)


async def demo_interactive():
    """Interactive demo mode."""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + " " * 10 + "IMAGE ADDER - INTERACTIVE MODE" + " " * 17 + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "═" * 58 + "╝")
    print("\n")
    print("This demo will show you how the image adder works.")
    print("You can ask it to add images to your document.")
    print("\nType 'quit' to exit.\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Exiting interactive mode...")
                break
            
            if not user_input:
                continue
            
            print("\nProcessing...\n")
            
            response = await graph.ainvoke({
                "messages": [
                    {"role": "user", "content": user_input}
                ]
            })
            
            print("Assistant:")
            print(response["messages"][-1].content)
            print("\n" + "-" * 60 + "\n")
            
        except KeyboardInterrupt:
            print("\n\nInterrupted. Exiting...")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}\n")


def print_usage():
    """Print usage information."""
    print("""
Usage: python test_image_adder.py [mode]

Modes:
  test        Run automated tests (default)
  interactive Run in interactive mode for manual testing
  help        Show this help message

Examples:
  python test_image_adder.py
  python test_image_adder.py test
  python test_image_adder.py interactive
  python test_image_adder.py help
    """)


def main():
    """Main entry point."""
    mode = sys.argv[1] if len(sys.argv) > 1 else "test"
    
    if mode == "help":
        print_usage()
    elif mode == "interactive":
        asyncio.run(demo_interactive())
    elif mode == "test":
        asyncio.run(run_all_tests())
    else:
        print(f"Unknown mode: {mode}")
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()

