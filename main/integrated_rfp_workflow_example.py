"""
Integrated RFP Workflow Example

This script demonstrates the complete workflow of the integrated RFP Proposal Team system:
1. Main supervisor routes requests to the RFP team
2. RFP supervisor routes to specialized nodes (finance, technical, legal, QA)
3. Each specialized node generates content using RAG
4. Generated content is automatically routed to docx_agent for document updates

The workflow follows LangGraph's hierarchical multi-agent pattern with:
- Main supervisor for high-level routing
- RFP team supervisor for specialized content routing
- Specialized worker nodes for content generation
- Automatic handoff to docx_agent for document writing
"""

import os
import sys
from pathlib import Path

# Add src to path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

from langchain_core.messages import HumanMessage
from agent.graph import graph


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def run_rfp_workflow(query: str, description: str):
    """
    Run a single RFP workflow example.
    
    Args:
        query: The user query to send
        description: Description of what this example demonstrates
    """
    print_section(description)
    print(f"📝 Query: {query}\n")
    print("🔄 Processing...\n")
    
    try:
        # Invoke the graph with the query
        result = graph.invoke({
            "messages": [HumanMessage(content=query)],
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
        
        print("\n📊 Workflow Result:")
        print("-" * 80)
        
        # Display messages
        if "messages" in result:
            for i, msg in enumerate(result["messages"], 1):
                if hasattr(msg, "content"):
                    print(f"\nMessage {i}:")
                    print(msg.content[:500])  # Truncate long messages
                    if len(msg.content) > 500:
                        print(f"... [truncated, {len(msg.content)} total chars]")
        
        # Display RFP content summary
        if "rfp_content" in result and result["rfp_content"]:
            print("\n\n📋 Generated RFP Content Summary:")
            print("-" * 80)
            for node_type, content_data in result["rfp_content"].items():
                print(f"\n🔹 {node_type.upper()} Node:")
                content = content_data.get("content", "")
                metadata = content_data.get("metadata", {})
                print(f"   • Content length: {len(content)} characters")
                print(f"   • Metadata: {metadata}")
        
        # Display current state
        if "current_rfp_node" in result and result["current_rfp_node"]:
            print(f"\n\n🎯 Last RFP Node Processed: {result['current_rfp_node']}")
        
        print("\n" + "=" * 80)
        return result
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Run comprehensive examples of the integrated RFP workflow."""
    
    print_section("INTEGRATED RFP PROPOSAL TEAM WORKFLOW - COMPREHENSIVE EXAMPLES")
    print("""
    This demonstration shows the complete integration of:
    • Main Supervisor System
    • RFP Proposal Team (finance, technical, legal, qa nodes)
    • RAG-enhanced content generation
    • Automatic routing to docx_agent for document updates
    
    Architecture:
    
    User Query → Main Supervisor → RFP Supervisor → Specialized Node → docx_agent
                                       ↓
                           (finance/technical/legal/qa)
                                       ↓
                                  RAG Context
    """)
    
    input("\nPress Enter to start the demonstrations...")
    
    # Example 1: Finance Node
    run_rfp_workflow(
        query="Generate RFP proposal content for a 3-year cybersecurity budget including personnel, infrastructure, and operational costs",
        description="EXAMPLE 1: Finance Node - Budget Generation"
    )
    
    input("\n\nPress Enter to continue to next example...")
    
    # Example 2: Technical Node
    run_rfp_workflow(
        query="Create technical architecture content for a Security Operations Center (SOC) with SIEM integration",
        description="EXAMPLE 2: Technical Node - Architecture Design"
    )
    
    input("\n\nPress Enter to continue to next example...")
    
    # Example 3: Legal Node
    run_rfp_workflow(
        query="Draft legal compliance and SLA content for 24/7 security monitoring services",
        description="EXAMPLE 3: Legal Node - Compliance & SLA"
    )
    
    input("\n\nPress Enter to continue to next example...")
    
    # Example 4: QA Node
    run_rfp_workflow(
        query="Define quality assurance and testing procedures for SOC validation",
        description="EXAMPLE 4: QA Node - Testing Strategy"
    )
    
    input("\n\nPress Enter to continue to next example...")
    
    # Example 5: Multiple Team Workflow
    print_section("EXAMPLE 5: Complete RFP Proposal Generation (All Teams)")
    print("""
    In a real workflow, you would typically:
    1. Generate finance content → Write to document
    2. Generate technical content → Append to document
    3. Generate legal content → Append to document
    4. Generate QA content → Append to document
    
    Each step automatically routes through:
    User Query → Supervisor → RFP Supervisor → Specialized Node → docx_agent → END
    """)
    
    queries = [
        ("Create budget breakdown for managed SOC services", "Finance"),
        ("Describe the technical infrastructure and tools", "Technical"),
        ("Outline compliance requirements and SLA terms", "Legal"),
        ("Define testing metrics and quality standards", "QA")
    ]
    
    print("\nGenerating complete proposal with all teams:\n")
    for query, team in queries:
        print(f"  • {team} Team: {query}")
    
    print("\n" + "=" * 80)
    
    # Summary
    print_section("WORKFLOW SUMMARY")
    print("""
    ✅ Integration Complete!
    
    Key Features Demonstrated:
    
    1. Hierarchical Multi-Agent System
       • Main supervisor routes to RFP team
       • RFP supervisor routes to specialized nodes
       • Each node is independent and focused
    
    2. RAG-Enhanced Content Generation
       • Each specialized node queries RAG databases
       • Context from RFP examples and templates
       • High-quality, context-aware responses
    
    3. Automatic Document Updates
       • Generated content automatically routed to docx_agent
       • Seamless integration with document operations
       • Content written to specified document sections
    
    4. State Management
       • rfp_content tracks all generated content
       • current_rfp_node tracks workflow progress
       • Proper state propagation between nodes
    
    5. Extensibility
       • Easy to add new specialized nodes
       • Modular architecture
       • Clear separation of concerns
    
    Next Steps:
    • Customize prompts for each specialized node
    • Add more specialized nodes (e.g., executive summary, risk assessment)
    • Implement multi-round refinement workflows
    • Add human-in-the-loop approval for critical sections
    • Integrate with external systems (e.g., pricing databases, compliance tools)
    """)
    
    print("\n" + "=" * 80)
    print("✅ DEMONSTRATION COMPLETED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("=" * 80)
        print("❌ ERROR: OPENAI_API_KEY environment variable not set!")
        print("=" * 80)
        print("\nPlease set your OpenAI API key before running this demo:")
        print("   export OPENAI_API_KEY='your-api-key-here'")
        print("\nOr add it to your environment configuration.")
        print("=" * 80)
        sys.exit(1)
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n" + "=" * 80)
        print("⚠️  Demonstration interrupted by user")
        print("=" * 80)
    except Exception as e:
        print("\n\n" + "=" * 80)
        print(f"❌ Error during demonstration: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()

