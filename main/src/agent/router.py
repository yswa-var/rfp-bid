"""
Supervisor Router

Handles routing logic for the supervisor system to determine which agent should handle a request.
"""

from .state import MessagesState


def supervisor_router(state: MessagesState) -> str:
    """Router for supervisor system with priority-based routing."""
    messages = state.get("messages", [])
    
    if not messages:
        return "general_assistant"
    
    from langchain_core.messages import HumanMessage
    user_messages = [m for m in messages if isinstance(m, HumanMessage)]
    
    if user_messages:
        last_user_content = user_messages[-1].content.lower()
        
        # PRIORITY 1: Check for EXPLICIT agent names (highest priority)
        # This allows users to directly invoke specific agents
        if "image_adder" in last_user_content or "image adder" in last_user_content:
            return "image_adder"
        
        if "docx_agent" in last_user_content or "docx agent" in last_user_content:
            return "docx_agent"
        
        if "pdf_parser" in last_user_content or "pdf parser" in last_user_content:
            return "pdf_parser"
        
        if "general_assistant" in last_user_content or "general assistant" in last_user_content:
            return "general_assistant"
        
        if "rfp_supervisor" in last_user_content or "rfp supervisor" in last_user_content:
            return "rfp_supervisor"
        
        # PRIORITY 2: Check for IMAGE-related operations (high priority)
        # Handle requests to add/insert images
        if any(phrase in last_user_content for phrase in [
            "add images", "insert images", "place images",
            "add image", "insert image", "place image",
            "add pictures", "insert pictures", "add photo"
        ]):
            return "image_adder"
        
        # PRIORITY 3: Check for DOCX-related operations (high priority)
        # These are common operations that should not be confused with RFP
        if any(phrase in last_user_content for phrase in [
            "docx", ".docx", "word document", "word doc",
            "edit document", "modify document", "update document",
            "read docx", "write docx", "create docx",
            "document title", "document content", "document section",
            "create a document", "create new document", "create document",
            "new document"
        ]):
            return "docx_agent"
        
        # PRIORITY 4: Check for PDF parsing requests
        if any(phrase in last_user_content for phrase in [
            "parse pdf", ".pdf", "index pdf", "extract from pdf", "upload pdf"
        ]):
            return "pdf_parser"
        
        # PRIORITY 5: Check for RFP proposal requests (more specific matching)
        # Only route to RFP if it's clearly about RFP proposals, not just mentioning "rfp"
        rfp_indicators = ["generate proposal", "create proposal", "proposal content",
                         "finance team", "technical team", "legal team", "qa team",
                         "rfp proposal", "proposal for rfp"]
        
        # Check if it's ACTUALLY about RFP work (not just mentioning rfp in passing)
        if any(phrase in last_user_content for phrase in rfp_indicators):
            return "rfp_supervisor"
        
        # Only route to RFP if "rfp" or "proposal" is at the START or is the main topic
        words = last_user_content.split()
        if len(words) > 0 and words[0] in ["rfp", "proposal"]:
            return "rfp_supervisor"
        
        # Check if "rfp" or "proposal" is the main subject (not just part of a filename/identifier)
        if ("rfp" in last_user_content or "proposal" in last_user_content) and \
           any(action in last_user_content for action in ["generate", "create", "draft", "write", "prepare"]):
            return "rfp_supervisor"
    
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
    elif "rfp" in last_supervisor_message or "proposal" in last_supervisor_message:
        return "rfp_supervisor"
    else:
        return "general_assistant"


def rfp_team_router(state: MessagesState) -> str:
    """
    Router for RFP Team - Routes to appropriate specialized node based on current state.
    """
    current_node = state.get("current_rfp_node")
    
    if current_node == "finance":
        return "rfp_finance"
    elif current_node == "technical":
        return "rfp_technical"
    elif current_node == "legal":
        return "rfp_legal"
    elif current_node == "qa":
        return "rfp_qa"
    else:
        # Default to finance if no node specified
        return "rfp_finance"


def rfp_to_docx_router(state: MessagesState) -> str:
    """
    Router to determine if we should go to docx_agent or end after RFP node completes.
    
    If rfp_content has been generated, route to docx_agent to write it to the document.
    Otherwise, end the flow.
    """
    rfp_content = state.get("rfp_content", {})
    current_node = state.get("current_rfp_node")
    
    # Check if we have content to write
    if current_node and current_node in rfp_content:
        content_data = rfp_content[current_node]
        if content_data and content_data.get("content"):
            # We have content, route to docx_agent
            return "docx_agent"
    
    # No content or error, end the flow
    return "__end__"
