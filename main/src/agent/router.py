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
        
        if any(phrase in last_user_content for phrase in [
            "setup multi-rag", "setup rag", "multi rag", "template rag", 
            "setup databases", "multi-rag", "setup multi"
        ]):
            return "multi_rag_setup"
        
        if any(phrase in last_user_content for phrase in [
            "generate proposal", "create proposal", "proposal generation", "rfp response", "hierarchical proposal"
        ]):
            return "proposal_supervisor"
        
        if any(phrase in last_user_content for phrase in [
            "launch rag editor", "launch editor", "interactive editor", "start rag editor", 
            "open document editor", "enhanced editor", "launch interactive", "full rag editor",
            "beautiful rag", "interactive rag", "launch rag", "start interactive"
        ]):
            return "interactive_rag_launcher"
        
        # RAG Editor takes priority for specific editor commands
        if any(phrase in last_user_content for phrase in [
            "rag editor", "ai editor", "document editor", "edit document", 
            "ai dynamic editor", "mcp editor"
        ]):
            return "rag_editor"
        
        # Check if we're already in a RAG editor session and continuing
        rag_messages = [msg for msg in messages if hasattr(msg, 'name') and msg.name == 'rag_editor']
        if rag_messages and any(cmd in last_user_content for cmd in ['load ', 'search ', 'add ', 'edit ', 'format', 'status', 'help']):
            return "rag_editor"
        
        # Route RAG commands to rag_editor (not full_rag_studio) - keep session in same node
        if any(phrase in last_user_content for phrase in [
            "find ", "search ", "replace ", "rag query ", "add content ", "add context ", "explore ",
            "info", "document info", "load document", "load ", "understanding of requirements", "status"
        ]) or last_user_content.startswith(("find ", "search ", "replace ", "rag query ", "add content ", "add context ", "explore ", "status")):
            return "rag_editor"
        
        if any(phrase in last_user_content for phrase in [
            "enhance proposal", "enhance content", "rag enhancement", "improve proposal",
            "enhance document", "rag improve", "content enhancement"
        ]):
            return "rag_enhancement"
    
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
    elif "interactive_rag_launcher" in last_supervisor_message or "interactive" in last_supervisor_message:
        return "interactive_rag_launcher"
    elif "rag_editor" in last_supervisor_message or "editor" in last_supervisor_message:
        return "rag_editor"
    else:
        return "general_assistant"
