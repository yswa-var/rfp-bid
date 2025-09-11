"""
Milvus Database Operations Helper Functions

This module provides helper functions for:
- PDF parsing using PyMuPDF
- Text chunking and vectorization
- Milvus database operations
- Querying with similarity search
"""

import os
import re
import fitz  # PyMuPDF
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_milvus import Milvus

# Load environment variables
load_dotenv()


class MilvusOps:
    """Helper class for Milvus database operations and PDF processing."""
    
    def __init__(self, db_name: str = "session.db"):
        """
        Initialize MilvusOps with database name.
        
        Args:
            db_name: Name of the Milvus database file
        """
        self.db_name = db_name
        # Use absolute path to ensure consistent database location
        self.db_path = os.path.abspath(db_name)
        self.embeddings = None
        self.vector_store = None
        self._initialize_embeddings()
    
    def _initialize_embeddings(self):
        """Initialize OpenAI embeddings."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is required. "
                "Please set it in your .env file or environment."
            )
        
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-large",
            api_key=api_key
        )
    
    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize text content for better chunking.
        
        Args:
            text: Raw text content
            
        Returns:
            Cleaned text content
        """
        if not text:
            return ""
        
        # Remove excessive whitespace and normalize line breaks
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Remove common PDF artifacts
        text = re.sub(r'^\s*Page \d+\s*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
        
        # Remove excessive punctuation
        text = re.sub(r'[.]{3,}', '...', text)
        text = re.sub(r'[-]{3,}', '---', text)
        
        # Clean up bullet points and numbering
        text = re.sub(r'^\s*[•·▪▫]\s*', '- ', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*\d+[.)]\s*', '', text, flags=re.MULTILINE)
        
        # Remove standalone single characters or very short lines
        text = re.sub(r'^\s*[A-Za-z]\s*$', '', text, flags=re.MULTILINE)
        
        # Remove lines that are just punctuation or symbols
        text = re.sub(r'^\s*[^\w\s]{2,}\s*$', '', text, flags=re.MULTILINE)
        
        # Normalize quotes and apostrophes
        text = re.sub(r'[""''`]', '"', text)
        text = re.sub(r'[''`]', "'", text)
        
        # Remove excessive spaces around punctuation
        text = re.sub(r'\s+([,.!?;:])', r'\1', text)
        text = re.sub(r'([,.!?;:])\s+', r'\1 ', text)
        
        # Final cleanup - remove multiple spaces and normalize
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    
    def _is_meaningful_content(self, text: str) -> bool:
        """
        Check if text contains meaningful content worth chunking.
        
        Args:
            text: Text content to evaluate
            
        Returns:
            True if content is meaningful, False otherwise
        """
        if not text or len(text.strip()) < 20:
            return False
        
        # Check for minimum word count
        words = text.split()
        if len(words) < 5:
            return False
        
        # Check for meaningful content patterns
        meaningful_patterns = [
            r'\b(?:the|and|or|but|in|on|at|to|for|of|with|by)\b',  # Common words
            r'\b(?:contract|agreement|proposal|requirement|service|project)\b',  # Business terms
            r'\b(?:shall|will|must|should|may|can|could|would)\b',  # Modal verbs
            r'\b\d{4}\b',  # Years
            r'\$\d+',  # Money amounts
            r'\b[A-Z]{2,}\b',  # Acronyms
        ]
        
        # Check if text contains at least one meaningful pattern
        for pattern in meaningful_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        # Check for sentence structure
        sentences = re.split(r'[.!?]+', text)
        meaningful_sentences = [s for s in sentences if len(s.strip().split()) >= 3]
        
        return len(meaningful_sentences) >= 1
    
    def parse_pdf(self, pdf_path: str) -> List[Document]:
        """
        Parse PDF file using PyMuPDF and extract text with metadata.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of Document objects with text content and metadata
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        documents = []
        
        try:
            # Open PDF with PyMuPDF
            pdf_document = fitz.open(pdf_path)
            
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                
                # Extract text
                text = page.get_text()
                
                # Clean the text
                cleaned_text = self._clean_text(text)
                
                # Only add pages with meaningful content
                if cleaned_text and self._is_meaningful_content(cleaned_text):
                    # Extract metadata
                    metadata = {
                        'source': pdf_path,
                        'page': page_num + 1,
                        'page_label': f"Page {page_num + 1}",
                        'file_path': pdf_path,
                        'total_pages': len(pdf_document),
                        'file_name': Path(pdf_path).name,
                        'file_size': os.path.getsize(pdf_path)
                    }
                    
                    # Get PDF metadata if available
                    pdf_metadata = pdf_document.metadata
                    if pdf_metadata:
                        metadata.update({
                            'title': pdf_metadata.get('title', ''),
                            'author': pdf_metadata.get('author', ''),
                            'creator': pdf_metadata.get('creator', ''),
                            'producer': pdf_metadata.get('producer', ''),
                            'creation_date': pdf_metadata.get('creationDate', ''),
                            'modification_date': pdf_metadata.get('modDate', '')
                        })
                    
                    # Create Document object with cleaned text
                    doc = Document(
                        page_content=cleaned_text,
                        metadata=metadata
                    )
                    documents.append(doc)
            
            pdf_document.close()
            print(f"Successfully parsed PDF: {pdf_path}")
            print(f"Extracted {len(documents)} pages")
            
        except Exception as e:
            raise Exception(f"Error parsing PDF {pdf_path}: {str(e)}")
        
        return documents
    
    def create_chunks(self, documents: List[Document], 
                     chunk_size: int = 1000, 
                     chunk_overlap: int = 200) -> List[Document]:
        """
        Split documents into chunks for better vectorization with intelligent filtering.
        
        Args:
            documents: List of Document objects
            chunk_size: Size of each chunk in characters
            chunk_overlap: Overlap between chunks in characters
            
        Returns:
            List of chunked Document objects
        """
        if not documents:
            raise ValueError("No documents provided for chunking")
        
        # Initialize text splitter with improved separators for RFP documents
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            add_start_index=True,
            separators=[
                "\n\n\n",  # Major section breaks
                "\n\n",    # Paragraph breaks
                "\n",      # Line breaks
                ". ",      # Sentence endings
                "! ",      # Exclamation endings
                "? ",      # Question endings
                "; ",      # Semicolon breaks
                ", ",      # Comma breaks
                " ",       # Word breaks
                ""         # Character breaks (last resort)
            ]
        )
        
        # Split documents
        raw_chunks = text_splitter.split_documents(documents)
        
        # Filter and clean chunks
        filtered_chunks = []
        for i, chunk in enumerate(raw_chunks):
            # Clean chunk content
            cleaned_content = self._clean_text(chunk.page_content)
            
            # Skip chunks that are too short or not meaningful
            if not self._is_meaningful_content(cleaned_content):
                continue
            
            # Skip chunks that are mostly metadata or headers
            if self._is_metadata_chunk(cleaned_content):
                continue
            
            # Update chunk with cleaned content
            chunk.page_content = cleaned_content
            
            # Clean and enhance metadata
            chunk.metadata = self._clean_metadata(chunk.metadata)
            chunk.metadata.update({
                'chunk_id': f"chunk_{i}",
                'chunk_length': len(cleaned_content),
                'word_count': len(cleaned_content.split()),
                'cleaned': True
            })
            
            filtered_chunks.append(chunk)
        
        print(f"Created {len(filtered_chunks)} high-quality chunks from {len(documents)} documents")
        print(f"Filtered out {len(raw_chunks) - len(filtered_chunks)} low-quality chunks")
        
        # Optional: Apply chunk summarization for quality improvement
        if len(filtered_chunks) > 0:
            try:
                filtered_chunks = self._apply_chunk_quality_improvement(filtered_chunks)
            except Exception as e:
                print(f"Warning: Chunk quality improvement failed: {e}")
                # Continue with original chunks if improvement fails
        
        return filtered_chunks
    
    def _apply_chunk_quality_improvement(self, chunks: List[Document]) -> List[Document]:
        """
        Apply quality improvement to chunks using the chunk summarizer.
        
        Args:
            chunks: List of document chunks
            
        Returns:
            List of improved chunks
        """
        try:
            # Import chunk summarizer
            from .chunk_summarizer import ChunkSummarizer
            
            # Create summarizer instance
            summarizer = ChunkSummarizer()
            
            # Apply quality improvement (synchronous version)
            improved_chunks = []
            for i, chunk in enumerate(chunks):
                try:
                    # Simple quality improvement - clean up formatting
                    improved_content = self._improve_chunk_formatting(chunk.page_content)
                    
                    # Create improved chunk
                    improved_chunk = Document(
                        page_content=improved_content,
                        metadata={
                            **chunk.metadata,
                            'quality_improved': True,
                            'improvement_timestamp': datetime.now().isoformat()
                        }
                    )
                    improved_chunks.append(improved_chunk)
                    
                except Exception as e:
                    print(f"Warning: Failed to improve chunk {i}: {e}")
                    improved_chunks.append(chunk)  # Use original chunk
            
            print(f"Applied quality improvement to {len(improved_chunks)} chunks")
            return improved_chunks
            
        except ImportError:
            print("Chunk summarizer not available, skipping quality improvement")
            return chunks
        except Exception as e:
            print(f"Chunk quality improvement failed: {e}")
            return chunks
    
    def _improve_chunk_formatting(self, content: str) -> str:
        """
        Improve chunk formatting for better readability.
        
        Args:
            content: Original chunk content
            
        Returns:
            Improved chunk content
        """
        if not content:
            return content
        
        # Fix common formatting issues
        improved = content
        
        # Fix bullet points
        improved = re.sub(r'^\s*[-•·▪▫]\s*', '- ', improved, flags=re.MULTILINE)
        
        # Fix numbering
        improved = re.sub(r'^\s*(\d+)[.)]\s*', r'\1. ', improved, flags=re.MULTILINE)
        
        # Fix spacing around punctuation
        improved = re.sub(r'\s+([,.!?;:])', r'\1', improved)
        improved = re.sub(r'([,.!?;:])\s+', r'\1 ', improved)
        
        # Fix paragraph spacing
        improved = re.sub(r'\n\s*\n', '\n\n', improved)
        
        # Remove excessive whitespace
        improved = re.sub(r'\s+', ' ', improved)
        
        return improved.strip()
    
    def _is_metadata_chunk(self, text: str) -> bool:
        """
        Check if chunk contains mostly metadata or headers.
        
        Args:
            text: Text content to evaluate
            
        Returns:
            True if chunk is mostly metadata, False otherwise
        """
        # Common metadata patterns
        metadata_patterns = [
            r'^(?:Page \d+|Confidential|Proprietary|Copyright|©|®|™)',
            r'^(?:Table of Contents|Index|References|Bibliography)',
            r'^(?:Appendix|Section|Chapter)\s+[A-Z\d]+',
            r'^\s*\d+\s*$',  # Just numbers
            r'^\s*[A-Z\s]{10,}\s*$',  # All caps headers
            r'^\s*[-=_]{3,}\s*$',  # Separator lines
        ]
        
        for pattern in metadata_patterns:
            if re.match(pattern, text.strip(), re.IGNORECASE):
                return True
        
        # Check if text is mostly non-alphanumeric
        alphanumeric_chars = len(re.findall(r'[a-zA-Z0-9]', text))
        total_chars = len(text.strip())
        
        if total_chars > 0 and alphanumeric_chars / total_chars < 0.3:
            return True
        
        return False
    
    def _clean_metadata(self, metadata: Dict[str, Any]) -> Dict[str, str]:
        """
        Clean and standardize metadata fields with enhanced processing.
        
        Args:
            metadata: Raw metadata dictionary
            
        Returns:
            Cleaned metadata dictionary
        """
        cleaned = {}
        
        # Essential fields with enhanced cleaning
        essential_fields = {
            'source': 'source',
            'page': 'page',
            'page_label': 'page_label',
            'file_name': 'file_name',
            'file_path': 'file_path',
            'total_pages': 'total_pages',
            'title': 'title',
            'author': 'author',
            'creator': 'creator',
            'producer': 'producer',
            'creation_date': 'creation_date',
            'modification_date': 'modification_date',
            'file_size': 'file_size'
        }
        
        for key, value in essential_fields.items():
            raw_value = metadata.get(value, '')
            
            # Clean and standardize values
            if key in ['page', 'total_pages', 'file_size']:
                # Numeric fields
                try:
                    cleaned[key] = str(int(float(raw_value))) if raw_value else '0'
                except (ValueError, TypeError):
                    cleaned[key] = '0'
            elif key in ['creation_date', 'modification_date']:
                # Date fields - normalize format
                if raw_value:
                    cleaned[key] = str(raw_value).strip()
                else:
                    cleaned[key] = ''
            elif key == 'file_name':
                # Clean file names
                if raw_value:
                    cleaned[key] = Path(raw_value).name
                else:
                    cleaned[key] = ''
            elif key == 'source':
                # Clean source paths
                if raw_value:
                    cleaned[key] = str(Path(raw_value).resolve())
                else:
                    cleaned[key] = ''
            else:
                # Text fields - clean and normalize
                if raw_value:
                    cleaned[key] = str(raw_value).strip()
                else:
                    cleaned[key] = ''
        
        # Add computed fields
        cleaned['document_type'] = self._detect_document_type(cleaned.get('title', ''), cleaned.get('file_name', ''))
        cleaned['processing_timestamp'] = datetime.now().isoformat()
        
        return cleaned
    
    def _detect_document_type(self, title: str, filename: str) -> str:
        """
        Detect document type based on title and filename.
        
        Args:
            title: Document title
            filename: Document filename
            
        Returns:
            Detected document type
        """
        text_to_check = f"{title} {filename}".lower()
        
        # RFP-related patterns
        if any(pattern in text_to_check for pattern in ['rfp', 'request for proposal', 'proposal']):
            return 'RFP'
        elif any(pattern in text_to_check for pattern in ['contract', 'agreement', 'terms']):
            return 'Contract'
        elif any(pattern in text_to_check for pattern in ['policy', 'guidelines', 'procedures']):
            return 'Policy'
        elif any(pattern in text_to_check for pattern in ['report', 'analysis', 'study']):
            return 'Report'
        elif any(pattern in text_to_check for pattern in ['manual', 'guide', 'handbook']):
            return 'Manual'
        else:
            return 'Document'
    
    def vectorize_and_store(self, chunks: List[Document]) -> Milvus:
        """
        Vectorize chunks and store them in Milvus database.
        
        Args:
            chunks: List of Document chunks to vectorize and store
            
        Returns:
            Milvus vector store instance
        """
        if not chunks:
            raise ValueError("No chunks provided for vectorization")
        
        try:
            # Remove existing database if it exists
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
                print(f"Removed existing database: {self.db_path}")
            
            # Create Milvus vector store
            self.vector_store = Milvus(
                embedding_function=self.embeddings,
                connection_args={"uri": self.db_path},
                index_params={
                    "index_type": "FLAT", 
                    "metric_type": "L2"
                },
            )
            
            # Add documents to vector store
            document_ids = self.vector_store.add_documents(documents=chunks)
            
            print(f"Successfully vectorized and stored {len(document_ids)} chunks")
            print(f"Database created: {self.db_path}")
            print(f"Database absolute path: {os.path.abspath(self.db_path)}")
            
            return self.vector_store
            
        except Exception as e:
            raise Exception(f"Error vectorizing and storing documents: {str(e)}")
    
    def setup_milvus_db(self, pdf_path: str, 
                       chunk_size: int = 1000, 
                       chunk_overlap: int = 200) -> Milvus:
        """
        Complete pipeline: parse PDF, create chunks, vectorize and store in Milvus.
        
        Args:
            pdf_path: Path to the PDF file
            chunk_size: Size of each chunk in characters
            chunk_overlap: Overlap between chunks in characters
            
        Returns:
            Milvus vector store instance
        """
        print(f"Setting up Milvus database '{self.db_name}' with PDF: {pdf_path}")
        
        # Step 1: Parse PDF
        documents = self.parse_pdf(pdf_path)
        
        # Step 2: Create chunks
        chunks = self.create_chunks(documents, chunk_size, chunk_overlap)
        
        # Step 3: Vectorize and store
        vector_store = self.vectorize_and_store(chunks)
        
        print("✅ Milvus database setup completed successfully!")
        return vector_store
    
    def query_database(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """
        Query the Milvus database and return top k matching results with accuracies.
        
        Args:
            query: Search query string
            k: Number of top results to return
            
        Returns:
            List of dictionaries containing results with content, metadata, and accuracy scores
        """
        if not self.vector_store:
            raise ValueError("No vector store available. Please setup the database first.")
        
        try:
            # Perform similarity search with scores
            results = self.vector_store.similarity_search_with_score(query, k=k)
            
            formatted_results = []
            for i, (doc, score) in enumerate(results):
                # Convert L2 distance to similarity score (lower distance = higher similarity)
                # Normalize score to 0-1 range (approximate)
                similarity_score = max(0, 1 - (score / 10))  # Adjust divisor based on your data
                
                result = {
                    'rank': i + 1,
                    'content': doc.page_content,
                    'metadata': doc.metadata,
                    'accuracy': round(similarity_score, 4),
                    'distance': round(score, 4),
                    'source_file': Path(doc.metadata.get('source', '')).name,
                    'page': doc.metadata.get('page', 'Unknown'),
                    'preview': doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
                }
                formatted_results.append(result)
            
            print(f"Found {len(formatted_results)} results for query: '{query}'")
            return formatted_results
            
        except Exception as e:
            raise Exception(f"Error querying database: {str(e)}")
    
    def get_database_info(self) -> Dict[str, Any]:
        """
        Get information about the current database.
        
        Returns:
            Dictionary containing database information
        """
        if not self.vector_store:
            return {"status": "No database loaded"}
        
        try:
            # Get collection info
            collection = self.vector_store._collection
            
            info = {
                "database_name": self.db_name,
                "database_path": self.db_path,
                "collection_name": collection.name,
                "status": "Active"
            }
            
            return info
            
        except Exception as e:
            return {"status": f"Error getting database info: {str(e)}"}
    
    def get_chunk_quality_stats(self, chunks: List[Document]) -> Dict[str, Any]:
        """
        Get quality statistics for a list of chunks.
        
        Args:
            chunks: List of document chunks
            
        Returns:
            Dictionary containing quality statistics
        """
        if not chunks:
            return {"error": "No chunks provided"}
        
        stats = {
            "total_chunks": len(chunks),
            "total_characters": sum(len(chunk.page_content) for chunk in chunks),
            "total_words": sum(len(chunk.page_content.split()) for chunk in chunks),
            "average_chunk_length": sum(len(chunk.page_content) for chunk in chunks) / len(chunks),
            "average_word_count": sum(len(chunk.page_content.split()) for chunk in chunks) / len(chunks),
            "cleaned_chunks": sum(1 for chunk in chunks if chunk.metadata.get('cleaned', False)),
            "quality_improved_chunks": sum(1 for chunk in chunks if chunk.metadata.get('quality_improved', False)),
            "document_types": {},
            "chunk_length_distribution": {
                "short": 0,    # < 500 chars
                "medium": 0,   # 500-1500 chars
                "long": 0      # > 1500 chars
            }
        }
        
        # Analyze document types
        for chunk in chunks:
            doc_type = chunk.metadata.get('document_type', 'Unknown')
            stats["document_types"][doc_type] = stats["document_types"].get(doc_type, 0) + 1
        
        # Analyze chunk length distribution
        for chunk in chunks:
            length = len(chunk.page_content)
            if length < 500:
                stats["chunk_length_distribution"]["short"] += 1
            elif length <= 1500:
                stats["chunk_length_distribution"]["medium"] += 1
            else:
                stats["chunk_length_distribution"]["long"] += 1
        
        return stats


# Convenience functions for direct usage
def setup_milvus_from_pdf(pdf_path: str, db_name: str = "session.db") -> MilvusOps:
    """
    Convenience function to setup Milvus database from PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        db_name: Name of the database file
        
    Returns:
        MilvusOps instance with loaded database
    """
    milvus_ops = MilvusOps(db_name)
    milvus_ops.setup_milvus_db(pdf_path)
    return milvus_ops


def query_milvus_db(milvus_ops: MilvusOps, query: str, k: int = 3) -> List[Dict[str, Any]]:
    """
    Convenience function to query Milvus database.
    
    Args:
        milvus_ops: MilvusOps instance
        query: Search query
        k: Number of results to return
        
    Returns:
        List of search results
    """
    return milvus_ops.query_database(query, k)


# Example usage
if __name__ == "__main__":
    # Example usage
    pdf_path = "../example-PDF/test.pdf"  # Update with your PDF path
    
    try:
        # Setup database
        milvus_ops = setup_milvus_from_pdf(pdf_path)
        
        # Query database
        results = query_milvus_db(milvus_ops, "What is the main topic?", k=3)
        
        # Print results
        for result in results:
            print(f"\nRank {result['rank']}: Accuracy {result['accuracy']}")
            print(f"Source: {result['source_file']}, Page {result['page']}")
            print(f"Preview: {result['preview']}")
            print("-" * 50)
            
    except Exception as e:
        print(f"Error: {e}")
