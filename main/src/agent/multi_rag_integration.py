"""
Multi-RAG Integration Script
"""

import os
from pathlib import Path
from .template_rag import TemplateRAG
from .rfp_rag import RFPRAG

class MultiRAGCoordinator:
    """Coordinates the three RAG systems."""
    
    def __init__(self):
        self.template_rag = TemplateRAG("template_rag.db")
        self.session_rag = RFPRAG("session_rag.db") 
        self.examples_rag = RFPRAG("rfp_rag.db")
    
    def setup_databases(self):
        """Setup all three RAG databases."""
        print("Setting up Multi-RAG system...")
        
        template_dir = "../example-PDF/templates-pdf"
        if Path(template_dir).exists():
            print("Adding template documents...")
            try:
                self.template_rag.add_data(template_dir)
                print("✅ Template RAG setup complete")
            except Exception as e:
                print(f"❌ Template RAG setup failed: {e}")
        
        examples_dir = "../example-PDF/rfp-pdf"
        if Path(examples_dir).exists():
            print("Adding RFP example documents...")
            try:
                self.examples_rag.add_data(examples_dir)
                print("✅ RFP Examples RAG setup complete")
            except Exception as e:
                print(f"❌ RFP Examples RAG setup failed: {e}")
        
        print("Initializing Session RAG (empty for now)...")
        
        print("Multi-RAG setup complete!")
    
    def add_session_rfp(self, rfp_file_path: str):
        """Add current RFP to session RAG."""
        print(f"Adding session RFP: {rfp_file_path}")
        
        if not Path(rfp_file_path).exists():
            print(f"❌ RFP file not found: {rfp_file_path}")
            return False

        import shutil
        temp_dir = "./temp_session"
        Path(temp_dir).mkdir(exist_ok=True)
        
        try:
            shutil.copy2(rfp_file_path, temp_dir)
            
            success = self.session_rag.add_data(temp_dir)

            shutil.rmtree(temp_dir)
            
            if success:
                print("✅ Session RFP added successfully!")
                return True
            else:
                print("❌ Failed to add session RFP")
                return False
                
        except Exception as e:
            print(f"❌ Session RFP setup failed: {e}")
            if Path(temp_dir).exists():
                shutil.rmtree(temp_dir)
            return False
    
    def query_all_rags(self, query: str, k: int = 3):
        """Enhanced query with structured 3-level context and better ranking."""
        try:
            results = {
                "template_context": [],
                "session_context": [], 
                "examples_context": []
            }
            
            # Query Template RAG with template-specific enhancement
            try:
                template_query = f"template structure format {query}"
                if hasattr(self.template_rag, 'query_data_enhanced'):
                    results["template_context"] = self.template_rag.query_data_enhanced(template_query, k)
                else:
                    results["template_context"] = self.template_rag.query_data(template_query, k)
                print(f"📋 Template RAG: Found {len(results['template_context'])} results")
            except Exception as e:
                print(f"Template RAG query error: {e}")
            
            # Query Session RAG (current RFP) with session-specific enhancement
            try:
                if hasattr(self.session_rag, 'vector_store') and self.session_rag.vector_store:
                    session_query = f"current rfp requirements {query}"
                    if hasattr(self.session_rag, 'query_data_enhanced'):
                        results["session_context"] = self.session_rag.query_data_enhanced(session_query, k)
                    else:
                        results["session_context"] = self.session_rag.query_data(session_query, k)
                    print(f"📄 Session RAG: Found {len(results['session_context'])} results")
                else:
                    print("📄 Session RAG: No current RFP loaded")
            except Exception as e:
                print(f"Session RAG query error: {e}")
            
            # Query Examples RAG with examples-specific enhancement
            try:
                examples_query = f"similar rfp examples {query}"
                if hasattr(self.examples_rag, 'query_data_enhanced'):
                    results["examples_context"] = self.examples_rag.query_data_enhanced(examples_query, k)
                else:
                    results["examples_context"] = self.examples_rag.query_data(examples_query, k)
                print(f"📚 Examples RAG: Found {len(results['examples_context'])} results")
            except Exception as e:
                print(f"Examples RAG query error: {e}")
            
            total_results = sum(len(ctx) for ctx in results.values())
            print(f"🎯 Total 3-level context results: {total_results}")
            
            return results
            
        except Exception as e:
            print(f"Error in enhanced multi-RAG query: {e}")
            return {
                "template_context": [],
                "session_context": [], 
                "examples_context": []
            }
    
    def get_context_quality_metrics(self, results: dict) -> dict:
        """Get quality metrics for the 3-level context."""
        metrics = {
            "template_coverage": len(results.get("template_context", [])) > 0,
            "session_coverage": len(results.get("session_context", [])) > 0,
            "examples_coverage": len(results.get("examples_context", [])) > 0,
            "total_context_sources": sum(len(ctx) for ctx in results.values()),
            "context_balance": {
                "template": len(results.get("template_context", [])),
                "session": len(results.get("session_context", [])),
                "examples": len(results.get("examples_context", []))
            }
        }
        
        coverage_score = sum([
            metrics["template_coverage"],
            metrics["session_coverage"], 
            metrics["examples_coverage"]
        ]) / 3.0
        
        metrics["overall_quality"] = coverage_score
        return metrics
      
      
if __name__ == "__main__":
    coordinator = MultiRAGCoordinator()
    coordinator.setup_databases()