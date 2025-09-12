#!/usr/bin/env python3
"""
RFP Example Documents RAG Script

This script provides functionality to:
- Add RFP example documents to the RAG system
- Query the RFP RAG database
- Manage RFP-specific vector operations

Usage:
    python rfp_rag.py add_data <rfp_directory>
    python rfp_rag.py query_data <query_string>
    python rfp_rag.py interactive
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add the parent directory to the path to import milvus_ops
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from .milvus_ops import MilvusOps
except ImportError:
    from milvus_ops import MilvusOps


class RFPRAG:
    """RFP RAG system for managing RFP example documents."""
    
    def __init__(self, db_name: str = "rfp_rag.db"):
        """
        Initialize RFP RAG system.
        
        Args:
            db_name: Name of the Milvus database file for RFP documents
        """
        self.db_name = db_name
        self.milvus_ops = MilvusOps(db_name)
        self.vector_store = None
        self._load_existing_database()
    
    def _load_existing_database(self):
        """Try to load existing database if it exists."""
        try:
            if os.path.exists(self.milvus_ops.db_path):
                # Create a new Milvus instance to load existing database
                from langchain_milvus import Milvus
                self.vector_store = Milvus(
                    embedding_function=self.milvus_ops.embeddings,
                    connection_args={"uri": self.milvus_ops.db_path},
                    index_params={
                        "index_type": "FLAT", 
                        "metric_type": "L2"
                    },
                )
                # Also set it in milvus_ops for consistency
                self.milvus_ops.vector_store = self.vector_store
                print(f"✅ Loaded existing RFP database: {self.db_name}")
        except Exception as e:
            # Database doesn't exist or can't be loaded
            pass
        
    def add_data(self, rfp_directory: str, chunk_size: int = 1200, chunk_overlap: int = 300) -> bool:
        """
        Add RFP example documents to the RAG system.
        
        Args:
            rfp_directory: Path to directory containing RFP example documents
            chunk_size: Size of each chunk in characters (larger for RFP docs)
            chunk_overlap: Overlap between chunks in characters
            
        Returns:
            True if successful, False otherwise
        """
        try:
            rfp_path = Path(rfp_directory)
            if not rfp_path.exists():
                print(f"❌ RFP directory not found: {rfp_directory}")
                return False
            
            # Find all PDF files in the RFP directory
            pdf_files = list(rfp_path.glob("**/*.pdf"))
            if not pdf_files:
                print(f"❌ No PDF files found in: {rfp_directory}")
                return False
            
            print(f"📁 Found {len(pdf_files)} RFP PDF files in directory")
            
            all_documents = []
            all_chunks = []
            
            # Process each PDF file
            for pdf_file in pdf_files:
                print(f"📄 Processing RFP: {pdf_file.name}")
                try:
                    # Parse PDF
                    documents = self.milvus_ops.parse_pdf(str(pdf_file))
                    all_documents.extend(documents)
                    
                    # Create chunks with RFP-specific settings
                    chunks = self.milvus_ops.create_chunks(documents, chunk_size, chunk_overlap)
                    all_chunks.extend(chunks)
                    
                    print(f"✅ Processed {pdf_file.name}: {len(documents)} pages, {len(chunks)} chunks")
                    
                except Exception as e:
                    print(f"❌ Error processing {pdf_file.name}: {str(e)}")
                    continue
            
            if not all_chunks:
                print("❌ No valid chunks created from RFP documents")
                return False
            
            # Vectorize and store all chunks
            print(f"🔢 Vectorizing and storing {len(all_chunks)} RFP chunks...")
            self.vector_store = self.milvus_ops.vectorize_and_store(all_chunks)
            
            # Get quality stats
            stats = self.milvus_ops.get_chunk_quality_stats(all_chunks)
            print(f"📊 RFP RAG Statistics:")
            print(f"   - Total chunks: {stats['total_chunks']}")
            print(f"   - Total words: {stats['total_words']}")
            print(f"   - Average chunk length: {stats['average_chunk_length']:.1f} characters")
            print(f"   - Document types: {stats['document_types']}")
            print(f"   - Chunk length distribution: {stats['chunk_length_distribution']}")
            
            print(f"✅ RFP RAG database created successfully: {self.db_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error adding RFP data: {str(e)}")
            return False
    
    def query_data(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Query the RFP RAG database.
        
        Args:
            query: Search query string
            k: Number of top results to return
            
        Returns:
            List of search results with content, metadata, and scores
        """
        try:
            if not self.vector_store:
                print("❌ No RFP database loaded. Please add data first.")
                return []
            
            print(f"🔍 Searching RFP database for: '{query}'")
            results = self.milvus_ops.query_database(query, k)
            
            if not results:
                print("❌ No results found")
                return []
            
            print(f"✅ Found {len(results)} RFP results:")
            for i, result in enumerate(results, 1):
                print(f"\n📋 Result {i}:")
                print(f"   📄 Source: {result['source_file']}")
                print(f"   📖 Page: {result['page']}")
                print(f"   🎯 Accuracy: {result['accuracy']:.3f}")
                print(f"   📝 Preview: {result['preview']}")
                print(f"   📊 Distance: {result['distance']:.3f}")
            
            return results
            
        except Exception as e:
            print(f"❌ Error querying RFP database: {str(e)}")
            return []
    
    def query_specific_rfp(self, query: str, rfp_name: str, k: int = 3) -> List[Dict[str, Any]]:
        """
        Query a specific RFP document.
        
        Args:
            query: Search query string
            rfp_name: Name of the RFP document to search in
            k: Number of top results to return
            
        Returns:
            List of search results from the specific RFP
        """
        try:
            if not self.vector_store:
                print("❌ No RFP database loaded. Please add data first.")
                return []
            
            print(f"🔍 Searching '{rfp_name}' for: '{query}'")
            results = self.milvus_ops.query_database(query, k * 2)  # Get more results to filter
            
            # Filter results by RFP name
            filtered_results = [r for r in results if rfp_name.lower() in r['source_file'].lower()]
            filtered_results = filtered_results[:k]  # Limit to requested number
            
            if not filtered_results:
                print(f"❌ No results found in {rfp_name}")
                return []
            
            print(f"✅ Found {len(filtered_results)} results in {rfp_name}:")
            for i, result in enumerate(filtered_results, 1):
                print(f"\n📋 Result {i}:")
                print(f"   📄 Source: {result['source_file']}")
                print(f"   📖 Page: {result['page']}")
                print(f"   🎯 Accuracy: {result['accuracy']:.3f}")
                print(f"   📝 Preview: {result['preview']}")
            
            return filtered_results
            
        except Exception as e:
            print(f"❌ Error querying specific RFP: {str(e)}")
            return []
    
    def get_rfp_list(self) -> List[str]:
        """Get list of RFP documents in the database."""
        try:
            if not self.vector_store:
                print("❌ No RFP database loaded. Please add data first.")
                return []
            
            # Query with a generic term to get all documents
            results = self.milvus_ops.query_database("document", k=100)
            
            # Extract unique RFP names
            rfp_names = list(set([r['source_file'] for r in results]))
            rfp_names.sort()
            
            return rfp_names
            
        except Exception as e:
            print(f"❌ Error getting RFP list: {str(e)}")
            return []
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get information about the RFP database."""
        return self.milvus_ops.get_database_info()
    
    def query_data_enhanced(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Enhanced query with better context formatting and ranking.
        
        Args:
            query: Search query string
            k: Number of top results to return
            
        Returns:
            List of enhanced search results with better context structure
        """
        try:
            if not self.vector_store:
                print("❌ No RFP database loaded. Please add data first.")
                return []
            
            print(f"🔍 Enhanced search in RFP database for: '{query}'")
            results = self.milvus_ops.query_database(query, k)
            
            if not results:
                print("❌ No results found")
                return []
            
            # Enhanced results with better ranking and context
            enhanced_results = []
            for i, result in enumerate(results):
                enhanced_result = {
                    'rank': i + 1,
                    'content': result.get('content', ''),
                    'preview': result.get('preview', result.get('content', ''))[:200],
                    'source_file': result.get('source_file', 'Unknown'),
                    'page': result.get('page', 'Unknown'),
                    'accuracy': result.get('accuracy', 0.0),
                    'distance': result.get('distance', float('inf')),
                    'relevance_score': 1.0 - (result.get('distance', 1.0) / 2.0),
                    'context_type': self._determine_context_type(result.get('content', '')),
                    'word_count': len(result.get('content', '').split())
                }
                enhanced_results.append(enhanced_result)
            
            print(f"✅ Found {len(enhanced_results)} enhanced RFP results:")
            for result in enhanced_results:
                print(f"\n📋 Result {result['rank']}:")
                print(f"   📄 Source: {result['source_file']}")
                print(f"   📖 Page: {result['page']}")
                print(f"   🎯 Relevance: {result['relevance_score']:.3f}")
                print(f"   📊 Type: {result['context_type']}")
                print(f"   📝 Preview: {result['preview']}")
            
            return enhanced_results
            
        except Exception as e:
            print(f"❌ Error in enhanced query: {str(e)}")
            return []
    
    def _determine_context_type(self, content: str) -> str:
        """Determine the type of context from content analysis."""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['requirement', 'scope', 'specification']):
            return 'Requirements'
        elif any(word in content_lower for word in ['technical', 'solution', 'approach', 'methodology']):
            return 'Technical'
        elif any(word in content_lower for word in ['price', 'cost', 'budget', 'payment']):
            return 'Financial'
        elif any(word in content_lower for word in ['timeline', 'schedule', 'deadline', 'milestone']):
            return 'Timeline'
        elif any(word in content_lower for word in ['legal', 'contract', 'terms', 'condition']):
            return 'Legal'
        elif any(word in content_lower for word in ['experience', 'reference', 'portfolio', 'case study']):
            return 'Experience'
        else:
            return 'General'
    
    def interactive_mode(self):
        """Run interactive query mode."""
        print("🤖 RFP RAG Interactive Mode")
        print("Type 'quit' or 'exit' to stop")
        print("Type 'info' to see database information")
        print("Type 'list' to see available RFP documents")
        print("Type 'search <rfp_name>' to search specific RFP")
        print("-" * 50)
        
        while True:
            try:
                query = input("\n🔍 Enter your query: ").strip()
                
                if query.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                elif query.lower() == 'info':
                    info = self.get_database_info()
                    print(f"📊 Database Info: {info}")
                    continue
                elif query.lower() == 'list':
                    rfp_list = self.get_rfp_list()
                    if rfp_list:
                        print("📋 Available RFP Documents:")
                        for i, rfp in enumerate(rfp_list, 1):
                            print(f"   {i}. {rfp}")
                    else:
                        print("❌ No RFP documents found")
                    continue
                elif query.lower().startswith('search '):
                    rfp_name = query[7:].strip()
                    if rfp_name:
                        self.query_specific_rfp("document", rfp_name)
                    else:
                        print("❌ Please specify RFP name after 'search'")
                    continue
                elif not query:
                    continue
                
                results = self.query_data(query)
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {str(e)}")


