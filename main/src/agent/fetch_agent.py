#!/usr/bin/env python3
"""
Fetch Agent - Website browsing and PDF processing with PyMuPDF
Handles multi-column layouts, tables, and comprehensive error logging.
"""

import os
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
import tempfile
import time

import fitz  # PyMuPDF
import requests
from bs4 import BeautifulSoup
import aiohttp
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fetch_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class FetchResult:
    """Result from fetch operation."""
    success: bool
    documents: List[Document]
    error: Optional[str] = None
    metadata: Dict[str, Any] = None
    processing_time: float = 0.0

@dataclass
class ParseConfig:
    """Configuration for PDF parsing."""
    chunk_size: int = 1000
    chunk_overlap: int = 200
    extract_tables: bool = True
    extract_images: bool = False
    handle_multi_column: bool = True
    ocr_fallback: bool = True

class FetchAgent:
    """
    Comprehensive fetch agent for RFP documents.
    Handles website browsing, PDF download, and advanced parsing.
    """
    
    def __init__(self, config: Optional[ParseConfig] = None):
        self.config = config or ParseConfig()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            add_start_index=True,
            separators=["\n\n", "\n", " ", ""]
        )
    
    async def fetch_from_url(self, url: str) -> FetchResult:
        """
        Main entry point for fetching documents from a URL.
        Automatically determines if it's a direct PDF or webpage with PDFs.
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting fetch operation for URL: {url}")
            
            # Check if URL points directly to a PDF
            if url.lower().endswith('.pdf'):
                result = await self._download_and_parse_pdf(url)
            else:
                result = await self._browse_and_extract_pdfs(url)
            
            result.processing_time = time.time() - start_time
            logger.info(f"Fetch operation completed in {result.processing_time:.2f}s")
            
            return result
            
        except Exception as e:
            error_msg = f"Failed to fetch from URL {url}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return FetchResult(
                success=False,
                documents=[],
                error=error_msg,
                processing_time=time.time() - start_time
            )
    
    async def _browse_and_extract_pdfs(self, url: str) -> FetchResult:
        """Browse webpage and extract PDF links."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise Exception(f"HTTP {response.status}: Failed to access {url}")
                    
                    content = await response.text()
                    
            # Parse HTML and find PDF links
            soup = BeautifulSoup(content, 'html.parser')
            pdf_links = []
            
            # Find direct PDF links
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.lower().endswith('.pdf'):
                    full_url = urljoin(url, href)
                    pdf_links.append(full_url)
                    logger.info(f"Found PDF link: {full_url}")
            
            if not pdf_links:
                logger.warning(f"No PDF links found on {url}")
                return FetchResult(
                    success=False,
                    documents=[],
                    error="No PDF documents found on the webpage"
                )
            
            # Download and parse all PDFs
            all_documents = []
            errors = []
            
            for pdf_url in pdf_links:
                try:
                    result = await self._download_and_parse_pdf(pdf_url)
                    if result.success:
                        all_documents.extend(result.documents)
                    else:
                        errors.append(f"Failed to process {pdf_url}: {result.error}")
                except Exception as e:
                    errors.append(f"Error processing {pdf_url}: {str(e)}")
                    logger.error(f"Error processing PDF {pdf_url}", exc_info=True)
            
            return FetchResult(
                success=len(all_documents) > 0,
                documents=all_documents,
                error="; ".join(errors) if errors else None,
                metadata={
                    "source_url": url,
                    "pdf_links_found": len(pdf_links),
                    "pdfs_processed": len(all_documents)
                }
            )
            
        except Exception as e:
            error_msg = f"Failed to browse and extract PDFs from {url}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return FetchResult(
                success=False,
                documents=[],
                error=error_msg
            )
    
    async def _download_and_parse_pdf(self, pdf_url: str) -> FetchResult:
        """Download and parse a single PDF."""
        temp_file = None
        try:
            logger.info(f"Downloading PDF from: {pdf_url}")
            
            # Download PDF
            response = self.session.get(pdf_url, stream=True)
            response.raise_for_status()
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                temp_file = f.name
            
            logger.info(f"PDF downloaded to temporary file: {temp_file}")
            
            # Parse PDF using PyMuPDF
            documents = self._parse_pdf_with_pymupdf(temp_file, pdf_url)
            
            return FetchResult(
                success=True,
                documents=documents,
                metadata={
                    "source_url": pdf_url,
                    "file_size": os.path.getsize(temp_file),
                    "num_documents": len(documents)
                }
            )
            
        except Exception as e:
            error_msg = f"Failed to download/parse PDF {pdf_url}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return FetchResult(
                success=False,
                documents=[],
                error=error_msg
            )
        finally:
            # Clean up temporary file
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except Exception as e:
                    logger.warning(f"Failed to clean up temp file {temp_file}: {e}")
    
    def _parse_pdf_with_pymupdf(self, file_path: str, source_url: str) -> List[Document]:
        """
        Parse PDF using PyMuPDF with advanced features:
        - Multi-column detection
        - Table extraction
        - Improved text layout recognition
        """
        documents = []
        
        try:
            # Open PDF
            pdf_doc = fitz.open(file_path)
            logger.info(f"Opened PDF with {len(pdf_doc)} pages")
            
            for page_num in range(len(pdf_doc)):
                page = pdf_doc[page_num]
                
                try:
                    # Extract text with layout preservation
                    if self.config.handle_multi_column:
                        text = self._extract_text_with_layout(page)
                    else:
                        text = page.get_text()
                    
                    # Extract tables if configured
                    tables_text = ""
                    if self.config.extract_tables:
                        tables_text = self._extract_tables_from_page(page)
                    
                    # Combine text and tables
                    full_text = text
                    if tables_text:
                        full_text += f"\n\n--- Tables ---\n{tables_text}"
                    
                    if full_text.strip():
                        # Get page metadata
                        metadata = {
                            "source": source_url,
                            "page": page_num + 1,
                            "page_label": str(page_num + 1),
                            "total_pages": len(pdf_doc),
                            "extraction_method": "pymupdf",
                            "has_tables": bool(tables_text)
                        }
                        
                        # Split into chunks
                        chunks = self.text_splitter.split_text(full_text)
                        
                        for i, chunk in enumerate(chunks):
                            chunk_metadata = metadata.copy()
                            chunk_metadata.update({
                                "chunk_id": f"{page_num + 1}_{i}",
                                "chunk_index": i,
                                "total_chunks": len(chunks)
                            })
                            
                            documents.append(Document(
                                page_content=chunk,
                                metadata=chunk_metadata
                            ))
                
                except Exception as e:
                    logger.error(f"Error processing page {page_num + 1}: {e}")
                    continue
            
            pdf_doc.close()
            logger.info(f"Successfully parsed PDF into {len(documents)} document chunks")
            
        except Exception as e:
            logger.error(f"Failed to parse PDF {file_path}: {e}", exc_info=True)
            
        return documents
    
    def _extract_text_with_layout(self, page) -> str:
        """
        Extract text with improved layout detection for multi-column documents.
        """
        try:
            # Get text blocks with position information
            blocks = page.get_text("dict")
            
            # Sort blocks by position (top to bottom, left to right for multi-column)
            text_blocks = []
            for block in blocks.get("blocks", []):
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line.get("spans", []):
                            text = span.get("text", "").strip()
                            if text:
                                bbox = span.get("bbox", [0, 0, 0, 0])
                                text_blocks.append({
                                    "text": text,
                                    "x0": bbox[0],
                                    "y0": bbox[1],
                                    "x1": bbox[2],
                                    "y1": bbox[3]
                                })
            
            # Sort by Y position first (top to bottom), then X position (left to right)
            text_blocks.sort(key=lambda x: (x["y0"], x["x0"]))
            
            # Group into lines and columns
            lines = []
            current_line = []
            current_y = None
            
            for block in text_blocks:
                if current_y is None or abs(block["y0"] - current_y) < 5:  # Same line
                    current_line.append(block)
                    current_y = block["y0"]
                else:  # New line
                    if current_line:
                        # Sort current line by X position
                        current_line.sort(key=lambda x: x["x0"])
                        lines.append(" ".join([b["text"] for b in current_line]))
                    current_line = [block]
                    current_y = block["y0"]
            
            # Add last line
            if current_line:
                current_line.sort(key=lambda x: x["x0"])
                lines.append(" ".join([b["text"] for b in current_line]))
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.warning(f"Layout extraction failed, falling back to simple text: {e}")
            return page.get_text()
    
    def _extract_tables_from_page(self, page) -> str:
        """
        Extract tables from a page using PyMuPDF.
        """
        try:
            tables = page.find_tables()
            tables_text = []
            
            for table in tables:
                try:
                    # Extract table data
                    table_data = table.extract()
                    if table_data:
                        # Format as simple text table
                        formatted_table = []
                        for row in table_data:
                            # Clean and join cells
                            clean_row = [str(cell).strip() if cell else "" for cell in row]
                            formatted_table.append(" | ".join(clean_row))
                        
                        if formatted_table:
                            tables_text.append("\n".join(formatted_table))
                            
                except Exception as e:
                    logger.warning(f"Failed to extract table: {e}")
                    continue
            
            return "\n\n".join(tables_text)
            
        except Exception as e:
            logger.warning(f"Table extraction failed: {e}")
            return ""

# Example usage and testing
async def main():
    """Test the fetch agent."""
    agent = FetchAgent()
    
    # Test with different URLs
    test_urls = [
        "https://example.com/sample.pdf",  # Direct PDF
        "https://example.com/rfp-page",    # Webpage with PDFs
    ]
    
    for url in test_urls:
        print(f"\n🔍 Testing URL: {url}")
        result = await agent.fetch_from_url(url)
        
        print(f"✅ Success: {result.success}")
        print(f"📄 Documents: {len(result.documents)}")
        print(f"⏱️ Time: {result.processing_time:.2f}s")
        
        if result.error:
            print(f"❌ Error: {result.error}")
        
        if result.metadata:
            print(f"📊 Metadata: {result.metadata}")

if __name__ == "__main__":
    asyncio.run(main())
