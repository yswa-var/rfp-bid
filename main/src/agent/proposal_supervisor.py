"""
Proposal Supervisor Agent

Hierarchical design with ProposalSupervisor routing work to multiple team subgraphs.
Each team is a compiled StateGraph registered as a node in the parent.
"""

import os
import time
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import StateGraph, START, END

from .state import MessagesState
from .proposal_rag_coordinator import ProposalRAGCoordinator
from .rag_editor_integration import integrate_rag_editor_with_proposal
from .rag_editor_agent import create_rag_enhancement_node


class ProposalSupervisorAgent:
    """Supervisor agent that routes proposal work to specialized teams."""
    
    def __init__(self):
        self.coordinator = ProposalRAGCoordinator()
        self.llm = ChatOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            temperature=0.2,
        )
        self.teams_completed = set()
        self.proposal_sections = {}
    
    def route(self, state: MessagesState) -> Dict[str, Any]:
        """Route proposal work to appropriate teams based on current state."""
        try:
            messages = state.get("messages", [])
            if not messages:
                return {
                    "messages": [AIMessage(content="Please provide RFP requirements to generate a proposal.", name="proposal_supervisor")]
                }
            
            # Get the last user message as RFP content
            user_messages = [m for m in messages if isinstance(m, HumanMessage)]
            if not user_messages:
                rfp_content = "General cybersecurity services RFP"
            else:
                rfp_content = user_messages[-1].content
            
            # Initialize state tracking if not present
            teams_completed = state.get("teams_completed", set())
            team_responses = state.get("team_responses", {})
            team_sequence = state.get("team_sequence", [])
            
            # Check if this is the first call (no teams completed yet)
            if not teams_completed and not team_sequence:
                print(f"🎯 Proposal Supervisor: Starting proposal generation for: {rfp_content[:100]}...")
                
                # Ensure RAG databases are ready
                if not self.coordinator.ensure_databases_ready():
                    return {
                        "messages": [AIMessage(content="❌ No RAG databases are available. Please setup databases first.", name="proposal_supervisor")]
                    }
                
                # Analyze RFP and determine team sequence
                team_sequence = self._analyze_rfp_and_plan_teams(rfp_content)
                
                # Start with the first team
                next_team = team_sequence[0] if team_sequence else "technical_team"
                
                return {
                    "messages": [AIMessage(content=f"🎯 Routing to {next_team} for proposal generation", name="proposal_supervisor")],
                    "next_team": next_team,
                    "team_sequence": team_sequence,
                    "rfp_content": rfp_content,
                    "teams_completed": set(),
                    "team_responses": {}
                }
            
            # Check if we have a team response to process
            last_message = messages[-1] if messages else None
            if last_message and hasattr(last_message, 'name') and last_message.name in ["technical_team", "finance_team", "legal_team", "qa_team"]:
                # Team completed, collect response
                team_name = last_message.name
                if team_name not in teams_completed:
                    teams_completed.add(team_name)
                    team_responses[team_name] = {
                        "content": last_message.content,
                        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                        "team": team_name
                    }
                    print(f"✅ Collected response from {team_name}")
            
            # Check if all teams are completed
            all_teams = {"finance_team", "legal_team", "qa_team", "technical_team"}
            if len(teams_completed) >= len(all_teams):
                # All teams completed, compose final proposal
                return self._compose_final_proposal(state, team_responses)
            
            # Determine next team
            remaining_teams = all_teams - teams_completed
            next_team = self._select_next_team(remaining_teams, state)
            
            return {
                "messages": [AIMessage(content=f"🔄 Routing to {next_team} for next phase", name="proposal_supervisor")],
                "next_team": next_team,
                "teams_completed": teams_completed,
                "team_responses": team_responses
            }
            
        except Exception as e:
            return {
                "messages": [AIMessage(content=f"❌ Supervisor routing failed: {e}", name="proposal_supervisor")]
            }
    
    def _analyze_rfp_and_plan_teams(self, rfp_content: str) -> List[str]:
        """Analyze RFP content and determine optimal team sequence."""
        try:
            analysis_prompt = f"""
            Analyze this RFP content and determine the optimal team sequence for proposal generation:
            
            RFP Content: {rfp_content[:500]}
            
            Available teams:
            - technical_team: Technical architecture, solution design, implementation approach
            - finance_team: Pricing, cost breakdown, financial terms, budget analysis
            - legal_team: Terms & conditions, compliance, legal requirements, contracts
            - qa_team: Quality assurance, testing, validation, risk management
            
            Return the team sequence as a comma-separated list, e.g., "technical_team,finance_team,legal_team,qa_team"
            """
            
            response = self.llm.invoke(analysis_prompt)
            team_sequence = [team.strip() for team in response.content.strip().split(",")]
            
            # Validate team names
            valid_teams = {"finance_team", "legal_team", "qa_team", "technical_team"}
            team_sequence = [team for team in team_sequence if team in valid_teams]
            
            # Ensure all teams are included
            for team in valid_teams:
                if team not in team_sequence:
                    team_sequence.append(team)
            
            print(f"📋 Team sequence planned: {team_sequence}")
            return team_sequence
            
        except Exception as e:
            print(f"⚠️  Team planning failed, using default sequence: {e}")
            return ["technical_team", "finance_team", "legal_team", "qa_team"]
    
    def _select_next_team(self, remaining_teams: set, state: MessagesState) -> str:
        """Select the next team based on current state and dependencies."""
        # Simple priority-based selection
        priority_order = ["technical_team", "finance_team", "legal_team", "qa_team"]
        
        for team in priority_order:
            if team in remaining_teams:
                return team
        
        # Fallback to first remaining team
        return list(remaining_teams)[0]
    
    def _compose_final_proposal(self, state: MessagesState, team_responses: Dict[str, Any]) -> Dict[str, Any]:
        """Compose the final proposal from all team contributions."""
        try:
            print("🎯 Composing final proposal from all team contributions...")
            
            # Save team responses to JSON file
            import json
            from pathlib import Path
            from .document_generator import DocumentGenerator
            
            responses_file = Path("team_responses.json")
            with open(responses_file, 'w') as f:
                json.dump(team_responses, f, indent=2, default=str)
            print(f"💾 Team responses saved to {responses_file}")

            # Generate structured documents using DocumentGenerator
            doc_generator = DocumentGenerator()
            responses_dir = Path("responses")
            responses_dir.mkdir(exist_ok=True)
            
            print("🏗️ Generating structured proposal documents...")
            generated_files = doc_generator.generate_all_formats(team_responses, responses_dir)
            
            # NEW: Integrate RAG Editor for enhanced DOCX generation
            print("🚀 Integrating RAG Editor for enhanced document generation...")
            rfp_content = state.get("rfp_content", "")
            
            try:
                rag_editor_results = integrate_rag_editor_with_proposal(
                    team_responses, 
                    rfp_content, 
                    str(responses_dir)
                )
                
                if rag_editor_results:
                    print("✅ RAG Editor integration completed successfully")
                    generated_files.update({
                        "rag_enhanced_json": rag_editor_results.get("enhanced_json"),
                        "rag_enhanced_outputs": rag_editor_results.get("enhanced_outputs", {})
                    })
                    
                    if "final_docx" in rag_editor_results:
                        generated_files["rag_enhanced_docx"] = rag_editor_results["final_docx"]
                        print(f"📄 RAG-enhanced DOCX saved to {rag_editor_results['final_docx']}")
                else:
                    print("⚠️ RAG Editor integration failed, continuing with standard generation")
                    
            except Exception as e:
                print(f"⚠️ RAG Editor integration error: {e}")
                print("Continuing with standard document generation...")
            
            # Create summary proposal for backward compatibility
            proposal_parts = [
                "# 🎯 **PROPOSAL RESPONSE**",
                f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
                f"**Teams Involved:** {', '.join(team_responses.keys())}",
                f"**Responses File:** {responses_file}",
                "",
                "## 📋 **Generated Documents**"
            ]
            
            for format_type, file_path in generated_files.items():
                proposal_parts.append(f"- **{format_type.upper()}**: {file_path}")
            
            proposal_parts.extend([
                "",
                "---",
                "",
                "## 📊 **Document Structure**",
                "",
                "The generated proposal follows this structure:",
                "",
                "1. **Summary** - Executive Overview, Key Benefits, Competitive Advantages, Success Metrics",
                "2. **About CPX** - Company information, certifications, and team composition", 
                "3. **Understanding of Requirements** - Project scope, stakeholder needs, success criteria",
                "4. **Proposed Solution** - Technical architecture and implementation approach",
                "5. **Implementation Plan** - Project phases, timeline, and resource allocation",
                "6. **Team and Experience** - Core team members and relevant experience",
                "7. **Pricing** - Cost breakdown, pricing model, and payment terms",
                "8. **Terms and Conditions** - Contractual terms and service agreements",
                "9. **Additional Services** - Optional modules and future enhancements",
                "10. **Appendices** - Technical specifications and supporting documentation",
                ""
            ])
            
            # Team section mapping for legacy display
            team_sections = {
                "technical_team": "## Technical Architecture & Solution Design",
                "finance_team": "## Pricing & Financial Analysis", 
                "legal_team": "## Legal & Compliance",
                "qa_team": "## Quality Assurance & Risk Management"
            }
            
            # Compose sections in logical order for summary
            section_order = ["technical_team", "finance_team", "legal_team", "qa_team"]
            
            proposal_parts.append("## 🔍 **Team Contributions Summary**")
            proposal_parts.append("")
            
            for team in section_order:
                if team in team_responses:
                    response = team_responses[team]
                    section_title = team_sections.get(team, f"## {team.title()}")
                    
                    proposal_parts.append(section_title)
                    proposal_parts.append(f"**Team:** {response.get('team', team)}")
                    proposal_parts.append(f"**Completed:** {response.get('timestamp', 'Unknown')}")
                    proposal_parts.append("")
                    
                    # Add truncated content for summary
                    content = response.get('content', 'No content available')
                    if len(content) > 500:
                        content = content[:500] + "... [Full content available in generated documents]"
                    
                    proposal_parts.append(content)
                    proposal_parts.append("")
            
            # Add generation summary
            proposal_parts.extend([
                "---",
                "## 📊 **GENERATION SUMMARY**",
                f"- **Teams Completed:** {len(team_responses)}/4",
                f"- **Documents Generated:** {len(generated_files)} formats",
                f"- **Processing Method:** Hierarchical team-based generation with RAG-enhanced document integration",
                f"- **Response Collection:** JSON file saved for reference",
                "",
                "**📋 Next Steps:**",
                "1. Review the generated structured proposal documents",
                "2. Check the RAG-enhanced DOCX for improved content quality",
                "3. Customize content as needed for specific RFP requirements", 
                "4. Add company-specific branding and formatting",
                "5. Submit the final proposal in required format"
            ])
            
            final_proposal = "\n".join(proposal_parts)
            
            # Save final response to markdown file for backward compatibility
            markdown_file = responses_dir / "last_response_main.md"
            with open(markdown_file, 'w', encoding='utf-8') as f:
                f.write(final_proposal)
            print(f"📄 Summary response saved to {markdown_file}")
            
            return {
                "messages": [AIMessage(content=final_proposal, name="proposal_supervisor")],
                "proposal_generated": True,
                "teams_completed": set(team_responses.keys()),
                "responses_file": str(responses_file),
                "markdown_file": str(markdown_file),
                "generated_files": generated_files,
                "rag_editor_integrated": "rag_enhanced_docx" in generated_files
            }
            
        except Exception as e:
            return {
                "messages": [AIMessage(content=f"❌ Final proposal composition failed: {e}", name="proposal_supervisor")]
            }
    
    def mark_team_completed(self, team_name: str, contribution: str):
        """Mark a team as completed and store their contribution."""
        self.teams_completed.add(team_name)
        self.proposal_sections[team_name] = contribution
        print(f"✅ Team {team_name} completed")


