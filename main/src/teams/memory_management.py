"""
Memory Manager for Teams RFP Bot - Handles conversation context and entity extraction
"""
import sqlite3
import json
import re
from typing import Dict, Any, List, Optional
from pathlib import Path
import datetime

class TeamsMemoryManager:
    """Manages conversation memory and entity extraction for Teams bot"""
    
    def __init__(self, db_path: str = "src/teams/data/memory.db"):
        self.db_path = db_path
        self._ensure_db_exists()
        self._init_db()
    
    def _ensure_db_exists(self):
        """Ensure the database directory and file exist"""
        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _init_db(self):
        """Initialize the database tables"""
        with sqlite3.connect(self.db_path) as conn:
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
        
        # Client company patterns - more comprehensive
        client_patterns = [
            r'client(?:\s+(?:is|company))?\s*:?\s*([A-Za-z][A-Za-z0-9\s&.,Inc]+?)(?:\s*[,.]|$)',
            r'(?:company|client|organization)(?:\s+name)?\s*:?\s*([A-Za-z][A-Za-z0-9\s&.,Inc]+?)(?:\s*[,.]|$)',
            r'for\s+([A-Za-z][A-Za-z0-9\s&.,Inc]+?)(?:\s*[,.]|$)',
            r'remember:.*?client.*?is\s+([A-Za-z][A-Za-z0-9\s&.,Inc]+?)(?:\s*[,.]|$)',
        ]
        
        for pattern in client_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                client_name = match.group(1).strip()
                # Clean up the client name
                client_name = re.sub(r'\s+', ' ', client_name)  # Remove extra spaces
                client_name = re.sub(r'[,.]$', '', client_name)  # Remove trailing punctuation
                if len(client_name) > 2 and not client_name.lower() in ['is', 'the', 'a', 'an']:
                    entities['client_company'] = client_name
                    break
        
        # Budget patterns - more comprehensive
        budget_patterns = [
            r'budget(?:\s+(?:is|of))?\s*:?\s*\$?([0-9,]+k?)\b',
            r'\$([0-9,]+k?)\b',
            r'([0-9,]+k?)\s*(?:budget|dollars|USD)',
            r'remember:.*?budget.*?is\s*\$?([0-9,]+k?)\b',
        ]
        
        for pattern in budget_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                budget_value = match.group(1).strip()
                # Normalize budget format
                if 'k' not in budget_value.lower() and len(budget_value) <= 3:
                    budget_value += 'k'
                if not budget_value.startswith('$'):
                    budget_value = f"${budget_value}"
                entities['budget_range'] = budget_value
                break
        
        # Project type patterns - more comprehensive
        project_patterns = [
            r'project(?:\s+(?:is|type))?\s*:?\s*([A-Za-z][A-Za-z0-9\s\-]+?)(?:\s+system|$)',
            r'(?:build|develop|create)\s+(?:an?\s+)?([A-Za-z][A-Za-z0-9\s\-]+?)(?:\s+system|$)',
            r'remember:.*?project.*?is\s+([A-Za-z][A-Za-z0-9\s\-]+?)(?:\s+system|$)',
        ]
        
        for pattern in project_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                project_name = match.group(1).strip()
                project_name = re.sub(r'\s+', ' ', project_name)
                if len(project_name) > 2:
                    if not project_name.endswith('system'):
                        project_name += " system"
                    entities['project_type'] = project_name
                    break
        
        # Timeline patterns
        timeline_patterns = [
            r'(?:timeline|deadline|due)\s*:?\s*([0-9]+\s*(?:weeks?|months?|days?))',
            r'in\s+([0-9]+\s*(?:weeks?|months?|days?))',
        ]
        
        for pattern in timeline_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                entities['timeline'] = match.group(1).strip()
                break
        
        return entities
    
    def update_memory(self, user_id: str, text: str) -> Dict[str, Any]:
        """Update user memory with extracted entities"""
        entities = self.extract_entities(text)
        
        with sqlite3.connect(self.db_path) as conn:
            # Store conversation
            conn.execute(
                "INSERT INTO conversations (user_id, message) VALUES (?, ?)",
                (user_id, text)
            )
            
            # Update memories
            for key, value in entities.items():
                conn.execute(
                    "INSERT OR REPLACE INTO memories (user_id, key, value) VALUES (?, ?, ?)",
                    (user_id, key, value)
                )
            
            conn.commit()
        
        return entities
    
    def get_memories(self, user_id: str) -> Dict[str, Any]:
        """Get all memories for a user"""
        memories = {}
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT key, value FROM memories WHERE user_id = ?",
                (user_id,)
            )
            
            for key, value in cursor.fetchall():
                memories[key] = value
        
        return memories
    
    def get_conversation_history(self, user_id: str, limit: int = 10) -> List[str]:
        """Get recent conversation history for a user"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT message FROM conversations WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
                (user_id, limit)
            )
            
            return [row[0] for row in cursor.fetchall()]
    
    def clear_memory(self, user_id: str) -> bool:
        """Clear all memory for a user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM memories WHERE user_id = ?", (user_id,))
                conn.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
                conn.commit()
            return True
        except Exception:
            return False
    
    def format_memory_summary(self, user_id: str) -> str:
        """Format memory summary for display"""
        memories = self.get_memories(user_id)
        
        if not memories:
            return "No project information stored yet."
        
        summary_parts = []
        for key, value in memories.items():
            formatted_key = key.replace('_', ' ').title()
            summary_parts.append(f"**{formatted_key}**: {value}")
        
        return "\n".join(summary_parts)