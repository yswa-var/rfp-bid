#!/usr/bin/env python3
"""
AI Dynamic Editor with LangGraph RAG Integration
Combines the existing AI Dynamic Editor with your RFP-bid LangGraph QA system
"""

import json
import subprocess
import sys
import os
import re
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Add the main RFP system to path
rfp_main_path = '/home/arun/Pictures/rfp-bid/main'
rfp_src_path = '/home/arun/Pictures/rfp-bid/main/src'

if os.path.exists(rfp_src_path):
    sys.path.insert(0, rfp_src_path)
    # Set PYTHONPATH environment variable as well
    os.environ['PYTHONPATH'] = rfp_src_path + ':' + os.environ.get('PYTHONPATH', '')
    print(f"✅ Added RFP system path: {rfp_src_path}")
else:
    print(f"❌ RFP system path not found: {rfp_src_path}")

# Import your existing LangGraph system
try:
    from agent.proposal_rag_coordinator import ProposalRAGCoordinator
    RAG_AVAILABLE = True
    print("✅ RAG system imported successfully")
except ImportError as e:
    print(f"❌ Failed to import RAG system: {e}")
    RAG_AVAILABLE = False

load_dotenv()

class AIDynamicEditorWithRAG:
    """Enhanced AI Dynamic Editor with LangGraph RAG integration"""
    
    def __init__(self, document_name="proposal_20250927_142039.docx"):
        self.document_path = f"/home/arun/Pictures/rfp-bid/Mcp_client_word/{document_name}"
        self.server_path = "/home/arun/Pictures/rfp-bid/Mcp_client_word/Office-Word-MCP-Server/word_mcp_server.py"
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.server_process = None
        self.tools = []
        self.rag_available = False
        self.rag_coordinator = None
        
        # Initialize RAG Coordinator from your RFP system if available
        if RAG_AVAILABLE:
            print("🔧 Initializing RAG systems...")
            try:
                self.rag_coordinator = ProposalRAGCoordinator()
                self.rag_available = True
                # Check RAG database status
                self.check_rag_status()
            except Exception as e:
                print(f"⚠️ RAG initialization failed: {e}")
                self.rag_available = False
        else:
            print("⚠️ RAG system not available - will use basic AI generation")
        
    def check_rag_status(self):
        """Check status of RAG databases"""
        if not self.rag_available or not self.rag_coordinator:
            return False
            
        try:
            status = self.rag_coordinator.get_database_status()
            ready_count = sum(status.values())
            
            print(f"📊 RAG Database Status ({ready_count}/3 ready):")
            print(f"- Template RAG: {'✅ Ready' if status['template_ready'] else '❌ Not available'}")
            print(f"- Examples RAG: {'✅ Ready' if status['examples_ready'] else '❌ Not available'}")  
            print(f"- Session RAG: {'✅ Ready' if status['session_ready'] else '⚠️ No current RFP'}")
            
            self.rag_available = ready_count > 0
            return self.rag_available
            
        except Exception as e:
            print(f"⚠️ RAG system check failed: {e}")
            self.rag_available = False
            return False
    
    def start_mcp_server(self):
        """Start MCP server and initialize connection"""
        try:
            print(f"🚀 Starting AI Dynamic Editor with RAG for: {os.path.basename(self.document_path)}")
            self.server_process = subprocess.Popen(
                [sys.executable, self.server_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Initialize MCP connection
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "AI Dynamic Editor with RAG", "version": "1.0.0"}
                }
            }
            
            self.server_process.stdin.write(json.dumps(init_request) + "\n")
            self.server_process.stdin.flush()
            
            response_line = self.server_process.stdout.readline()
            if response_line:
                response = json.loads(response_line.strip())
                if "result" in response:
                    initialized = {"jsonrpc": "2.0", "method": "notifications/initialized"}
                    self.server_process.stdin.write(json.dumps(initialized) + "\n")
                    self.server_process.stdin.flush()
                    
                    # Load available tools
                    self.load_available_tools()
                    
                    print("✅ MCP Server ready for AI-powered operations with RAG")
                    return True
            return False
        except Exception as e:
            print(f"❌ Failed to start MCP server: {e}")
            return False
    
    def load_available_tools(self):
        """Load and display available MCP tools"""
        try:
            tools_request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
            self.server_process.stdin.write(json.dumps(tools_request) + "\n")
            self.server_process.stdin.flush()
            
            response_line = self.server_process.stdout.readline()
            if response_line:
                response = json.loads(response_line.strip())
                if "result" in response and "tools" in response["result"]:
                    self.tools = response["result"]["tools"]
                    
                    # Find search-related tools
                    search_tools = [t["name"] for t in self.tools if "search" in t["name"].lower() or "find" in t["name"].lower()]
                    print(f"🔧 Available search tools: {', '.join(search_tools)}")
                    print(f"📊 Total MCP tools loaded: {len(self.tools)}")
                    return True
            return False
        except Exception as e:
            print(f"❌ Failed to load tools: {e}")
            return False
    
    def call_mcp_tool(self, tool_name, arguments=None):
        """Call MCP tool directly"""
        try:
            request = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": tool_name}
            }
            
            if arguments:
                request["params"]["arguments"] = arguments
            
            self.server_process.stdin.write(json.dumps(request) + "\n")
            self.server_process.stdin.flush()
            
            response_line = self.server_process.stdout.readline()
            if response_line:
                response = json.loads(response_line.strip())
                if "result" in response:
                    return response["result"]
            return None
        except Exception as e:
            print(f"❌ MCP tool call failed: {e}")
            return None
    
    def search_document(self, search_text):
        """Search document and return ALL matches with context - USER CHOICE VERSION"""
        search_result = self.call_mcp_tool("find_text_in_document", {
            "filename": self.document_path,
            "text_to_find": search_text,
            "match_case": False,  # Make search case-insensitive
            "whole_word": False   # Allow partial matches
        })
        
        if search_result and "content" in search_result:
            content = search_result["content"][0]["text"]
            print(f"🔍 Debug - Search result: {content[:300]}...")
            
            try:
                # Try to parse as JSON
                matches_data = json.loads(content)
                
                if isinstance(matches_data, dict) and "occurrences" in matches_data:
                    # Get full document text for context
                    full_text_result = self.call_mcp_tool("get_document_text", {
                        "filename": self.document_path
                    })
                    
                    if full_text_result and "content" in full_text_result:
                        full_text = full_text_result["content"][0]["text"]
                        lines = full_text.split('\n')
                        
                        # Process ALL matches, not just headers
                        all_matches = []
                        for match in matches_data.get("occurrences", []):
                            paragraph_index = match.get("paragraph_index", -1)
                            print(f"🔍 Debug - Processing match at paragraph_index: {paragraph_index}")
                            
                            if 0 <= paragraph_index < len(lines):
                                match_text = lines[paragraph_index].strip()
                                print(f"🔍 Debug - Extracted line: '{match_text}'")
                                
                                # If the line is empty, try to get it from the match context
                                if not match_text and "context" in match:
                                    match_text = match["context"].strip()
                                    print(f"🔍 Debug - Using context as match_text: '{match_text}'")
                                
                                # Classify match type for user information
                                match_type = self._classify_match_type(match_text)
                                
                                # Get context (10 lines before and after for better context)
                                context_start = max(0, paragraph_index - 10)
                                context_end = min(len(lines), paragraph_index + 15)
                                context_lines = []
                                
                                for j in range(context_start, context_end):
                                    if j < len(lines):
                                        line = lines[j].strip()
                                        if line:  # Only include non-empty lines
                                            if j == paragraph_index:
                                                # Highlight the matching line
                                                highlighted_line = line.replace(search_text, f">>> **{search_text}** <<<")
                                                context_lines.append(f"[LINE {j+1}] {highlighted_line}")
                                            else:
                                                context_lines.append(f"[LINE {j+1}] {line}")
                                
                                context = '\n'.join(context_lines)
                                
                                # Check if this is likely a section header
                                is_section_header = self._is_likely_section_header(lines, paragraph_index, search_text)
                                
                                all_matches.append({
                                    "line_number": paragraph_index + 1,
                                    "context": context,
                                    "match_text": search_text,
                                    "position": match.get("position", 0),
                                    "is_section_header": is_section_header,
                                    "actual_line": match_text if match_text else match.get("context", "").strip(),
                                    "paragraph_index": paragraph_index,
                                    "match_type": match_type
                                })
                            else:
                                print(f"🔍 Debug - paragraph_index {paragraph_index} out of range (total lines: {len(lines)})")
                        
                        return all_matches
                elif isinstance(matches_data, dict) and "matches" in matches_data:
                    return matches_data["matches"]
                elif isinstance(matches_data, list):
                    return matches_data
                    
            except json.JSONDecodeError:
                # If not JSON, treat as plain text result
                print(f"📄 Plain text result: {content}")
                return []
        
        return []
    
    def _classify_match_type(self, match_text):
        """Classify the type of match for user information"""
        match_lower = match_text.lower()
        
        # Check for different types of content
        if any(marker in match_lower for marker in ['#', 'heading', 'section', 'chapter']):
            return "Header"
        elif match_lower.startswith('•') or match_lower.startswith('- '):
            return "List Item"
        elif 'table of contents' in match_lower or 'toc' in match_lower:
            return "TOC Reference"
        elif len(match_text.split()) > 10:
            return "Content Paragraph"
        else:
            return "Text Fragment"
    
    def _is_likely_section_header(self, paragraphs, para_index, search_text):
        """Determine if a match is likely a section header vs just a reference"""
        if para_index >= len(paragraphs):
            return False
            
        line = paragraphs[para_index].strip()
        
        # Check if it's preceded by whitespace (indented - likely TOC)
        if line.startswith('   ') or line.startswith('\t') or line.startswith('• '):
            return False  # Likely a table of contents item
        
        # Check if it's a standalone header (line contains mostly the search text)
        if len(line) - len(search_text) < 20:  # Allow some extra text
            return True
            
        # Check if it's followed by descriptive content
        if para_index + 1 < len(paragraphs):
            next_line = paragraphs[para_index + 1].strip()
            # If next line is descriptive text (not bullets/numbers), it's likely a header
            if next_line and not next_line.startswith('•') and not next_line.startswith('-') and not next_line.startswith('   '):
                return True
                
        return False
    
    def query_rag_for_context(self, query_text, context_type="general"):
        """Query your LangGraph RAG system for relevant context"""
        if not self.rag_available or not self.rag_coordinator:
            print("⚠️ RAG system not available, using basic AI generation")
            return self.generate_basic_content(query_text, context_type)
        
        try:
            print(f"🔍 Querying RAG system for: {query_text}")
            
            # Query all RAG databases for context
            contexts = self.rag_coordinator.query_all_rags(query_text, k=3)
            
            # Format the contexts for AI processing
            formatted_context = self._format_rag_contexts(contexts)
            
            return formatted_context
            
        except Exception as e:
            print(f"❌ RAG query failed: {e}")
            return self.generate_basic_content(query_text, context_type)
    
    def _format_rag_contexts(self, contexts):
        """Format RAG contexts for AI processing"""
        formatted = {
            "template_context": [],
            "examples_context": [],
            "session_context": [],
            "summary": ""
        }
        
        if not contexts:
            return formatted
        
        # Process template context
        if "template_context" in contexts:
            for result in contexts["template_context"][:2]:
                if isinstance(result, dict):
                    formatted["template_context"].append({
                        "content": result.get('content', result.get('preview', str(result)))[:500],
                        "source": result.get('source_file', 'Template'),
                        "relevance": result.get('accuracy', 0)
                    })
        
        # Process examples context  
        if "examples_context" in contexts:
            for result in contexts["examples_context"][:2]:
                if isinstance(result, dict):
                    formatted["examples_context"].append({
                        "content": result.get('content', result.get('preview', str(result)))[:500],
                        "source": result.get('source_file', 'Example'),
                        "relevance": result.get('accuracy', 0)
                    })
        
        # Process session context
        if "session_context" in contexts:
            for result in contexts["session_context"][:2]:
                if isinstance(result, dict):
                    formatted["session_context"].append({
                        "content": result.get('content', result.get('preview', str(result)))[:500],
                        "source": result.get('source_file', 'Current RFP'),
                        "relevance": result.get('accuracy', 0)
                    })
        
        # Create summary
        total_contexts = len(formatted["template_context"]) + len(formatted["examples_context"]) + len(formatted["session_context"])
        formatted["summary"] = f"Found {total_contexts} relevant contexts from RAG databases"
        
        return formatted
    
    def generate_enhanced_content_with_rag(self, query_text, context_type, document_context=""):
        """Generate content using RAG context and AI"""
        try:
            # Get RAG context
            rag_contexts = self.query_rag_for_context(query_text, context_type)
            
            # Build comprehensive prompt with RAG context
            prompt = f"""Generate professional content for a business document based on the following context:

**Request**: {query_text}
**Context Type**: {context_type}
**Document Context**: {document_context[:200]}

**RAG KNOWLEDGE BASE CONTEXT:**

**Template Context (Structure/Format):**
{self._format_context_section(rag_contexts.get('template_context', []))}

**Examples Context (Previous Similar Content):**
{self._format_context_section(rag_contexts.get('examples_context', []))}

**Session Context (Current RFP/Project):**
{self._format_context_section(rag_contexts.get('session_context', []))}

**INSTRUCTIONS:**
- Generate professional business content suitable for RFP responses
- Use the template context for proper structure and format
- Incorporate relevant examples from similar documents
- Align with current RFP/project requirements from session context
- Write in professional proposal language
- Make it specific and actionable, not generic
- Format as clean text ready to insert into a document
- DO NOT include line numbers like [LINE 123] or similar formatting
- DO NOT include technical formatting artifacts
- Generate clean, readable content only

**GENERATED CONTENT:**"""
            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert business proposal writer with access to a comprehensive knowledge base."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=800
            )
            
            generated_content = response.choices[0].message.content.strip()
            
            # Clean the content - remove line numbers and formatting artifacts
            cleaned_content = self._clean_generated_content(generated_content)
            
            print("📝 Generated Content with RAG Context:")
            print("-" * 50)
            print(generated_content)  # Show original for debugging
            print("-" * 50)
            
            return cleaned_content
            
        except Exception as e:
            print(f"❌ Enhanced content generation failed: {e}")
            return self.generate_basic_content(query_text, context_type)
    
    def _format_context_section(self, context_list):
        """Format a context section for the prompt"""
        if not context_list:
            return "No relevant context available."
        
        formatted = []
        for i, ctx in enumerate(context_list, 1):
            relevance = ctx.get('relevance', 0)
            source = ctx.get('source', 'Unknown')
            content = ctx.get('content', '')[:300]
            
            formatted.append(f"**Source {i}:** {source} (Relevance: {relevance:.1%})\n{content}...")
        
        return "\n\n".join(formatted)
    
    def _clean_generated_content(self, content):
        """Clean generated content by removing line numbers and formatting artifacts"""
        import re
        
        # Remove line number patterns like [LINE 175], [LINE 176], etc.
        cleaned = re.sub(r'\[LINE \d+\]\s*', '', content)
        
        # Remove bullet points that are just line references
        cleaned = re.sub(r'•\s*\[LINE \d+\].*?\n', '', cleaned)
        
        # Remove excessive newlines
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        
        # Remove any remaining line reference artifacts
        cleaned = re.sub(r'LINE \d+[:\s]*', '', cleaned)
        
        # Clean up any double spaces
        cleaned = re.sub(r'\s{2,}', ' ', cleaned)
        
        return cleaned.strip()
    
    def generate_basic_content(self, query_text, context_type):
        """Fallback content generation without RAG"""
        try:
            prompt = f"""Generate professional content for: {query_text}
            Context: {context_type}
            
            Requirements:
            - Professional business language
            - Specific and actionable content
            - Suitable for RFP responses
            - 3-4 detailed points"""
            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a professional business content writer."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"❌ Basic content generation failed: {e}")
            return f"• Professional expertise in {query_text}\n• Industry best practices implementation\n• Proven track record of success\n• Commitment to quality delivery"
    
    def find_command(self, search_text):
        """Find text in document with context - ENHANCED VERSION"""
        print(f"\n🔍 SEARCHING FOR: '{search_text}'")
        print("=" * 60)
        
        matches = self.search_document(search_text)
        
        if matches:
            print(f"📍 Found {len(matches)} match(es) for '{search_text}':")
            print("=" * 60)
            
            # Categorize matches
            section_headers = []
            references = []
            
            for i, match in enumerate(matches, 1):
                is_header = match.get("is_section_header", False)
                actual_line = match.get("actual_line", "")
                
                print(f"\n🔍 Match {i} (line {match.get('line_number', 'unknown')}):")
                print(f"📄 Actual line: '{actual_line}'")
                print(f"🏷️  Type: {'📋 Section Header' if is_header else '📎 Reference/TOC'}")
                print("-" * 50)
                
                context = match.get("context", "No context available")
                print(context)
                print("-" * 50)
                
                if is_header:
                    section_headers.append((i, match))
                else:
                    references.append((i, match))
            
            # Help user choose the right match
            if section_headers and references:
                print(f"\n💡 ANALYSIS:")
                print(f"📋 Found {len(section_headers)} actual section header(s): {[f'Match {i}' for i, _ in section_headers]}")
                print(f"📎 Found {len(references)} reference(s)/TOC item(s): {[f'Match {i}' for i, _ in references]}")
                print(f"\n💡 TIP: Choose a section header (📋) to add content to the actual section.")
            
            print(f"\n🤖 Choose what to do:")
            print("   • Type a number (1-{}) to work with that specific match".format(len(matches)))
            print("   • Type 'add [content request]' - add RAG content to ALL matches")
            print("   • Type 'enhance' - enhance existing content")
            print("   • Type 'skip' - just show search results")
            print("   • Type 'search section' - try section-specific search")
            
            user_choice = input("Your choice: ").strip()
            
            # Handle numbered selection
            if user_choice.isdigit():
                choice_num = int(user_choice)
                if 1 <= choice_num <= len(matches):
                    selected_match = matches[choice_num - 1]
                    print(f"\n✅ Selected match {choice_num}")
                    print(f"📝 Line: {selected_match.get('actual_line', 'No line info')}")
                    print(f"🏷️  Type: {selected_match.get('is_section_header', 'Unknown')}")
                    
                    # Now ask what to do with the selected match
                    action = input("\nWhat would you like to do? (add [request]/enhance/view context): ").strip()
                    if action.lower().startswith('add '):
                        content_request = action[4:].strip()
                        self.add_rag_content_to_specific_match(selected_match, content_request, search_text)
                    elif action.lower() == 'enhance':
                        self.enhance_specific_match(selected_match, search_text)
                    elif action.lower() in ['view context', 'context']:
                        print(f"\n📄 Full context for match {choice_num}:")
                        print("=" * 60)
                        print(selected_match.get('context', 'No context available'))
                        print("=" * 60)
                else:
                    print(f"❌ Invalid selection. Please choose 1-{len(matches)}")
            elif user_choice.lower().startswith('add '):
                content_request = user_choice[4:].strip()
                self.add_rag_content_near_matches(matches, content_request, search_text)
            elif user_choice.lower() == 'enhance':
                self.enhance_existing_content(matches, search_text)
            elif user_choice.lower() == 'search section':
                self.search_for_actual_section(search_text)
            else:
                print("✅ Search completed")
        else:
            print(f"❌ No matches found for '{search_text}'")
            print(f"\n💡 Try searching for:")
            print(f"   • Part of the text: '{search_text.split()[-1] if ' ' in search_text else search_text[:5]}'")
            print(f"   • Without punctuation: '{search_text.replace('.', '').replace(',', '')}'")
            print(f"   • Just the number: '{search_text.split('.')[0] if '.' in search_text else search_text}')")
    
    def search_for_actual_section(self, search_text):
        """Search specifically for section headers, not TOC references"""
        try:
            # Get full document text
            full_text_result = self.call_mcp_tool("get_document_text", {
                "filename": self.document_path
            })
            
            if not full_text_result or "content" not in full_text_result:
                print("❌ Could not retrieve document text")
                return
                
            full_text = full_text_result["content"][0]["text"]
            paragraphs = full_text.split('\n')
            
            print(f"\n🔍 SECTION-SPECIFIC SEARCH FOR: '{search_text}'")
            print("=" * 60)
            
            section_matches = []
            for i, paragraph in enumerate(paragraphs):
                line = paragraph.strip()
                # Look for exact match that's NOT a bullet point or indented
                if search_text in line and not line.startswith('•') and not line.startswith('   '):
                    # Check if it looks like a section header
                    if len(line) < 100:  # Headers are usually short
                        section_matches.append((i, line))
            
            if section_matches:
                print(f"📋 Found {len(section_matches)} potential section header(s):")
                print("=" * 60)
                
                for i, (line_num, line_content) in enumerate(section_matches, 1):
                    print(f"\n📋 Section {i} [LINE {line_num + 1}]:")
                    print(f"   Header: '{line_content}'")
                    
                    # Show context around this section
                    context_start = max(0, line_num - 2)
                    context_end = min(len(paragraphs), line_num + 5)
                    
                    print("   Context:")
                    for j in range(context_start, context_end):
                        if j < len(paragraphs) and paragraphs[j].strip():
                            marker = "  >>> " if j == line_num else "      "
                            print(f"{marker}{paragraphs[j].strip()}")
                    print("-" * 50)
                
                # Now ask if they want to add content to one of these sections
                print(f"\n🤖 Add RAG-enhanced content to which section?")
                print(f"   • Type section number (1-{len(section_matches)})")
                print(f"   • Type 'skip' to cancel")
                
                choice = input("Section number: ").strip()
                
                if choice.isdigit():
                    section_num = int(choice) - 1
                    if 0 <= section_num < len(section_matches):
                        selected_line_num, selected_line = section_matches[section_num]
                        
                        # Ask what content to add
                        print(f"\n📋 Selected: '{selected_line}'")
                        content_request = input("What content to add? (e.g., 'detailed case studies'): ").strip()
                        
                        if content_request:
                            # Generate and add content
                            self.add_content_to_specific_line(selected_line_num, selected_line, content_request)
                    else:
                        print("❌ Invalid section number")
                else:
                    print("✅ Section search cancelled")
            else:
                print(f"❌ No section headers found for '{search_text}'")
                print(f"💡 The section might not exist yet. Would you like to create it?")
                
        except Exception as e:
            print(f"❌ Section search failed: {e}")
    
    def add_content_to_specific_line(self, line_num, line_content, content_request):
        """Add RAG-enhanced content after a specific line"""
        try:
            print(f"🤖 Generating content for '{content_request}' to add after '{line_content}'...")
            
            # Generate content using RAG
            generated_content = self.generate_enhanced_content_with_rag(
                content_request, 
                f"content for {line_content}",
                line_content
            )
            
            # Ask for confirmation
            confirm = input(f"\n✅ Add this content after '{line_content}'? (y/n): ").strip().lower()
            
            if confirm == 'y':
                # Add content using MCP tool with the exact line content as target
                result = self.call_mcp_tool("insert_line_or_paragraph_near_text", {
                    "filename": self.document_path,
                    "target_text": line_content.strip(),
                    "line_text": f"\n{generated_content}",
                    "position": "after"
                })
                
                if result and "content" in result:
                    print(f"✅ Added RAG-enhanced content: {result['content'][0]['text']}")
                    print("📄 Document updated successfully!")
                else:
                    print("❌ Failed to add content")
            else:
                print("❌ Content addition cancelled")
                
        except Exception as e:
            print(f"❌ Content addition failed: {e}")
    
    
    def explore_document_structure(self, pattern):
        """Explore document structure to find sections and headers"""
        try:
            # Get full document text
            full_text_result = self.call_mcp_tool("get_document_text", {
                "filename": self.document_path
            })
            
            if not full_text_result or "content" not in full_text_result:
                print("❌ Could not retrieve document text")
                return
                
            full_text = full_text_result["content"][0]["text"]
            paragraphs = full_text.split('\n')
            
            print(f"\n🔍 EXPLORING DOCUMENT STRUCTURE FOR PATTERN: '{pattern}'")
            print("=" * 60)
            
            matches = []
            for i, paragraph in enumerate(paragraphs):
                line = paragraph.strip()
                if pattern.lower() in line.lower() and line:
                    matches.append((i, line))
            
            if matches:
                print(f"📍 Found {len(matches)} lines containing '{pattern}':")
                print("=" * 60)
                
                for i, (line_num, line_content) in enumerate(matches, 1):
                    # Determine line type
                    line_type = "📋 Header" if self._is_likely_header(line_content) else "📝 Content"
                    
                    print(f"\n{i}. [LINE {line_num + 1}] {line_type}")
                    print(f"   Content: '{line_content}'")
                    
                    # Show a bit of context
                    context_start = max(0, line_num - 2)
                    context_end = min(len(paragraphs), line_num + 3)
                    
                    print("   Context:")
                    for j in range(context_start, context_end):
                        if j < len(paragraphs) and paragraphs[j].strip():
                            marker = "  >>> " if j == line_num else "      "
                            print(f"{marker}{paragraphs[j].strip()}")
                    print("-" * 50)
            else:
                print(f"❌ No lines found containing '{pattern}'")
                
                # Suggest alternatives
                print(f"\n💡 Try exploring with:")
                print(f"   • 'explore Case' - broader search")
                print(f"   • 'explore 10' - section numbers")
                print(f"   • 'explore Studies' - just keywords")
                
        except Exception as e:
            print(f"❌ Document exploration failed: {e}")
    
    def _is_likely_header(self, line_content):
        """Determine if a line is likely a header"""
        line = line_content.strip()
        
        # Check for section numbering patterns
        if re.match(r'^\d+\.', line) or re.match(r'^\d+\.\d+\.', line):
            return True
            
        # Check for bullet points that might be headers
        if line.startswith('•') and len(line.split()) <= 5:
            return True
            
        # Check if it's all caps or mostly caps
        if len(line) > 3 and line.isupper():
            return True
            
        return False
    
    def add_rag_content_near_matches(self, matches, content_request, search_text):
        """Add RAG-generated content near found matches"""
        try:
            # Get document context from matches
            document_context = matches[0].get("context", "") if matches else ""
            
            # Generate content using RAG
            print(f"🤖 Generating content for '{content_request}' using RAG knowledge...")
            generated_content = self.generate_enhanced_content_with_rag(
                content_request, 
                f"content related to {search_text}",
                document_context
            )
            
            # Ask for confirmation
            confirm = input(f"\n✅ Add this content near '{search_text}'? (y/n): ").strip().lower()
            
            if confirm == 'y':
                # Choose which match to add content to
                if len(matches) > 1:
                    print(f"\n❓ Add content after which match? (1-{len(matches)})")
                    try:
                        choice = int(input("Match number: ").strip()) - 1
                        if 0 <= choice < len(matches):
                            target_matches = [matches[choice]]
                        else:
                            print("❌ Invalid choice, using first match")
                            target_matches = [matches[0]]
                    except ValueError:
                        print("❌ Invalid input, using first match")
                        target_matches = [matches[0]]
                else:
                    target_matches = matches
                
                # Add content using MCP tool
                for match in target_matches:
                    result = self.call_mcp_tool("insert_line_or_paragraph_near_text", {
                        "filename": self.document_path,
                        "target_text": search_text,
                        "line_text": f"\n{generated_content}",
                        "position": "after"
                    })
                    
                    if result and "content" in result:
                        print(f"✅ Added RAG-enhanced content: {result['content'][0]['text']}")
                    else:
                        print("❌ Failed to add content")
                
                print("📄 Document updated successfully with RAG-enhanced content!")
            else:
                print("❌ Operation cancelled")
                
        except Exception as e:
            print(f"❌ RAG content addition failed: {e}")
    
    def enhance_existing_content(self, matches, search_text):
        """Enhance existing content using RAG"""
        try:
            if not matches:
                print("❌ No content to enhance")
                return
                
            # Get existing content context
            existing_content = matches[0].get("context", "")
            
            print(f"🤖 Enhancing existing content around '{search_text}' using RAG knowledge...")
            
            enhanced_content = self.generate_enhanced_content_with_rag(
                f"enhance and expand content about {search_text}",
                "content enhancement",
                existing_content
            )
            
            confirm = input(f"\n✅ Replace content near '{search_text}' with enhanced version? (y/n): ").strip().lower()
            
            if confirm == 'y':
                # Use search and replace to enhance
                result = self.call_mcp_tool("insert_line_or_paragraph_near_text", {
                    "filename": self.document_path,
                    "target_text": search_text,
                    "line_text": f"\n**ENHANCED CONTENT:**\n{enhanced_content}",
                    "position": "after"
                })
                
                if result and "content" in result:
                    print(f"✅ Enhanced content added: {result['content'][0]['text']}")
                else:
                    print("❌ Failed to enhance content")
                    
                print("📄 Document enhanced successfully with RAG knowledge!")
            else:
                print("❌ Enhancement cancelled")
                
        except Exception as e:
            print(f"❌ Content enhancement failed: {e}")
    
    def get_document_info(self):
        """Get document information"""
        info_result = self.call_mcp_tool("get_document_info", {
            "filename": self.document_path
        })
        
        if info_result and "content" in info_result:
            print("📊 Document Info:")
            info_data = json.loads(info_result["content"][0]["text"])
            for key, value in info_data.items():
                print(f"{key}: {value}")
    
    def interactive_mode(self):
        """Interactive AI-powered editing mode with RAG integration"""
        print("\n🎯 AI DYNAMIC DOCUMENT EDITOR WITH RAG")
        print("=" * 60)
        
        # Get document info
        self.get_document_info()
        
        print("\n🎮 ENHANCED COMMANDS:")
        print("• find 'text' - Search document, then optionally add RAG-enhanced content")
        print("• replace 'old' with 'new' - Smart text replacement")
        print("• rag query 'question' - Direct RAG system query")
        print("• add content 'request' - Generate and add RAG-enhanced content")
        print("• explore 'pattern' - Explore document structure (e.g., 'explore 10.')")
        print("• info - Show document information")
        print("• quit - Exit editor")
        
        print("\n💡 KEY FEATURES:")
        print("• RAG-powered content generation from your knowledge base")
        print("• Context-aware enhancements using templates, examples, and current RFP")
        print("• Smart section detection and professional content generation")
        print("• Direct integration with your LangGraph QA system")
        print("\n")
        
        while True:
            command = input(f"RAG Edit {os.path.basename(self.document_path)}: ").strip()
            
            if command.lower() in ['quit', 'q', 'exit']:
                break
            
            if command.lower() == 'info':
                self.get_document_info()
                continue
            
            if not command:
                continue
            
            # Process find commands (enhanced with RAG)
            if command.startswith('find '):
                search_text = command[5:].strip()
                # Remove quotes if present
                if search_text.startswith('"') and search_text.endswith('"'):
                    search_text = search_text[1:-1]
                elif search_text.startswith("'") and search_text.endswith("'"):
                    search_text = search_text[1:-1]
                
                self.find_command(search_text)
                continue
            
            # Process explore commands
            if command.startswith('explore '):
                pattern = command[8:].strip()
                if pattern.startswith('"') and pattern.endswith('"'):
                    pattern = pattern[1:-1]
                elif pattern.startswith("'") and pattern.endswith("'"):
                    pattern = pattern[1:-1]
                
                self.explore_document_structure(pattern)
                continue
            
            # Process RAG query commands
            if command.startswith('rag query '):
                query_text = command[10:].strip()
                if query_text.startswith('"') and query_text.endswith('"'):
                    query_text = query_text[1:-1]
                elif query_text.startswith("'") and query_text.endswith("'"):
                    query_text = query_text[1:-1]
                
                print(f"🔍 Querying RAG system: {query_text}")
                contexts = self.query_rag_for_context(query_text)
                print("📚 RAG Results:")
                print("-" * 40)
                for ctx_type, ctx_list in contexts.items():
                    if ctx_type != "summary" and ctx_list:
                        print(f"\n**{ctx_type.replace('_', ' ').title()}:**")
                        for ctx in ctx_list[:1]:  # Show first result
                            print(f"- {ctx.get('source', 'Unknown')}: {ctx.get('content', '')[:200]}...")
                continue
            
            # Process add content commands
            if command.startswith('add content '):
                content_request = command[12:].strip()
                if content_request.startswith('"') and content_request.endswith('"'):
                    content_request = content_request[1:-1]
                elif content_request.startswith("'") and content_request.endswith("'"):
                    content_request = content_request[1:-1]
                
                print(f"🤖 Generating content for: {content_request}")
                generated_content = self.generate_enhanced_content_with_rag(
                    content_request, 
                    "general content addition", 
                    ""
                )
                
                confirm = input(f"\n✅ Add this content to the end of document? (y/n): ").strip().lower()
                if confirm == 'y':
                    result = self.call_mcp_tool("add_paragraph", {
                        "filename": self.document_path,
                        "text": generated_content
                    })
                    
                    if result and "content" in result:
                        print(f"✅ Added content: {result['content'][0]['text']}")
                    else:
                        print("❌ Failed to add content")
                continue
            
            # Process replace commands
            if ' with ' in command and command.startswith('replace '):
                parts = command[8:].split(' with ', 1)  # Remove 'replace ' prefix
                if len(parts) == 2:
                    old_text = parts[0].strip().strip("'\"")
                    new_text = parts[1].strip().strip("'\"")
                    
                    result = self.call_mcp_tool("search_and_replace", {
                        "filename": self.document_path,
                        "find_text": old_text,
                        "replace_text": new_text
                    })
                    
                    if result and "content" in result:
                        print(f"✅ {result['content'][0]['text']}")
                    else:
                        print("❌ Replace operation failed")
                    continue
            
            print("❓ Command not recognized. Try:")
            print("   • find 'certification' - Find and optionally enhance with RAG")
            print("   • explore 'Case Studies' - Explore document structure")
            print("   • rag query 'ethereum expertise' - Query RAG knowledge base")
            print("   • add content 'project timeline' - Generate RAG-enhanced content")
            print("   • replace 'old text' with 'new text' - Replace text")
            
            print("-" * 60)
    
    
    def add_rag_content_to_specific_match(self, match, content_request, search_text):
        """Add RAG content to a specific match"""
        try:
            print(f"🎯 Adding RAG content to specific match: {match.get('actual_line', 'Unknown')[:60]}...")
            
            # Generate content using RAG
            rag_content = self.generate_enhanced_content_with_rag(
                content_request,
                f"specific content for {search_text}",
                match.get('context', '')
            )
            
            if rag_content:
                # Get the paragraph index for insertion
                paragraph_index = match.get('paragraph_index', match.get('line_number', 1) - 1)
                
                # Insert content after the matched line
                self.add_content_to_specific_line_index(paragraph_index, rag_content)
                print(f"✅ RAG content added after line {paragraph_index + 1}")
            else:
                print("❌ Failed to generate RAG content")
                
        except Exception as e:
            print(f"❌ Specific match content addition failed: {e}")
    
    def enhance_specific_match(self, match, search_text):
        """Enhance a specific match using RAG"""
        try:
            print(f"🌟 Enhancing specific match: {match.get('actual_line', 'Unknown')[:60]}...")
            
            existing_content = match.get('context', '')
            enhanced_content = self.generate_enhanced_content_with_rag(
                f"enhance and expand content about {search_text}",
                "content enhancement",
                existing_content
            )
            
            if enhanced_content:
                paragraph_index = match.get('paragraph_index', match.get('line_number', 1) - 1)
                self.add_content_to_specific_line_index(paragraph_index, enhanced_content)
                print(f"✅ Content enhanced at line {paragraph_index + 1}")
            else:
                print("❌ Failed to generate enhanced content")
                
        except Exception as e:
            print(f"❌ Specific match enhancement failed: {e}")
    
    def add_content_to_specific_line_index(self, paragraph_index, content):
        """Add content after a specific paragraph line"""
        try:
            # Insert content as new paragraphs after the target line
            paragraphs = content.split('\n\n')
            
            for i, paragraph in enumerate(paragraphs):
                if paragraph.strip():
                    result = self.call_mcp_tool("insert_line_or_paragraph_near_text", {
                        "filename": self.document_path,
                        "target_paragraph_index": paragraph_index + i,
                        "line_text": paragraph.strip(),
                        "position": "after"
                    })
                    
                    if result and "error" in str(result):
                        print(f"⚠️  Warning: {result}")
                    else:
                        print(f"📝 Added paragraph {i+1} after line {paragraph_index + i + 1}")
                        
        except Exception as e:
            print(f"❌ Content insertion failed: {e}")

    def cleanup(self):
        """Cleanup MCP server"""
        if self.server_process:
            self.server_process.terminate()
            print("🛑 Stopping MCP server...")

def main():
    """Main entry point"""
    print("🚀 Starting AI Dynamic Editor with LangGraph RAG Integration")
    editor = AIDynamicEditorWithRAG()
    
    try:
        if editor.start_mcp_server():
            editor.interactive_mode()
        else:
            print("❌ Failed to start AI Dynamic Editor with RAG")
    
    except KeyboardInterrupt:
        print("\n⏹️  Interrupted by user")
    finally:
        editor.cleanup()
        print("👋 RAG-enhanced dynamic editing session ended!")

if __name__ == "__main__":
    main()