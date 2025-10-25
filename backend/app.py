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
import socketio

from session_manager import SessionManager, Session
from agent_runner import AgentRunner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Socket.IO server
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=True,
    engineio_logger=False
)

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

# Mount Socket.IO at /ws
socket_app = socketio.ASGIApp(sio, app)

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
    logger.info(f"Resolving document: {filename}, candidate_path: {candidate_path}")
    
    if candidate_path.is_absolute() and candidate_path.exists():
        logger.info(f"Found absolute path: {candidate_path}")
        return candidate_path

    # when only name provided search directories
    for directory in DOCUMENT_SEARCH_DIRS:
        candidate = directory / candidate_path
        logger.info(f"Checking: {candidate}, exists: {candidate.exists()}")
        if candidate.exists():
            logger.info(f"Found document at: {candidate}")
            return candidate

    # When no extension, try .docx
    if candidate_path.suffix == "":
        for directory in DOCUMENT_SEARCH_DIRS:
            candidate = directory / f"{candidate_path}.docx"
            candidate = Path(candidate)
            logger.info(f"Checking with .docx: {candidate}, exists: {candidate.exists()}")
            if candidate.exists():
                logger.info(f"Found document at: {candidate}")
                return candidate

    logger.warning(f"Document not found: {filename}")
    return None

# ============================================================================
# Socket.IO Event Handlers (MVP Real-time Support)
# ============================================================================

@sio.event
async def connect(sid, environ):
    """Handle WebSocket connection"""
    logger.info(f"Socket.IO client connected: {sid}")
    await sio.emit("connection_status", {"connected": True, "sid": sid}, to=sid)


@sio.event
async def disconnect(sid):
    """Handle WebSocket disconnection"""
    logger.info(f"Socket.IO client disconnected: {sid}")


@sio.event
async def join_session(sid, data):
    """Join a session room for targeted messages"""
    session_id = data.get("session_id")
    if session_id:
        await sio.enter_room(sid, session_id)
        logger.info(f"Client {sid} joined session {session_id}")
        await sio.emit("joined_session", {"session_id": session_id}, to=sid)


