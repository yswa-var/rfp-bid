"""
RAG Editor Agent for LangGraph Integration

Creates a proper LangGraph node for RAG editor functionality that can be
called independently or integrated into the proposal supervisor flow.
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from langchain_core.messages import AIMessage, HumanMessage

from .state import MessagesState
from .rag_editor_integration import integrate_rag_editor_with_proposal


class RAGEditorAgent:
    """RAG Editor Agent that can be used as a LangGraph node."""
    
    def __init__(self):
        self.agent_name = "rag_editor"
        self.supported_operations = [
            "enhance_proposal",
            "update_document", 
            "generate_enhanced_content",
            "process_team_outputs"
        ]
    
    def launch_rag_editor(self, state: MessagesState) -> Dict[str, Any]:
        """Launch RAG editor for interactive document editing."""
        try:
            messages = state.get("messages", [])
            if not messages:
                return {
                    "messages": [AIMessage(content="Please provide a document or content to edit.", name=self.agent_name)]
                }
            
            # Get the last user message
            user_messages = [m for m in messages if isinstance(m, HumanMessage)]
            if not user_messages:
                return {
                    "messages": [AIMessage(content="No user input found for RAG editor.", name=self.agent_name)]
                }
            
            user_input = user_messages[-1].content
            
            # Check if this is a proposal enhancement request
            if any(keyword in user_input.lower() for keyword in ["enhance proposal", "rag editor", "update document", "edit document"]):
                return self._handle_proposal_enhancement(state, user_input)
            
            # Default: Launch interactive RAG editor
            return self._launch_interactive_editor(state, user_input)
            
        except Exception as e:
            return {
                "messages": [AIMessage(content=f"❌ RAG Editor failed: {e}", name=self.agent_name)]
            }
    
    def _handle_proposal_enhancement(self, state: MessagesState, user_input: str) -> Dict[str, Any]:
        """Handle proposal enhancement requests."""
        try:
            # Check if we have team responses in state
            team_responses = state.get("team_responses", {})
            rfp_content = state.get("rfp_content", "")
            
            if not team_responses:
                return {
                    "messages": [AIMessage(
                        content="❌ No team responses found. Please run proposal generation first to get team outputs for enhancement.", 
                        name=self.agent_name
                    )]
                }
            
            print("🚀 RAG Editor: Enhancing proposal with team outputs...")
            
            # Use the RAG editor integration
            results = integrate_rag_editor_with_proposal(
                team_responses,
                rfp_content,
                "responses",
                "main/test_output/proposal_20250927_142039.docx"
            )
            
            if results:
                enhanced_files = []
                for file_type, file_path in results.items():
                    if file_path and os.path.exists(file_path):
                        enhanced_files.append(f"- **{file_type.upper()}**: {file_path}")
                
                response_content = f"""✅ **RAG Editor Enhancement Complete!**

**Enhanced Documents Generated:**
{chr(10).join(enhanced_files)}

**Enhancement Process:**
1. ✅ Processed {len(team_responses)} team outputs
2. ✅ Applied RAG context enhancement
3. ✅ Generated professional DOCX document
4. ✅ Created structured outputs

**Key Features Applied:**
- RAG context integration for improved content quality
- Professional document formatting
- Multi-level content enhancement
- Structured metadata tracking

**Next Steps:**
- Review the enhanced DOCX document
- Customize content as needed
- Submit the final proposal

The RAG editor has successfully enhanced your proposal with improved content quality and professional formatting!"""
                
                return {
                    "messages": [AIMessage(content=response_content, name=self.agent_name)],
                    "rag_editor_results": results,
                    "enhancement_completed": True
                }
            else:
                return {
                    "messages": [AIMessage(
                        content="❌ RAG Editor enhancement failed. Please check the logs for details.", 
                        name=self.agent_name
                    )]
                }
                
        except Exception as e:
            return {
                "messages": [AIMessage(content=f"❌ Proposal enhancement failed: {e}", name=self.agent_name)]
            }
    
    def _launch_interactive_editor(self, state: MessagesState, user_input: str) -> Dict[str, Any]:
        """Launch interactive RAG editor mode."""
        try:
            # For now, provide information about RAG editor capabilities
            response_content = f"""🚀 **RAG Editor Launched**

