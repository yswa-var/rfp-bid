"""DOCX Manager for reading and updating DOCX documents."""

import asyncio
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
from docx2python import docx2python
from docx import Document
from react_agent.docx_indexer import DocxIndexer


class DocxManager:
    """Manage DOCX documents with read and update capabilities."""
    
    def __init__(self, docx_path: str):
        """Initialize manager with a DOCX file path."""
        self.docx_path = Path(docx_path)
        self.indexer = DocxIndexer(str(self.docx_path))
        self.index_data: List[Dict[str, Any]] = []
        self._index_loaded = False
    
    def _refresh_index(self) -> None:
        """Refresh the internal index."""
        self.index_data = self.indexer.index()
        self._index_loaded = True
    
    async def _ensure_index_loaded(self) -> None:
        """Ensure the index is loaded, loading it asynchronously if needed."""
        if not self._index_loaded:
            self.index_data = await asyncio.to_thread(self.indexer.index)
            self._index_loaded = True
    
    def get_paragraph(self, anchor: List[Any]) -> Optional[Dict[str, Any]]:
        """Get a paragraph by its anchor.
        
        Args:
            anchor: List representing [body, table, row, col, par] position
            
        Returns:
            Dictionary with paragraph info or None if not found
        """
        # Note: This method assumes the index is already loaded
        # The async wrapper in tools.py will call _ensure_index_loaded first
        for p in self.index_data:
            if p['anchor'] == anchor:
                return p
        return None
    
    def get_outline(self) -> List[Dict[str, Any]]:
        """Get document outline (headings only).
        
        Returns:
            List of heading paragraphs with metadata
        """
        return self.indexer.get_outline()
    
    def search(self, query: str, case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """Search for paragraphs containing text.
        
        Args:
            query: Text to search for
            case_sensitive: Whether to match case
            
        Returns:
            List of matching paragraphs
        """
        return self.indexer.find_by_text(query, case_sensitive)
    
    def update_paragraph(self, anchor: List[Any], new_text: str) -> bool:
        """Update a paragraph at the given anchor.
        
        Args:
            anchor: List representing [body, table, row, col, par] position
            new_text: New text content for the paragraph
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load the document with python-docx for editing
            doc = Document(str(self.docx_path))
            
            # Extract the position from anchor
            if len(anchor) < 5 or anchor[0] != "body":
                return False
            
            _, table_idx, row_idx, col_idx, par_idx = anchor
            
            # For simplicity, we'll update based on paragraph index
            # Note: This is a simplified approach. In production, you'd want
            # more sophisticated mapping between docx2python and python-docx structures
            
            # Try to find the paragraph by matching text
            old_para = self.get_paragraph(anchor)
            if not old_para:
                return False
            
            old_text = old_para['text']
            
            # Search for the paragraph in the document
            for paragraph in doc.paragraphs:
                if paragraph.text.strip() == old_text:
                    # Update the paragraph
                    paragraph.text = new_text
                    
                    # Save the document
                    doc.save(str(self.docx_path))
                    
                    # Refresh index
                    self._refresh_index()
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error updating paragraph: {e}")
            return False
    
    def get_all_paragraphs(self) -> List[Dict[str, Any]]:
        """Get all paragraphs with metadata.
        
        Returns:
            List of all paragraphs
        """
        return self.index_data.copy()
    
    def export_index(self, output_path: str) -> None:
        """Export the index to a JSON file.
        
        Args:
            output_path: Path to save the JSON file
        """
        self.indexer.save_index(output_path)


# Global instance (will be initialized when needed)
_docx_manager: Optional[DocxManager] = None


def get_docx_manager(docx_path: Optional[str] = None) -> DocxManager:
    """Get or create the global DOCX manager instance."""
    global _docx_manager
    
    if _docx_manager is None:
        if docx_path is None:
            # Default path - you can make this configurable
            docx_path = "/Users/yash/Documents/rfp/rfp-bid/master.docx"
        _docx_manager = DocxManager(docx_path)
    
    return _docx_manager


def reset_docx_manager() -> None:
    """Reset the global DOCX manager instance."""
    global _docx_manager
    _docx_manager = None
