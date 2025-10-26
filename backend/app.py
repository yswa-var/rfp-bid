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
import json
import tempfile
import glob

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
    logger=False,
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
OUTPUT_DOCX_DIR = BASE_DIR.parent / "main" / "test_output" / "docx"
OUTPUT_CONTENT_DIR = BASE_DIR.parent / "main" / "test_output" / "content"
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


def parse_timestamp_from_filename(filename: str) -> Optional[str]:
    """Extract timestamp from output_TIMESTAMP.docx or content_TIMESTAMP.json format"""
    if filename.startswith("output_") and filename.endswith(".docx"):
        # Extract timestamp: output_20251023_140331.docx -> 20251023_140331
        timestamp_part = filename[7:-5]  # Remove "output_" and ".docx"
        return timestamp_part
    elif filename.startswith("content_") and filename.endswith(".json"):
        # Extract timestamp: content_1761430891.json -> 1761430891
        timestamp_part = filename[8:-5]  # Remove "content_" and ".json"
        return timestamp_part
    return None


def get_sorted_output_documents() -> List[Path]:
    """Get list of output documents sorted by timestamp (newest first)"""
    if not OUTPUT_DOCX_DIR.exists():
        logger.warning(f"Output directory does not exist: {OUTPUT_DOCX_DIR}")
        return []
    
    documents = []
    for file_path in OUTPUT_DOCX_DIR.glob("output_*.docx"):
        timestamp = parse_timestamp_from_filename(file_path.name)
        if timestamp:
            documents.append((timestamp, file_path))
    
    # Sort by timestamp descending (newest first)
    documents.sort(key=lambda x: x[0], reverse=True)
    return [doc[1] for doc in documents]


