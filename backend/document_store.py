"""
Simple in-memory document store for MVP
Tracks documents, versions, and approval state
"""

import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import shutil


@dataclass
class ApprovalLink:
    """Minimal approval tracking"""
    interrupt_id: str
    decision: Optional[str] = None  # 'approved' | 'rejected' | None
    decided_at: Optional[float] = None


@dataclass
class DocVersion:
    """Document version record"""
    version: int
    created_at: float
    source_path: str
    note: Optional[str] = None
    approval: Optional[ApprovalLink] = None


@dataclass
class DocumentRecord:
    """Document metadata"""
    id: str
    name: str
    latest_version: int
    created_at: float
    updated_at: float
    versions: List[DocVersion]


class DocumentStore:
    """In-memory document store with filesystem persistence"""
    
    def __init__(self, storage_dir: str = "storage/docs"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.documents: Dict[str, DocumentRecord] = {}
        self._next_id = 1
    
    def create_document(self, filename: str, file_path: str, note: Optional[str] = None) -> DocumentRecord:
        """Create a new document with initial version"""
        doc_id = str(self._next_id)
        self._next_id += 1
        
        # Copy file to storage
        dest_path = self.storage_dir / f"{doc_id}_v1_{filename}"
        shutil.copy2(file_path, dest_path)
        
        now = time.time()
        version = DocVersion(
            version=1,
            created_at=now,
            source_path=str(dest_path),
            note=note
        )
        
        doc = DocumentRecord(
            id=doc_id,
            name=filename,
            latest_version=1,
            created_at=now,
            updated_at=now,
            versions=[version]
        )
        
        self.documents[doc_id] = doc
        return doc
    
    def add_version(self, doc_id: str, file_path: str, note: Optional[str] = None, 
                   interrupt_id: Optional[str] = None) -> Optional[DocVersion]:
        """Add a new version to an existing document"""
        doc = self.documents.get(doc_id)
        if not doc:
            return None
        
        new_version = doc.latest_version + 1
        filename = doc.name
        
        # Copy file to storage
        dest_path = self.storage_dir / f"{doc_id}_v{new_version}_{filename}"
        shutil.copy2(file_path, dest_path)
        
        now = time.time()
        approval_link = ApprovalLink(interrupt_id=interrupt_id) if interrupt_id else None
        
        version = DocVersion(
            version=new_version,
            created_at=now,
            source_path=str(dest_path),
            note=note,
            approval=approval_link
        )
        
        doc.versions.append(version)
        doc.latest_version = new_version
        doc.updated_at = now
        
        return version
    
    def get_document(self, doc_id: str) -> Optional[DocumentRecord]:
        """Get document metadata"""
        return self.documents.get(doc_id)
    
    def list_documents(self) -> List[DocumentRecord]:
        """List all documents"""
        return list(self.documents.values())
    
    def get_version(self, doc_id: str, version: int) -> Optional[DocVersion]:
        """Get a specific version"""
        doc = self.documents.get(doc_id)
        if not doc:
            return None
        
        for v in doc.versions:
            if v.version == version:
                return v
        return None
    
    def get_latest_version(self, doc_id: str) -> Optional[DocVersion]:
        """Get the latest version"""
        doc = self.documents.get(doc_id)
        if not doc or not doc.versions:
            return None
        return doc.versions[-1]
    
    def update_approval_decision(self, doc_id: str, interrupt_id: str, decision: str) -> bool:
        """Update approval decision for a version with matching interrupt_id"""
        doc = self.documents.get(doc_id)
        if not doc:
            return False
        
        for version in doc.versions:
            if version.approval and version.approval.interrupt_id == interrupt_id:
                version.approval.decision = decision
                version.approval.decided_at = time.time()
                return True
        
        return False


# Global instance
document_store = DocumentStore()
