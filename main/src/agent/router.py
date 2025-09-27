"""
Supervisor Router

Handles routing logic for the supervisor system to determine which agent should handle a request.
"""

from .state import MessagesState


def supervisor_router(state: MessagesState) -> str:
    """Enhanced router to handle Multi-RAG functionality."""
    messages = state.get("messages", [])
    
    if not messages:
        return "general_assistant"
    
    from langchain_core.messages import HumanMessage
    user_messages = [m for m in messages if isinstance(m, HumanMessage)]
    
    if user_messages:
        last_user_content = user_messages[-1].content.lower()
        
        # Word editing gets highest priority - check first
        if any(phrase in last_user_content for phrase in [
            "edit document", "modify document", "update document", "change document",
            ".docx", ".doc", "word document", "edit word", "modify word", "edit file"
        ]):
            return "word_editor"
        
        if any(phrase in last_user_content for phrase in [
            "setup multi-rag", "setup rag", "multi rag", "template rag", 
            "setup databases", "multi-rag", "setup multi"
        ]):
            return "multi_rag_setup"
        
        if any(phrase in last_user_content for phrase in [
            "generate proposal", "create proposal", "proposal generation", "rfp response", "hierarchical proposal"
        ]):
            return "proposal_supervisor"
    
    # Check if session database was created - end the session
    last_message = messages[-1].content if hasattr(messages[-1], 'content') else ""
    if "Created Milvus session database 'session.db'" in last_message:
        return "__end__"
    
    if any(phrase in last_message for phrase in [
        "Session DB not found.",
        "Error connecting to session DB:",
        "Error processing your question:",
        "I couldn't find any relevant information"
    ]):
        return "__end__"
    
    # Get the last AI message from supervisor
    supervisor_messages = [msg for msg in messages if hasattr(msg, 'name') and msg.name == 'supervisor']
    if not supervisor_messages:
        return "general_assistant"
    
    last_supervisor_message = supervisor_messages[-1].content.lower()
    
    # Check supervisor's decision
    if "pdf_parser" in last_supervisor_message or "parse" in last_supervisor_message:
        return "pdf_parser"
    elif "multi_rag_setup" in last_supervisor_message:
        return "multi_rag_setup"
    elif "proposal_supervisor" in last_supervisor_message:
        return "proposal_supervisor"
    elif "word_editor" in last_supervisor_message:
        return "word_editor"
    else:
        return "general_assistant"
