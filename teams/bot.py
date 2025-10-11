import os
import json
from typing import Dict, Any, Optional

import requests
from botbuilder.core import ActivityHandler, TurnContext, MessageFactory, CardFactory
from botbuilder.schema import (
    Activity,
    ActivityTypes,
    Attachment,
    SuggestedActions,
    CardAction,
    ActionTypes,
)
from botbuilder.core.conversation_state import ConversationState
from botbuilder.core.user_state import UserState
from config import DefaultConfig
import logging

logger = logging.getLogger(__name__)

class DOCXAgentBot(ActivityHandler):
    def __init__(self, conversation_state: ConversationState, user_state: UserState):
        self.conversation_state = conversation_state
        self.user_state = user_state
        self.config = DefaultConfig()
        
        # Backend API configuration
        self.backend_url = self.config.BACKEND_API_URL
        
    async def on_message_activity(self, turn_context: TurnContext):
        """Handle incoming messages"""
        user_id = turn_context.activity.from_property.id
        user_name = turn_context.activity.from_property.name
        # Handle cases where the activity may not include text (e.g., adaptive card submits)
        raw_text = turn_context.activity.text or ""
        message_text = raw_text.strip()

        # If this is an adaptive card submit with value payload, handle via submit action handler
        if not message_text and turn_context.activity.value:
            logger.info("Received adaptive card submit via message activity; delegating to submit handler")
            await self.on_submit_action(turn_context)
            return
        
        # Get user profile for memory
        user_profile = await self._get_user_profile(turn_context, user_id, user_name)
        
        try:
            if self._is_approval_response(message_text):
                response = await self._handle_approval(turn_context, user_id, message_text, user_profile)
            else:
                response = await self._send_to_backend(user_id, message_text, user_profile)

            if response.get("requires_approval", False):
                await self._send_approval_message(turn_context, response)
                await self._persist_user_profile(turn_context, user_profile)
            else:
                await turn_context.send_activity(MessageFactory.text(response["message"]))
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await turn_context.send_activity(
                MessageFactory.text("Sorry, I encountered an error. Please try again.")
            )
    
    async def on_members_added_activity(self, members_added: list, turn_context: TurnContext):
        """Greet new members"""
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                welcome_message = (
                    "👋 Hello! I'm your DOCX Document Agent.\n\n"
                    "I can help you:\n"
                    "• 📄 Index and analyze DOCX documents\n"
                    "• ✏️ Edit document content (with approval)\n"
                    "• 📋 Generate table of contents\n"
                    "• 🔍 Search through documents\n"
                    "• 📊 Get document outlines\n\n"
                    "Just upload a DOCX file or ask me what you'd like to do!"
                )
                await turn_context.send_activity(MessageFactory.text(welcome_message))
    
    async def _get_user_profile(self, turn_context: TurnContext, user_id: str, user_name: str) -> Dict[str, Any]:
        """Get or create user profile with memory"""
        user_state_accessor = self.user_state.create_property("UserProfile")
        user_profile = await user_state_accessor.get(turn_context, lambda: {})
        
      
        if not user_profile.get("initialized"):
            user_profile.update({
                "user_id": user_id,
                "name": user_name,
                "teams_id": user_id,
                "platform": "teams",
                "initialized": True,
                "preferences": {},
                "interaction_count": 0
            })
        
        
        user_profile["interaction_count"] = user_profile.get("interaction_count", 0) + 1
       
        await user_state_accessor.set(turn_context, user_profile)
        await self.user_state.save_changes(turn_context)
        
        return user_profile

    async def _persist_user_profile(self, turn_context: TurnContext, user_profile: Dict[str, Any]):
        """Persist updated user profile to user state"""
        user_state_accessor = self.user_state.create_property("UserProfile")
        await user_state_accessor.set(turn_context, user_profile)
        await self.user_state.save_changes(turn_context)

    async def _persist_pending_session(self, turn_context: TurnContext, session_id: str):
        """Persist pending approval session id to user profile"""
        user_state_accessor = self.user_state.create_property("UserProfile")
        user_profile = await user_state_accessor.get(turn_context, lambda: {})
        user_profile["pending_session_id"] = session_id
        await user_state_accessor.set(turn_context, user_profile)
        await self.user_state.save_changes(turn_context)
    
    def _is_approval_response(self, message: str) -> bool:
        """Check if message is an approval response"""
        if not message:
            return False

        normalized = message.strip().lower()
        first_token = normalized.split()[0]
        approval_keywords = {"yes", "no", "approve", "reject", "/approve", "/reject"}
        return normalized in approval_keywords or first_token in approval_keywords

    
    async def _handle_approval(self, turn_context: TurnContext, user_id: str, message: str, user_profile: Dict) -> Dict[str, Any]:
        """Handle approval/rejection responses via backend approval endpoint"""

        normalized = message.lower().strip()
        approval_keywords = {"yes", "approve", "/approve"}
        rejection_keywords = {"no", "reject", "/reject"}
        is_approval = normalized in approval_keywords
        session_id = user_profile.get("pending_session_id")

        # Allow message format "/approve <session_id>"
        parts = message.split()
        if len(parts) > 1:
            session_id = parts[1]

        if not session_id:
            logger.warning("No pending session found, attempting recovery...")
            return {
                "message": "Your session has expired. Please start a new operation.",
                "requires_approval": False
            }

        response = await self._send_approval_to_backend(
            user_id=user_id,
            session_id=session_id,
            approved=is_approval,
            user_profile=user_profile,
        )

        logger.info("Approval processed successfully via approval endpoint")

        # Clear pending session id after completing approval
        if "pending_session_id" in user_profile:
            user_profile.pop("pending_session_id", None)
        # Persist the updated user profile after clearing pending session
        await self._persist_user_profile(turn_context, user_profile)

        return response
    
    async def _send_to_backend(self, user_id: str, message: str, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Send message to FastAPI backend"""
        payload = {
            "user_id": f"teams_{user_id}",
            "message": message,
            "platform": "teams",
            "metadata": {
                "user_profile": user_profile,
                "teams_context": True
            }
        }

        logger.info(f"Sending to backend: user={payload['user_id']}, message='{message}'")
        logger.info(f"Backend URL: {self.backend_url}/api/chat")

        try:
            response = requests.post(f"{self.backend_url}/api/chat", json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()

            logger.info(f"Backend response status: {response.status_code}")
            logger.info(f"Backend response: {result.get('message', 'No message')[:100]}...")

            if result.get("requires_approval"):
                pending_session_id = result.get("session_id")
                if pending_session_id:
                    user_profile["pending_session_id"] = pending_session_id
                    # Persist the user profile immediately after setting pending session
                    await self._persist_user_profile(turn_context, user_profile)
                logger.info(f"Approval required for session: {pending_session_id}")

            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Backend request failed: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Backend error response: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error sending to backend: {e}")
            raise

    async def _send_approval_to_backend(self, user_id: str, session_id: str, approved: bool, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Send approval decision to FastAPI backend"""
        payload = {
            "user_id": f"teams_{user_id}",
            "session_id": session_id,
            "approved": approved,
            "platform": "teams",
            "user_profile": user_profile
        }

        logger.info(f"Sending approval to backend: user={payload['user_id']}, session={session_id}, approved={approved}")
        logger.info(f"Backend URL: {self.backend_url}/api/approve")

        try:
            response = requests.post(f"{self.backend_url}/api/approve", json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()

            logger.info(f"Backend approval response status: {response.status_code}")
            logger.info(f"Backend approval response: {result.get('message', 'No message')[:100]}...")

            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Backend approval request failed: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Backend approval error response: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error sending approval to backend: {e}")
            raise

    async def _send_approval_message(self, turn_context: TurnContext, response: Dict[str, Any]):
        """Send approval request with action buttons"""
        approval_text = response.get("message", "🔔 Approval required")
        session_id = response.get("session_id") or ""

        if session_id:
            approval_text = (
                f"{approval_text}\n\nSession ID: {session_id}\n"
                "Reply with /approve or /reject, or tap a button below."
            )
        else:
            approval_text = (
                f"{approval_text}\n\n"
                "Reply with /approve or /reject, or tap a button below."
            )

        message = MessageFactory.text(approval_text)
        message.suggested_actions = SuggestedActions(
            actions=[
                CardAction(
                    title="✅ Approve",
                    type=ActionTypes.im_back,
                    value="/approve",
                ),
                CardAction(
                    title="❌ Reject",
                    type=ActionTypes.im_back,
                    value="/reject",
                ),
            ]
        )

        await turn_context.send_activity(message)
    
    def _create_approval_card(self, response: Dict[str, Any]) -> Attachment:
        """Create adaptive card for approval requests"""
        card_content = {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.3",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "🔔 Approval Required",
                    "weight": "Bolder",
                    "size": "Medium",
                    "color": "Attention"
                },
                {
                    "type": "TextBlock",
                    "text": response["message"],
                    "wrap": True,
                    "spacing": "Medium"
                }
            ],
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "✅ Approve",
                    "data": {
                        "action": "approve",
                        "session_id": response.get("session_id")
                    },
                    "style": "positive"
                },
                {
                    "type": "Action.Submit",
                    "title": "❌ Reject", 
                    "data": {
                        "action": "reject",
                        "session_id": response.get("session_id")
                    },
                    "style": "destructive"
                }
            ]
        }
        
        return CardFactory.adaptive_card(card_content)
    
    async def on_submit_action(self, turn_context: TurnContext):
        """Handle adaptive card submit actions"""
        try:
            action_data = turn_context.activity.value
            user_id = turn_context.activity.from_property.id

            logger.info(f"Processing submit action: {action_data}")
            logger.info(f"From user: {turn_context.activity.from_property.name} ({user_id})")

            if action_data.get("action") == "approve":
                message = "/approve"
                logger.info("User clicked approve button")
            elif action_data.get("action") == "reject":
                message = "/reject"
                logger.info("User clicked reject button")
            else:
                logger.warning(f"Unknown action: {action_data.get('action')}")
                return

            session_id = action_data.get("session_id")
            if session_id:
                logger.info(f"Session ID included: {session_id}")

            user_profile = await self._get_user_profile(turn_context, user_id, turn_context.activity.from_property.name)

            # Ensure we track the pending session id in case card submit bypassed text flow
            if session_id:
                user_profile["pending_session_id"] = session_id
                await self._persist_user_profile(turn_context, user_profile)

            # Process approval using approval endpoint
            logger.info("Sending approval to backend...")
            response = await self._handle_approval(turn_context, user_id, message, user_profile)

            logger.info(f"Approval response: {response.get('message', 'No message')[:100]}...")
            await turn_context.send_activity(MessageFactory.text(response["message"]))
            await self._persist_user_profile(turn_context, user_profile)

        except Exception as e:
            logger.error(f"Error in submit action: {e}")
            logger.error(f"Action data: {action_data}")
            logger.error(f"Turn context activity: {turn_context.activity}")
            await turn_context.send_activity(
                MessageFactory.text("Sorry, I encountered an error processing your approval. Please try again.")
            )