def proposal_team_router(state: MessagesState) -> str:
    """Route to the appropriate team based on supervisor decision."""
    messages = state.get("messages", [])
    
    # Check if proposal is already generated (HIGHEST PRIORITY)
    if state.get("proposal_generated", False):
        print("🎯 Proposal generation completed - ending flow")
        return "__end__"
    
    # Check if all teams are completed FIRST (highest priority)
    teams_completed = state.get("teams_completed", set())
    all_teams = {"finance_team", "legal_team", "qa_team", "technical_team"}
    if len(teams_completed) >= len(all_teams):
        # All teams completed, check if RAG enhancement is needed
        rag_enhanced = state.get("rag_editor_integrated", False)
        enhancement_completed = state.get("enhancement_completed", False)
        if not rag_enhanced and not enhancement_completed:
            print("🎯 All teams completed - starting RAG enhancement")
            return "rag_editor_enhancement"
        print("🎯 All teams completed and enhanced - ending flow")
        return "__end__"
    
    # Check for explicit next_team in state
    next_team = state.get("next_team")
    if next_team and next_team != "__end__":
        return next_team
    
    # Look for routing decision in the last message
    if messages:
        last_message = messages[-1]
        if isinstance(last_message, AIMessage) and last_message.name == "proposal_supervisor":
            content = last_message.content.lower()
            
            if "routing to finance_team" in content:
                return "finance_team"
            elif "routing to legal_team" in content:
                return "legal_team"
            elif "routing to qa_team" in content:
                return "qa_team"
            elif "routing to technical_team" in content:
                return "technical_team"
            elif "routing to rag_editor" in content:
                return "rag_editor_enhancement"
            elif "composing final proposal" in content:
                return "__end__"
    
    # Default to technical team
    return "technical_team"