@sio.event
async def send_message(sid, data):
    """
    Handle real-time chat message from WebSocket
    Reuses existing agent_runner logic with agent selection support
    """
    try:
        user_id = data.get("user_id", f"ws_{sid}")
        message_text = data.get("message", "")
        session_id = data.get("session_id", "default")
        selected_agent = data.get("selected_agent", "supervisor")  # Get selected agent
        
        if not message_text:
            await sio.emit("error", {"message": "Message text is required"}, to=sid)
            return
        
        logger.info(f"WebSocket message from {user_id}: {message_text} (Agent: {selected_agent})")
        
        # Get or create session
        session = session_manager.get_or_create_session(
            user_id=user_id,
            platform="websocket"
        )
        
        # Store selected agent in session metadata
        session_manager.update_session_metadata(
            session.session_id,
            {"selected_agent": selected_agent}
        )
        
        # Check for pending approval
        if session.pending_approval:
            # Check if this is an approval response
            normalized_text = message_text.strip().lower()
            if _is_decision_command(normalized_text):
                approved = _is_approval(normalized_text)
                
                # Resume agent with approval
                result = await agent_runner.resume_with_approval(
                    session_id=session.session_id,
                    thread_id=session.thread_id,
                    approved=approved
                )
                
                # Clear pending approval
                session_manager.clear_pending_approval(session.session_id)
                
                # Emit response
                await sio.emit("message_response", {
                    "session_id": session.session_id,
                    "message": result["message"],
                    "requires_approval": False,
                    "status": "completed"
                }, room=session.session_id)
                
                return
            else:
                await sio.emit("message_response", {
                    "session_id": session.session_id,
                    "message": "You have a pending approval. Please respond with /approve or /reject first.",
                    "requires_approval": False,
                    "status": "error"
                }, to=sid)
                return
        
        # Check for /load command
        if message_text.startswith("/load "):
            filename = message_text.replace("/load ", "").strip()
            document_result = _attempt_load_document(filename, {}, session)
            
            # Emit message response
            await sio.emit("message_response", {
                "session_id": session.session_id,
                "message": document_result["message"],
                "requires_approval": False,
                "status": document_result.get("status", "completed")
            }, room=session.session_id)
            
            # Also emit directly to the requesting socket
            await sio.emit("message_response", {
                "session_id": session.session_id,
                "message": document_result["message"],
                "requires_approval": False,
                "status": document_result.get("status", "completed")
            }, to=sid)
            
            # If document loaded successfully, also emit document data
            if document_result.get("status") == "completed" and session.metadata.get("document_path"):
                doc_path = session.metadata["document_path"]
                # Get document via the document API
                try:
                    from rct_agent.docx_manager import DocxManager
                    manager = DocxManager(doc_path)
                    manager._refresh_index()
                    
                    # Structure the data for frontend
                    sections = []
                    current_section = None
                    
                    for para in manager.index_data:
                        if para.get('level', 0) > 0:  # It's a heading
                            if current_section:
                                sections.append(current_section)
                            current_section = {
                                'title': para['text'],
                                'level': para['level'],
                                'paragraphs': []
                            }
                        elif current_section:
                            current_section['paragraphs'].append(para['text'])
                        else:
                            # Paragraph before first heading
                            if not sections:
                                sections.append({
                                    'title': 'Introduction',
                                    'level': 0,
                                    'paragraphs': [para['text']]
                                })
                            else:
                                sections[-1]['paragraphs'].append(para['text'])
                    
                    if current_section:
                        sections.append(current_section)
                    
                    structured = {
                        'sections': sections,
                        'toc': [{'text': s['title'], 'level': s['level']} for s in sections if s.get('title')]
                    }
                    
                    # Emit to both room and directly to socket
                    await sio.emit("document_loaded", {
                        "session_id": session.session_id,
                        "document_name": session.metadata.get("document_name"),
                        "document_path": doc_path,
                        "content": structured
                    }, room=session.session_id)
                    
                    await sio.emit("document_loaded", {
                        "session_id": session.session_id,
                        "document_name": session.metadata.get("document_name"),
                        "document_path": doc_path,
                        "content": structured
                    }, to=sid)
                    
                    logger.info(f"Emitted document_loaded for /load command to socket {sid}")
                    
                except Exception as doc_err:
                    logger.error(f"Error loading document content: {doc_err}")
            
            return
        
        # Normal message processing with agent selection
        # Prepend agent directive if not supervisor
        if selected_agent and selected_agent != 'supervisor':
            # Force routing to selected agent by mentioning it explicitly
            enhanced_message = f"[Route to {selected_agent}] {message_text}"
        else:
            enhanced_message = message_text
        
        result = await agent_runner.process_message(
            session_id=session.session_id,
            thread_id=session.thread_id,
            message=enhanced_message,
            document_context=session.metadata or{},
            selected_agent=selected_agent  # Pass selected agent to runner
        )
        
        # Handle approval requests
        if result.get("requires_approval"):
            approval_data = result.get("approval_data", {})
            session_manager.set_pending_approval(
                session_id=session.session_id,
                approval_data=approval_data
            )
            
            approval_msg = format_approval_message(approval_data)
            
            await sio.emit("message_response", {
                "session_id": session.session_id,
                "message": approval_msg,
                "requires_approval": True,
                "approval_data": approval_data,
                "status": "waiting_approval"
            }, room=session.session_id)
            
            await sio.emit("message_response", {
                "session_id": session.session_id,
                "message": approval_msg,
                "requires_approval": True,
                "approval_data": approval_data,
                "status": "waiting_approval"
            }, to=sid)
        else:
            # Normal response - emit to both room and directly to socket
            await sio.emit("message_response", {
                "session_id": session.session_id,
                "message": result["message"],
                "requires_approval": False,
                "status": "completed"
            }, room=session.session_id)
            
            await sio.emit("message_response", {
                "session_id": session.session_id,
                "message": result["message"],
                "requires_approval": False,
                "status": "completed"
            }, to=sid)
            
    except Exception as e:
        logger.error(f"Error processing WebSocket message: {str(e)}", exc_info=True)
        await sio.emit("error", {
            "message": f"Sorry, I encountered an error: {str(e)}"
        }, to=sid)


