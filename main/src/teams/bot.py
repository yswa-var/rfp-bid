"""
RFP Teams Bot - Professional Teams Bot for RFP proposal generation
"""
import logging
from typing import List
from botbuilder.core import ActivityHandler, TurnContext, MessageFactory
from botbuilder.schema import ChannelAccount

from simple_rfp_agent import SimpleRFPAgent
from memory_management import TeamsMemoryManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RFPTeamsBot(ActivityHandler):
    """Professional Teams bot for RFP proposal generation"""
    
    def __init__(self):
        super().__init__()
        self.simple_agent = SimpleRFPAgent()
        self.memory_manager = TeamsMemoryManager()
        print("🚀 RFP Teams Bot initialized successfully")
    
    async def on_message_activity(self, turn_context: TurnContext) -> None:
        """Handle incoming messages"""
        try:
            user_message = turn_context.activity.text
            user_id = turn_context.activity.from_property.id or "user-id-0"
            
            print(f"📨 Received from {user_id}: {user_message}")
            
            # Update memory and extract entities
            extracted_entities = self.memory_manager.update_memory(user_id, user_message)
            if extracted_entities:
                print(f"🧠 Extracted: {extracted_entities}")
            
            # Get current memories
            memories = self.memory_manager.get_memories(user_id)
            
            # Handle remember commands with confirmation
            if user_message.lower().startswith("remember:"):
                memory_summary = self.memory_manager.format_memory_summary(user_id)
                response = f"""
✅ **Information Saved Successfully!**

{memory_summary}

**Ready for:** Generate proposal | Technical architecture | Budget breakdown | Legal terms
                """
            else:
                # Process with RFP agent
                response = await self.simple_agent.process_rfp_request(user_id, user_message, memories)
            
            await turn_context.send_activity(MessageFactory.text(response))
            print("✅ Response sent successfully")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            error_response = """
🔧 **System Ready**

Try: **"Remember: Client is [Company], budget is $[Amount], project is [Description]"**
Then: **"Generate proposal"** or **"Technical architecture"**
            """
            await turn_context.send_activity(MessageFactory.text(error_response))
    
    async def on_members_added_activity(self, members_added: List[ChannelAccount], turn_context: TurnContext) -> None:
        """Welcome new members"""
        welcome_text = """
🎯 **Welcome to RFP Proposal Assistant!**

**Quick Start:**
1. **"Remember: Client is [Company], budget is $[Amount], project is [Description]"**
2. **"Generate proposal"** - Get comprehensive RFP response
3. **"Technical architecture"** - System design details

**Powered by:** LangGraph Multi-Agent System
        """
        
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(MessageFactory.text(welcome_text))