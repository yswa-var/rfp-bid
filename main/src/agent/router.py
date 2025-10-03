"""
Supervisor Router

Handles routing logic for the supervisor system to determine which agent should handle a request.
"""

from .state import MessagesState


def supervisor_router(state: MessagesState) -> str:
    """Router for supervisor system."""
    messages = state.get("messages", [])
    
    if not messages:
        return "general_assistant"
    
    from langchain_core.messages import HumanMessage
    user_messages = [m for m in messages if isinstance(m, HumanMessage)]
    
    if user_messages:
        last_user_content = user_messages[-1].content.lower()
        
        # Check for PDF parsing requests first (before docx)
        if any(phrase in last_user_content for phrase in [
            "parse pdf", "pdf", "index pdf", "extract from pdf"
        ]):
            return "pdf_parser"
        
        # Check for docx-related requests
        if any(phrase in last_user_content for phrase in [
            "docx", "word document", "edit document", 
            "modify document", "read docx", "write docx", ".docx", "word doc"
        ]):
            return "docx_agent"
        
        # Check if it's a document creation request (generic)
        if "create" in last_user_content and "document" in last_user_content:
            return "docx_agent"
        
        if any(phrase in last_user_content for phrase in [
            "generate proposal", "create proposal", "proposal generation", "rfp response", "hierarchical proposal"
        ]):
            return "technical_team"
        
    
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
    elif "docx_agent" in last_supervisor_message or "word document" in last_supervisor_message:
        return "docx_agent"
    elif "technical_team" in last_supervisor_message or "proposal" in last_supervisor_message:
        return "technical_team"
    else:
        return "general_assistant"
