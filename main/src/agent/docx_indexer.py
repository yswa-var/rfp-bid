"""DOCX Indexer for creating structured navigation and anchor mapping."""

import json
import re
from typing import Any, Dict, List, Optional
from pathlib import Path
from docx2python import docx2python
from dataclasses import dataclass, asdict


@dataclass
class Paragraph:
    """Represents a paragraph with its location and metadata."""
    anchor: List[Any]  # [table, row, col, par]
    breadcrumb: str
    style: str
    text: str
    level: int = 0  # Heading level (0 for normal, 1-6 for headings)


class DocxIndexer:
    """Index a DOCX file for easy navigation and manipulation."""
    
    def __init__(self, docx_path: str):
        """Initialize indexer with a DOCX file path."""
        self.docx_path = Path(docx_path)
        self.paragraphs: List[Paragraph] = []
        self.heading_stack: List[Dict[str, Any]] = []
        self.docx_obj = None
        
    def _detect_heading_level(self, text: str) -> Optional[int]:
        """Detect if text is a heading and return its level."""
        # Common heading patterns
        if not text or not text.strip():
            return None
            
        text = text.strip()
        
        # Pattern 1: Numbered headings like "1.", "1.1.", "2.3.4."
        if re.match(r'^\d+(\.\d+)*\.?\s+', text):
            dots = text.split()[0].count('.')
            return min(dots + 1, 6)
        
        # Pattern 2: All caps (likely a main heading)
        if text.isupper() and len(text.split()) <= 10:
            return 1
            
        # Pattern 3: Known heading keywords
        heading_keywords = ['table of contents', 'summary', 'introduction', 'conclusion']
        if any(keyword in text.lower() for keyword in heading_keywords):
            return 2
            
        return None
    
    def _build_breadcrumb(self, text: str, level: int) -> str:
        """Build a breadcrumb trail based on heading hierarchy."""
        # Update heading stack
        # Remove headings at same or deeper level
        self.heading_stack = [h for h in self.heading_stack if h['level'] < level]
        
        # Add current heading
        if level > 0:
            self.heading_stack.append({'level': level, 'text': text[:50]})
        
        # Build breadcrumb
        if not self.heading_stack:
            return "Document Root"
        
        return " > ".join([h['text'] for h in self.heading_stack])
    
    def index(self) -> List[Dict[str, Any]]:
        """Index the DOCX file and return structured paragraph data."""
        self.paragraphs = []
        self.heading_stack = []
        
        with docx2python(str(self.docx_path)) as docx:
            self.docx_obj = docx
            pars = docx.body
            
            # Iterate through depth-4: [table][row][column][paragraph]
            for table_idx, table in enumerate(pars):
                for row_idx, row in enumerate(table):
                    for col_idx, col in enumerate(row):
                        for par_idx, par in enumerate(col):
                            text = par.strip() if isinstance(par, str) else str(par).strip()
                            
                            if not text or text == '\n':
                                continue
                            
                            # Create anchor
                            anchor = ["body", table_idx, row_idx, col_idx, par_idx]
                            
                            # Detect heading level
                            level = self._detect_heading_level(text) or 0
                            
                            # Determine style
                            if level == 1:
                                style = "Heading 1"
                            elif level == 2:
                                style = "Heading 2"
                            elif level > 2:
                                style = f"Heading {level}"
                            else:
                                style = "Normal"
                            
                            # Build breadcrumb
                            breadcrumb = self._build_breadcrumb(text, level)
                            
                            # Create paragraph object
                            paragraph = Paragraph(
                                anchor=anchor,
                                breadcrumb=breadcrumb,
                                style=style,
                                text=text,
                                level=level
                            )
                            
                            self.paragraphs.append(paragraph)
        
        return [asdict(p) for p in self.paragraphs]
    
    def get_outline(self) -> List[Dict[str, Any]]:
        """Get document outline (headings only)."""
        return [asdict(p) for p in self.paragraphs if p.level > 0]
    
    def find_by_anchor(self, anchor: List[Any]) -> Optional[Dict[str, Any]]:
        """Find a paragraph by its anchor."""
        for p in self.paragraphs:
            if p.anchor == anchor:
                return asdict(p)
        return None
    
    def find_by_text(self, search_text: str, case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """Find paragraphs containing specific text."""
        results = []
        for p in self.paragraphs:
            text = p.text if case_sensitive else p.text.lower()
            search = search_text if case_sensitive else search_text.lower()
            if search in text:
                results.append(asdict(p))
        return results
    
    def save_index(self, output_path: str) -> None:
        """Save the index to a JSON file."""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump([asdict(p) for p in self.paragraphs], f, indent=2, ensure_ascii=False)


def main():
    """Example usage of the indexer."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python docx_indexer.py <docx_path> [output_json]")
        sys.exit(1)
    
    docx_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "index.json"
    
    indexer = DocxIndexer(docx_path)
    paragraphs = indexer.index()
    
    print(f"Indexed {len(paragraphs)} paragraphs")
    print(f"\nFirst 5 paragraphs:")
    for p in paragraphs[:5]:
        print(f"\nAnchor: {p['anchor']}")
        print(f"Breadcrumb: {p['breadcrumb']}")
        print(f"Style: {p['style']}")
        print(f"Text: {p['text'][:80]}...")
    
    # Save index
    indexer.save_index(output_path)
    print(f"\nIndex saved to: {output_path}")
    
    # Show outline
    outline = indexer.get_outline()
    print(f"\nDocument Outline ({len(outline)} headings):")
    for heading in outline[:10]:
        indent = "  " * (heading['level'] - 1)
        print(f"{indent}- {heading['text'][:60]}")


if __name__ == "__main__":
    main()
