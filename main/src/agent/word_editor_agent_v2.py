"""
Word Document Editor Agent using Office-Word-MCP-Server

This agent handles Word document editing operations using the Office-Word-MCP-Server
via MCP (Model Context Protocol) client integration.
"""

import os
import re
import asyncio
import sys
from typing import Dict, Any, List, Optional
from pathlib import Path

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
    
    def _initialize_db(self):
        """Initialize RAG database for context."""
        try:
            if os.path.exists("session.db"):
                self.session_db = MilvusOps("session.db")
        except Exception as e:
            print(f"⚠️ Failed to initialize session database: {e}")
    
    def edit_document_section(self, state: MessagesState) -> Dict[str, Any]:
        """Main method to edit document sections."""
        try:
            # Run async operation in sync context
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in an async context, need to handle differently
                import nest_asyncio
                nest_asyncio.apply()
                result = asyncio.run(self._async_edit_document_section(state))
            else:
                result = loop.run_until_complete(self._async_edit_document_section(state))
            return result
        except Exception as e:
            return {
                "messages": [AIMessage(
                    content=f"❌ Error processing document: {str(e)}",
                    name="word_editor"
                )]
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
                        content="❌ Could not find a document path in your request. Please specify a .docx file.",
                        name="word_editor"
                    )]
                }
            
            # Apply the edit using MCP
            result_text = await self._process_document_edit(
                parsed_input["document_path"],
                parsed_input["instruction"]
            )
            
            return {
                "messages": [AIMessage(content=result_text, name="word_editor")]
            }
            
        except Exception as e:
            return {
                "messages": [AIMessage(
                    content=f"❌ Error processing document: {str(e)}",
                    name="word_editor"
                )]
            }
    
    async def _process_document_edit(self, doc_path: str, instruction: str) -> str:
        """Process document editing using MCP server."""
        try:
            # Ensure absolute path
            if not os.path.isabs(doc_path):
                doc_path = os.path.abspath(doc_path)
            
            print(f"🔧 Processing document: {doc_path}")
            print(f"📝 Instruction: {instruction}")
            
            # Start MCP server and create session
            server_cmd = [
                sys.executable, 
                "-c", 
                "import office_word_mcp_server; office_word_mcp_server.run_server()"
            ]
            
            server_params = StdioServerParameters(
                command=server_cmd[0],
                args=server_cmd[1:],
                env=None
            )
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # Check if document exists, create if needed
                    if not os.path.exists(doc_path):
                        print(f"📄 Document does not exist, creating: {doc_path}")
                        result = await session.call_tool(
                            "create_document",
                            {
                                "filename": doc_path,
                                "title": "Generated Document",
                                "author": "RFP Assistant"
                            }
                        )
                        print(f"✅ Document created: {result.content}")
                    
                    # Parse instruction and apply appropriate action
                    action_result = await self._apply_instruction(session, doc_path, instruction)
                    
                    # Get final document info
                    info_result = await session.call_tool("get_document_info", {"filename": doc_path})
                    
                    response = f"✅ Document edited successfully!\n\n"
                    response += f"📄 **Document:** {doc_path}\n"
                    response += f"📝 **Action Applied:** {action_result}\n\n"
                    response += f"📊 **Document Info:**\n{info_result.content[0].text}\n\n"
                    response += f"💡 The document has been updated based on your instruction."
                    
                    return response
                    
        except Exception as e:
            return f"❌ Error processing document with MCP: {str(e)}"
    
    async def _apply_instruction(self, session: ClientSession, doc_path: str, instruction: str) -> str:
        """Apply the specific instruction to the document."""
        instruction_lower = instruction.lower()
        
        try:
            # Determine action based on instruction
            if "add" in instruction_lower and ("heading" in instruction_lower or "title" in instruction_lower):
                # Extract heading text
                heading_text = self._extract_text_content(instruction, ["add", "heading", "title"])
                result = await session.call_tool(
                    "add_heading",
                    {
                        "filename": doc_path,
                        "text": heading_text or "New Heading",
                        "level": 1 if "title" in instruction_lower else 2
                    }
                )
                return f"Added heading: {heading_text}"
                
            elif "add" in instruction_lower and "paragraph" in instruction_lower:
                # Extract paragraph text
                paragraph_text = self._extract_text_content(instruction, ["add", "paragraph"])
                result = await session.call_tool(
                    "add_paragraph",
                    {
                        "filename": doc_path,
                        "text": paragraph_text or "New paragraph content"
                    }
                )
                return f"Added paragraph: {paragraph_text[:100]}..."
                
            elif "add" in instruction_lower and ("table" in instruction_lower):
                # Add table
                result = await session.call_tool(
                    "add_table",
                    {
                        "filename": doc_path,
                        "rows": 3,
                        "cols": 3,
                        "data": [["Header 1", "Header 2", "Header 3"], 
                                ["Row 1 Col 1", "Row 1 Col 2", "Row 1 Col 3"], 
                                ["Row 2 Col 1", "Row 2 Col 2", "Row 2 Col 3"]]
                    }
                )
                return "Added 3x3 table"
                
            elif "replace" in instruction_lower or "change" in instruction_lower:
                # Extract old and new text for replacement
                find_text, replace_text = self._extract_replacement_text(instruction)
                if find_text and replace_text:
                    result = await session.call_tool(
                        "search_and_replace",
                        {
                            "filename": doc_path,
                            "find_text": find_text,
                            "replace_text": replace_text
                        }
                    )
                    return f"Replaced '{find_text}' with '{replace_text}'"
                else:
                    # Add as new content if replacement fails
                    content = self._extract_text_content(instruction, ["replace", "change", "with"])
                    result = await session.call_tool(
                        "add_paragraph",
                        {"filename": doc_path, "text": content}
                    )
                    return f"Added new content: {content}"
                    
            else:
                # Default: add as paragraph
                content = instruction.replace("add", "").replace("insert", "").strip()
                if len(content) < 10:
                    content = f"Content based on instruction: {instruction}"
                    
                result = await session.call_tool(
                    "add_paragraph",
                    {"filename": doc_path, "text": content}
                )
                return f"Added content: {content[:100]}..."
                
        except Exception as e:
            # Fallback: add instruction as paragraph
            result = await session.call_tool(
                "add_paragraph",
                {"filename": doc_path, "text": f"Note: {instruction}"}
            )
            return f"Added instruction as note: {instruction}"
    
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
                    "instruction": match.group(2).strip()
                }
        
        # If no pattern matches, try to find any file path
        path_match = re.search(r'([^\s]+\.docx?)', user_input, re.IGNORECASE)
        if path_match:
            path = path_match.group(1)
            instruction = user_input.replace(path, "").strip()
            return {
                "document_path": path,
                "instruction": instruction
            }
        
        return {
            "document_path": "",
            "instruction": user_input
        }
    
    def _extract_text_content(self, instruction: str, stop_words: List[str]) -> str:
        """Extract meaningful text content from instruction."""
        # Remove stop words and clean up
        text = instruction
        for word in stop_words:
            text = text.replace(word, " ").replace(word.title(), " ")
        
        # Clean up whitespace
        text = " ".join(text.split())
        
        # If text is too short, use original instruction
        if len(text.strip()) < 3:
            text = instruction
            
        return text.strip()
    
    def _extract_replacement_text(self, instruction: str) -> tuple:
        """Extract old and new text for replacement operations."""
        patterns = [
            r"replace (.+?) with (.+)",
            r"change (.+?) to (.+)",
            r"update (.+?) with (.+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, instruction, re.IGNORECASE)
            if match:
                return match.group(1).strip().strip('"\''), match.group(2).strip().strip('"\'')
        
        return None, None