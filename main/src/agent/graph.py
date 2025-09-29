"""
Multi-Agent Supervisor System (modular)

Supervisor agent routes queries to worker agents and handles iterative
clarifications as needed.
"""

import os
import sys
from pathlib import Path
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent

_CURRENT_DIR = Path(__file__).resolve().parent
_SRC_DIR = _CURRENT_DIR.parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from agent.state import MessagesState
from agent.agents import PDFParserAgent, CreateRAGAgent, GeneralAssistantAgent
from agent.rag_editor_agent import create_rag_editor_node
from agent.proposal_supervisor import build_parent_proposal_graph
from agent.multi_rag_setup import MultiRAGSetupAgent
from agent.interactive_rag_launcher import create_interactive_rag_launcher_node
# from agent.full_rag_studio import create_full_rag_editor_studio_node  # Commented out - using rag_editor instead
from agent.router import supervisor_router

__all__ = ["graph"]


def create_supervisor_system():
    """Create the complete supervisor system with worker agents."""

    supervisor_llm = ChatOpenAI(
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    pdf_parser_agent = PDFParserAgent()
    create_rag_agent = CreateRAGAgent()
    general_assistant = GeneralAssistantAgent()
    
    # Multi-RAG setup agent
    multi_rag_setup_agent = MultiRAGSetupAgent()
    
    # Hierarchical Proposal Supervisor System (replaces proposal_generator)
    proposal_supervisor_graph = build_parent_proposal_graph()

    supervisor_prompt = (
        "You are a supervisor managing multiple agents:\n"
        "- pdf_parser: Parses user-provided PDF paths and creates text chunks, then automatically creates the RAG database.\n"
        "- multi_rag_setup: Sets up the Multi-RAG system with templates, examples, and session databases.\n"
        "- proposal_supervisor: Hierarchical proposal generation with specialized teams (technical, finance, legal, qa).\n"
        "- rag_editor: Complete RAG Editor functionality with document editing, search, formatting, and all 54 MCP tools.\n"
        "- interactive_rag_launcher: Launches the full interactive RAG editor with beautiful UI and complete editing interface.\n\n"
        "ROUTING INSTRUCTIONS:\n"
        "- If user mentions 'setup multi-rag', 'setup databases', 'multi rag', or 'template rag', respond EXACTLY with: 'I will route this to multi_rag_setup'.\n"
        "- If user asks 'generate proposal', 'create proposal', 'rfp response', 'hierarchical proposal', or mentions 'proposal', respond EXACTLY with: 'I will route this to proposal_supervisor'.\n"
        "- If user provides PDF files or asks to 'index PDFs', respond EXACTLY with: 'I will route this to pdf_parser'.\n"
        "- If user mentions 'rag editor', 'edit document', 'search content', 'add content', 'add context', 'format document', 'find', 'replace', 'rag query', 'explore', 'info', 'status', 'load document', 'understanding of requirements', or wants document editing with RAG, respond EXACTLY with: 'I will route this to rag_editor'.\n"
        "- If user mentions 'launch rag editor', 'launch editor', 'interactive editor', 'start rag editor', 'open document editor', 'enhanced editor', or 'launch interactive', respond EXACTLY with: 'I will route this to interactive_rag_launcher'.\n"
        "- For other questions, respond EXACTLY with: 'I will route this to general_assistant'.\n"
        "- IMPORTANT: Always respond with exactly one routing decision using the exact phrases above.\n"
        "- Do not do any work yourself, only route to the appropriate agent."
    )

    supervisor_agent = create_react_agent(
        supervisor_llm,
        tools=[],
        prompt=supervisor_prompt,
        name="supervisor",
    )

    workflow = StateGraph(MessagesState)
    

    workflow.add_node("supervisor", supervisor_agent)
    workflow.add_node("pdf_parser", pdf_parser_agent.parse_pdfs)
    workflow.add_node("create_rag", create_rag_agent.create_rag_database)
    workflow.add_node("general_assistant", general_assistant.query_documents)
    workflow.add_node("rag_editor", create_rag_editor_node())
    workflow.add_node("interactive_rag_launcher", create_interactive_rag_launcher_node())
    # workflow.add_node("full_rag_studio", create_full_rag_editor_studio_node())  # Commented out - using rag_editor instead

    workflow.add_node("multi_rag_setup", multi_rag_setup_agent.setup_multi_rag)
    workflow.add_node("proposal_supervisor", proposal_supervisor_graph)

    workflow.add_edge(START, "supervisor")

    workflow.add_conditional_edges(
        "supervisor",
        supervisor_router,
        {
            "pdf_parser": "pdf_parser",
            "general_assistant": "general_assistant",
            "rag_editor": "rag_editor",
            "interactive_rag_launcher": "interactive_rag_launcher",
            # "full_rag_studio": "full_rag_studio",  # Commented out - using rag_editor instead
            "multi_rag_setup": "multi_rag_setup",      
            "proposal_supervisor": "proposal_supervisor",
            "__end__": END
        }
    )
    
    # Existing flows
    workflow.add_edge("pdf_parser", "create_rag")
    workflow.add_edge("create_rag", END)
    workflow.add_edge("general_assistant", END)
    workflow.add_edge("rag_editor", END)
    workflow.add_edge("interactive_rag_launcher", END)
    # workflow.add_edge("full_rag_studio", END)  # Commented out - using rag_editor instead
    
    # Multi-RAG flows
    workflow.add_edge("multi_rag_setup", END)
    workflow.add_edge("proposal_supervisor", END)

    return workflow.compile()

graph = create_supervisor_system()