@sio.event
async def request_document(sid, data):
    """
    Handle manual document load request from frontend
    Returns the latest loaded document for the current session
    """
    try:
        user_id = data.get("user_id", f"ws_{sid}")
        frontend_session_id = data.get("session_id", "default")
        
        # Get or create session using the same logic as send_message
        session = session_manager.get_or_create_session(
            user_id=user_id,
            platform="websocket"
        )
        
        # Check if a document is loaded
        if not session.metadata or not session.metadata.get("document_path"):
            await sio.emit("message_response", {
                "session_id": frontend_session_id,
                "message": "No document loaded yet. Please use '/load <filename>' in the chat.",
                "requires_approval": False,
                "status": "info"
            }, to=sid)  # Emit directly to the socket, not to a room
            return
        
        # Get document path
        doc_path = session.metadata.get("document_path")
        if not os.path.exists(doc_path):
            await sio.emit("error", {"message": "Document file not found"}, to=sid)
            return
        
        # Parse and emit document
        try:
            from rct_agent.docx_manager import DocxManager
            manager = DocxManager(doc_path)
            manager._refresh_index()
            
            sections = []
            current_section = None
            
            for item in manager.index_data:
                level = item.get('level', 0)
                text = item.get('text', '').strip()
                
                if level > 0:  # Heading
                    if current_section:
                        sections.append(current_section)
                    current_section = {
                        'title': text,
                        'level': level,
                        'paragraphs': []
                    }
                elif text and current_section:  # Regular paragraph
                    current_section['paragraphs'].append(text)
                    
            if current_section:
                sections.append(current_section)
            
            structured = {
                'sections': sections,
                'toc': [{'text': s['title'], 'level': s['level']} for s in sections if s.get('title')]
            }
            
            await sio.emit("document_loaded", {
                "session_id": frontend_session_id,
                "document_name": session.metadata.get("document_name"),
                "document_path": doc_path,
                "content": structured
            }, to=sid)  # Emit directly to the socket, not to a room
            
            logger.info(f"Manually emitted document_loaded to socket {sid} for user {user_id}")
            
        except Exception as doc_err:
            logger.error(f"Error loading document content: {doc_err}")
            await sio.emit("error", {"message": f"Error loading document: {str(doc_err)}"}, to=sid)
            
    except Exception as e:
        logger.error(f"Error handling request_document: {str(e)}", exc_info=True)
        await sio.emit("error", {
            "message": f"Error requesting document: {str(e)}"
        }, to=sid)


# ============================================================================
# Document API Endpoints
# ============================================================================

from fastapi import File, UploadFile, Query
from fastapi.responses import FileResponse, StreamingResponse
from document_store import document_store
import sys
import difflib

# Add main/src to path for DocxManager
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'main', 'src'))

try:
    from rct_agent.docx_manager import DocxManager
    from rct_agent.docx_indexer import DocxIndexer
    DOCX_SUPPORT = True
except ImportError:
    logger.warning("DocxManager not available - document parsing will be limited")
    DOCX_SUPPORT = False


@app.get("/api/documents")
async def list_documents():
    """List all documents"""
    docs = document_store.list_documents()
    return {
        "documents": [
            {
                "id": doc.id,
                "name": doc.name,
                "latest_version": doc.latest_version,
                "created_at": doc.created_at,
                "updated_at": doc.updated_at
            }
            for doc in docs
        ]
    }


@app.get("/api/documents/{doc_id}")
async def get_document_content(doc_id: str):
    """Get structured document content"""
    doc = document_store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    latest_version = document_store.get_latest_version(doc_id)
    if not latest_version:
        raise HTTPException(status_code=404, detail="No versions found")
    
    if not DOCX_SUPPORT:
        return {
            "id": doc_id,
            "name": doc.name,
            "version": latest_version.version,
            "headings": [],
            "sections": [],
            "toc": []
        }
    
    try:
        manager = DocxManager(latest_version.source_path)
        outline = manager.get_outline()
        
        # Build TOC from headings
        toc = [
            {
                "text": item["text"],
                "level": item.get("level", 0),
                "anchor": item["anchor"]
            }
            for item in outline
        ]
        
        # Get all paragraphs
        manager._refresh_index()
        sections = [
            {
                "text": p["text"],
                "style": p.get("style", ""),
                "anchor": p["anchor"]
            }
            for p in manager.index_data
        ]
        
        return {
            "id": doc_id,
            "name": doc.name,
            "version": latest_version.version,
            "headings": outline,
            "sections": sections,
            "toc": toc
        }
    except Exception as e:
        logger.error(f"Error parsing document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error parsing document: {str(e)}")


