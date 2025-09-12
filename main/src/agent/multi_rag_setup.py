"""
Multi-RAG Setup Agent

Handles setup and initialization of the Multi-RAG system.
"""

from typing import Dict, Any
from langchain_core.messages import AIMessage

from .state import MessagesState
from .proposal_rag_coordinator import ProposalRAGCoordinator


class MultiRAGSetupAgent:
    """Agent to setup the Multi-RAG system."""
    
    def __init__(self):
        self.coordinator = ProposalRAGCoordinator()
    
    def setup_multi_rag(self, state: MessagesState) -> Dict[str, Any]:
        """Setup all three RAG databases."""
        try:
            self.coordinator.setup_databases()
            
            # Get database status for detailed feedback
            status = self.coordinator.get_database_status()
            ready_count = sum(status.values())
            
            response = f"""✅ **Multi-RAG System Setup Complete!**

📊 **Database Status ({ready_count}/3 ready):**
- **Template RAG**: {'✅ Ready' if status['template_ready'] else '❌ Not available'}
- **Examples RAG**: {'✅ Ready' if status['examples_ready'] else '❌ Not available'}  
- **Session RAG**: {'✅ Ready' if status['session_ready'] else '⚠️ No current RFP (use session.db)'}

🎯 **Next Steps:**
- Say "generate proposal" to create a proposal using available RAG systems
- Upload PDFs and create session database for current RFP context
- Ask questions about templates or RFP examples

💡 **Note**: Session RAG uses the same session.db as the general assistant.
"""
            
            return {
                "messages": [AIMessage(content=response, name="multi_rag_setup")],
                "multi_rag_ready": True,
                "databases_ready": ready_count
            }
            
        except Exception as e:
            return {
                "messages": [AIMessage(content=f"❌ Multi-RAG setup failed: {e}", name="multi_rag_setup")]
            }
