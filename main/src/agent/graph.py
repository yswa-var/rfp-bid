"""
Multi-Agent Supervisor System (modular)

Supervisor agent routes queries to worker agents.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent

_CURRENT_DIR = Path(__file__).resolve().parent
_SRC_DIR = _CURRENT_DIR.parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from agent.state import MessagesState
from agent.agents import PDFParserAgent, CreateRAGAgent, GeneralAssistantAgent, RFPProposalTeam
from agent.router import supervisor_router, rfp_team_router, rfp_to_docx_router
from react_agent.graph import graph as docx_agent_graph

__all__ = ["graph"]


def create_supervisor_system():
    """Create the complete supervisor system with RFP Proposal Team integration."""

    supervisor_llm = ChatOpenAI(
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    # Initialize agents
    pdf_parser_agent = PDFParserAgent()
    create_rag_agent = CreateRAGAgent()
    general_assistant = GeneralAssistantAgent()
    rfp_team = RFPProposalTeam()
    
    supervisor_prompt = (
        "You are a supervisor managing multiple INDEPENDENT agents:\n\n"
        "AGENTS:\n"
        "- docx_agent: Handles ALL DOCX/Word document operations independently (read, search, edit, create, modify documents).\n"
        "- pdf_parser: Parses user-provided PDF paths, creates text chunks, then automatically creates the RAG database.\n"
        "- general_assistant: Answers questions using the RAG database independently.\n"
        "- rfp_supervisor: Manages COMPLETE RFP proposal generation with specialized teams (finance, technical, legal, QA).\n\n"
        "ROUTING PRIORITY (Check in this order):\n"
        "1. If user explicitly mentions an agent name (e.g., 'docx_agent', 'pdf_parser', 'general_assistant'), route to that agent.\n"
        "2. If user wants to edit/modify/update/read/create a document or mentions 'docx'/'word document', respond: 'I will route this to docx_agent'.\n"
        "3. If user provides PDF files or asks to 'parse PDFs'/'index PDFs', respond: 'I will route this to pdf_parser'.\n"
        "4. If user wants to GENERATE/CREATE a complete RFP proposal (not just edit a document with 'rfp' in the name), respond: 'I will route this to rfp_supervisor'.\n"
        "5. For general questions or queries about existing knowledge, respond: 'I will route this to general_assistant'.\n\n"
        "IMPORTANT:\n"
        "- Each agent works INDEPENDENTLY - they don't need the supervisor except for routing.\n"
        "- If a user mentions 'rfp' as part of a filename (e.g., 'rfp-9903'), it's likely a document name, NOT an RFP proposal request.\n"
        "- Document operations (edit, update, modify, read) should ALWAYS go to docx_agent, even if 'rfp' is in the document name.\n"
        "- Always respond with exactly ONE routing decision using the exact phrases above.\n"
        "- Do not do any work yourself, only route to the appropriate agent."
    )

    supervisor_agent = create_react_agent(
        supervisor_llm,
        tools=[],
        prompt=supervisor_prompt,
        name="supervisor",
    )

    workflow = StateGraph(MessagesState)
    
    # Main supervisor and worker agents
    workflow.add_node("supervisor", supervisor_agent)
    workflow.add_node("pdf_parser", pdf_parser_agent.parse_pdfs)
    workflow.add_node("create_rag", create_rag_agent.create_rag_database)
    workflow.add_node("general_assistant", general_assistant.query_documents)
    workflow.add_node("docx_agent", docx_agent_graph)
    
    # RFP Proposal Team nodes
    workflow.add_node("rfp_supervisor", rfp_team.rfp_supervisor)
    workflow.add_node("rfp_finance", rfp_team.finance_node)
    workflow.add_node("rfp_technical", rfp_team.technical_node)
    workflow.add_node("rfp_legal", rfp_team.legal_node)
    workflow.add_node("rfp_qa", rfp_team.qa_node)

    # Main entry point
    workflow.add_edge(START, "supervisor")

    # Supervisor routing
    workflow.add_conditional_edges(
        "supervisor",
        supervisor_router,
        {
            "pdf_parser": "pdf_parser",
            "general_assistant": "general_assistant",
            "docx_agent": "docx_agent",
            "rfp_supervisor": "rfp_supervisor",
            "__end__": END
        }
    )
    
    # PDF parser flow
    workflow.add_edge("pdf_parser", "create_rag")
    workflow.add_edge("create_rag", END)
    
    # General assistant flow
    workflow.add_edge("general_assistant", END)
    
    # RFP Team flow - supervisor routes to appropriate team node
    workflow.add_conditional_edges(
        "rfp_supervisor",
        rfp_team_router,
        {
            "rfp_finance": "rfp_finance",
            "rfp_technical": "rfp_technical",
            "rfp_legal": "rfp_legal",
            "rfp_qa": "rfp_qa"
        }
    )
    
    # After each RFP team node completes, route to docx_agent to write content
    workflow.add_conditional_edges(
        "rfp_finance",
        rfp_to_docx_router,
        {
            "docx_agent": "docx_agent",
            "__end__": END
        }
    )
    
    workflow.add_conditional_edges(
        "rfp_technical",
        rfp_to_docx_router,
        {
            "docx_agent": "docx_agent",
            "__end__": END
        }
    )
    
    workflow.add_conditional_edges(
        "rfp_legal",
        rfp_to_docx_router,
        {
            "docx_agent": "docx_agent",
            "__end__": END
        }
    )
    
    workflow.add_conditional_edges(
        "rfp_qa",
        rfp_to_docx_router,
        {
            "docx_agent": "docx_agent",
            "__end__": END
        }
    )
    
    # Direct docx_agent flow (for standalone document operations)
    workflow.add_edge("docx_agent", END)

    return workflow.compile()

graph = create_supervisor_system()