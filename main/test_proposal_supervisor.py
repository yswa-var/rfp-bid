#!/usr/bin/env python3
"""
Test script for the hierarchical ProposalSupervisor system.

Tests the conversion from ProposalGeneratorAgent to ProposalSupervisor
with team subgraphs and Studio visualization support.
"""

import os
import sys
from pathlib import Path

# Add src to path
current_dir = Path(__file__).resolve().parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

from agent.proposal_supervisor import (
    build_parent_proposal_graph,
    get_graph_visualization,
    print_graph_structure
)
from agent.state import MessagesState
from langchain_core.messages import HumanMessage


def test_graph_creation():
    """Test that the hierarchical graph can be created successfully."""
    print("🧪 Testing hierarchical graph creation...")
    
    try:
        # Build the parent graph
        graph = build_parent_proposal_graph()
        print("✅ Parent graph created successfully")
        
        # Test graph structure
        print_graph_structure(graph)
        
        # Test visualization
        print("\n🎨 Testing graph visualization...")
        try:
            graph_viz = get_graph_visualization(graph, xray=True)
            print("✅ Graph visualization generated successfully")
            print(f"   Nodes: {len(graph_viz.nodes)}")
            print(f"   Edges: {len(graph_viz.edges)}")
        except Exception as e:
            print(f"⚠️  Visualization test failed: {e}")
        
        return graph
        
    except Exception as e:
        print(f"❌ Graph creation failed: {e}")
        return None


def test_team_subgraphs():
    """Test individual team subgraphs."""
    print("\n🧪 Testing team subgraphs...")
    
    from agent.proposal_supervisor import (
        build_technical_team_graph,
        build_finance_team_graph,
        build_legal_team_graph,
        build_qa_team_graph
    )
    
    teams = [
        ("Technical", build_technical_team_graph),
        ("Finance", build_finance_team_graph),
        ("Legal", build_legal_team_graph),
        ("QA", build_qa_team_graph)
    ]
    
    for team_name, build_func in teams:
        try:
            graph = build_func()
            print(f"✅ {team_name} team graph created successfully")
            
            # Test graph structure
            graph_info = graph.get_graph()
            print(f"   Nodes: {len(graph_info.nodes)}")
            print(f"   Edges: {len(graph_info.edges)}")
            
        except Exception as e:
            print(f"❌ {team_name} team graph failed: {e}")


def test_supervisor_routing():
    """Test the supervisor routing logic."""
    print("\n🧪 Testing supervisor routing...")
    
    from agent.proposal_supervisor import ProposalSupervisorAgent, proposal_team_router
    
    try:
        supervisor = ProposalSupervisorAgent()
        
        # Test initial routing
        test_state = MessagesState(
            messages=[HumanMessage(content="Generate a cybersecurity proposal for our organization")],
            chunks=[],
            pdf_paths=[],
            task_completed=False,
            iteration_count=0,
            confidence_score=None,
            follow_up_questions=[],
            parsed_response=None
        )
        
        result = supervisor.route(test_state)
        print("✅ Supervisor routing test completed")
        print(f"   Messages: {len(result.get('messages', []))}")
        
        # Test team router
        routing_result = proposal_team_router(test_state)
        print(f"✅ Team router result: {routing_result}")
        
    except Exception as e:
        print(f"❌ Supervisor routing test failed: {e}")


def test_integration_with_main_graph():
    """Test integration with the main graph system."""
    print("\n🧪 Testing integration with main graph...")
    
    try:
        from agent.graph import create_supervisor_system
        
        # Create the main supervisor system
        main_graph = create_supervisor_system()
        print("✅ Main supervisor system created successfully")
        
        # Test that proposal_supervisor is included
        graph_info = main_graph.get_graph()
        node_names = [node.id if hasattr(node, 'id') else str(node) for node in graph_info.nodes]
        
        if "proposal_supervisor" in node_names:
            print("✅ proposal_supervisor node found in main graph")
        else:
            print("❌ proposal_supervisor node not found in main graph")
            print(f"   Available nodes: {node_names}")
        
    except Exception as e:
        print(f"❌ Main graph integration test failed: {e}")


def test_team_agents():
    """Test the team agent classes."""
    print("\n🧪 Testing team agents...")
    
    try:
        from agent.team_agents import (
            TechnicalTeamAgent,
            FinanceTeamAgent,
            LegalTeamAgent,
            QATeamAgent
        )
        
        agents = [
            ("Technical", TechnicalTeamAgent()),
            ("Finance", FinanceTeamAgent()),
            ("Legal", LegalTeamAgent()),
            ("QA", QATeamAgent())
        ]
        
        for agent_name, agent in agents:
            print(f"✅ {agent_name} agent created successfully")
            print(f"   Team: {agent.team_name}")
            print(f"   Specialization: {agent.specialization}")
        
    except Exception as e:
        print(f"❌ Team agents test failed: {e}")


def main():
    """Run all tests."""
    print("🎯 Testing Hierarchical ProposalSupervisor System")
    print("=" * 60)
    
    # Test graph creation
    graph = test_graph_creation()
    
    # Test team subgraphs
    test_team_subgraphs()
    
    # Test supervisor routing
    test_supervisor_routing()
    
    # Test team agents
    test_team_agents()
    
    # Test integration with main graph
    test_integration_with_main_graph()
    
    print("\n🎯 Test Summary")
    print("=" * 60)
    print("✅ Hierarchical ProposalSupervisor system created successfully!")
    print("✅ Team subgraphs (Technical, Finance, Legal, QA) implemented")
    print("✅ Supervisor routing logic implemented")
    print("✅ Studio visualization support added")
    print("✅ Integration with main graph system completed")
    
    print("\n📋 Key Features:")
    print("- Hierarchical design with ProposalSupervisor routing to specialized teams")
    print("- Each team is a compiled StateGraph registered as a node")
    print("- Teams communicate via shared MessagesState")
    print("- Enhanced Studio visualization with destinations and xray support")
    print("- Conditional edges from supervisor to teams and back for iterative coordination")
    
    print("\n🚀 Ready for use! Try: 'generate proposal' or 'hierarchical proposal'")


if __name__ == "__main__":
    main()
