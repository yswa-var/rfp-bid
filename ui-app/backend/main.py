"""
LangGraph UI Backend Server
FastAPI + Socket.IO for real-time communication
"""
import os
import sys
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
import socketio
from dotenv import load_dotenv

# Add main directory to path for imports
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from langgraph_sdk import get_client

# Load environment variables
load_dotenv()

# Logging setup
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.getenv("LOG_FILE", "ui-app.log"))
    ]
)
logger = logging.getLogger(__name__)

# Configuration
LANGGRAPH_SERVER_URL = os.getenv("LANGGRAPH_SERVER_URL", "http://localhost:8123")
ASSISTANT_ID = os.getenv("ASSISTANT_ID", "agent")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
ENABLE_WEBSOCKET = os.getenv("ENABLE_WEBSOCKET", "true").lower() == "true"


# Session storage
class SessionManager:
    """Manage conversation sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.storage_file = Path("sessions.json")
        self._load_sessions()
    
    def _load_sessions(self):
        """Load sessions from file"""
        if self.storage_file.exists():
            try:
                with open(self.storage_file, 'r') as f:
                    self.sessions = json.load(f)
                logger.info(f"Loaded {len(self.sessions)} sessions")
            except Exception as e:
                logger.error(f"Error loading sessions: {e}")
                self.sessions = {}
    
    def _save_sessions(self):
        """Save sessions to file"""
        try:
            with open(self.storage_file, 'w') as f:
                json.dump(self.sessions, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving sessions: {e}")
    
    def create_session(self, session_id: str, user_name: str = "User") -> Dict[str, Any]:
        """Create a new session"""
        session = {
            "session_id": session_id,
            "thread_id": None,
            "user_name": user_name,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "messages": [],
            "pending_approvals": []
        }
        self.sessions[session_id] = session
        self._save_sessions()
        logger.info(f"Created session {session_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID"""
        return self.sessions.get(session_id)
    
    def update_session(self, session_id: str, updates: Dict[str, Any]):
        """Update session data"""
        if session_id in self.sessions:
            self.sessions[session_id].update(updates)
            self.sessions[session_id]["last_activity"] = datetime.utcnow().isoformat()
            self._save_sessions()
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all sessions"""
        return list(self.sessions.values())
    
    def delete_session(self, session_id: str):
        """Delete a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            self._save_sessions()
            logger.info(f"Deleted session {session_id}")


# Initialize managers
session_manager = SessionManager()
langgraph_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global langgraph_client
    
    # Startup
    logger.info("=== STARTING LANGGRAPH UI BACKEND ===")
    logger.info(f"LangGraph Server: {LANGGRAPH_SERVER_URL}")
    logger.info(f"Assistant ID: {ASSISTANT_ID}")
    
    try:
        langgraph_client = get_client(url=LANGGRAPH_SERVER_URL)
        # Test connection
        assistants = await langgraph_client.assistants.search()
        logger.info(f"✅ Connected to LangGraph Server ({len(assistants)} assistants available)")
    except Exception as e:
        logger.error(f"❌ Failed to connect to LangGraph Server: {e}")
        logger.warning("Server will start but LangGraph features may not work")
    
    yield
    
    # Shutdown
    logger.info("=== SHUTTING DOWN ===")


# FastAPI app
app = FastAPI(title="LangGraph UI Backend", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Socket.IO server
if ENABLE_WEBSOCKET:
    sio = socketio.AsyncServer(
        async_mode='asgi',
        cors_allowed_origins=CORS_ORIGINS,
        logger=True,
        engineio_logger=True
    )
    sio_app = socketio.ASGIApp(sio, app)
else:
    sio_app = app


# Pydantic models
class ChatMessage(BaseModel):
    session_id: str
    message: str
    user_name: Optional[str] = "User"


class ApprovalDecision(BaseModel):
    session_id: str
    thread_id: str
    tool_call_id: str
    tool_name: str
    approved: bool


class SessionCreate(BaseModel):
    user_name: Optional[str] = "User"


# REST API Endpoints
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "langgraph_server": LANGGRAPH_SERVER_URL,
        "langgraph_connected": langgraph_client is not None
    }
    
    if langgraph_client:
        try:
            assistants = await langgraph_client.assistants.search()
            status["assistants_available"] = len(assistants)
        except Exception as e:
            status["langgraph_error"] = str(e)
            status["langgraph_connected"] = False
    
    return status