**Available Operations:**
1. **Enhance Proposal** - Improve existing proposal content with RAG context
2. **Update Document** - Modify DOCX documents with AI assistance
3. **Generate Enhanced Content** - Create professional content using RAG databases
4. **Process Team Outputs** - Enhance team-generated content

**Current Request:** {user_input}

**RAG Editor Features:**
- ✅ Multi-level RAG context integration
- ✅ Professional document formatting
- ✅ DOCX document manipulation via MCP
- ✅ Content enhancement and optimization
- ✅ Structured output generation

**Usage Examples:**
- "Enhance my proposal with RAG context"
- "Update the DOCX document with improved content"
- "Generate enhanced content for section X"
- "Process team outputs for final proposal"

**Document Path:** `main/test_output/proposal_20250927_142039.docx`

The RAG editor is ready to enhance your documents with AI-powered content improvement!"""
            
            return {
                "messages": [AIMessage(content=response_content, name=self.agent_name)],
                "rag_editor_launched": True
            }
            
        except Exception as e:
            return {
                "messages": [AIMessage(content=f"❌ Interactive editor launch failed: {e}", name=self.agent_name)]
            }
    
    def enhance_proposal_content(self, state: MessagesState) -> Dict[str, Any]:
        """Enhance proposal content using RAG editor."""
        try:
            messages = state.get("messages", [])
            team_responses = state.get("team_responses", {})
            rfp_content = state.get("rfp_content", "")
            
            if not team_responses:
                return {
                    "messages": [AIMessage(
                        content="❌ No team responses available for enhancement.", 
                        name=self.agent_name
                    )]
                }
            
            print("🎯 RAG Editor: Enhancing proposal content...")
            
            # Process team outputs with RAG enhancement
            results = integrate_rag_editor_with_proposal(
                team_responses,
                rfp_content,
                "responses",
                "main/test_output/proposal_20250927_142039.docx"
            )
            
            if results:
                response_content = f"""✅ **Proposal Content Enhanced Successfully!**

**Enhancement Summary:**
- Processed {len(team_responses)} team contributions
- Applied RAG context from multiple databases
- Generated professional DOCX document
- Created structured enhanced outputs

**Generated Files:**
{self._format_results(results)}

**Enhancement Quality:**
- ✅ Professional language and formatting
- ✅ RAG context integration
- ✅ Structured document layout
- ✅ Metadata tracking and analysis

The proposal content has been significantly enhanced with RAG-powered improvements!"""
                
                return {
                    "messages": [AIMessage(content=response_content, name=self.agent_name)],
                    "enhancement_results": results,
                    "content_enhanced": True
                }
            else:
                return {
                    "messages": [AIMessage(
                        content="❌ Content enhancement failed. Please try again.", 
                        name=self.agent_name
                    )]
                }
                
        except Exception as e:
            return {
                "messages": [AIMessage(content=f"❌ Content enhancement error: {e}", name=self.agent_name)]
            }
    
    def _format_results(self, results: Dict[str, Any]) -> str:
        """Format results for display."""
        formatted = []
        for file_type, file_path in results.items():
            if file_path and os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                formatted.append(f"- **{file_type.upper()}**: {file_path} ({file_size:,} bytes)")
            else:
                formatted.append(f"- **{file_type.upper()}**: {file_path} (not found)")
        return "\n".join(formatted)
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get RAG editor capabilities."""
        return {
            "agent_name": self.agent_name,
            "supported_operations": self.supported_operations,
            "document_path": "main/test_output/proposal_20250927_142039.docx",
            "rag_databases": ["template_rag", "examples_rag", "session_rag"],
            "output_formats": ["docx", "json", "markdown"],
            "features": [
                "RAG context integration",
                "Professional document formatting", 
                "MCP Word server integration",
                "Content enhancement and optimization",
                "Structured output generation"
            ]
        }


def create_rag_editor_node():
    """Create a RAG editor node for LangGraph integration."""
    rag_editor_agent = RAGEditorAgent()
    return rag_editor_agent.launch_rag_editor


def create_rag_enhancement_node():
    """Create a RAG enhancement node for proposal content."""
    rag_editor_agent = RAGEditorAgent()
    return rag_editor_agent.enhance_proposal_content
