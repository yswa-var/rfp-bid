"""
Proposal RAG Coordinator

Coordinates the three RAG systems for proposal generation using the same databases
as the existing system (session.db, template_rag.db, rfp_rag.db).
"""

import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from langchain_milvus import Milvus
from langchain_openai import OpenAIEmbeddings

from .template_rag import TemplateRAG
from .rfp_rag import RFPRAG
from .milvus_ops import MilvusOps


class ProposalRAGCoordinator:
    """Coordinates the three RAG systems for proposal generation."""
    
    def __init__(self):
        # Use the same database names as the existing system
        self.template_rag = None
        self.examples_rag = None
        self.session_milvus = MilvusOps("session.db")  # Use session.db like general_assistant
        self.session_vector_store = None
        
        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-large",
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        self._initialize_all_databases()
    
    def _initialize_all_databases(self):
        """Initialize all three RAG databases with proper error handling."""
        print("🔧 Initializing RAG databases...")
        
        # Initialize Template RAG
        try:
            self.template_rag = TemplateRAG("template_rag.db")
            if self.template_rag.vector_store is None:
                print("⚠️  Template database exists but failed to load, attempting manual load...")
                self._manual_load_database("template_rag.db", "template")
            else:
                print("✅ Template RAG loaded successfully")
        except Exception as e:
            print(f"❌ Error initializing Template RAG: {e}")
        
        # Initialize Examples RAG
        try:
            self.examples_rag = RFPRAG("rfp_rag.db")
            if self.examples_rag.vector_store is None:
                print("⚠️  Examples database exists but failed to load, attempting manual load...")
                self._manual_load_database("rfp_rag.db", "examples")
            else:
                print("✅ Examples RAG loaded successfully")
        except Exception as e:
            print(f"❌ Error initializing Examples RAG: {e}")
        
        # Initialize Session database
        try:
            if os.path.exists(self.session_milvus.db_path):
                self.session_vector_store = Milvus(
                    embedding_function=self.embeddings,
                    connection_args={"uri": self.session_milvus.db_path},
                    index_params={"index_type": "FLAT", "metric_type": "L2"},
                )
                print(f"✅ Session database loaded: {self.session_milvus.db_path}")
            else:
                print(f"⚠️  Session database not found: {self.session_milvus.db_path}")
        except Exception as e:
            print(f"❌ Error loading session database: {e}")
    
    def _manual_load_database(self, db_name: str, db_type: str):
        """Manually load a database that failed to load automatically."""
        try:
            db_path = os.path.join(os.path.dirname(__file__), db_name)
            if os.path.exists(db_path):
                vector_store = Milvus(
                    embedding_function=self.embeddings,
                    connection_args={"uri": db_path},
                    index_params={"index_type": "FLAT", "metric_type": "L2"},
                )
                
                if db_type == "template" and self.template_rag:
                    self.template_rag.vector_store = vector_store
                    print(f"✅ Manually loaded Template RAG: {db_name}")
                elif db_type == "examples" and self.examples_rag:
                    self.examples_rag.vector_store = vector_store
                    print(f"✅ Manually loaded Examples RAG: {db_name}")
                    
        except Exception as e:
            print(f"❌ Manual load failed for {db_type}: {e}")
    
    def setup_databases(self):
        """Setup template and examples RAG databases."""
        print("🔧 Setting up RAG databases for proposal generation...")
        
        # Setup Template RAG
        template_dir = Path("../example-PDF/templates-pdf")
        if template_dir.exists():
            print("📋 Setting up Template RAG...")
            try:
                if self.template_rag is None:
                    self.template_rag = TemplateRAG("template_rag.db")
                
                if not (self.template_rag and self.template_rag.vector_store):
                    # Try manual load first
                    self._manual_load_database("template_rag.db", "template")
                    
                    # If still not loaded, add data
                    if not (self.template_rag and self.template_rag.vector_store):
                        self.template_rag.add_data(str(template_dir))
                        print("✅ Template RAG setup complete")
                    else:
                        print("✅ Template RAG loaded from existing database")
                else:
                    print("✅ Template RAG already loaded")
            except Exception as e:
                print(f"❌ Template RAG setup failed: {e}")
        else:
            print(f"⚠️  Template directory not found: {template_dir}")
        
        # Setup Examples RAG
        examples_dir = Path("../example-PDF/rfp-pdf")
        if examples_dir.exists():
            print("📚 Setting up Examples RAG...")
            try:
                if self.examples_rag is None:
                    self.examples_rag = RFPRAG("rfp_rag.db")
                
                if not (self.examples_rag and self.examples_rag.vector_store):
                    # Try manual load first
                    self._manual_load_database("rfp_rag.db", "examples")
                    
                    # If still not loaded, add data
                    if not (self.examples_rag and self.examples_rag.vector_store):
                        self.examples_rag.add_data(str(examples_dir))
                        print("✅ Examples RAG setup complete")
                    else:
                        print("✅ Examples RAG loaded from existing database")
                else:
                    print("✅ Examples RAG already loaded")
            except Exception as e:
                print(f"❌ Examples RAG setup failed: {e}")
        else:
            print(f"⚠️  Examples directory not found: {examples_dir}")
        
        # Check session database
        if self.session_vector_store:
            print("✅ Session database ready")
        else:
            print("⚠️  Session database not available - current RFP context will be limited")
        
        print("🎯 RAG setup complete!")
    
    def query_all_rags(self, query: str, k: int = 3) -> Dict[str, List[Dict[str, Any]]]:
        """Query all three RAG systems with enhanced context."""
        results = {
            "template_context": [],
            "session_context": [],
            "examples_context": []
        }
        
        # Query Template RAG
        try:
            if self.template_rag and self.template_rag.vector_store:
                template_query = f"proposal template structure format {query}"
                template_results = self.template_rag.query_data(template_query, k)
                if template_results:
                    results["template_context"] = template_results
                    print(f"📋 Template RAG: Found {len(template_results)} results")
                else:
                    print("📋 Template RAG: No results found for query")
            else:
                print("❌ No template database loaded. Please add data first.")
        except Exception as e:
            print(f"❌ Template RAG query error: {e}")
        
        # Query Session RAG (current RFP from session.db)
        try:
            if self.session_vector_store:
                session_results = self.session_vector_store.similarity_search(
                    f"current rfp requirements {query}", k=k
                )
                if session_results:
                    # Convert to the expected format
                    formatted_results = []
                    for doc in session_results:
                        formatted_results.append({
                            "content": doc.page_content,
                            "source_file": doc.metadata.get("source", "session.db"),
                            "accuracy": 0.8  # Default accuracy for session docs
                        })
                    results["session_context"] = formatted_results
                    print(f"📄 Session RAG: Found {len(formatted_results)} results")
                else:
                    print("📄 Session RAG: No results found")
            else:
                print("📄 Session RAG: No current RFP loaded")
        except Exception as e:
            print(f"❌ Session RAG query error: {e}")
        
        # Query Examples RAG
        try:
            if self.examples_rag and self.examples_rag.vector_store:
                examples_query = f"similar rfp examples {query}"
                examples_results = self.examples_rag.query_data(examples_query, k)
                if examples_results:
                    results["examples_context"] = examples_results
                    print(f"📚 Examples RAG: Found {len(examples_results)} results")
                else:
                    print("📚 Examples RAG: No results found for query")
            else:
                print("❌ No RFP database loaded. Please add data first.")
        except Exception as e:
            print(f"❌ Examples RAG query error: {e}")
        
        total_results = sum(len(ctx) for ctx in results.values())
        print(f"🎯 Total 3-level context results: {total_results}")
        
        return results
    
    def get_database_status(self) -> Dict[str, bool]:
        """Get the status of all three databases."""
        return {
            "template_ready": self.template_rag is not None and self.template_rag.vector_store is not None,
            "session_ready": self.session_vector_store is not None,
            "examples_ready": self.examples_rag is not None and self.examples_rag.vector_store is not None
        }
    
    def ensure_databases_ready(self) -> bool:
        """Ensure databases are ready, setup if needed."""
        status = self.get_database_status()
        
        if not any(status.values()):
            print("🔧 No databases ready, setting up...")
            self.setup_databases()
            status = self.get_database_status()
        
        ready_count = sum(status.values())
        print(f"📊 Database Status: {ready_count}/3 ready")
        print(f"   - Template: {'✅' if status['template_ready'] else '❌'}")
        print(f"   - Session: {'✅' if status['session_ready'] else '❌'}")
        print(f"   - Examples: {'✅' if status['examples_ready'] else '❌'}")
        
        return ready_count > 0  # At least one database should be ready
