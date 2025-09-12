#!/usr/bin/env python3
"""
Template RAG Script

This script provides functionality to:
- Add template documents to the RAG system
- Query the template RAG database
- Manage template-specific vector operations

Usage:
    python template_rag.py add_data <template_directory>
    python template_rag.py query_data <query_string>
    python template_rag.py interactive
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add the parent directory to the path to import milvus_ops
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .milvus_ops import MilvusOps


class TemplateRAG:
    """Template RAG system for managing template documents."""
    
    def __init__(self, db_name: str = "template_rag.db"):
        """
        Initialize Template RAG system.
        
        Args:
            db_name: Name of the Milvus database file for templates
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
                print(f"✅ Loaded existing template database: {self.db_name}")
        except Exception as e:
            # Database doesn't exist or can't be loaded
            pass
        
    def add_data(self, template_directory: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> bool:
        """
        Add template documents to the RAG system.
        
        Args:
            template_directory: Path to directory containing template documents
            chunk_size: Size of each chunk in characters
            chunk_overlap: Overlap between chunks in characters
            
        Returns:
            True if successful, False otherwise
        """
        try:
            template_path = Path(template_directory)
            if not template_path.exists():
                print(f"❌ Template directory not found: {template_directory}")
                return False
            
            # Find all PDF files in the template directory
            pdf_files = list(template_path.glob("**/*.pdf"))
            if not pdf_files:
                print(f"❌ No PDF files found in: {template_directory}")
                return False
            
            print(f"📁 Found {len(pdf_files)} PDF files in template directory")
            
            all_documents = []
            all_chunks = []
            
            # Process each PDF file
            for pdf_file in pdf_files:
                print(f"📄 Processing: {pdf_file.name}")
                try:
                    # Parse PDF
                    documents = self.milvus_ops.parse_pdf(str(pdf_file))
                    all_documents.extend(documents)
                    
                    # Create chunks
                    chunks = self.milvus_ops.create_chunks(documents, chunk_size, chunk_overlap)
                    all_chunks.extend(chunks)
                    
                    print(f"✅ Processed {pdf_file.name}: {len(documents)} pages, {len(chunks)} chunks")
                    
                except Exception as e:
                    print(f"❌ Error processing {pdf_file.name}: {str(e)}")
                    continue
            
            if not all_chunks:
                print("❌ No valid chunks created from template documents")
                return False
            
            # Vectorize and store all chunks
            print(f"🔢 Vectorizing and storing {len(all_chunks)} template chunks...")
            self.vector_store = self.milvus_ops.vectorize_and_store(all_chunks)
            
            # Get quality stats
            stats = self.milvus_ops.get_chunk_quality_stats(all_chunks)
            print(f"📊 Template RAG Statistics:")
            print(f"   - Total chunks: {stats['total_chunks']}")
            print(f"   - Total words: {stats['total_words']}")
            print(f"   - Average chunk length: {stats['average_chunk_length']:.1f} characters")
            print(f"   - Document types: {stats['document_types']}")
            
            print(f"✅ Template RAG database created successfully: {self.db_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error adding template data: {str(e)}")
            return False
    
    def query_data(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Query the template RAG database.
        
        Args:
            query: Search query string
            k: Number of top results to return
            
        Returns:
            List of search results with content, metadata, and scores
        """
        try:
            if not self.vector_store:
                print("❌ No template database loaded. Please add data first.")
                return []
            
            print(f"🔍 Searching template database for: '{query}'")
            results = self.milvus_ops.query_database(query, k)
            
            if not results:
                print("❌ No results found")
                return []
            
            print(f"✅ Found {len(results)} template results:")
            for i, result in enumerate(results, 1):
                print(f"\n📋 Result {i}:")
                print(f"   📄 Source: {result['source_file']}")
                print(f"   📖 Page: {result['page']}")
                print(f"   🎯 Accuracy: {result['accuracy']:.3f}")
                print(f"   📝 Preview: {result['preview']}")
                print(f"   📊 Distance: {result['distance']:.3f}")
            
            return results
            
        except Exception as e:
            print(f"❌ Error querying template database: {str(e)}")
            return []
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get information about the template database."""
        return self.milvus_ops.get_database_info()
    
    def interactive_mode(self):
        """Run interactive query mode."""
        print("🤖 Template RAG Interactive Mode")
        print("Type 'quit' or 'exit' to stop")
        print("Type 'info' to see database information")
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
    parser = argparse.ArgumentParser(description="Template RAG System")
    parser.add_argument("command", choices=["add_data", "query_data", "interactive"], 
                       help="Command to execute")
    parser.add_argument("--template_dir", "-d", type=str, 
                       help="Template directory path (for add_data)")
    parser.add_argument("--query", "-q", type=str, 
                       help="Query string (for query_data)")
    parser.add_argument("--k", "-k", type=int, default=5, 
                       help="Number of results to return (default: 5)")
    parser.add_argument("--db_name", type=str, default="template_rag.db", 
                       help="Database name (default: template_rag.db)")
    parser.add_argument("--chunk_size", type=int, default=1000, 
                       help="Chunk size in characters (default: 1000)")
    parser.add_argument("--chunk_overlap", type=int, default=200, 
                       help="Chunk overlap in characters (default: 200)")
    
    args = parser.parse_args()
    
    # Initialize Template RAG
    template_rag = TemplateRAG(args.db_name)
    
    if args.command == "add_data":
        if not args.template_dir:
            print("❌ Template directory is required for add_data command")
            sys.exit(1)
        
        success = template_rag.add_data(args.template_dir, args.chunk_size, args.chunk_overlap)
        sys.exit(0 if success else 1)
    
    elif args.command == "query_data":
        if not args.query:
            print("❌ Query string is required for query_data command")
            sys.exit(1)
        
        results = template_rag.query_data(args.query, args.k)
        sys.exit(0 if results else 1)
    
    elif args.command == "interactive":
        template_rag.interactive_mode()


if __name__ == "__main__":
    main()