def get_sorted_content_json_files() -> List[Path]:
    """Get list of content JSON files sorted by timestamp (newest first)"""
    if not OUTPUT_CONTENT_DIR.exists():
        logger.warning(f"Content directory does not exist: {OUTPUT_CONTENT_DIR}")
        return []
    
    json_files = []
    for file_path in OUTPUT_CONTENT_DIR.glob("content_*.json"):
        timestamp = parse_timestamp_from_filename(file_path.name)
        if timestamp:
            json_files.append((timestamp, file_path))
    
    # Sort by timestamp descending (newest first)
    json_files.sort(key=lambda x: x[0], reverse=True)
    return [json_file[1] for json_file in json_files]


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
    Handle real-time chat message from WebSocket with execution trail streaming
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
        
        # Normal message processing with agent selection and streaming
        # Prepend agent directive if not supervisor
        if selected_agent and selected_agent != 'supervisor':
            # Force routing to selected agent by mentioning it explicitly
            enhanced_message = f"[Route to {selected_agent}] {message_text}"
        else:
            enhanced_message = message_text
        
        # Define streaming callback to emit trail events
        async def stream_callback(event):
            """Send execution trail events to frontend in real-time"""
            await sio.emit("execution_trail", {
                "session_id": session.session_id,
                "trail_event": event,
                "timestamp": datetime.now().isoformat()
            }, to=sid)
        
        # Emit processing started
        await sio.emit("processing_started", {
            "session_id": session.session_id,
            "message": message_text,
            "selected_agent": selected_agent
        }, to=sid)
        
        # Use streaming method instead of regular process_message
        try:
            result = await agent_runner.process_message_stream(
                session_id=session.session_id,
                thread_id=session.thread_id,
                message=enhanced_message,
                document_context=session.metadata or{},
                selected_agent=selected_agent,
                event_callback=stream_callback  # Pass callback
            )
            
            logger.info(f"Stream processing completed. Result: {result.get('message', 'No message')[:100]}")
            
        except Exception as stream_error:
            logger.error(f"Error in stream processing: {stream_error}", exc_info=True)
            # Emit error to frontend
            await sio.emit("message_response", {
                "session_id": session.session_id,
                "message": f"Sorry, I encountered an error: {str(stream_error)}",
                "requires_approval": False,
                "status": "error"
            }, to=sid)
            return
        
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
    Handle document load request from frontend
    Returns the latest document from OUTPUT_CONTENT_DIR (JSON files)
    """
    try:
        frontend_session_id = data.get("session_id", "default")
        
        # Get latest JSON content file
        json_files = get_sorted_content_json_files()
        
        if not json_files:
            await sio.emit("message_response", {
                "session_id": frontend_session_id,
                "message": "No documents available yet. Waiting for documents...",
                "requires_approval": False,
                "status": "info"
            }, to=sid)
            return
        
        # Get the latest JSON file
        json_path = json_files[0]
        
        if not json_path.exists():
            await sio.emit("error", {"message": "Document file not found"}, to=sid)
            return
        
        # Load and parse JSON content
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                content_data = json.load(f)
            
            # Structure the content for frontend
            sections = []
            for section_name, section_items in content_data.items():
                section = {
                    'title': section_name.replace('_', ' '),
                    'items': []
                }
                
                for item in section_items:
                    item_type = item.get('type')
                    if item_type == 'heading':
                        section['items'].append({
                            'type': 'heading',
                            'text': item.get('text', ''),
                            'level': item.get('level', 1)
                        })
                    elif item_type == 'paragraph':
                        section['items'].append({
                            'type': 'paragraph',
                            'text': item.get('text', '')
                        })
                    elif item_type == 'image':
                        image_path = item.get('path', '')
                        if image_path:
                            image_filename = Path(image_path).name
                            section['items'].append({
                                'type': 'image',
                                'filename': image_filename,
                                'path': image_path,
                                'width': item.get('width', 480)
                            })
                    elif item_type == 'table':
                        section['items'].append({
                            'type': 'table',
                            'data': item.get('data', [])
                        })
                
                sections.append(section)
            
            await sio.emit("document_loaded", {
                "session_id": frontend_session_id,
                "document_name": json_path.name,
                "document_path": str(json_path),
                "content": {"sections": sections}
            }, to=sid)
            
            logger.info(f"Emitted document_loaded to socket {sid}: {json_path.name}")
            
        except Exception as doc_err:
            logger.error(f"Error loading document content: {doc_err}")
            await sio.emit("error", {"message": f"Error loading document: {str(doc_err)}"}, to=sid)
            
    except Exception as e:
        logger.error(f"Error handling request_document: {str(e)}", exc_info=True)
        await sio.emit("error", {
            "message": f"Error requesting document: {str(e)}"
        }, to=sid)


@sio.event
async def get_latest_document(sid, data):
    """
    Get the latest document from OUTPUT_CONTENT_DIR (JSON files)
    This is called by the frontend polling mechanism
    """
    try:
        frontend_session_id = data.get("session_id", "default")
        
        # Get latest JSON content file
        json_files = get_sorted_content_json_files()
        
        if not json_files:
            # No documents available yet
            await sio.emit("no_documents", {
                "session_id": frontend_session_id,
                "message": "Monitoring for documents..."
            }, to=sid)
            return
        
        # Get the latest JSON file
        json_path = json_files[0]
        
        if not json_path.exists():
            await sio.emit("error", {"message": "Document file not found"}, to=sid)
            return
        
        # Load and parse JSON content
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                content_data = json.load(f)
            
            # Structure the content for frontend
            sections = []
            for section_name, section_items in content_data.items():
                section = {
                    'title': section_name.replace('_', ' '),
                    'items': []
                }
                
                for item in section_items:
                    item_type = item.get('type')
                    if item_type == 'heading':
                        section['items'].append({
                            'type': 'heading',
                            'text': item.get('text', ''),
                            'level': item.get('level', 1)
                        })
                    elif item_type == 'paragraph':
                        section['items'].append({
                            'type': 'paragraph',
                            'text': item.get('text', '')
                        })
                    elif item_type == 'image':
                        # Convert absolute path to relative for serving
                        image_path = item.get('path', '')
                        if image_path:
                            # Extract just the filename from the path
                            image_filename = Path(image_path).name
                            section['items'].append({
                                'type': 'image',
                                'filename': image_filename,
                                'path': image_path,  # Keep original for backend reference
                                'width': item.get('width', 480)
                            })
                    elif item_type == 'table':
                        section['items'].append({
                            'type': 'table',
                            'data': item.get('data', [])
                        })
                
                sections.append(section)
            
            await sio.emit("document_loaded", {
                "session_id": frontend_session_id,
                "document_name": json_path.name,
                "document_path": str(json_path),
                "content": {"sections": sections}
            }, to=sid)
            
            # Also emit the file count
            await sio.emit("content_file_count", {
                "session_id": frontend_session_id,
                "count": len(json_files)
            }, to=sid)
            
            # logger.info(f"Polled and emitted document: {json_path.name}")
            
        except Exception as doc_err:
            logger.error(f"Error loading document content: {doc_err}")
            await sio.emit("error", {"message": f"Error loading document: {str(doc_err)}"}, to=sid)
            
    except Exception as e:
        logger.error(f"Error handling get_latest_document: {str(e)}", exc_info=True)
        await sio.emit("error", {
            "message": f"Error getting latest document: {str(e)}"
        }, to=sid)


@sio.event
async def accept_document(sid, data):
    """
    Accept the current document
    Logs acceptance and sends confirmation
    """
    try:
        document_name = data.get("document_name", "")
        frontend_session_id = data.get("session_id", "default")
        
        logger.info(f"Document accepted: {document_name} by socket {sid}")
        
        await sio.emit("document_accepted", {
            "session_id": frontend_session_id,
            "document_name": document_name,
            "message": f"Document '{document_name}' accepted successfully!"
        }, to=sid)
        
    except Exception as e:
        logger.error(f"Error handling accept_document: {str(e)}", exc_info=True)
        await sio.emit("error", {
            "message": f"Error accepting document: {str(e)}"
        }, to=sid)


@sio.event
async def get_content_file_count(sid, data):
    """
    Get the count of JSON files in the content directory
    Used to determine if reject button should be disabled
    """
    try:
        frontend_session_id = data.get("session_id", "default")
        
        # Get count of JSON content files
        json_files = get_sorted_content_json_files()
        file_count = len(json_files)
        
        await sio.emit("content_file_count", {
            "session_id": frontend_session_id,
            "count": file_count
        }, to=sid)
        
        # logger.info(f"Content file count: {file_count}")
        
    except Exception as e:
        logger.error(f"Error getting content file count: {str(e)}", exc_info=True)
        await sio.emit("error", {
            "message": f"Error getting file count: {str(e)}"
        }, to=sid)


@sio.event
async def reject_document(sid, data):
    """
    Reject and delete the current document (JSON and corresponding DOCX)
    Then load the next latest document
    """
    try:
        document_name = data.get("document_name", "")
        frontend_session_id = data.get("session_id", "default")
        
        logger.info(f"Document rejected: {document_name} by socket {sid}")
        
        # Delete the JSON file
        json_path = OUTPUT_CONTENT_DIR / document_name
        if json_path.exists():
            json_path.unlink()
            logger.info(f"Deleted JSON file: {json_path}")
        else:
            logger.warning(f"JSON file not found for deletion: {json_path}")
        
        # Also delete the corresponding DOCX file if it exists
        # Extract timestamp and find matching docx
        timestamp = parse_timestamp_from_filename(document_name)
        if timestamp:
            # Find matching DOCX files with this timestamp
            for docx_file in OUTPUT_DOCX_DIR.glob(f"output_*{timestamp}*.docx"):
                if docx_file.exists():
                    docx_file.unlink()
                    logger.info(f"Deleted corresponding DOCX file: {docx_file}")
        
        # Get the next latest JSON file
        json_files = get_sorted_content_json_files()
        
        if not json_files:
            # No more documents available
            await sio.emit("document_rejected", {
                "session_id": frontend_session_id,
                "document_name": document_name,
                "message": f"Document '{document_name}' rejected and deleted. No more documents available."
            }, to=sid)
            
            await sio.emit("no_documents", {
                "session_id": frontend_session_id,
                "message": "No documents available"
            }, to=sid)
            return
        
        # Load the next JSON file
        next_json_path = json_files[0]
        
        try:
            with open(next_json_path, 'r', encoding='utf-8') as f:
                content_data = json.load(f)
            
            # Structure the content for frontend
            sections = []
            for section_name, section_items in content_data.items():
                section = {
                    'title': section_name.replace('_', ' '),
                    'items': []
                }
                
                for item in section_items:
                    item_type = item.get('type')
                    if item_type == 'heading':
                        section['items'].append({
                            'type': 'heading',
                            'text': item.get('text', ''),
                            'level': item.get('level', 1)
                        })
                    elif item_type == 'paragraph':
                        section['items'].append({
                            'type': 'paragraph',
                            'text': item.get('text', '')
                        })
                    elif item_type == 'image':
                        image_path = item.get('path', '')
                        if image_path:
                            image_filename = Path(image_path).name
                            section['items'].append({
                                'type': 'image',
                                'filename': image_filename,
                                'path': image_path,
                                'width': item.get('width', 480)
                            })
                    elif item_type == 'table':
                        section['items'].append({
                            'type': 'table',
                            'data': item.get('data', [])
                        })
                
                sections.append(section)
            
            await sio.emit("document_rejected", {
                "session_id": frontend_session_id,
                "document_name": document_name,
                "message": f"Document '{document_name}' rejected and deleted. Loading next document..."
            }, to=sid)
            
            await sio.emit("document_loaded", {
                "session_id": frontend_session_id,
                "document_name": next_json_path.name,
                "document_path": str(next_json_path),
                "content": {"sections": sections}
            }, to=sid)
            
            # Emit updated file count after rejection
            updated_json_files = get_sorted_content_json_files()
            await sio.emit("content_file_count", {
                "session_id": frontend_session_id,
                "count": len(updated_json_files)
            }, to=sid)
            
            logger.info(f"After rejection, loaded next document: {next_json_path.name}")
            
        except Exception as doc_err:
            logger.error(f"Error loading next document after rejection: {doc_err}")
            await sio.emit("error", {"message": f"Error loading next document: {str(doc_err)}"}, to=sid)
            
    except Exception as e:
        logger.error(f"Error handling reject_document: {str(e)}", exc_info=True)
        await sio.emit("error", {
            "message": f"Error rejecting document: {str(e)}"
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

# Import directly from module file to avoid package init issues
import importlib.util
_converter_path = os.path.join(os.path.dirname(__file__), '..', 'main', 'src', 'react_agent', 'json_docx_converter.py')
_spec = importlib.util.spec_from_file_location("json_docx_converter", _converter_path)
_converter_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_converter_module)
convert_json_to_docx = _converter_module.convert_json_to_docx


def get_latest_config_file() -> Optional[Path]:
    """Get the latest config file from CONFIG_DIR."""
    config_dir = BASE_DIR.parent / "main" / "test_output" / "config"
    if not config_dir.exists():
        return None
    
    pattern = str(config_dir / "config_*.json")
    files = glob.glob(pattern)
    
    if not files:
        # Try fallback config.json
        fallback = config_dir / "config.json"
        return fallback if fallback.exists() else None
    
    # Extract timestamps and return latest
    versioned = []
    for f in files:
        try:
            basename = os.path.basename(f)
            timestamp_str = basename.replace("config_", "").replace(".json", "")
            timestamp = int(timestamp_str)
            versioned.append((timestamp, Path(f)))
        except ValueError:
            continue
    
    if versioned:
        versioned.sort(reverse=True)
        return versioned[0][1]
    return None


@app.get("/api/images/{image_filename}")
async def serve_image(image_filename: str):
    """
    Serve images from the main/images directory
    """
    try:
        # Look for the image in the main/images directory
        image_path = BASE_DIR.parent / "main" / "images" / image_filename
        
        if not image_path.exists():
            raise HTTPException(status_code=404, detail="Image not found")
        
        return FileResponse(
            path=str(image_path),
            media_type="image/png"  # Adjust based on file extension if needed
        )
    except Exception as e:
        logger.error(f"Error serving image {image_filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/download/docx/latest")
async def download_latest_docx():
    """
    Download the latest rendered DOCX file from test_output/docx directory
    """
    try:
        # Get the latest DOCX file
        docx_files = get_sorted_output_documents()
        
        if not docx_files:
            raise HTTPException(status_code=404, detail="No DOCX files available")
        
        latest_docx = docx_files[0]
        
        if not latest_docx.exists():
            raise HTTPException(status_code=404, detail="DOCX file not found")
        
        return FileResponse(
            path=str(latest_docx),
            filename=latest_docx.name,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading DOCX: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/download/docx/{content_filename}")
async def download_docx_for_content(content_filename: str):
    """
    Render and download a DOCX file from the content JSON on-demand.
    Uses the latest config file and specified content file to generate a fresh DOCX.
    """
    try:
        # Validate content file exists
        content_path = OUTPUT_CONTENT_DIR / content_filename
        if not content_path.exists():
            raise HTTPException(status_code=404, detail="Content file not found")
        
        # Get latest config file
        latest_config = get_latest_config_file()
        if not latest_config or not latest_config.exists():
            raise HTTPException(status_code=404, detail="No config file found")
        
        # Create temporary file for DOCX output
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.docx', delete=False) as tmp_file:
            temp_docx_path = tmp_file.name
        
        try:
            # Render DOCX using convert_json_to_docx
            success, message = convert_json_to_docx(
                str(latest_config),
                str(content_path),
                temp_docx_path
            )
            
            if not success:
                raise HTTPException(status_code=500, detail=f"Failed to render DOCX: {message}")
            
            # Generate friendly filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            download_filename = f"output_{timestamp}.docx"
            
            # Return file and schedule cleanup
            return FileResponse(
                path=temp_docx_path,
                filename=download_filename,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                background=lambda: os.unlink(temp_docx_path) if os.path.exists(temp_docx_path) else None
            )
        except Exception as render_err:
            # Clean up temp file on error
            if os.path.exists(temp_docx_path):
                os.unlink(temp_docx_path)
            raise render_err
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering DOCX for download: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/traces/{run_id}")
async def get_trace_data(run_id: str, retry: int = 0):
    """
    Fetch trace data from LangSmith API
    This endpoint acts as a proxy to the LangSmith API to fetch execution traces
    """
    import httpx
    import asyncio
    
    logger.info(f"🔍 API: Fetching trace for run_id: {run_id} (retry: {retry})")
    
    langsmith_api_key = os.getenv("LANGCHAIN_API_KEY")
    langsmith_api_url = os.getenv("LANGSMITH_API_URL", "https://api.smith.langchain.com")
    
    if not langsmith_api_key:
        logger.error("🔍 API: LangSmith API key not configured")
        raise HTTPException(status_code=503, detail="LangSmith API key not configured")
    
    try:
        async with httpx.AsyncClient() as client:
            # Add retry logic with exponential backoff (LangSmith might need time to process)
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logger.info(f"🔍 API: Attempt {attempt + 1}/{max_retries} to fetch from LangSmith")
                    response = await client.get(
                        f"{langsmith_api_url}/runs/{run_id}",
                        headers={"x-api-key": langsmith_api_key},
                        timeout=10.0
                    )
                    
                    logger.info(f"🔍 API: LangSmith response status: {response.status_code}")
                    
                    if response.status_code == 404:
                        if attempt < max_retries - 1:
                            # Wait before retry (exponential backoff)
                            wait_time = 2 ** attempt
                            logger.info(f"🔍 API: Trace not found yet, waiting {wait_time}s before retry...")
                            await asyncio.sleep(wait_time)
                            continue
                        raise HTTPException(status_code=404, detail="Trace not found in LangSmith after retries")
                    
                    response.raise_for_status()
                    trace_data = response.json()
                    logger.info(f"🔍 API: Successfully fetched trace data")
                    return trace_data
                    
                except httpx.TimeoutException:
                    if attempt < max_retries - 1:
                        logger.warning(f"🔍 API: Timeout, retrying...")
                        await asyncio.sleep(2 ** attempt)
                        continue
                    raise
            
    except httpx.HTTPError as e:
        logger.error(f"🔍 API: Error fetching trace: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch trace: {str(e)}")


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
