"""
Thread Manager for mapping Teams conversations to LangGraph threads
"""
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class ThreadManager:
    """Manages mapping between Teams conversation IDs and LangGraph thread IDs"""
    
    def __init__(self, storage_file: str = "thread_mappings.json"):
        self.storage_file = Path(storage_file)
        self.mappings: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self._load_mappings()
    
    def _load_mappings(self):
        """Load thread mappings from storage file"""
        if self.storage_file.exists():
            try:
                with open(self.storage_file, 'r') as f:
                    self.mappings = json.load(f)
                logger.info(f"Loaded {len(self.mappings)} thread mappings from {self.storage_file}")
            except Exception as e:
                logger.error(f"Error loading thread mappings: {e}")
                self.mappings = {}
        else:
            logger.info(f"No existing thread mappings found, starting fresh")
            self.mappings = {}
    
    async def _save_mappings(self):
        """Save thread mappings to storage file"""
        async with self._lock:
            try:
                with open(self.storage_file, 'w') as f:
                    json.dump(self.mappings, f, indent=2)
                logger.debug(f"Saved {len(self.mappings)} thread mappings")
            except Exception as e:
                logger.error(f"Error saving thread mappings: {e}")
    
    async def get_thread_id(self, conversation_id: str) -> Optional[str]:
        """Get LangGraph thread ID for a Teams conversation"""
        mapping = self.mappings.get(conversation_id)
        if mapping:
            logger.debug(f"Found existing thread {mapping['thread_id']} for conversation {conversation_id}")
            return mapping['thread_id']
        return None
    
    async def create_mapping(
        self, 
        conversation_id: str, 
        thread_id: str,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Create a new mapping between Teams conversation and LangGraph thread"""
        mapping = {
            "thread_id": thread_id,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "user_name": user_name,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        self.mappings[conversation_id] = mapping
        await self._save_mappings()
        
        logger.info(f"Created thread mapping: conversation={conversation_id} → thread={thread_id}")
        return mapping
    
    async def update_activity(self, conversation_id: str):
        """Update last activity timestamp for a conversation"""
        if conversation_id in self.mappings:
            self.mappings[conversation_id]["last_activity"] = datetime.utcnow().isoformat()
            await self._save_mappings()
    
    async def get_mapping(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get full mapping data for a conversation"""
        return self.mappings.get(conversation_id)
    
    async def delete_mapping(self, conversation_id: str) -> bool:
        """Delete a thread mapping"""
        if conversation_id in self.mappings:
            del self.mappings[conversation_id]
            await self._save_mappings()
            logger.info(f"Deleted thread mapping for conversation {conversation_id}")
            return True
        return False
    
    async def get_all_mappings(self) -> Dict[str, Dict[str, Any]]:
        """Get all thread mappings"""
        return self.mappings.copy()
    
    async def cleanup_old_mappings(self, days: int = 30):
        """Remove mappings older than specified days"""
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        to_remove = []
        for conv_id, mapping in self.mappings.items():
            last_activity = datetime.fromisoformat(mapping["last_activity"])
            if last_activity < cutoff:
                to_remove.append(conv_id)
        
        for conv_id in to_remove:
            del self.mappings[conv_id]
        
        if to_remove:
            await self._save_mappings()
            logger.info(f"Cleaned up {len(to_remove)} old thread mappings")
        
        return len(to_remove)

