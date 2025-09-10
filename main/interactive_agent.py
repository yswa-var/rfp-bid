#!/usr/bin/env python3
"""
Interactive RFP RAG Agent
A command-line interface for querying documents using the RAG agent.
"""

import os
import sys
from dotenv import load_dotenv
from src.agent.graph import graph

def main():
    """Run the interactive RAG agent."""
    # Load environment variables
    load_dotenv()
    
    # Check if API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not found in environment variables")
        print("Please add your OpenAI API key to the .env file")
        sys.exit(1)
    
    print("🤖 RFP RAG Agent - Interactive Mode")
    print("=" * 50)
    print("Ask questions about the documents in the knowledge base.")
    print("Type 'quit', 'exit', or 'q' to exit.")
    print("Type 'help' for available commands.")
    print("=" * 50)
    
    while True:
        try:
            # Get user input
            question = input("\n💬 Your question: ").strip()
            
            # Handle special commands
            if question.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            elif question.lower() == 'help':
                show_help()
                continue
            elif question.lower() == 'examples':
                show_examples()
                continue
            elif not question:
                print("❓ Please enter a question.")
                continue
            
            # Process the question
            print("\n🔍 Processing your question...")
            result = graph.invoke({"question": question})
            
            # Display results
            if result.get("error"):
                print(f"❌ Error: {result['error']}")
            else:
                print("\n📝 Answer:")
                print("-" * 40)
                print(result.get("answer", "No answer generated"))
                print("-" * 40)
                
                # Show sources if available
                sources = result.get("sources", [])
                if sources:
                    print("\n📚 Sources:")
                    for i, source in enumerate(sources, 1):
                        print(f"  {i}. {source.get('file', 'Unknown')} - Page {source.get('page', 'Unknown')}")
                        if source.get('author') != 'Unknown':
                            print(f"     Author: {source.get('author')}")
        
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ An error occurred: {e}")

def show_help():
    """Display help information."""
    print("\n📖 Available Commands:")
    print("  help     - Show this help message")
    print("  examples - Show example questions")
    print("  quit/exit/q - Exit the application")
    print("\n💡 Tips:")
    print("  - Ask specific questions about the documents")
    print("  - Questions about policies, costs, estimates work well")
    print("  - The agent will provide sources for its answers")

def show_examples():
    """Display example questions."""
    print("\n🎯 Example Questions:")
    print("  • What are the estimates for green hydrogen production cost according to KPMG?")
    print("  • What are the benefits of the National Green Hydrogen Mission?")
    print("  • What are the policy recommendations for green hydrogen?")
    print("  • Who are the key stakeholders in green hydrogen development?")
    print("  • What are the challenges in green hydrogen production?")

if __name__ == "__main__":
    main()
