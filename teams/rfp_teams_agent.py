"""
RFP Teams Agent - Simple integration with main LangGraph system
"""

import asyncio
import traceback
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from memory_management import TeamsMemoryManager

class RFPTeamsAgent:
    """Simple RFP Teams Agent - just run main system and get proposal"""
    
    def __init__(self):
        self.memory_manager = TeamsMemoryManager()
        self.main_graph = None
        self.initialized = False
        print("🚀 Initializing with EXISTING main system...")

    async def initialize(self):
        """Initialize with the existing main system ONCE"""
        try:
            if self.initialized:
                print("✅ Already initialized")
                return
                
            import sys
            import os
            from pathlib import Path
            
            current_dir = Path(__file__).parent.absolute()
            main_path = (current_dir.parent / "main").absolute()
            src_path = (main_path / "src").absolute()
            
            paths_to_add = [str(main_path), str(src_path)]
            for path in paths_to_add:
                if os.path.exists(path) and path not in sys.path:
                    sys.path.insert(0, path)
            
            print(f"✅ Added paths: {paths_to_add}")
            
            original_cwd = os.getcwd()
            os.chdir(str(main_path))
            
            try:
                
                from agent.state import MessagesState
                from agent.graph import graph
                
                print("✅ Imported main system components")
                
                self.main_graph = graph
                print(f"✅ Main graph loaded successfully: {type(self.main_graph)}")
                
            finally:
                os.chdir(original_cwd)
                
            self.initialized = True
            print("✅ RFP Teams Agent initialized with EXISTING main system")
            
        except Exception as e:
            print(f"❌ Failed to initialize RFP Teams Agent: {str(e)}")
            traceback.print_exc()
            raise

    async def process_message(self, message: str, user_id: str) -> str:
        """Process message - run LangGraph and get result"""
        try:
            print(f"🔄 Processing message: {message}...")
            
            self.memory_manager.update_user_context(user_id, message)
            user_context = self.memory_manager.get_user_context(user_id)
            user_context['last_message'] = message
            
            if self._is_proposal_request(message):
                print("🎯 PROPOSAL GENERATION REQUESTED")
                return await self._run_main_langgraph_simple(message, user_id)
            else:
                print("💬 REGULAR CONVERSATION")
                return await self._handle_conversation(message, user_id)
                
        except Exception as e:
            print(f"❌ Error processing message: {str(e)}")
            traceback.print_exc()
            return f"❌ System error: {str(e)}"

    async def _run_main_langgraph_simple(self, message: str, user_id: str) -> str:
        """Run main LangGraph system SIMPLY - no loops, no complications"""
        try:
            print("🚀 Running main LangGraph system...")
            
            user_context = self.memory_manager.get_user_context(user_id)

            from langchain_core.messages import HumanMessage
            
           
            initial_state = {
                "messages": [HumanMessage(content=message)],
                "chunks": [],
                "pdf_paths": [],
                "task_completed": False,
                "iteration_count": 0,
                "confidence_score": None,
                "follow_up_questions": [],
                "teams_completed": set(),
                "team_responses": {}
            }
            
          
            config = {
                "recursion_limit": 12,  # if it creates too many proposal please change it to lower number
                "configurable": {
                    "thread_id": f"simple_{user_id}_{int(datetime.now().timestamp())}"
                }
            }
            
            print("⏳ Executing LangGraph...")
            
            final_result = None
            nodes_hit = []
            
            try:
                async for chunk in self.main_graph.astream(initial_state, config=config):
                    if isinstance(chunk, dict):
                        for node_name, node_output in chunk.items():
                            nodes_hit.append(node_name)
                            print(f"📡 Node: {node_name}")
                            
                            # Store the final result
                            if isinstance(node_output, dict):
                                final_result = node_output
                                
            except Exception as e:
                print(f"⏳ LangGraph completed: {str(e)}")
            
            print(f"📊 Nodes executed: {nodes_hit}")
            
            await asyncio.sleep(5)
            
            return await self._get_newly_generated_proposal_only(user_id, user_context)
            
        except Exception as e:
            print(f"❌ LangGraph execution error: {str(e)}")
            traceback.print_exc()
            return f"❌ LangGraph error: {str(e)}"

    async def _get_newly_generated_proposal_only(self, user_id: str, user_context: dict) -> List[str]:
        """Get ONLY newly generated proposal files - prioritize fresh content"""
        try:
            print("📁 Looking for NEWLY generated proposal files...")
            
            priority_dirs = [
                Path("../main/test_output"),         # Primary generation directory
                Path("../main/responses"),           # Secondary generation directory
                Path("../main"),                     # Main directory
                Path("./test_output"),               # Local test output
                Path("./responses"),                 # Local responses
            ]
            
            current_time = datetime.now().timestamp()
            new_proposal_files = []
            
            # Look for files created in the last 2 minutes ONLY
            for search_dir in priority_dirs:
                if search_dir.exists():
                    print(f"📂 Checking for NEW files in: {search_dir.absolute()}")
                    
                    for file_path in search_dir.glob("**/*.md"):
                        try:
                            file_age = current_time - file_path.stat().st_mtime
                            
                            if file_age < 120:  # Last 2 minutes ONLY
                                if 'proposal' in file_path.name.lower():
                                    new_proposal_files.append((file_path, file_age))
                                    print(f"📄 Found NEW proposal file: {file_path} (age: {file_age:.1f}s)")
                        except Exception as e:
                            print(f"⚠️ Error checking file {file_path}: {e}")
                            continue
            
            if new_proposal_files:
                # Sort by most recent first
                new_proposal_files.sort(key=lambda x: x[1])
                latest_file, age = new_proposal_files[0]
                
                print(f"✅ Using NEWLY generated file: {latest_file} (age: {age:.1f}s)")
                
                try:
                    # Read the FULL content of the NEW proposal
                    with open(latest_file, 'r', encoding='utf-8') as f:
                        proposal_content = f.read()
                    
                    print(f"✅ Successfully read NEW proposal: {len(proposal_content)} characters")
                    
                    return self._format_multiple_messages(proposal_content, user_context)
                    
                except Exception as read_error:
                    print(f"❌ Could not read NEW proposal file: {read_error}")
            
            return [f"""⚠️ **New Proposal Generation Status**

Hi {user_context.get('name', 'there')}!

The LangGraph system executed but no NEW proposal file was generated in the last 2 minutes.

**Your Request**: {user_context.get('last_message', 'proposal generation')}
**Budget**: {user_context.get('budget', '$200k')}

**This means:**
1. The proposal generation process may still be running
2. Files are being saved to a different location
3. The system needs more time to complete all team responses

**Try again in a moment** - the system should generate a fresh proposal file! 🚀

**Debug Info**: LangGraph completed but no fresh files found in:
- ../main/test_output
- ../main/responses
- ../main"""]
            
        except Exception as e:
            print(f"❌ Error searching for NEW proposal files: {e}")
            traceback.print_exc()
            return [f"""🔧 **System Status**

Hi {user_context.get('name', 'there')}!

There was an error checking for newly generated proposal files.

**Error**: {str(e)}

**Please try your request again** - the system should generate a new proposal document! 🚀"""]

    def _format_multiple_messages(self, content: str, user_context: dict) -> List[str]:
        """Format the response as multiple messages to show complete content"""
        
        messages = []
        
        # Create header message
        header = f"""✅ **NEW RFP Proposal Generated Successfully!**

**Client**: {user_context.get('name', 'Client')} | **Company**: {user_context.get('company', 'Organization')} | **Budget**: {user_context.get('budget', '$200k')}

---

*Sending complete NEW proposal in multiple messages...*"""
        
        messages.append(header)
        
        # Split content into chunks that fit Teams message limits
        chunk_size = 3000  
        content_chunks = []
        
        # Try to split at logical points (sections, paragraphs)
        lines = content.split('\n')
        current_chunk = ""
        
        for line in lines:
            # If adding this line would exceed chunk size, save current chunk
            if len(current_chunk) + len(line) + 1 > chunk_size:
                if current_chunk.strip():
                    content_chunks.append(current_chunk.strip())
                current_chunk = line
            else:
                if current_chunk:
                    current_chunk += "\n" + line
                else:
                    current_chunk = line
        
        # Add the last chunk
        if current_chunk.strip():
            content_chunks.append(current_chunk.strip())
        
        # Create messages for each chunk
        total_chunks = len(content_chunks)
        
        for i, chunk in enumerate(content_chunks, 1):
            chunk_message = f"""**📄 NEW Proposal Part {i}/{total_chunks}**

{chunk}

---
*Continued...*""" if i < total_chunks else f"""**📄 NEW Proposal Part {i}/{total_chunks} - Final**

{chunk}

---
*Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} via LangGraph*
*Complete NEW proposal delivered in {total_chunks} parts*"""
            
            messages.append(chunk_message)
        
        return messages

    def _is_proposal_request(self, message: str) -> bool:
        """Check if message is requesting proposal generation"""
        proposal_keywords = [
            'proposal', 'generate', 'create', 'rfp', 'quote', 
            'estimate', 'bid', 'offer', 'solution'
        ]
        return any(keyword in message.lower() for keyword in proposal_keywords)

    async def _handle_conversation(self, message: str, user_id: str) -> str:
        """Handle regular conversation"""
        user_context = self.memory_manager.get_user_context(user_id)
        message_lower = message.lower()
        
        updated_entities = {}
        
        if 'budget' in message_lower or '$' in message:
            import re
            budget_match = re.search(r'\$(\d+(?:,\d{3})*(?:k|m)?)', message, re.IGNORECASE)
            if budget_match:
                updated_entities['budget'] = budget_match.group(0)
        
        if 'company' in message_lower or 'corp' in message_lower:
            import re
            company_match = re.search(r'company\s+([A-Za-z0-9\s]+)', message, re.IGNORECASE)
            if not company_match:
                company_match = re.search(r'([A-Za-z0-9]+\s*corp)', message, re.IGNORECASE)
            if company_match:
                updated_entities['company'] = company_match.group(1).strip()
        
        if 'i am' in message_lower or 'my name is' in message_lower:
            import re
            name_match = re.search(r'i am\s+([A-Za-z]+)', message, re.IGNORECASE)
            if not name_match:
                name_match = re.search(r'my name is\s+([A-Za-z]+)', message, re.IGNORECASE)
            if name_match:
                updated_entities['name'] = name_match.group(1).strip()
        

        if updated_entities:
            with sqlite3.connect(self.memory_manager.db_path) as conn:
                for key, value in updated_entities.items():
                    conn.execute(
                        "INSERT OR REPLACE INTO memories (user_id, key, value) VALUES (?, ?, ?)",
                        (user_id, key, value)
                    )
                conn.commit()
            user_context.update(updated_entities)
        
        if any(word in message_lower for word in ['hello', 'hi', 'hey']):
            return f"""👋 **Hi {user_context.get('name', 'there')}!**

I create comprehensive RFP proposals using our LangGraph system.

**Your Info**:
• **Company**: {user_context.get('company', 'Your Organization')}
• **Budget**: {user_context.get('budget', 'To be determined')}

**Ready to start?** Try: "Generate a proposal for [your project]" 🚀"""
        
        elif any(word in message_lower for word in ['help', 'what can you do']):
            return f"""🤖 **Hi {user_context.get('name', 'there')}!** 

I create complete RFP proposals using our LangGraph multi-agent system.

**💡 Just say:**
• "Generate a proposal for cloud computing"
• "Create a proposal for web development"
• "Generate an RFP for AI services"

Ready to create your proposal? 🚀"""
        
        else:
            return f"""✅ **Information saved!**

**Your Details:**
• **Name**: {user_context.get('name', 'Not provided')}
• **Company**: {user_context.get('company', 'Not provided')}  
• **Budget**: {user_context.get('budget', 'Not provided')}

**Ready for proposals?** Try: "Generate a proposal for [your project]" 🚀"""