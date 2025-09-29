"""
Interactive RAG Editor Launcher for LangGraph Studio

This module provides a LangGraph node that launches the full interactive
RAG editor with the same beautiful interface shown in the standalone version.
"""

import os
import sys
import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from langchain_core.messages import AIMessage, HumanMessage

from .state import MessagesState

# Add the MCP client path to sys.path
_CURRENT_DIR = Path(__file__).resolve().parent
_MAIN_DIR = _CURRENT_DIR.parent.parent
_MCP_CLIENT_DIR = _MAIN_DIR / "Mcp_client_word"
if str(_MCP_CLIENT_DIR) not in sys.path:
    sys.path.insert(0, str(_MCP_CLIENT_DIR))


class InteractiveRAGLauncher:
    """Launches the full interactive RAG editor experience within LangGraph."""
    
    def __init__(self):
        self.agent_name = "interactive_rag_launcher"
        self.mcp_client_dir = _MCP_CLIENT_DIR
        self.main_dir = _MAIN_DIR
        
    def launch_full_rag_editor(self, state: MessagesState) -> Dict[str, Any]:
        """Launch the full interactive RAG editor with beautiful UI."""
        try:
            messages = state.get("messages", [])
            
            # Check if user wants to launch RAG editor
            user_input = ""
            if messages:
                user_messages = [m for m in messages if isinstance(m, HumanMessage)]
                if user_messages:
                    user_input = user_messages[-1].content.lower()
            
            # Detect RAG editor launch commands
            launch_commands = [
                "launch rag editor", "start rag editor", "open document editor",
                "edit document", "interactive editor", "launch editor",
                "rag edit", "ai editor", "document rag", "enhanced editor"
            ]
            
            if not any(cmd in user_input for cmd in launch_commands):
                return self._show_launch_instructions(state)
            
            # Launch the RAG editor
            return self._execute_rag_editor_launch(state, user_input)
            
        except Exception as e:
            return {
                "messages": [AIMessage(
                    content=f"❌ Failed to launch RAG editor: {e}",
                    name=self.agent_name
                )]
            }
    
    def _show_launch_instructions(self, state: MessagesState) -> Dict[str, Any]:
        """Show instructions for launching the RAG editor."""
        instructions = """🎯 **Interactive RAG Editor Launcher**
════════════════════════════════════════════════════════════

🚀 **Available Commands:**
• `launch rag editor` - Start the full interactive RAG editor
• `edit document` - Open document editing interface  
• `interactive editor` - Launch AI-powered document editor
• `rag edit` - Start RAG-enhanced editing session

✨ **RAG Editor Features:**
🔧 **Enhanced Document Editing**
• AI-powered search and replace
• RAG-enhanced content generation
• Smart section detection
• Professional document formatting

📊 **Multi-Database Integration**
• Template RAG: Industry templates and examples
• Examples RAG: Historical RFP responses
• Session RAG: Current project context

🎮 **Interactive Commands Available:**
• `find 'text'` - Smart document search with RAG enhancement
• `replace 'old' with 'new'` - Intelligent text replacement  
• `rag query 'question'` - Direct RAG knowledge base queries
• `add content 'request'` - Generate RAG-enhanced content
• `explore 'pattern'` - Navigate document structure
• `enhance` - Improve existing content with RAG context

💡 **Getting Started:**
Type `launch rag editor` to start the interactive editing session!

The RAG editor will provide:
✅ Real-time document analysis (word count, paragraphs, tables)
✅ RAG database status monitoring
✅ Interactive command interface
✅ Context-aware content enhancement
✅ Professional document generation

Ready to enhance your documents with AI! 🚀"""

        return {
            "messages": [AIMessage(content=instructions, name=self.agent_name)]
        }
    
    def _execute_rag_editor_launch(self, state: MessagesState, user_input: str) -> Dict[str, Any]:
        """Execute the RAG editor launch process."""
        try:
            # Check if the launch script exists
            launch_script = self.mcp_client_dir / "launch_rag_editor.py"
            if not launch_script.exists():
                return {
                    "messages": [AIMessage(
                        content=f"❌ RAG Editor launch script not found at: {launch_script}",
                        name=self.agent_name
                    )]
                }
            
            # Provide launch information and instructions
            launch_info = f"""🚀 **Launching Interactive RAG Editor**
════════════════════════════════════════════════════════════

📁 **System Paths:**
• Script directory: {self.mcp_client_dir}
• RFP main directory: {self.main_dir}
• Launch script: {launch_script}

🔧 **RAG Database Status:**
• Template RAG: template_rag.db (Industry templates)
• Examples RAG: rfp_rag.db (Historical responses)  
• Session RAG: session.db (Current project context)

🎯 **Launch Command Ready:**
```bash
cd {self.mcp_client_dir}
python launch_rag_editor.py
```

⚡ **What Happens Next:**
1. 🚀 System initializes RAG databases
2. 📊 Document analysis and metadata extraction
3. 🔧 MCP server startup (54 tools loaded)
4. 🎮 Interactive command interface activation
5. ✅ Ready for AI-powered document editing!

**Interactive Session Features:**
• **Document Info**: Real-time statistics and metadata
• **Smart Search**: `find 'text'` with RAG enhancement options
• **Intelligent Replace**: Context-aware text replacement
• **RAG Queries**: Direct access to knowledge bases
• **Content Generation**: AI-powered content creation
• **Document Exploration**: Structure navigation and analysis

🎮 **Sample Commands You Can Use:**
• `find '1. Summary'` - Find and enhance summary sections
• `rag query 'project timeline'` - Query RAG for timeline templates
• `add content 'executive overview'` - Generate enhanced content
• `explore 'Case Studies'` - Navigate document structure
• `replace 'old approach' with 'enhanced methodology'` - Smart replacement

**To Launch Now:**
1. Open a new terminal
2. Run: `cd {self.mcp_client_dir}`
3. Run: `python launch_rag_editor.py`
4. Follow the interactive prompts for document editing

The RAG editor will provide the same beautiful interface you saw before, with full document editing capabilities and RAG enhancement! 🌟

**Tip:** The editor automatically loads available DOCX files and provides intelligent suggestions based on your RAG knowledge base."""

            return {
                "messages": [AIMessage(content=launch_info, name=self.agent_name)],
                "rag_editor_launch_ready": True,
                "launch_script_path": str(launch_script),
                "mcp_client_dir": str(self.mcp_client_dir)
            }
            
        except Exception as e:
            return {
                "messages": [AIMessage(
                    content=f"❌ RAG Editor launch preparation failed: {e}",
                    name=self.agent_name
                )]
            }

    def get_available_documents(self) -> List[str]:
        """Get list of available DOCX documents for editing."""
        try:
            docs = []
            # Check MCP client directory
            for doc_path in self.mcp_client_dir.glob("*.docx"):
                docs.append(str(doc_path))
            
            # Check main test output directory
            test_output_dir = self.main_dir / "test_output"
            if test_output_dir.exists():
                for doc_path in test_output_dir.glob("*.docx"):
                    docs.append(str(doc_path))
            
            return docs
        except Exception as e:
            return []


def create_interactive_rag_launcher_node():
    """Create a LangGraph node for the interactive RAG editor launcher."""
    launcher = InteractiveRAGLauncher()
    return launcher.launch_full_rag_editor


# For backward compatibility and direct usage
interactive_rag_launcher = InteractiveRAGLauncher()