"""
Memory Manager for Teams RFP Bot - Uses EXISTING database schema
"""
import sqlite3
import json
import re
from typing import Dict, Any, List, Optional
from pathlib import Path
import datetime

class TeamsMemoryManager:
    """Manages conversation memory and entity extraction for Teams bot"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent / "data" / "memory.db"
        
        self.db_path = str(db_path)
        self._ensure_db_exists()
        self._init_db()
    
    def _ensure_db_exists(self):
        """Ensure the database directory and file exist"""
        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _init_db(self):
        """Initialize the database tables - USE EXISTING SCHEMA"""
        with sqlite3.connect(self.db_path) as conn:
            # Use the EXISTING schema that was working
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    user_id TEXT,
                    key TEXT,
                    value TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, key)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    user_id TEXT,
                    message TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
    
    def extract_entities(self, text: str) -> Dict[str, str]:
        """Extract key entities from text using improved patterns"""
        entities = {}
        text_lower = text.lower()
        
        # Name and company patterns - handle "I am X from Y" format
        name_company_patterns = [
            r'(?:i\'?m|my name is|i am)\s+([A-Za-z]+)\s+(?:form|from)\s+([A-Za-z][A-Za-z0-9\s&.,Inc]+?)(?:\s*[,.]|$)',
            r'(?:i\'?m|my name is|i am)\s+([A-Za-z]+).*(?:company|work at)\s*:?\s*([A-Za-z][A-Za-z0-9\s&.,Inc]+?)(?:\s*[,.]|$)',
        ]
        
        for pattern in name_company_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                company = match.group(2).strip().rstrip('.,')
                entities['name'] = name
                entities['company'] = company
                break
        
        # Separate name extraction
        if 'name' not in entities:
            name_patterns = [
                r'(?:i\'?m|my name is|i am)\s+([A-Za-z]+)',
                r'hello.*i\'?m\s+([A-Za-z]+)',
            ]
            
            for pattern in name_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    entities['name'] = match.group(1).strip()
                    break
        
        # Separate company extraction
        if 'company' not in entities:
            company_patterns = [
                r'(?:company|corp|corporation|inc|llc)(?:\s+name)?\s*:?\s*([A-Za-z][A-Za-z0-9\s&.,Inc]+?)(?:\s*[,.]|$)',
                r'(?:from|at|with)\s+([A-Za-z][A-Za-z0-9\s&.,Inc]*(?:corp|inc|llc|corporation))(?:\s*[,.]|$)',
            ]
            
            for pattern in company_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    company = match.group(1).strip().rstrip('.,')
                    if len(company) > 2:
                        entities['company'] = company
                    break
        
        # Budget patterns
        budget_patterns = [
            r'budget(?:\s+(?:is|of))?\s*:?\s*\$?([0-9,]+k?)\b',
            r'\$([0-9,]+k?)\b',
            r'([0-9,]+k?)\s*(?:budget|dollars|USD)',
        ]
        
        for pattern in budget_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                budget_value = match.group(1).strip()
                if 'k' not in budget_value.lower() and len(budget_value) >= 4:
                    budget_value = budget_value + '0' if len(budget_value) == 4 else budget_value
                entities['budget'] = f"${budget_value}"
                break
        
        # Project type extraction
        if any(word in text_lower for word in ['proposal', 'need', 'require', 'want', 'generate']):
            # Extract what they need
            project_patterns = [
                r'(?:proposal|need|require|want|generate).*?for\s+(?:a|an)?\s*([A-Za-z][A-Za-z0-9\s\-]+?)(?:\s+with|\s+and|$)',
                r'(?:cloud|ai|infrastructure|system|platform)\s+([A-Za-z][A-Za-z0-9\s\-]*)',
            ]
            
            for pattern in project_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    project_type = match.group(1).strip()
                    if len(project_type) > 2:
                        entities['project'] = project_type
                    break
        
        return entities
    
    def update_user_context(self, user_id: str, message: str):
        """Update user context - REQUIRED METHOD"""
        entities = self.extract_entities(message)
        
        with sqlite3.connect(self.db_path) as conn:
            # Store conversation
            conn.execute(
                "INSERT INTO conversations (user_id, message) VALUES (?, ?)",
                (user_id, message)
            )
            
            # Update memories with extracted entities
            for key, value in entities.items():
                conn.execute(
                    "INSERT OR REPLACE INTO memories (user_id, key, value) VALUES (?, ?, ?)",
                    (user_id, key, value)
                )
            
            conn.commit()
    
    def store_conversation(self, user_id: str, message: str, response: str):
        """Store conversation using EXISTING schema and update memories"""
        # This method calls update_user_context internally
        self.update_user_context(user_id, message)
    
    def get_conversation_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get conversation history using EXISTING schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT message, timestamp FROM conversations WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
                (user_id, limit)
            )
            
            rows = cursor.fetchall()
            
            history = []
            for row in reversed(rows):  # Reverse to get chronological order
                history.append({
                    'message': row[0],
                    'response': '',  # We don't store responses in the existing schema
                    'timestamp': row[1]
                })
        
        return history
    
    def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get user context from memories table"""
        memories = {}
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT key, value FROM memories WHERE user_id = ?",
                (user_id,)
            )
            
            for key, value in cursor.fetchall():
                memories[key] = value
        
        return memories
    
    def build_context_summary(self, user_id: str) -> str:
        """Build a context summary for the user"""
        context = self.get_user_context(user_id)
        history = self.get_conversation_history(user_id)
        
        if not context and not history:
            return "No context available yet."
        
        summary_parts = ["📋 **Context Summary:**"]
        
        if context.get('name'):
            summary_parts.append(f"- **Contact:** {context['name']}")
        
        if context.get('company'):
            summary_parts.append(f"- **Company:** {context['company']}")
        
        if context.get('budget'):
            summary_parts.append(f"- **Budget:** {context['budget']}")
        
        if context.get('project'):
            summary_parts.append(f"- **Project Type:** {context['project']}")
        
        if history:
            summary_parts.append(f"- **Conversation:** {len(history)} messages")
        
        return "\n".join(summary_parts)
    
    def format_memory_summary(self, user_id: str) -> str:
        """Format memory summary for display - EXISTING method"""
        memories = self.get_user_context(user_id)
        
        if not memories:
            return "No project information stored yet."
        
        summary_parts = []
        for key, value in memories.items():
            formatted_key = key.replace('_', ' ').title()
            summary_parts.append(f"**{formatted_key}**: {value}")
        
        return "\n".join(summary_parts)