@app.get("/api/status")
async def get_status():
    """Get system status"""
    return {
        "langgraph_url": LANGGRAPH_SERVER_URL,
        "assistant_id": ASSISTANT_ID,
        "websocket_enabled": ENABLE_WEBSOCKET,
        "active_sessions": len(session_manager.sessions),
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/api/sessions")
async def create_session(data: SessionCreate):
    """Create a new chat session"""
    import uuid
    session_id = str(uuid.uuid4())
    session = session_manager.create_session(session_id, data.user_name)
    return session


@app.get("/api/sessions")
async def list_sessions():
    """List all sessions"""
    return {"sessions": session_manager.list_sessions()}


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session details"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    session_manager.delete_session(session_id)
    return {"message": "Session deleted"}


@app.post("/api/chat/send")
async def send_message(data: ChatMessage):
    """Send a message to the AI"""
    if not langgraph_client:
        raise HTTPException(status_code=503, detail="LangGraph Server not connected")
    
    session = session_manager.get_session(data.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        # Get or create thread
        thread_id = session.get("thread_id")
        if not thread_id:
            thread = await langgraph_client.threads.create(
                metadata={
                    "session_id": data.session_id,
                    "user_name": data.user_name,
                    "platform": "web-ui"
                }
            )
            thread_id = thread["thread_id"]
            session_manager.update_session(data.session_id, {"thread_id": thread_id})
        
        # Add user message to session
        user_message = {
            "role": "user",
            "content": data.message,
            "timestamp": datetime.utcnow().isoformat()
        }
        session["messages"].append(user_message)
        session_manager.update_session(data.session_id, {"messages": session["messages"]})
        
        # Send to LangGraph
        logger.info(f"Sending message to thread {thread_id}")
        run = await langgraph_client.runs.wait(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID,
            input={"messages": [{"role": "user", "content": data.message}]}
        )
        
        logger.info(f"Run completed with status: {run.get('status', 'unknown')}")
        
        # Handle response
        response_data = await _handle_run_response(session_id=data.session_id, thread_id=thread_id, run=run)
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error sending message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/approval")
async def submit_approval(data: ApprovalDecision):
    """Submit approval decision"""
    if not langgraph_client:
        raise HTTPException(status_code=503, detail="LangGraph Server not connected")
    
    try:
        logger.info(f"Approval decision: {data.approved} for {data.tool_name}")
        
        # Resume run with approval decision
        run = await langgraph_client.runs.wait(
            thread_id=data.thread_id,
            assistant_id=ASSISTANT_ID,
            input=None,
            command={
                "resume": {
                    "tool_call_id": data.tool_call_id,
                    "tool_name": data.tool_name,
                    "approved": data.approved
                }
            }
        )
        
        # Handle completed run
        response_data = await _handle_run_response(session_id=data.session_id, thread_id=data.thread_id, run=run)
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error handling approval: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/documents")
async def list_documents():
    """List available documents"""
    docx_dir = Path(os.getenv("DOCX_OUTPUT_DIR", "test_output/docx"))
    if not docx_dir.exists():
        return {"documents": []}
    
    documents = []
    for file in docx_dir.glob("*.docx"):
        documents.append({
            "name": file.name,
            "path": str(file),
            "size": file.stat().st_size,
            "modified": datetime.fromtimestamp(file.stat().st_mtime).isoformat()
        })
    
    return {"documents": documents}


@app.get("/api/documents/{filename}")
async def get_document(filename: str):
    """Get document content (for download)"""
    docx_dir = Path(os.getenv("DOCX_OUTPUT_DIR", "test_output/docx"))
    file_path = docx_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")
    
    return FileResponse(file_path, filename=filename)


# Helper functions
async def _handle_run_response(session_id: str, thread_id: str, run: Dict[str, Any]) -> Dict[str, Any]:
    """Handle different run response types"""
    
    # Check if direct output
    if isinstance(run, dict) and "messages" in run and "status" not in run:
        return _handle_success(session_id, {"output": run})
    
    # Check for interrupt
    if isinstance(run, dict) and "__interrupt__" in run:
        return await _handle_interrupt(session_id, thread_id, run)
    
    # Handle status-based responses
    status = run.get("status", "unknown")
    
    if status == "success":
        return _handle_success(session_id, run)
    
    elif status == "interrupted":
        return await _handle_interrupt(session_id, thread_id, run)
    
    elif status == "error":
        error_msg = run.get("error", "Unknown error")
        return {
            "type": "error",
            "message": error_msg
        }
    
    else:
        return {
            "type": "unknown",
            "status": status,
            "data": run
        }


def _handle_success(session_id: str, run: Dict[str, Any]) -> Dict[str, Any]:
    """Handle successful run"""
    output = run.get("output", {})
    messages = output.get("messages", [])
    
    if messages:
        last_message = messages[-1]
        content = last_message.get("content", "") if isinstance(last_message, dict) else str(last_message)
        
        # Add AI message to session
        session = session_manager.get_session(session_id)
        if session:
            ai_message = {
                "role": "assistant",
                "content": content,
                "timestamp": datetime.utcnow().isoformat()
            }
            session["messages"].append(ai_message)
            session_manager.update_session(session_id, {"messages": session["messages"]})
        
        return {
            "type": "success",
            "message": content,
            "full_output": output
        }
    
    return {
        "type": "success",
        "message": "Task completed successfully"
    }


async def _handle_interrupt(session_id: str, thread_id: str, run: Dict[str, Any]) -> Dict[str, Any]:
    """Handle interrupted run (approval needed)"""
    try:
        # Get thread state
        state = await langgraph_client.threads.get_state(thread_id)
        
        # Look for approval request
        approval_data = None
        interrupts = state.get("interrupts", [])
        
        for interrupt in interrupts:
            value = interrupt.get("value", {})
            if isinstance(value, dict) and value.get("type") == "approval_request":
                approval_data = value
                break
        
        # Also check run data
        if not approval_data and "__interrupt__" in run:
            interrupt_value = run.get("__interrupt__", {})
            if isinstance(interrupt_value, dict) and interrupt_value.get("type") == "approval_request":
                approval_data = interrupt_value
        
        if approval_data:
            # Save pending approval in session
            session = session_manager.get_session(session_id)
            if session:
                session["pending_approvals"].append({
                    "thread_id": thread_id,
                    "approval_data": approval_data,
                    "timestamp": datetime.utcnow().isoformat()
                })
                session_manager.update_session(session_id, {"pending_approvals": session["pending_approvals"]})
            
            return {
                "type": "approval_required",
                "thread_id": thread_id,
                "tool_name": approval_data.get("tool_name"),
                "tool_call_id": approval_data.get("tool_call_id"),
                "description": approval_data.get("description"),
                "args": approval_data.get("args")
            }
        
        return {
            "type": "interrupted",
            "message": "Operation was paused. Please provide input."
        }
        
    except Exception as e:
        logger.error(f"Error handling interrupt: {e}", exc_info=True)
        return {
            "type": "error",
            "message": f"Error processing approval request: {str(e)}"
        }


# Socket.IO events (if enabled)
if ENABLE_WEBSOCKET:
    @sio.event
    async def connect(sid, environ):
        logger.info(f"Client connected: {sid}")
        await sio.emit('connection_status', {'status': 'connected'}, room=sid)
    
    @sio.event
    async def disconnect(sid):
        logger.info(f"Client disconnected: {sid}")
    
    @sio.event
    async def join_session(sid, data):
        session_id = data.get('session_id')
        logger.info(f"Client {sid} joined session {session_id}")
        await sio.enter_room(sid, session_id)
    
    @sio.event
    async def send_message(sid, data):
        """Handle chat message via WebSocket"""
        try:
            session_id = data.get('session_id')
            message = data.get('message')
            
            # Process message (reuse REST logic)
            chat_data = ChatMessage(session_id=session_id, message=message)
            response = await send_message(chat_data)
            
            # Emit response to session room
            await sio.emit('message_response', response, room=session_id)
            
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            await sio.emit('error', {'message': str(e)}, room=sid)


# Run the app
if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("BACKEND_HOST", "0.0.0.0")
    port = int(os.getenv("BACKEND_PORT", 8000))
    
    logger.info(f"Starting server on {host}:{port}")
    
    if ENABLE_WEBSOCKET:
        uvicorn.run(sio_app, host=host, port=port, log_level="info")
    else:
        uvicorn.run(app, host=host, port=port, log_level="info")
