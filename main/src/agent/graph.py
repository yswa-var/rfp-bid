"""
Multi-Agent Supervisor System (modular)

Supervisor agent routes queries to worker agents and handles iterative
clarifications as needed.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent

# Ensure 'src' is on sys.path so absolute imports work when loaded by path
_CURRENT_DIR = Path(__file__).resolve().parent
_SRC_DIR = _CURRENT_DIR.parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from agent.state import MessagesState
from agent.agents import PDFParserAgent, CreateRAGAgent, GeneralAssistantAgent
from agent.tools import create_handoff_tool


def supervisor_router(state: MessagesState) -> str:
    """Route to appropriate agent based on supervisor agent decision and confidence score."""
    messages = state.get("messages", [])
    confidence_score = state.get("confidence_score")
    follow_up_questions = state.get("follow_up_questions", [])
    uploaded_files = state.get("uploaded_files", [])
    
    # Check if files were uploaded through LangGraph Studio UI
    if uploaded_files:
        return "pdf_parser"
    
    if not messages:
        return "general_assistant"
    
    # Check if session database was created - end the session
    last_message = messages[-1].content if hasattr(messages[-1], 'content') else ""
    if "Created Milvus session database 'session.db'" in last_message:
        return "__end__"
    
    # Check for error messages that should end the conversation
    if any(phrase in last_message for phrase in [
        "Session DB not found.",
        "Error connecting to session DB:",
        "Error processing your question:",
        "I couldn't find any relevant information"
    ]):
        return "__end__"
    
    # Confidence-based routing logic
    if confidence_score is not None:
        if confidence_score > 5:
            # High confidence - end the conversation with clear response
            return "__end__"
        elif confidence_score <= 5 and follow_up_questions:
            # Low confidence with follow-up questions - ask user for clarification
            follow_up_message = f"I need more information to provide a better answer. Here are some follow-up questions:\n\n" + "\n".join([f"• {q}" for q in follow_up_questions])
            return "__end__"  # End to ask follow-up questions
        else:
            # Low confidence without follow-up questions - end anyway
            return "__end__"
    
    # Get the last AI message from supervisor
    supervisor_messages = [msg for msg in messages if hasattr(msg, 'name') and msg.name == 'supervisor']
    if not supervisor_messages:
        return "general_assistant"
    
    last_supervisor_message = supervisor_messages[-1].content.lower()
    
    # Check supervisor's decision
    if "pdf_parser" in last_supervisor_message or "parse" in last_supervisor_message:
        return "pdf_parser"
    else:
        return "general_assistant"


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

    supervisor_prompt = (
        "You are a supervisor managing two agents:\n"
        "- pdf_parser: Parses PDF files (either uploaded through UI or provided as file paths) and creates text chunks, then automatically creates the RAG database. Once the milvus session is created, end the session.\n"
        "- general_assistant: Answers questions using session.db and cites sources. The system will automatically end the conversation based on confidence scores.\n\n"
        "ROUTING INSTRUCTIONS:\n"
        "- If user provides PDF files (via upload or file paths), asks to 'index PDFs', 'process documents', 'upload files', or mentions PDF paths, respond with 'I will route this to pdf_parser'.\n"
        "- If user asks general questions about documents, queries, or needs help, respond with 'I will route this to general_assistant'.\n"
        "- Always respond with exactly one of these two routing decisions.\n"
        "- Do not do any work yourself, only route to the appropriate agent.\n"
        "- The general_assistant will automatically handle confidence-based conversation ending.\n"
        "- Files uploaded through LangGraph Studio UI will automatically route to pdf_parser."
    )

    supervisor_agent = create_react_agent(
        supervisor_llm,
        tools=[],  # No tools needed for simple routing
        prompt=supervisor_prompt,
        name="supervisor",
    )

    workflow = StateGraph(MessagesState)
    
    # Add nodes
    workflow.add_node("supervisor", supervisor_agent)
    workflow.add_node("pdf_parser", pdf_parser_agent.parse_pdfs)
    workflow.add_node("create_rag", create_rag_agent.create_rag_database)
    workflow.add_node("general_assistant", general_assistant.query_documents)

    # Add edges with conditional routing
    workflow.add_edge(START, "supervisor")
    
    # Conditional edges from supervisor to worker agents or END
    workflow.add_conditional_edges(
        "supervisor",
        supervisor_router,
        {
            "pdf_parser": "pdf_parser",
            "general_assistant": "general_assistant",
            "__end__": END
        }
    )
    
    # PDF parser flows to create_rag, then to END
    workflow.add_edge("pdf_parser", "create_rag")
    workflow.add_edge("create_rag", END)
    
    # General assistant goes directly to END (confidence-based routing handled in supervisor_router)
    workflow.add_edge("general_assistant", END)

    return workflow.compile()


# Create and export graph
graph = create_supervisor_system()