@app.post("/api/documents")
async def upload_document(file: UploadFile = File(...), note: Optional[str] = None):
    """Upload a new document"""
    if not file.filename.endswith('.docx'):
        raise HTTPException(status_code=400, detail="Only .docx files are supported")
    
    # Save temp file
    temp_path = Path("/tmp") / file.filename
    with open(temp_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Create document record
    doc = document_store.create_document(file.filename, str(temp_path), note)
    
    # Cleanup temp file
    temp_path.unlink()
    
    return {
        "id": doc.id,
        "name": doc.name,
        "version": doc.latest_version,
        "created_at": doc.created_at
    }


@app.post("/api/documents/{doc_id}/versions")
async def upload_document_version(
    doc_id: str, 
    file: UploadFile = File(...), 
    note: Optional[str] = None,
    interrupt_id: Optional[str] = None
):
    """Upload a new version of an existing document"""
    doc = document_store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not file.filename.endswith('.docx'):
        raise HTTPException(status_code=400, detail="Only .docx files are supported")
    
    # Save temp file
    temp_path = Path("/tmp") / file.filename
    with open(temp_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Add version
    version = document_store.add_version(doc_id, str(temp_path), note, interrupt_id)
    
    # Cleanup temp file
    temp_path.unlink()
    
    if not version:
        raise HTTPException(status_code=500, detail="Failed to create version")
    
    return {
        "id": doc_id,
        "version": version.version,
        "created_at": version.created_at,
        "note": version.note,
        "has_approval": version.approval is not None
    }


@app.get("/api/documents/{doc_id}/export")
async def export_document(doc_id: str, version: Optional[int] = None):
    """Download a document version"""
    doc = document_store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if version:
        doc_version = document_store.get_version(doc_id, version)
    else:
        doc_version = document_store.get_latest_version(doc_id)
    
    if not doc_version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    file_path = Path(doc_version.source_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=str(file_path),
        filename=doc.name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


@app.get("/api/documents/{doc_id}/diff")
async def get_document_diff(
    doc_id: str,
    before: int = Query(..., description="Before version number"),
    after: int = Query(..., description="After version number")
):
    """Get diff between two document versions"""
    doc = document_store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    before_version = document_store.get_version(doc_id, before)
    after_version = document_store.get_version(doc_id, after)
    
    if not before_version or not after_version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    if not DOCX_SUPPORT:
        return {
            "before": ["DOCX support not available"],
            "after": ["DOCX support not available"],
            "hunks": []
        }
    
    try:
        # Parse both versions
        before_manager = DocxManager(before_version.source_path)
        after_manager = DocxManager(after_version.source_path)
        
        before_manager._refresh_index()
        after_manager._refresh_index()
        
        # Extract text lines
        before_lines = [p["text"] for p in before_manager.index_data]
        after_lines = [p["text"] for p in after_manager.index_data]
        
        # Generate diff using difflib
        differ = difflib.SequenceMatcher(None, before_lines, after_lines)
        
        hunks = []
        for tag, i1, i2, j1, j2 in differ.get_opcodes():
            hunks.append({
                "type": tag,  # 'replace', 'delete', 'insert', 'equal'
                "before_start": i1,
                "before_end": i2,
                "after_start": j1,
                "after_end": j2
            })
        
        return {
            "before": before_lines,
            "after": after_lines,
            "hunks": hunks
        }
    except Exception as e:
        logger.error(f"Error generating diff: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating diff: {str(e)}")


# ============================================================================
# Run Server
# ============================================================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "app:socket_app",  # Use socket_app instead of app for WebSocket support
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