# Team subgraph builders
def build_technical_team_graph() -> StateGraph:
    """Build technical team subgraph."""
    from .team_agents import TechnicalTeamAgent
    
    workflow = StateGraph(MessagesState)
    technical_agent = TechnicalTeamAgent()
    
    workflow.add_node("technical_rag_query", technical_agent.query_rag_context)
    workflow.add_node("technical_compose", technical_agent.compose_section)
    
    workflow.add_edge(START, "technical_rag_query")
    workflow.add_edge("technical_rag_query", "technical_compose")
    workflow.add_edge("technical_compose", END)
    
    return workflow.compile()


def build_finance_team_graph() -> StateGraph:
    """Build finance team subgraph."""
    from .team_agents import FinanceTeamAgent
    
    workflow = StateGraph(MessagesState)
    finance_agent = FinanceTeamAgent()
    
    workflow.add_node("finance_rag_query", finance_agent.query_rag_context)
    workflow.add_node("finance_compose", finance_agent.compose_section)
    
    workflow.add_edge(START, "finance_rag_query")
    workflow.add_edge("finance_rag_query", "finance_compose")
    workflow.add_edge("finance_compose", END)
    
    return workflow.compile()


def build_legal_team_graph() -> StateGraph:
    """Build legal team subgraph."""
    from .team_agents import LegalTeamAgent
    
    workflow = StateGraph(MessagesState)
    legal_agent = LegalTeamAgent()
    
    workflow.add_node("legal_rag_query", legal_agent.query_rag_context)
    workflow.add_node("legal_compose", legal_agent.compose_section)
    
    workflow.add_edge(START, "legal_rag_query")
    workflow.add_edge("legal_rag_query", "legal_compose")
    workflow.add_edge("legal_compose", END)
    
    return workflow.compile()


