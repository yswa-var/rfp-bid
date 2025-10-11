"""
FastAPI Backend for LangGraph DOCX Agent Bot
Enables the agent to be used across multiple chat platforms
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uvicorn
import logging
from datetime import datetime
import uuid
import os
from pathlib import Path

from session_manager import SessionManager, Session
from agent_runner import AgentRunner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="DOCX Agent Bot API",
    description="Multi-platform bot backend for LangGraph DOCX Agent",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize managers
# CSV file will be created in the backend directory
csv_path = os.getenv("SESSIONS_CSV_PATH", "sessions.csv")
session_manager = SessionManager(csv_file=csv_path)
agent_runner = AgentRunner()


# Common constants/helpers
BASE_DIR = Path(__file__).resolve().parent
EXTRA_DOC_DIRS = tuple(
    Path(p).expanduser()
    for p in os.getenv("DOC_AGENT_DOCUMENT_DIRS", "").split(os.pathsep)
    if p.strip()
)
DOCUMENT_SEARCH_DIRS = tuple(
    path
    for path in (
        BASE_DIR,
        BASE_DIR.parent,
        BASE_DIR.parent / "main",
        BASE_DIR.parent / "documents",
        *EXTRA_DOC_DIRS,
    )
    if path.exists()
)
DEFAULT_DOC_CANDIDATES = tuple(
    name
    for name in (
        os.getenv("DEFAULT_DOCX_NAME"),
        "master.docx",
        "Master.docx",
    )
    if name
)
APPROVE_KEYWORDS = frozenset({"yes", "approve", "/approve"})
REJECT_KEYWORDS = frozenset({"no", "reject", "/reject"})


# ============================================================================
# Request/Response Models
# ============================================================================

class ChatMessage(BaseModel):
    """Standard chat message format"""
    user_id: str
    message: str
    platform: str = "api"  # api, telegram, discord, slack, whatsapp,teams
    metadata: Optional[Dict[str, Any]] = None

    def normalized_user_id(self) -> str:
        return f"{self.platform}_{self.user_id}" if not self.user_id.startswith(f"{self.platform}_") else self.user_id

    def user_profile(self) -> Dict[str, Any]:
        return (self.metadata or {}).get("user_profile", {})


class ChatResponse(BaseModel):
    """Standard response format"""
    user_id: str
    message: str
    platform: str = "api"
    requires_approval: bool = False
    approval_data: Optional[Dict[str, Any]] = None
    session_id: str
    metadata: Optional[Dict[str, Any]] = {}
    status: str = "completed"  # completed, waiting_approval, error


class ApprovalRequest(BaseModel):
    """Approval response from user"""
    user_id: str
    session_id: str
    approved: bool
    platform: str = "api"
    user_profile: Optional[Dict[str, Any]] = {}


# ============================================================================
# Health Check & Info
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "DOCX Agent Bot API",
        "version": "1.0.0",
        "status": "online",
        "endpoints": {
            "chat": "/api/chat",
            "approve": "/api/approve",
            "sessions": "/api/sessions",
            "webhooks": {
            }
        },
        "documentation": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "active_sessions": session_manager.get_active_session_count()
    }


# ============================================================================
# Core Chat API
# ============================================================================

@app.post("/api/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    """
    Main chat endpoint for all platforms
    
    This endpoint:
    1. Receives a message from any platform
    2. Routes it to the LangGraph agent
    3. Handles approval flows if needed
    4. Returns a response
    """
    try:
        logger.info(f"Received message from {message.user_id} on {message.platform}")
        
        # Normalize user id and get session
        normalized_user_id = message.normalized_user_id()
        session = session_manager.get_or_create_session(
            user_id=normalized_user_id,
            platform=message.platform,
        )
        
        user_profile = message.user_profile()
        enhanced_message = message.message
        
        if user_profile.get("name"):
            enhanced_message = f"[User: {user_profile['name']}] {message.message}"
            logger.info("Processing message for user: %s", user_profile['name'])
        
        if user_profile:
            session_manager.update_session_metadata(
                session.session_id,
                {"user_profile": user_profile},
            )
        
        if message.message.startswith("/load "):
            filename = message.message.replace("/load ", "").strip()
            document_result = _attempt_load_document(filename, user_profile, session)
            return ChatResponse(
                user_id=message.user_id,
                platform=message.platform,
                session_id=session.session_id,
                **document_result,
            )
        
        normalized_text = message.message.strip().lower()
        if session.pending_approval and _is_decision_command(normalized_text):
            approval_response = ApprovalRequest(
                user_id=message.user_id,
                session_id=session.session_id,
                approved=_is_approval(normalized_text),
                platform=message.platform,
                user_profile=user_profile
            )
            
            try:
                # Process the approval
                session = session_manager.get_session(approval_response.session_id)
                if not session:
                    raise HTTPException(status_code=404, detail="Session not found")
                
                if not session.pending_approval:
                    return ChatResponse(
                        user_id=normalized_user_id,
                        message="No pending approval found.",
                        platform=message.platform,
                        requires_approval=False,
                        session_id=session.session_id,
                        status="error"
                    )
                
                # Resume agent with approval decision
                result = await agent_runner.resume_with_approval(
                    session_id=approval_response.session_id,
                    thread_id=session.thread_id,
                    approved=approval_response.approved
                )
                
                # Clear pending approval
                session_manager.clear_pending_approval(approval_response.session_id)
                
                response_metadata = {}
                if user_profile:
                    response_metadata["user_profile"] = user_profile
                
                return ChatResponse(
                    user_id=normalized_user_id,
                    message=result["message"],
                    platform=message.platform,
                    requires_approval=False,
                    session_id=session.session_id,
                    metadata=response_metadata,
                    status="completed"
                )
                
            except Exception as e:
                logger.error(f"Error processing approval: {str(e)}", exc_info=True)
                return ChatResponse(
                    user_id=normalized_user_id,
                    message="Sorry, there was an error processing your approval. Please try again.",
                    platform=message.platform,
                    requires_approval=False,
                    session_id=session.session_id,
                    status="error"
                )
                
        # Check if user has a pending approval
        if session.pending_approval:
            return ChatResponse(
                user_id=normalized_user_id,
                message="You have a pending approval request. Please respond with /approve or /reject first.",
                platform=message.platform,
                requires_approval=False,
                session_id=session.session_id,
                status="error"
            )
        
        # Run the agent
        document_context = {}
        if session.metadata and session.metadata.get("document_path"):
            document_context = {
                "document_path": session.metadata["document_path"],
                "document_name": session.metadata.get("document_name", "unknown"),
                "loaded": True
            }
            
            # Create a more explicit message for the agent
            doc_info = (
                f"\n\nDOCUMENT CONTEXT:\n"
                f"- Document loaded: {session.metadata['document_name']}\n"
                f"- File path: {session.metadata['document_path']}\n"
                f"- Status: Ready for processing\n"
                f"- User request: {enhanced_message}\n"
                f"\nPlease process this request using the loaded document."
            )
            enhanced_message = doc_info
        else:
            document_context = {}
        
        result = await agent_runner.process_message(
            session_id=session.session_id,
            thread_id=session.thread_id,
            message=enhanced_message,
            document_context=document_context
        )
        
        # Check if approval is required
        if result.get("requires_approval"):
            approval_data = result.get("approval_data", {})
            session_manager.set_pending_approval(
                session_id=session.session_id,
                approval_data=approval_data
            )
            if user_profile:
                session_manager.update_session_metadata(
                    session.session_id,
                    {"user_profile": user_profile},
                )
            
            # Format approval message for user
            approval_msg = format_approval_message(approval_data)
            
            response_metadata = {}
            if user_profile:
                response_metadata["user_profile"] = user_profile
            
            return ChatResponse(
                user_id=normalized_user_id,
                message=approval_msg,
                platform=message.platform,
                requires_approval=True,
                approval_data=result["approval_data"],
                session_id=session.session_id,
                metadata=response_metadata,
                status="waiting_approval"
            )
            
        response_metadata = {}
        if user_profile:
            response_metadata["user_profile"] = user_profile
        
        # Normal response
        return ChatResponse(
            user_id=normalized_user_id,
            message=result["message"],
            platform=message.platform,
            requires_approval=False,
            session_id=session.session_id,
            metadata=response_metadata,
            status="completed"
        )
        
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}", exc_info=True)
        return ChatResponse(
            user_id=normalized_user_id,
            message="Sorry, I encountered an error processing your request. Please try again.",
            platform=message.platform,
            requires_approval=False,
            session_id=session.session_id if 'session' in locals() else str(uuid.uuid4()),
            status="error"
        )


@app.post("/api/approve")
async def approve(approval: ApprovalRequest):
    """
    Handle approval/rejection from user
    
    When a user responds to an approval request, this endpoint:
    1. Retrieves the pending operation
    2. Resumes the agent with approval/rejection
    3. Returns the final result
    """
    try:
        logger.info(f"Approval response from {approval.user_id}: {approval.approved}")
        
        # Get session
        session = session_manager.get_session(approval.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Check if there's a pending approval
        if not session.pending_approval:
            return ChatResponse(
                user_id=approval.user_id,
                message="No pending approval found.",
                platform=approval.platform,
                requires_approval=False,
                session_id=session.session_id,
                status="error"
            )
        
        # Resume agent with approval decision
        result = await agent_runner.resume_with_approval(
            session_id=session.session_id,
            thread_id=session.thread_id,
            approved=approval.approved
        )
        
        # Clear pending approval
        session_manager.clear_pending_approval(approval.session_id)
        
        response_metadata = {}
        if approval.user_profile:
            response_metadata["user_profile"] = approval.user_profile
            
        
        return ChatResponse(
            user_id=approval.user_id,
            message=result["message"],
            platform=approval.platform,
            requires_approval=False,
            session_id=session.session_id,
            metadata=response_metadata,
            status="completed"
        )
        
    except Exception as e:
        logger.error(f"Error processing approval: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Session Management
# ============================================================================

@app.get("/api/sessions/{user_id}")
async def get_user_sessions(user_id: str):
    """Get all sessions for a user"""
    sessions = session_manager.get_user_sessions(user_id)
    return {
        "user_id": user_id,
        "sessions": [s.to_dict() for s in sessions]
    }


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    success = session_manager.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "deleted", "session_id": session_id}


@app.get("/api/sessions")
async def list_all_sessions():
    """List all active sessions (admin endpoint)"""
    return {
        "active_sessions": session_manager.get_all_sessions(),
        "count": session_manager.get_active_session_count()
    }

@app.get("/api/debug/session/{user_id}")
async def debug_session(user_id: str):
    """Debug endpoint to see session state"""
    session = session_manager.get_or_create_session(user_id, "debug")
    return {
        "session_id": session.session_id,
        "user_id": session.user_id,
        "pending_approval": session.pending_approval,
        "metadata": session.metadata,
        "created_at": session.created_at,
        "last_activity": session.last_activity
    }

@app.post("/api/debug/clear-session/{user_id}")
async def clear_session(user_id: str):
    """Clear session state for debugging"""
    sessions = session_manager.get_user_sessions(user_id)
    for session in sessions:
        session_manager.clear_pending_approval(session.session_id)
    return {"message": f"Cleared session state for {user_id}"}

# Add this endpoint after the debug endpoints:
# ============================================================================
# Helper Functions
# ============================================================================

def format_approval_message(approval_data: Dict[str, Any]) -> str:
    """Format approval request for user-friendly display"""
    description = approval_data.get("description", "")
    
    message = f"""
