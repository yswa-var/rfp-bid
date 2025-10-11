"""
Example Usage of RFP Proposal Agent

This script demonstrates how to use the RFPProposalAgent class for generating
RFP proposal content across different domains (finance, technical, legal, QA).
"""

import os
import sys
from pathlib import Path

# Add src to path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

from agent.RFP_proposal_agent import RFPProposalAgent


def main():
    print("=" * 80)
    print("RFP PROPOSAL AGENT - COMPREHENSIVE DEMO")
    print("=" * 80)
    
    # Initialize the agent
    print("\n🚀 Initializing RFP Proposal Agent...")
    agent = RFPProposalAgent(response_file="demo_responses.json")
    print("✅ Agent initialized successfully!")
    
    # ========================================================================
    # 1. Test Chat GPT (General conversation)
    # ========================================================================
    print("\n" + "=" * 80)
    print("1️⃣  CHAT GPT - General Conversation")
    print("=" * 80)
    
    chat_queries = [
        "What are the key components of a successful RFP proposal?",
        "How should I structure the executive summary?",
    ]
    
    for query in chat_queries:
        print(f"\n💬 Query: {query}")
        response = agent.chat_gpt(query)
        print(f"🤖 Response:\n{response}\n")
    
    # ========================================================================
    # 2. Test Query RAG (Database queries)
    # ========================================================================
    print("\n" + "=" * 80)
    print("2️⃣  QUERY RAG - Database Search")
    print("=" * 80)
    
    rag_queries = [
        "cybersecurity requirements for SOC",
        "managed security service provider qualifications",
    ]
    
    for query in rag_queries:
        print(f"\n🔍 Query: {query}")
        results = agent.query_rag(query, k=3, database="all")
        print(f"📊 Found {len(results)} results:")
        for i, result in enumerate(results[:2], 1):
            print(f"\n   Result {i}:")
            print(f"   • Database: {result.get('database', 'unknown')}")
            print(f"   • Source: {result.get('source_file', 'Unknown')}")
            print(f"   • Accuracy: {result.get('accuracy', 0):.2%}")
            print(f"   • Preview: {result.get('preview', '')[:150]}...")
    
    # ========================================================================
    # 3. Test Finance Node
    # ========================================================================
    print("\n" + "=" * 80)
    print("3️⃣  FINANCE NODE - Budget and Cost Analysis")
    print("=" * 80)
    
    finance_queries = [
        "Create a detailed 3-year budget for a managed SOC service including personnel, infrastructure, and operational costs",
        "Provide a cost-benefit analysis for implementing a 24/7 security operations center",
    ]
    
    for query in finance_queries:
        print(f"\n💰 Query: {query}")
        result = agent.finance_node(query, k=5)
        
        if result['success']:
            print(f"✅ Generated finance content:")
            print(f"📝 Response:\n{result['response']}\n")
            print(f"📚 Used {len(result['context'])} context sources")
            print(f"🎯 Average accuracy: {result['metadata'].get('avg_accuracy', 0):.2%}")
        else:
            print(f"❌ Error: {result['response']}")
    
    # ========================================================================
    # 4. Test Technical Node
    # ========================================================================
    print("\n" + "=" * 80)
    print("4️⃣  TECHNICAL NODE - Technical Architecture")
    print("=" * 80)
    
    technical_queries = [
        "Describe the technical architecture for a Security Operations Center (SOC) with SIEM integration",
        "Outline the security monitoring tools and technologies required for threat detection",
    ]
    
    for query in technical_queries:
        print(f"\n🔧 Query: {query}")
        result = agent.technical_node(query, k=5)
        
        if result['success']:
            print(f"✅ Generated technical content:")
            print(f"📝 Response:\n{result['response']}\n")
            print(f"📚 Used {len(result['context'])} context sources")
        else:
            print(f"❌ Error: {result['response']}")
    
    # ========================================================================
    # 5. Test Legal Node
    # ========================================================================
    print("\n" + "=" * 80)
    print("5️⃣  LEGAL NODE - Compliance and Contracts")
    print("=" * 80)
    
    legal_queries = [
        "Draft service level agreements (SLA) for 24/7 security monitoring with 99.9% uptime guarantee",
        "Outline data protection and compliance requirements for handling sensitive security information",
    ]
    
    for query in legal_queries:
        print(f"\n⚖️  Query: {query}")
        result = agent.legal_node(query, k=5)
        
        if result['success']:
            print(f"✅ Generated legal content:")
            print(f"📝 Response:\n{result['response']}\n")
            print(f"📚 Used {len(result['context'])} context sources")
        else:
            print(f"❌ Error: {result['response']}")
    
    # ========================================================================
    # 6. Test QA Node
    # ========================================================================
    print("\n" + "=" * 80)
    print("6️⃣  QA NODE - Testing and Quality Assurance")
    print("=" * 80)
    
    qa_queries = [
        "Create a comprehensive testing strategy for validating SOC security monitoring capabilities",
        "Define quality metrics and KPIs for measuring SOC performance and effectiveness",
    ]
    
    for query in qa_queries:
        print(f"\n🧪 Query: {query}")
        result = agent.qa_node(query, k=5)
        
        if result['success']:
            print(f"✅ Generated QA content:")
            print(f"📝 Response:\n{result['response']}\n")
            print(f"📚 Used {len(result['context'])} context sources")
        else:
            print(f"❌ Error: {result['response']}")
    
    # ========================================================================
    # 7. Response Summary and Tracking
    # ========================================================================
    print("\n" + "=" * 80)
    print("7️⃣  RESPONSE SUMMARY AND TRACKING")
    print("=" * 80)
    
    summary = agent.get_response_summary()
    print("\n📊 Overall Summary:")
    print(f"   • Total Responses: {summary['total']}")
    print(f"   • First Response: {summary.get('first_response', 'N/A')}")
    print(f"   • Last Response: {summary.get('last_response', 'N/A')}")
    print("\n📈 Responses by Node Type:")
    for node_type, count in summary['by_node'].items():
        print(f"   • {node_type}: {count}")
    
    # Show sample of tracked responses
    print("\n📝 Sample of Tracked Responses (Last 3):")
    all_responses = agent.get_all_responses()
    for i, resp in enumerate(all_responses[-3:], 1):
        print(f"\n   Response {i}:")
        print(f"   • Node Type: {resp['node_type']}")
        print(f"   • Timestamp: {resp['timestamp']}")
        print(f"   • Query: {resp['query'][:80]}...")
        print(f"   • Response Length: {len(resp['response'])} characters")
        print(f"   • Context Sources: {len(resp.get('context', []))}")
    
    # ========================================================================
    # 8. Export Specific Node Responses
    # ========================================================================
    print("\n" + "=" * 80)
    print("8️⃣  EXPORT SPECIFIC NODE RESPONSES")
    print("=" * 80)
    
    # Get all finance responses
    finance_responses = agent.get_all_responses(node_type="finance")
    print(f"\n💰 Finance Node Responses: {len(finance_responses)}")
    
    # Get all technical responses
    technical_responses = agent.get_all_responses(node_type="technical")
    print(f"🔧 Technical Node Responses: {len(technical_responses)}")
    
    # Get all legal responses
    legal_responses = agent.get_all_responses(node_type="legal")
    print(f"⚖️  Legal Node Responses: {len(legal_responses)}")
    
    # Get all QA responses
    qa_responses = agent.get_all_responses(node_type="qa")
    print(f"🧪 QA Node Responses: {len(qa_responses)}")
    
    print("\n" + "=" * 80)
    print("✅ DEMO COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    print(f"\n💾 All responses have been saved to: {agent.response_file}")
    print("📖 You can review the JSON file for detailed tracking information")


if __name__ == "__main__":
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable not set!")
        print("Please set it before running this demo:")
        print("   export OPENAI_API_KEY='your-api-key-here'")
        sys.exit(1)
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()