def main():
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(description="RFP RAG System")
    parser.add_argument("command", choices=["add_data", "query_data", "interactive"], 
                       help="Command to execute")
    parser.add_argument("--rfp_dir", "-d", type=str, 
                       help="RFP directory path (for add_data)")
    parser.add_argument("--query", "-q", type=str, 
                       help="Query string (for query_data)")
    parser.add_argument("--k", "-k", type=int, default=5, 
                       help="Number of results to return (default: 5)")
    parser.add_argument("--db_name", type=str, default="rfp_rag.db", 
                       help="Database name (default: rfp_rag.db)")
    parser.add_argument("--chunk_size", type=int, default=1200, 
                       help="Chunk size in characters (default: 1200)")
    parser.add_argument("--chunk_overlap", type=int, default=300, 
                       help="Chunk overlap in characters (default: 300)")
    parser.add_argument("--rfp_name", type=str, 
                       help="Specific RFP name to search in")
    
    args = parser.parse_args()
    
    # Initialize RFP RAG
    rfp_rag = RFPRAG(args.db_name)
    
    if args.command == "add_data":
        if not args.rfp_dir:
            print("❌ RFP directory is required for add_data command")
            sys.exit(1)
        
        success = rfp_rag.add_data(args.rfp_dir, args.chunk_size, args.chunk_overlap)
        sys.exit(0 if success else 1)
    
    elif args.command == "query_data":
        if not args.query:
            print("❌ Query string is required for query_data command")
            sys.exit(1)
        
        if args.rfp_name:
            results = rfp_rag.query_specific_rfp(args.query, args.rfp_name, args.k)
        else:
            results = rfp_rag.query_data(args.query, args.k)
        sys.exit(0 if results else 1)
    
    elif args.command == "interactive":
        rfp_rag.interactive_mode()


if __name__ == "__main__":
    main()