🔔 **Approval Required**

{description}

Reply with:
• `/approve` or `yes` to proceed
• `/reject` or `no` to cancel
"""
    return message.strip()


def _attempt_load_document(filename: str, user_profile: Dict[str, Any], session: Session) -> Dict[str, Any]:
    """Try to resolve and persist document metadata while preparing response payload."""
    filename = (filename or "").strip()
    response_metadata: Dict[str, Any] = {}

    if user_profile:
        response_metadata["user_profile"] = user_profile

    if not filename:
        return {
            "message": "❌ Please provide a document name. Example: /load master.docx",
            "requires_approval": False,
            "metadata": response_metadata,
            "status": "error",
        }

    resolved_path = resolve_document_path(filename)

    if not resolved_path:
        search_dirs = "\n".join(f"• {path}" for path in DOCUMENT_SEARCH_DIRS)
        return {
            "message": (
                f"❌ Document '{filename}' not found.\n\n"
                f"Searched in:\n{search_dirs}\n\n"
                f"Upload the file or update DOC_AGENT_DOCUMENT_DIRS."
            ),
            "requires_approval": False,
            "metadata": response_metadata,
            "status": "error",
        }

    session_manager.update_session_metadata(
        session.session_id,
        {
            "document_path": str(resolved_path),
            "document_name": resolved_path.name,
            "document_loaded_at": datetime.utcnow().isoformat(),
        },
    )

    return {
        "message": (
            f"✅ Document '{resolved_path.name}' loaded successfully!\n\n"
            f"📍 Location: {resolved_path}\n\n"
            "You can now:\n"
            "• Summarize the document\n"
            "• Search for specific content\n"
            "• Request the structure\n"
            "• Draft edits (approval required)"
        ),
        "requires_approval": False,
        "metadata": response_metadata,
        "status": "completed",
    }


def _is_decision_command(message: str) -> bool:
    """Check if the incoming message is an approval decision."""
    if not message:
        return False
    first_token = message.split()[0]
    return first_token in APPROVE_KEYWORDS or first_token in REJECT_KEYWORDS


def _is_approval(message: str) -> bool:
    """Return True when the message indicates approval."""
    if not message:
        return False
    first_token = message.split()[0]
    return first_token in APPROVE_KEYWORDS


def load_test_document(filename: str = None):
    """Load a test document for development"""
    target = filename or next(iter(DEFAULT_DOC_CANDIDATES), None)
    resolved = resolve_document_path(target) if target else None
    return str(resolved) if resolved else None


def resolve_document_path(filename: str) -> Optional[Path]:
    """Resolve a filename against known directories and return the first match."""
    if not filename:
        return None

    candidate_path = Path(filename).expanduser()
    if candidate_path.is_absolute() and candidate_path.exists():
        return candidate_path

    # when only name provided search directories
    for directory in DOCUMENT_SEARCH_DIRS:
        candidate = directory / candidate_path
        if candidate.exists():
            return candidate

    # When no extension, try .docx
    if candidate_path.suffix == "":
        for directory in DOCUMENT_SEARCH_DIRS:
            candidate = directory / f"{candidate_path}.docx"
            candidate = Path(candidate)
            if candidate.exists():
                return candidate

    return None

# ============================================================================
# Run Server
# ============================================================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
