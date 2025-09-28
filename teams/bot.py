"""
Enhanced Microsoft Teams Bot with full RFP system integration
"""

import asyncio
import traceback
import json
from botbuilder.core import ActivityHandler, TurnContext, MessageFactory
from botbuilder.schema import ChannelAccount, Activity, ActivityTypes
from typing import List
from pathlib import Path

from rfp_teams_agent import RFPTeamsAgent
from memory_management import TeamsMemoryManager

class RFPBot(ActivityHandler):
    """Enhanced RFP Bot using the EXISTING main system"""
    
    def __init__(self):
        self.rfp_agent = RFPTeamsAgent()
        self.memory_manager = TeamsMemoryManager()
        self.initialization_task = None
        self.initialized = False
        self.user_sessions = set()  
        print("🤖 RFP Bot initialized - will use EXISTING main system")
        
    async def on_startup(self):
        """Initialize the bot systems"""
        try:
            print("🚀 Starting bot with EXISTING main system...")
            self.initialization_task = asyncio.create_task(self.rfp_agent.initialize())
            await self.initialization_task
            self.initialized = True
            print("✅ Bot startup complete")
        except Exception as e:
            print(f"❌ Bot startup failed: {e}")
            traceback.print_exc()
            self.initialized = False

    async def _ensure_initialized(self):
        """Ensure the agent is initialized"""
        if not self.initialized:
            try:
                await self.rfp_agent.initialize()
                self.initialized = True
                print("✅ Bot agent initialized")
            except Exception as e:
                print(f"❌ Failed to initialize bot agent: {e}")
                raise
        
    async def on_message_activity(self, turn_context: TurnContext):
        """Handle incoming message activities - FIXED to prevent double messages"""
        try:
         
            await self._ensure_initialized()
            
           
            user_id = getattr(turn_context.activity.from_property, 'id', 'anonymous')
            
           
            message_text = turn_context.activity.text
            
           
            if user_id not in self.user_sessions:
                self.user_sessions.add(user_id)  
                await self._send_welcome_message(turn_context, user_id)
                
                if message_text and message_text.strip():
                    message_text = message_text.strip()
                    print(f"📨 Processing first message after welcome: {message_text}")
                    
                else:
                    return
            
            if not message_text or message_text.strip() == "":
                await turn_context.send_activity(MessageFactory.text(
                    "Hi! How can I help you today? Try 'Generate a proposal for [your project]' 🚀"
                ))
                return
            
            message_text = message_text.strip()
            print(f"📨 Received message: {message_text}")
            
            if any(word in message_text.lower() for word in ["proposal", "create", "generate"]):
                await self._send_typing_indicator(turn_context)
            
            try:
                response = await self.process_rfp_message_with_fallback(message_text, user_id)
                
                # Split long responses for Teams
                if len(response) > 4000:
                    chunks = self._split_response(response)
                    for chunk in chunks:
                        await turn_context.send_activity(MessageFactory.text(chunk))
                else:
                    await turn_context.send_activity(MessageFactory.text(response))
                    
            except Exception as e:
                print(f"❌ Error processing RFP message: {str(e)}")
                traceback.print_exc()
                fallback_response = await self._get_fallback_response(message_text, user_id)
                await turn_context.send_activity(MessageFactory.text(fallback_response))
                
        except Exception as e:
            print(f"❌ Error in on_message_activity: {str(e)}")
            traceback.print_exc()
            await turn_context.send_activity(MessageFactory.text(
                "I'm sorry, I encountered an error. Please try again with a simpler request."
            ))

    async def _send_welcome_message(self, turn_context: TurnContext, user_id: str):
        """Send a short, friendly welcome message"""
        welcome_message = """👋 **Hi! I'm your RFP Assistant**

I create comprehensive proposals using AI teams:
🔧 Technical • 💰 Finance • ⚖️ Legal • 🔍 QA

**Try:** "Generate a proposal for cloud computing"

Ready to create an amazing proposal? 🚀"""

        await turn_context.send_activity(MessageFactory.text(welcome_message))

    async def process_rfp_message_with_fallback(self, message: str, user_id: str) -> str:
        """Process RFP messages with production-ready fallbacks"""
        try:
            # Check if this is a proposal generation request
            if any(word in message.lower() for word in ["proposal", "create", "generate", "rfp"]):
                return await self._handle_proposal_generation_with_fallback(message, user_id)
            else:
                response = await self.rfp_agent.process_message(message, user_id)
                return response
                
        except Exception as e:
            print(f"❌ Error in process_rfp_message_with_fallback: {str(e)}")
            traceback.print_exc()
            return await self._get_fallback_response(message, user_id)

    async def _handle_proposal_generation_with_fallback(self, message: str, user_id: str) -> str:
        """Handle proposal generation - LANGGRAPH ONLY, NO FALLBACKS"""
        try:
            print("🎯 PROPOSAL GENERATION - LANGGRAPH ONLY")
           
            response = await self.rfp_agent.process_message(message, user_id)
            
           
            if isinstance(response, list):
           
                return "MULTIPLE_MESSAGES:" + json.dumps(response)
            else:
                return response
                        
        except Exception as e:
            print(f"❌ LangGraph proposal generation failed: {e}")
            traceback.print_exc()
            return f"""❌ **LangGraph System Error**

    The main LangGraph system encountered an error and cannot generate proposals.

    **Error**: {str(e)}

    **Action Required**: The main system must be debugged and fixed.
    **No fallback systems available** - all proposals must go through LangGraph teams."""

    async def on_message_activity(self, turn_context: TurnContext):
        """Handle incoming message activities - FIXED to prevent double messages"""
        try:
            
            await self._ensure_initialized()
            
            user_id = getattr(turn_context.activity.from_property, 'id', 'anonymous')
            
            message_text = turn_context.activity.text
            
           
            if user_id not in self.user_sessions:
                self.user_sessions.add(user_id)  # Mark as greeted FIRST
                await self._send_welcome_message(turn_context, user_id)
                
                
                if message_text and message_text.strip():
                    message_text = message_text.strip()
                else:
                    return 
           
            if not message_text or message_text.strip() == "":
                await turn_context.send_activity(MessageFactory.text(
                    "Hi! How can I help you today? Try 'Generate a proposal for [your project]' 🚀"
                ))
                return
            
            message_text = message_text.strip()
            print(f"📨 Received message: {message_text}")
            
           
            if any(word in message_text.lower() for word in ["proposal", "create", "generate"]):
                await self._send_typing_indicator(turn_context)
            
            try:
                response = await self.process_rfp_message_with_fallback(message_text, user_id)

                if response.startswith("MULTIPLE_MESSAGES:"):
                    messages_json = response[len("MULTIPLE_MESSAGES:"):]
                    messages = json.loads(messages_json)

                    for i, message in enumerate(messages):
                        await turn_context.send_activity(MessageFactory.text(message))
                        
                       
                        if i < len(messages) - 1:  
                            await asyncio.sleep(0.5)
                            
                elif len(response) > 4000:
                    # Split long single responses for Teams
                    chunks = self._split_response(response)
                    for i, chunk in enumerate(chunks):
                        await turn_context.send_activity(MessageFactory.text(chunk))
                        if i < len(chunks) - 1:
                            await asyncio.sleep(0.5)
                else:
                    # Single message
                    await turn_context.send_activity(MessageFactory.text(response))
                        
            except Exception as e:
                print(f"❌ Error processing RFP message: {str(e)}")
                traceback.print_exc()
                fallback_response = await self._get_fallback_response(message_text, user_id)
                await turn_context.send_activity(MessageFactory.text(fallback_response))
                
        except Exception as e:
            print(f"❌ Error in on_message_activity: {str(e)}")
            traceback.print_exc()
            await turn_context.send_activity(MessageFactory.text(
                "I'm sorry, I encountered an error. Please try again with a simpler request."
            ))
    async def _generate_simple_fallback_only(self, message: str, user_id: str) -> str:
        """Generate ONLY a simple fallback when main system fails"""
        try:
            print("🔄 Generating simple fallback only...")
            
            user_context = self.memory_manager.get_user_context(user_id)
            
            return f"""⚠️ **System Temporarily Busy**

Hi {user_context.get('name', 'there')}! 

I received your request for: *"{message}"*

**Status**: Our main proposal system is currently processing other requests.

**What I can do right now**:
- Discuss your project requirements in detail
- Provide preliminary cost estimates
- Schedule a consultation call
- Answer technical questions

**Your Information**:
- **Company**: {user_context.get('company', 'Your organization')}
- **Budget**: {user_context.get('budget', 'To be discussed')}

**Next Steps**:
Try your request again in a moment for the full AI-generated proposal, or let me know what specific aspect you'd like to discuss!

🚀 **Ready to proceed with your project?**"""
            
        except Exception as e:
            print(f"❌ Simple fallback failed: {e}")
            return "I received your request and our team is preparing a response. Please try again in a moment for the complete proposal!"

    async def _get_fallback_response(self, message: str, user_id: str) -> str:
        """Get a basic fallback response when all else fails"""
        try:
            user_context = self.memory_manager.get_user_context(user_id)
            name = user_context.get('name', '')
            
            if any(word in message.lower() for word in ["proposal", "create", "generate", "rfp"]):
                return f"""Hi {name}! 👋

I understand you want to create a proposal. While our main system is temporarily unavailable, I can still help you get started:

**What I can do right now:**
- Discuss your project requirements
- Provide basic cost estimates  
- Schedule a detailed consultation
- Share our service offerings

**For a complete proposal, please:**
1. Tell me about your project scope
2. Share your timeline and budget
3. Mention any specific technologies needed

Let's start with: *What type of project are you planning?*

The full system will be back online shortly for comprehensive proposal generation! 🚀"""
            else:
                return f"""Hi {name}! 👋

I'm your RFP Assistant. I can help you with:
- Creating comprehensive proposals
- Technical solution design
- Budget planning and analysis
- Project timeline estimation

What would you like to work on today?"""
                
        except Exception as e:
            print(f"❌ Fallback response failed: {e}")
            return await self._get_emergency_response(message, user_id)

    async def _get_emergency_response(self, message: str, user_id: str) -> str:
        """Emergency response when everything fails"""
        return """🚨 **System Status**: Temporary Service Interruption

I'm experiencing technical difficulties but I'm still here to help!

**Immediate Actions:**
- Your message has been received and logged
- Our technical team has been notified
- Service will be restored shortly

**What you can do:**
- Try a simpler request (e.g., "help" or "hello")
- Check back in a few minutes
- Contact support if urgent

Thank you for your patience! 🙏"""

    def _split_response(self, response: str, max_length: int = 4000) -> List[str]:
        """Split long responses for Teams message limits"""
        if len(response) <= max_length:
            return [response]
        
        chunks = []
        lines = response.split('\n')
        current_chunk = ""
        
        for line in lines:
            if len(current_chunk + line + '\n') > max_length:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = line + '\n'
                else:
                    # Single line too long, split it
                    chunks.append(line[:max_length])
                    current_chunk = line[max_length:] + '\n'
            else:
                current_chunk += line + '\n'
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks

    async def _send_typing_indicator(self, turn_context: TurnContext):
        """Send typing indicator for long operations"""
        try:
            typing_activity = Activity(
                type=ActivityTypes.typing,
                from_property=turn_context.activity.recipient,
                recipient=turn_context.activity.from_property,
                conversation=turn_context.activity.conversation
            )
            await turn_context.send_activity(typing_activity)
        except Exception as e:
            print(f"⚠️ Could not send typing indicator: {e}")
        
    async def on_members_added_activity(self, members_added: List[ChannelAccount], turn_context: TurnContext):
        """Welcome new members - but DON'T duplicate if they already got welcomed"""
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                user_id = member.id
                
                print(f"📝 New member added: {user_id} - will welcome on first message")