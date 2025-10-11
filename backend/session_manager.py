"""
Session Manager for handling user conversations across platforms
Uses CSV file for persistent storage
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import uuid
import asyncio
import threading
import csv
import os
from pathlib import Path
import json


@dataclass
class Session:
    """Represents a user session/conversation"""
    session_id: str
    user_id: str
    platform: str
    thread_id: str  # LangGraph thread ID
    created_at: datetime
    last_activity: datetime
    pending_approval: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "platform": self.platform,
            "thread_id": self.thread_id,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "has_pending_approval": self.pending_approval is not None,
            "metadata": self.metadata
        }


class SessionManager:
    """Manages user sessions across platforms with CSV persistence"""
    
    def __init__(self, session_timeout_minutes: int = 60, csv_file: str = "sessions.csv"):
        """
        Initialize session manager with CSV persistence

        Args:
            session_timeout_minutes: Minutes of inactivity before session expires
            csv_file: Path to CSV file for storing sessions
        """
        self._sessions: Dict[str, Session] = {}
        self._user_sessions: Dict[str, List[str]] = {}  # user_id -> [session_ids]
        self._lock = threading.Lock()
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self.csv_file = csv_file

        # Clear CSV file for demo purposes (clean slate every time)
        self._clear_csv_for_demo()

        # Ensure CSV file exists and load existing sessions
        self._init_csv()
        self._load_sessions()

        # Start cleanup task
        self._start_cleanup_task()

    def _clear_csv_for_demo(self):
        """Clear CSV file for demo purposes (clean slate)"""
        try:
            # Simply overwrite the CSV file with just headers
            with open(self.csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'session_id', 'user_id', 'platform', 'thread_id',
                    'created_at', 'last_activity', 'pending_approval', 'metadata'
                ])
            print(f"Cleared sessions CSV file for demo: {self.csv_file}")
        except Exception as e:
            print(f"Error clearing CSV file for demo: {e}")

    def _init_csv(self):
        """Initialize CSV file with headers if it doesn't exist"""
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'session_id', 'user_id', 'platform', 'thread_id',
                    'created_at', 'last_activity', 'pending_approval', 'metadata'
                ])
    
    def _load_sessions(self):
        """Load sessions from CSV file"""
        if not os.path.exists(self.csv_file):
            return
        
        try:
            with open(self.csv_file, 'r', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        session = Session(
                            session_id=row['session_id'],
                            user_id=row['user_id'],
                            platform=row['platform'],
                            thread_id=row['thread_id'],
                            created_at=datetime.fromisoformat(row['created_at']),
                            last_activity=datetime.fromisoformat(row['last_activity']),
                            pending_approval=json.loads(row['pending_approval']) if row['pending_approval'] else None,
                            metadata=json.loads(row['metadata']) if row['metadata'] else {}
                        )
                        
                        # Only load non-expired sessions
                        if datetime.utcnow() - session.last_activity < self.session_timeout:
                            self._sessions[session.session_id] = session
                            
                            # Build user_sessions index
                            if session.user_id not in self._user_sessions:
                                self._user_sessions[session.user_id] = []
                            self._user_sessions[session.user_id].append(session.session_id)
                    except Exception as e:
                        print(f"Error loading session from CSV: {e}")
                        continue
            
            print(f"Loaded {len(self._sessions)} sessions from {self.csv_file}")
        except Exception as e:
            print(f"Error reading CSV file: {e}")
    
    def _save_sessions(self):
        """Save all sessions to CSV file"""
        try:
            with open(self.csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                # Write header
                writer.writerow([
                    'session_id', 'user_id', 'platform', 'thread_id',
                    'created_at', 'last_activity', 'pending_approval', 'metadata'
                ])
                
                # Write sessions
                for session in self._sessions.values():
                    writer.writerow([
                        session.session_id,
                        session.user_id,
                        session.platform,
                        session.thread_id,
                        session.created_at.isoformat(),
                        session.last_activity.isoformat(),
                        json.dumps(session.pending_approval) if session.pending_approval else '',
                        json.dumps(session.metadata) if session.metadata else '{}'
                    ])
        except Exception as e:
            print(f"Error saving sessions to CSV: {e}")
    
    def get_or_create_session(
        self, 
        user_id: str, 
        platform: str = "api",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Session:
        """
        Get existing session or create a new one for user
        
        Args:
            user_id: Unique user identifier
            platform: Platform name (telegram, discord, slack, etc.)
            metadata: Optional metadata for the session
            
        Returns:
            Session object
        """
        with self._lock:
            # Check for existing active session
            if user_id in self._user_sessions:
                for session_id in self._user_sessions[user_id]:
                    session = self._sessions.get(session_id)
                    if session and session.platform == platform:
                        # Update last activity
                        session.last_activity = datetime.utcnow()
                        self._save_sessions()  # Save to CSV
                        return session
            
            # Create new session
            session = Session(
                session_id=str(uuid.uuid4()),
                user_id=user_id,
                platform=platform,
                thread_id=str(uuid.uuid4()),  # LangGraph thread ID
                created_at=datetime.utcnow(),
                last_activity=datetime.utcnow(),
                metadata=metadata or {}
            )
            
            # Store session
            self._sessions[session.session_id] = session
            
            # Add to user sessions
            if user_id not in self._user_sessions:
                self._user_sessions[user_id] = []
            self._user_sessions[user_id].append(session.session_id)
            
            # Save to CSV
            self._save_sessions()
            
            return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                # Update last activity
                session.last_activity = datetime.utcnow()
                self._save_sessions()  # Save to CSV
            return session
    
    def get_user_sessions(self, user_id: str) -> List[Session]:
        """Get all sessions for a user"""
        with self._lock:
            session_ids = self._user_sessions.get(user_id, [])
            return [
                self._sessions[sid] 
                for sid in session_ids 
                if sid in self._sessions
            ]
    
    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """Get all active sessions"""
        with self._lock:
            return [s.to_dict() for s in self._sessions.values()]
    
    def get_active_session_count(self) -> int:
        """Get count of active sessions"""
        with self._lock:
            return len(self._sessions)
    
    def set_pending_approval(
        self, 
        session_id: str, 
        approval_data: Dict[str, Any]
    ) -> bool:
        """
        Set pending approval data for a session
        
        Args:
            session_id: Session ID
            approval_data: Approval request data
            
        Returns:
            True if successful, False if session not found
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            
            session.pending_approval = approval_data
            session.last_activity = datetime.utcnow()
            self._save_sessions()  # Save to CSV
            return True
    
    def update_session_metadata(
        self,
        session_id: str,
        metadata_updates: Dict[str, Any]
    ) -> bool:
        """Merge metadata updates into the session and persist to CSV"""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False

            session.metadata = {
                **(session.metadata or {}),
                **metadata_updates,
            }
            session.last_activity = datetime.utcnow()
            self._save_sessions()
            return True

    def clear_pending_approval(self, session_id: str) -> bool:
        """Clear pending approval from a session"""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            
            session.pending_approval = None
            session.last_activity = datetime.utcnow()
            self._save_sessions()  # Save to CSV
            return True
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            
            # Remove from user sessions
            if session.user_id in self._user_sessions:
                self._user_sessions[session.user_id] = [
                    sid for sid in self._user_sessions[session.user_id]
                    if sid != session_id
                ]
                
                # Remove user entry if no more sessions
                if not self._user_sessions[session.user_id]:
                    del self._user_sessions[session.user_id]
            
            # Remove session
            del self._sessions[session_id]
            self._save_sessions()  # Save to CSV
            return True
    
    def cleanup_expired_sessions(self) -> int:
        """
        Remove expired sessions based on timeout
        
        Returns:
            Number of sessions removed
        """
        with self._lock:
            now = datetime.utcnow()
            expired_sessions = [
                session_id
                for session_id, session in self._sessions.items()
                if now - session.last_activity > self.session_timeout
            ]
            
            # Delete expired sessions (this will save to CSV)
            for session_id in expired_sessions:
                # Direct deletion without recursion
                session = self._sessions.get(session_id)
                if session:
                    if session.user_id in self._user_sessions:
                        self._user_sessions[session.user_id] = [
                            sid for sid in self._user_sessions[session.user_id]
                            if sid != session_id
                        ]
                        if not self._user_sessions[session.user_id]:
                            del self._user_sessions[session.user_id]
                    del self._sessions[session_id]
            
            # Save once after all deletions
            if expired_sessions:
                self._save_sessions()
            
            return len(expired_sessions)
    
    def _start_cleanup_task(self):
        """Start background task to cleanup expired sessions"""
        def cleanup_loop():
            while True:
                try:
                    removed = self.cleanup_expired_sessions()
                    if removed > 0:
                        print(f"Cleaned up {removed} expired sessions")
                except Exception as e:
                    print(f"Error in session cleanup: {e}")
                
                # Run cleanup every 5 minutes
                threading.Event().wait(300)
        
        cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        cleanup_thread.start()