def build_qa_team_graph() -> StateGraph:
    """Build QA team subgraph."""
    from .team_agents import QATeamAgent
    
    workflow = StateGraph(MessagesState)
    qa_agent = QATeamAgent()
    
    workflow.add_node("qa_rag_query", qa_agent.query_rag_context)
    workflow.add_node("qa_compose", qa_agent.compose_section)
    
    workflow.add_edge(START, "qa_rag_query")
    workflow.add_edge("qa_rag_query", "qa_compose")
    workflow.add_edge("qa_compose", END)
    
    return workflow.compile()


def build_parent_proposal_graph():
    """Build the parent proposal graph with supervisor and team subgraphs."""
    workflow = StateGraph(MessagesState)
    
    # Supervisor agent
    proposal_supervisor = ProposalSupervisorAgent().route
    
    # Build team subgraphs
    technical_graph = build_technical_team_graph()
    finance_graph = build_finance_team_graph()
    legal_graph = build_legal_team_graph()
    qa_graph = build_qa_team_graph()
    
    # Add nodes: supervisor + compiled subgraphs (teams)
    # Enhanced with destinations metadata for Studio visualization
    workflow.add_node(
        "proposal_supervisor", 
        proposal_supervisor, 
        destinations={
            "finance_team": "Finance Team - Pricing & Financial Analysis",
            "legal_team": "Legal Team - Terms & Compliance", 
            "qa_team": "QA Team - Quality Assurance & Risk Management",
            "technical_team": "Technical Team - Architecture & Solution Design",
            "__end__": "Final Proposal Composition"
        }
    )
    
    # Add team subgraphs with enhanced metadata
    workflow.add_node("finance_team", finance_graph, metadata={"team": "Finance", "specialization": "Pricing & Financial Analysis"})
    workflow.add_node("legal_team", legal_graph, metadata={"team": "Legal", "specialization": "Terms & Compliance"})
    workflow.add_node("qa_team", qa_graph, metadata={"team": "QA", "specialization": "Quality Assurance & Risk Management"})
    workflow.add_node("technical_team", technical_graph, metadata={"team": "Technical", "specialization": "Architecture & Solution Design"})
    
    # Add RAG editor node for proposal enhancement
    workflow.add_node("rag_editor_enhancement", create_rag_enhancement_node(), metadata={"team": "RAG Editor", "specialization": "Content Enhancement & Document Processing"})
    
    # Entry
    workflow.add_edge(START, "proposal_supervisor")
    
    # Routing from supervisor to a single team
    workflow.add_conditional_edges(
        "proposal_supervisor",
        proposal_team_router,
        {
            "finance_team": "finance_team",
            "legal_team": "legal_team",
            "qa_team": "qa_team",
            "technical_team": "technical_team",
            "rag_editor_enhancement": "rag_editor_enhancement",
            "__end__": END,
        },
    )
    
    # Always hand control back to supervisor for the next team/iteration
    workflow.add_edge("finance_team", "proposal_supervisor")
    workflow.add_edge("legal_team", "proposal_supervisor")
    workflow.add_edge("qa_team", "proposal_supervisor")
    workflow.add_edge("technical_team", "proposal_supervisor")
    workflow.add_edge("rag_editor_enhancement", END)  # RAG enhancement goes directly to END
    
    # Compile with enhanced visualization support
    compiled_graph = workflow.compile()
    
    # Add graph metadata for Studio visualization
    compiled_graph.metadata = {
        "title": "Hierarchical Proposal Generation System",
        "description": "Multi-team proposal generation with specialized agents and RAG editor integration",
        "version": "1.0",
        "teams": ["Technical", "Finance", "Legal", "QA", "RAG Editor"],
        "visualization": {
            "xray": True,
            "show_destinations": True,
            "team_colors": {
                "technical_team": "#3B82F6",  # Blue
                "finance_team": "#10B981",    # Green  
                "legal_team": "#F59E0B",      # Yellow
                "qa_team": "#EF4444",         # Red
                "rag_editor_enhancement": "#8B5CF6"  # Purple
            }
        }
    }
    
    return compiled_graph


def get_graph_visualization(graph, xray=True):
    """Get enhanced graph visualization for Studio."""
    try:
        if xray:
            return graph.get_graph(xray=True)
        else:
            return graph.get_graph()
    except Exception as e:
        print(f"⚠️  Graph visualization error: {e}")
        return graph.get_graph()


def print_graph_structure(graph):
    """Print the graph structure for debugging."""
    try:
        print("🎯 Hierarchical Proposal Graph Structure:")
        print("=" * 50)
        
        # Get graph info
        graph_info = graph.get_graph()
        print(f"Nodes: {len(graph_info.nodes)}")
        print(f"Edges: {len(graph_info.edges)}")
        
        # Print team information
        print("\n📋 Teams:")
        teams = ["technical_team", "finance_team", "legal_team", "qa_team"]
        for team in teams:
            print(f"  - {team}: Specialized subgraph")
        
        print("\n🔄 Flow:")
        print("  START -> proposal_supervisor -> [team] -> proposal_supervisor -> [next_team] -> ... -> END")
        
        # Print metadata if available
        if hasattr(graph, 'metadata'):
            print(f"\n📊 Metadata: {graph.metadata}")
            
    except Exception as e:
        print(f"❌ Error printing graph structure: {e}")
