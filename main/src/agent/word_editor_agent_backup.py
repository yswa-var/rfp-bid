"""
Word Document Editor Agent using Office-Word-MCP-Server

This agent handles Word document editing operations using the Office-Word-MCP-Server
via MCP (Model Context Protocol) client integration.
"""

import os
import re
import asyncio
import subprocess
import sys
import json
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import nest_asyncio

# Apply nest_asyncio to handle event loop conflicts
nest_asyncio.apply()

from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import PromptTemplate

# MCP Client imports
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    print("⚠️ MCP client not available. Install with: pip install mcp")
    MCP_AVAILABLE = False

from .state import MessagesState
from .milvus_ops import MilvusOps


class WordEditorAgent:
    """Agent for editing Word documents using Office-Word-MCP-Server."""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            temperature=0.1,
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        self.session_db = None
        self._initialize_db()
        self.mcp_session = None
        self.server_process = None
    
    def _initialize_db(self):
        """Initialize RAG database for context."""
        try:
            if os.path.exists("session.db"):
                self.session_db = MilvusOps("session.db")
        except Exception as e:
            print(f"⚠️ Could not initialize RAG database: {e}")
    
    async def _connect_to_word_server(self) -> bool:
        """Connect to the Office-Word-MCP-Server."""
        try:
            if not MCP_AVAILABLE:
                print("❌ MCP client not available")
                return False
            
            # Find the word_mcp_server.py script from the installed package
            import site
            import glob
            
            # Look for the server script in site-packages
            possible_paths = []
            for site_dir in site.getsitepackages():
                server_path = os.path.join(site_dir, "word_mcp_server.py")
                if os.path.exists(server_path):
                    possible_paths.append(server_path)
            
            # Also check the Office-Word-MCP-Server repository structure
            repo_server_path = os.path.join(os.getcwd(), "..", "..", "word_mcp_server.py")
            if os.path.exists(repo_server_path):
                possible_paths.append(repo_server_path)
                
            # Try using uvx/office-word-mcp-server command
            server_cmd = ["python", "-m", "office_word_mcp_server"]
            
            if not possible_paths:
                # Fallback to package run_server function
                print("🔧 Using office_word_mcp_server.run_server")
                # This will run the server in a subprocess
                import office_word_mcp_server
                server_cmd = [sys.executable, "-c", "import office_word_mcp_server; office_word_mcp_server.run_server()"]
            else:
                print(f"🔧 Using Word MCP server from: {possible_paths[0]}")
                server_cmd = [sys.executable, possible_paths[0]]
            
            # Create MCP client session with stdio transport
            server_params = StdioServerParameters(
                command=server_cmd[0],
                args=server_cmd[1:] if len(server_cmd) > 1 else [],
                env=None
            )
            
            print(f"🚀 Starting MCP server with command: {' '.join(server_cmd)}")
            
            # Create stdio client context
            self.mcp_session = await stdio_client(server_params).__aenter__()
            await self.mcp_session.initialize()
            
            print("✅ Connected to Office-Word-MCP-Server successfully")
            
            # List available tools
            tools_result = await self.mcp_session.list_tools()
            available_tools = [tool.name for tool in tools_result.tools]
            print(f"📋 Available tools: {', '.join(available_tools[:5])}{'...' if len(available_tools) > 5 else ''}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect to Word MCP server: {e}")
            return False
    
    def edit_document_section(self, state: MessagesState) -> Dict[str, Any]:
        """Main method to edit Word document sections based on Q&A."""
        try:
            # Check if we're already in an event loop
            try:
                import asyncio
                loop = asyncio.get_running_loop()
                # We're in a running loop, use create_task
                import nest_asyncio
                nest_asyncio.apply()
                return asyncio.run(self._async_edit_document_section(state))
            except RuntimeError:
                # No running loop, safe to use asyncio.run
                return asyncio.run(self._async_edit_document_section(state))
        except ImportError:
            # nest_asyncio not available, fallback to sync operation
            return self._sync_edit_document_section(state)
        except Exception as e:
            return {
                "messages": [AIMessage(
                    content=f"❌ Error in Word Editor: {str(e)}",
                    name="word_editor"
                )]
            }
    
    def _sync_edit_document_section(self, state: MessagesState) -> Dict[str, Any]:
        """Synchronous fallback for document editing."""
        messages = state.get("messages", [])
        if not messages:
            return {
                "messages": [AIMessage(
                    content="Please provide a document path and editing instructions.",
                    name="word_editor"
                )]
            }
        
        # Get the latest user message
        user_message = None
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                user_message = msg.content
                break
        
        if not user_message:
            return {
                "messages": [AIMessage(
                    content="No user message found to process.",
                    name="word_editor"
                )]
            }
        
        # Parse the user input
        parsed_input = self._parse_edit_request(user_message)
        
        if not parsed_input["document_path"]:
            return {
                "messages": [AIMessage(
                    content="❌ Please provide a valid document path. Format: 'Edit document [path] - [your instruction]'",
                    name="word_editor"
                )]
            }
        
        # For now, return a message indicating the operation would be performed
        doc_path = parsed_input["document_path"]
        instruction = parsed_input["instruction"]
        
        if not os.path.exists(doc_path):
            return {
                "messages": [AIMessage(
                    content=f"❌ Document not found: {doc_path}",
                    name="word_editor"
                )]
            }
        
        result = f"✅ Word Editor Agent Ready!\n\n"
        result += f"📄 Document: {doc_path}\n"
        result += f"📝 Instruction: {instruction}\n\n"
        result += f"🔧 The following operations would be performed:\n"
        result += f"1. Connect to Office Word MCP Server\n"
        result += f"2. Read document content using MCP tools\n"
        result += f"3. Use AI to find relevant section matching your query\n"
        result += f"4. Generate improved content using RAG context\n"
        result += f"5. Apply changes using MCP search_and_replace\n"
        result += f"6. Create backup and report detailed results\n\n"
        result += f"💡 To enable full functionality, ensure the MCP server is properly configured."
        
        return {
            "messages": [AIMessage(content=result, name="word_editor")]
        }
    
    async def _async_edit_document_section(self, state: MessagesState) -> Dict[str, Any]:
        """Async method to handle MCP server communication."""
        if not MCP_AVAILABLE:
            return {
                "messages": [AIMessage(
                    content="❌ MCP client not available. Install with: pip install mcp",
                    name="word_editor"
                )]
            }
        
        try:
            messages = state.get("messages", [])
            if not messages:
                return {
                    "messages": [AIMessage(
                        content="Please provide a document path and editing instructions.",
                        name="word_editor"
                    )]
                }
            
            # Get the latest user message
            user_message = None
            for msg in reversed(messages):
                if isinstance(msg, HumanMessage):
                    user_message = msg.content
                    break
            
            if not user_message:
                return {
                    "messages": [AIMessage(
                        content="No user message found to process.",
                        name="word_editor"
                    )]
                }
            
            # Parse the user input
            parsed_input = self._parse_edit_request(user_message)
            
            if not parsed_input["document_path"]:
                return {
                    "messages": [AIMessage(
                        content="❌ Please provide a valid document path. Format: 'Edit document [path] - [your question/instruction]'",
                        name="word_editor"
                    )]
                }
            
            # Process the document editing using MCP
            result = await self._process_document_edit_mcp(
                parsed_input["document_path"],
                parsed_input["question"],
                parsed_input["instruction"]
            )
            
            return {
                "messages": [AIMessage(content=result, name="word_editor")]
            }
            
        finally:
            # Clean up resources
            await self.exit_stack.aclose()
    
    async def _process_document_edit_mcp(self, doc_path: str, question: str, instruction: str) -> str:
        """Process document editing using MCP server."""
        try:
            # Check if document exists
            if not os.path.exists(doc_path):
                return f"❌ Document not found: {doc_path}"
            
            session = await self._connect_to_word_server()
            
            print(f"📄 Processing document: {doc_path}")
            print(f"📝 Question/Instruction: {question}")
            
            # Get document content using MCP
            result = await session.call_tool(
                "get_document_text",
                arguments={"filename": doc_path}
            )
            
            doc_text = ""
            if result.content:
                for content_item in result.content:
                    if hasattr(content_item, 'text'):
                        doc_text += content_item.text
                    else:
                        doc_text += str(content_item)
            
            if not doc_text:
                return f"❌ Could not read document content from: {doc_path}"
            
            # Find relevant section using AI
            relevant_section = self._find_relevant_section(doc_text, question)
            
            if not relevant_section:
                return f"❌ Could not find relevant section for: {question}"
            
            # Generate the edit based on the instruction and context
            edit_content = self._generate_edit_content(
                relevant_section, question, instruction, doc_text
            )
            
            # Apply the edit to the document using MCP
            edit_result = await self._apply_edit_to_document_mcp(
                session, doc_path, relevant_section, edit_content
            )
            
            return edit_result
            
        except Exception as e:
            return f"❌ Error processing document with MCP: {str(e)}"
    
    async def _apply_edit_to_document_mcp(self, session, doc_path: str, section: Dict[str, Any], new_content: str) -> str:
        """Apply the edit to the actual Word document using MCP."""
        try:
            # Create a backup first
            backup_path = doc_path.replace('.docx', '_backup.docx')
            if not os.path.exists(backup_path):
                try:
                    result = await session.call_tool(
                        "copy_document",
                        arguments={
                            "source_filename": doc_path,
                            "destination_filename": backup_path
                        }
                    )
                    print(f"📋 Backup created: {backup_path}")
                except Exception as e:
                    print(f"⚠️ Could not create backup: {e}")
            
            # Use search and replace to update the content
            old_text = section["original_text"]
            
            result = await session.call_tool(
                "search_and_replace",
                arguments={
                    "filename": doc_path,
                    "find_text": old_text,
                    "replace_text": new_content
                }
            )
            
            # Check if the operation was successful
            success = False
            if result.content:
                for content_item in result.content:
                    content_str = str(content_item).lower()
                    if "success" in content_str or "replaced" in content_str:
                        success = True
                        break
            
            if success:
                response = f"✅ Successfully updated document section!\n\n"
                response += f"📄 Document: {doc_path}\n"
                if os.path.exists(backup_path):
                    response += f"📋 Backup: {backup_path}\n"
                response += f"\n**Original Text:**\n{old_text[:200]}{'...' if len(old_text) > 200 else ''}\n\n"
                response += f"**Updated Text:**\n{new_content[:200]}{'...' if len(new_content) > 200 else ''}\n\n"
                response += f"💡 The section has been updated based on your instruction."
                
                return response
            else:
                # Try partial matching if exact replacement fails
                words = old_text.split()
                if len(words) > 10:
                    partial_text = " ".join(words[:10])
                    result = await session.call_tool(
                        "search_and_replace",
                        arguments={
                            "filename": doc_path,
                            "find_text": partial_text,
                            "replace_text": new_content
                        }
                    )
                    
                    # Check success again
                    partial_success = False
                    if result.content:
                        for content_item in result.content:
                            content_str = str(content_item).lower()
                            if "success" in content_str or "replaced" in content_str:
                                partial_success = True
                                break
                    
                    if partial_success:
                        return f"✅ Partially updated document section (first part matched).\n📄 Document: {doc_path}"
                
                return f"⚠️ Could not find exact text match for replacement. The document structure may have changed.\nOriginal text preview: {old_text[:100]}..."
        
        except Exception as e:
            return f"❌ Error applying edit to document: {str(e)}"
    
    def _parse_edit_request(self, user_input: str) -> Dict[str, str]:
        """Parse user input to extract document path and editing instructions."""
        
        # Try different patterns to extract document path and instructions
        patterns = [
            r"edit document (.+?) - (.+)",
            r"edit (.+?) section (.+)",
            r"modify document (.+?) (.+)",
            r"update (.+?) with (.+)",
            r"change in (.+?) the (.+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, user_input, re.IGNORECASE)
            if match:
                return {
                    "document_path": match.group(1).strip(),
                    "question": match.group(2).strip(),
                    "instruction": match.group(2).strip()
                }
        
        # If no pattern matches, try to find any file path
        path_match = re.search(r'([^\s]+\.docx?)', user_input, re.IGNORECASE)
        if path_match:
            path = path_match.group(1)
            instruction = user_input.replace(path, "").strip()
            return {
                "document_path": path,
                "question": instruction,
                "instruction": instruction
            }
        
        return {
            "document_path": "",
            "question": user_input,
            "instruction": user_input
        }
    
    def _find_relevant_section(self, doc_text: str, question: str) -> Optional[Dict[str, Any]]:
        """Find the most relevant section in the document for the question."""
        
        # Split document into paragraphs
        paragraphs = doc_text.split('\n\n')
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        # Use LLM to find most relevant section
        prompt = PromptTemplate(
            input_variables=["question", "paragraphs"],
            template="""
You are analyzing a document to find the most relevant section for editing.

Question/Instruction: {question}

Document Paragraphs:
{paragraphs}

Find the paragraph that is most relevant to the question. Return:
1. The paragraph number (0-based index)
2. The exact paragraph text
3. A brief explanation of why it's relevant

Format your response as:
PARAGRAPH_INDEX: [number]
PARAGRAPH_TEXT: [exact text]
RELEVANCE: [explanation]

If no relevant paragraph is found, respond with:
PARAGRAPH_INDEX: -1
"""
        )
        
        # Prepare paragraphs text with indices
        paragraphs_text = ""
        for i, para in enumerate(paragraphs):
            paragraphs_text += f"[{i}] {para}\n\n"
        
        try:
            response = self.llm.invoke(prompt.format(
                question=question,
                paragraphs=paragraphs_text
            ))
            
            # Parse response
            response_text = response.content
            
            # Extract paragraph index
            index_match = re.search(r'PARAGRAPH_INDEX:\s*(-?\d+)', response_text)
            if not index_match:
                return None
            
            para_index = int(index_match.group(1))
            if para_index == -1 or para_index >= len(paragraphs):
                return None
            
            # Extract paragraph text
            text_match = re.search(r'PARAGRAPH_TEXT:\s*(.+?)(?=RELEVANCE:|$)', response_text, re.DOTALL)
            para_text = text_match.group(1).strip() if text_match else paragraphs[para_index]
            
            return {
                "index": para_index,
                "text": para_text,
                "original_text": paragraphs[para_index]
            }
            
        except Exception as e:
            print(f"⚠️ Error finding relevant section: {e}")
            return None
    
    def _generate_edit_content(self, section: Dict[str, Any], question: str, 
                             instruction: str, full_doc_text: str) -> str:
        """Generate new content for the section based on the instruction."""
        
        # Get additional context from RAG if available
        rag_context = ""
        if self.session_db:
            try:
                rag_results = self.session_db.query_database(question, k=3)
                if rag_results:
                    rag_context = "\n".join([r['content'] for r in rag_results])
            except Exception as e:
                print(f"⚠️ RAG query failed: {e}")
        
        prompt = PromptTemplate(
            input_variables=["original_text", "instruction", "context", "rag_context"],
            template="""
You are editing a Word document section based on user instructions.

Original Section Text:
{original_text}

User Instruction:
{instruction}

Document Context (surrounding text):
{context}

Additional Context from Knowledge Base:
{rag_context}

Generate the improved/edited version of this section. Requirements:
1. Keep the same general structure and format
2. Incorporate the user's requested changes
3. Maintain professional tone appropriate for business documents
4. Ensure consistency with the rest of the document
5. If adding new information, base it on the knowledge base context when available

Return ONLY the edited text, no explanations or markers.
"""
        )
        
        try:
            response = self.llm.invoke(prompt.format(
                original_text=section["text"],
                instruction=instruction,
                context=full_doc_text[:1000] + "..." if len(full_doc_text) > 1000 else full_doc_text,
                rag_context=rag_context[:500] + "..." if len(rag_context) > 500 else rag_context
            ))
            
            return response.content.strip()
            
        except Exception as e:
            print(f"⚠️ Error generating edit content: {e}")
            return section["text"]  # Return original if generation fails