"""
Teams Bot with LangGraph Server Integration
"""
import logging
from typing import Dict, Any, Optional
from botbuilder.core import ActivityHandler, TurnContext, MessageFactory
from botbuilder.schema import Activity, ActivityTypes, ChannelAccount, SuggestedActions, CardAction, ActionTypes
from langgraph_sdk import get_client

from config import Config
from thread_manager import ThreadManager

logger = logging.getLogger(__name__)


class LangGraphTeamsBot(ActivityHandler):
    """Teams bot that integrates with LangGraph Server"""
    
    def __init__(self, config: Config, thread_manager: ThreadManager):
        super().__init__()
        self.config = config
        self.thread_manager = thread_manager
        
        # Initialize LangGraph client
        self.langgraph_client = get_client(url=config.LANGGRAPH_SERVER_URL)
        logger.info(f"Initialized LangGraph client for {config.LANGGRAPH_SERVER_URL}")
        
        # Track pending approvals per conversation
        self.pending_approvals: Dict[str, Dict[str, Any]] = {}
    
    async def on_message_activity(self, turn_context: TurnContext):
        """Handle incoming messages from Teams"""
        try:
            user_id = turn_context.activity.from_property.id
            user_name = turn_context.activity.from_property.name
            conversation_id = turn_context.activity.conversation.id
            message_text = (turn_context.activity.text or "").strip()
            
            logger.info(f"Message from {user_name} ({user_id}) in conversation {conversation_id}: {message_text[:100]}")
            
            # Check if this is an approval response
            if conversation_id in self.pending_approvals and self._is_approval_response(message_text):
                await self._handle_approval_response(turn_context, message_text)
                return
            
            # Check if user has pending approval (and isn't responding to it)
            if conversation_id in self.pending_approvals:
                await turn_context.send_activity(
                    "⚠️ You have a pending approval request. Please respond with /approve or /reject first."
                )
                return
            
            # Get or create thread for this conversation
            thread_id = await self._get_or_create_thread(
                conversation_id=conversation_id,
                user_id=user_id,
                user_name=user_name
            )
            
            # Update activity timestamp
            await self.thread_manager.update_activity(conversation_id)
            
            # Send typing indicator
            await turn_context.send_activity(Activity(type=ActivityTypes.typing))
            
            # Process message with LangGraph
            await self._process_with_langgraph(turn_context, thread_id, message_text)
            
        except Exception as e:
            logger.error(f"Error in on_message_activity: {e}", exc_info=True)
            await turn_context.send_activity(
                "❌ Sorry, I encountered an error processing your message. Please try again."
            )
    
    async def on_members_added_activity(self, members_added: list, turn_context: TurnContext):
        """Send welcome message when bot is added to conversation"""
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                welcome_message = (
                    "👋 Hello! I'm your LangGraph AI Assistant.\n\n"
                    "I can help you with:\n"
                    "• 📄 Document operations (read, edit, create DOCX files)\n"
                    "• 📝 RFP proposal generation\n"
                    "• 💬 General questions and assistance\n"
                    "• 🔍 PDF parsing and knowledge retrieval\n\n"
                    "For document operations that modify files, I'll ask for your approval first.\n\n"
                    "What can I help you with today?"
                )
                await turn_context.send_activity(MessageFactory.text(welcome_message))
    
    async def _get_or_create_thread(
        self, 
        conversation_id: str, 
        user_id: str, 
        user_name: str
    ) -> str:
        """Get existing thread or create new one for conversation"""
        # Check if thread already exists
        thread_id = await self.thread_manager.get_thread_id(conversation_id)
        
        if thread_id:
            logger.debug(f"Using existing thread {thread_id}")
            return thread_id
        
        # Create new thread
        logger.info(f"Creating new thread for conversation {conversation_id}")
        thread = await self.langgraph_client.threads.create(
            metadata={
                "conversation_id": conversation_id,
                "user_id": user_id,
                "user_name": user_name,
                "platform": "teams"
            }
        )
        
        thread_id = thread["thread_id"]
        
        # Store mapping
        await self.thread_manager.create_mapping(
            conversation_id=conversation_id,
            thread_id=thread_id,
            user_id=user_id,
            user_name=user_name,
            metadata={"platform": "teams"}
        )
        
        logger.info(f"Created new thread {thread_id} for conversation {conversation_id}")
        return thread_id
    
    async def _process_with_langgraph(
        self, 
        turn_context: TurnContext, 
        thread_id: str, 
        message: str
    ):
        """Process message through LangGraph Server"""
        conversation_id = turn_context.activity.conversation.id
        
        try:
            # Create and wait for run to complete
            logger.info(f"Creating run for thread {thread_id}")
            
            run = await self.langgraph_client.runs.wait(
                thread_id=thread_id,
                assistant_id=self.config.ASSISTANT_ID,
                input={"messages": [{"role": "user", "content": message}]}
            )
            
            # Debug: log the actual response
            logger.debug(f"Run response type: {type(run)}")
            logger.debug(f"Run response keys: {run.keys() if isinstance(run, dict) else 'Not a dict'}")
            logger.info(f"Run completed with status: {run.get('status', 'unknown')}")
            
            # Handle different run statuses
            # Check if this is the final output (direct response) or a run object
            if isinstance(run, dict) and "messages" in run:
                # This is the direct output from a successful run
                logger.info("Received direct output from run")
                await self._handle_success(turn_context, {"output": run})
            elif isinstance(run, dict) and "__interrupt__" in run:
                # This is an interrupt response
                logger.info("Received interrupt from run")
                await self._handle_interrupt(turn_context, thread_id, run)
            elif isinstance(run, dict) and "status" in run:
                # This is a run object with status
                status = run["status"]
                logger.info(f"Run status: {status}")

                if status == "success":
                    await self._handle_success(turn_context, run)

                elif status == "interrupted":
                    await self._handle_interrupt(turn_context, thread_id, run)

                elif status == "error":
                    error_msg = run.get("error", "Unknown error occurred")
                    logger.error(f"Run failed with error: {error_msg}")
                    await turn_context.send_activity(
                        f"❌ An error occurred while processing your request:\n{error_msg}"
                    )

                elif status == "timeout":
                    logger.warning(f"Run timed out for thread {thread_id}")
                    await turn_context.send_activity(
                        "⏱️ The operation took too long. Please try a simpler request."
                    )

                else:
                    logger.warning(f"Unexpected run status: {status}")
                    await turn_context.send_activity(
                        f"⚠️ Unexpected status: {status}"
                    )
            else:
                # Unknown response format
                logger.error(f"Unexpected run response format: {type(run)}, keys: {run.keys() if isinstance(run, dict) else 'N/A'}")
                await turn_context.send_activity(
                    "⚠️ Received unexpected response format from LangGraph Server."
                )
        
        except Exception as e:
            logger.error(f"Error processing with LangGraph: {e}", exc_info=True)
            await turn_context.send_activity(
                "❌ Failed to process your request. Please check if LangGraph Server is running."
            )
    
    async def _handle_completed_run(self, turn_context: TurnContext, thread_id: str, run: Dict[str, Any]):
        """Handle completed run response (same logic as _process_with_langgraph)"""
        # Debug: log the actual response
        logger.debug(f"Completed run response type: {type(run)}")
        logger.debug(f"Completed run response keys: {run.keys() if isinstance(run, dict) else 'Not a dict'}")

        # Handle different run statuses
        # Check if this is the final output (direct response) or a run object
        if isinstance(run, dict) and "messages" in run:
            # This is the direct output from a successful run
            logger.info("Received direct output from completed run")
            await self._handle_success(turn_context, {"output": run})
        elif isinstance(run, dict) and "__interrupt__" in run:
            # This is an interrupt response
            logger.info("Received interrupt from completed run")
            await self._handle_interrupt(turn_context, thread_id, run)
        elif isinstance(run, dict) and "status" in run:
            # This is a run object with status
            status = run["status"]
            logger.info(f"Completed run status: {status}")

            if status == "success":
                await self._handle_success(turn_context, run)

            elif status == "interrupted":
                await self._handle_interrupt(turn_context, thread_id, run)

            elif status == "error":
                error_msg = run.get("error", "Unknown error occurred")
                logger.error(f"Completed run failed with error: {error_msg}")
                await turn_context.send_activity(
                    f"❌ An error occurred while processing your request:\n{error_msg}"
                )

            elif status == "timeout":
                logger.warning(f"Completed run timed out for thread {thread_id}")
                await turn_context.send_activity(
                    "⏱️ The operation took too long. Please try a simpler request."
                )

            else:
                logger.warning(f"Unexpected completed run status: {status}")
                await turn_context.send_activity(
                    f"⚠️ Unexpected status: {status}"
                )
        else:
            # Unknown response format
            logger.error(f"Unexpected completed run response format: {type(run)}, keys: {run.keys() if isinstance(run, dict) else 'N/A'}")
            await turn_context.send_activity(
                "⚠️ Received unexpected response format from LangGraph Server."
            )

    async def _handle_success(self, turn_context: TurnContext, run: Dict[str, Any]):
        """Handle successful run completion"""
        # Extract response from run output
        output = run.get("output", {})

        # Get the last AI message from the output
        messages = output.get("messages", [])
        if messages:
            last_message = messages[-1]

            # Handle different message types
            if isinstance(last_message, dict):
                content = last_message.get("content", "")
            else:
                content = str(last_message)

            if content:
                await turn_context.send_activity(content)
            else:
                await turn_context.send_activity("✅ Task completed successfully.")
        else:
            await turn_context.send_activity("✅ Task completed.")
    
    async def _handle_interrupt(
        self,
        turn_context: TurnContext,
        thread_id: str,
        run: Dict[str, Any]
    ):
        """Handle interrupted run (approval required)"""
        conversation_id = turn_context.activity.conversation.id

        try:
            # Get thread state to inspect the interrupt
            logger.info(f"Getting state for interrupted thread {thread_id}")
            state = await self.langgraph_client.threads.get_state(thread_id)

            # Debug: log full state structure
            logger.debug(f"Full state: {state}")

            # Look for approval request in tasks
            approval_data = None
            tasks = state.get("values", {}).get("tasks", [])

            # Also check interrupts directly in state
            interrupts = state.get("interrupts", [])

            logger.debug(f"State interrupts: {interrupts}")
            logger.debug(f"State tasks: {tasks}")
            logger.debug(f"Run interrupt data: {run}")

            # Try to find approval request in interrupts
            for interrupt in interrupts:
                logger.debug(f"Checking interrupt: {interrupt}")
                value = interrupt.get("value", {})
                if isinstance(value, dict) and value.get("type") == "approval_request":
                    approval_data = value
                    logger.info(f"Found approval request: {approval_data}")
                    break

            # Also check the run data for interrupt info
            if not approval_data and "__interrupt__" in run:
                interrupt_data = run.get("__interrupt__", {})
                logger.debug(f"Checking run interrupt data: {interrupt_data}")
                if isinstance(interrupt_data, dict):
                    # Look for approval data in various possible locations
                    if interrupt_data.get("type") == "approval_request":
                        approval_data = interrupt_data
                    elif "value" in interrupt_data and isinstance(interrupt_data["value"], dict):
                        if interrupt_data["value"].get("type") == "approval_request":
                            approval_data = interrupt_data["value"]
            
            if approval_data:
                description = approval_data.get("description", "A sensitive operation requires approval.")
                tool_name = approval_data.get("tool_name", "unknown")

                logger.info(f"Approval required for {tool_name}")

                # Store pending approval
                self.pending_approvals[conversation_id] = {
                    "thread_id": thread_id,
                    "approval_data": approval_data,
                    "run": run
                }

                # Send approval request with suggested actions
                await self._send_approval_request(turn_context, description)
            else:
                # Try to extract approval info from interrupt data more broadly
                interrupt_info = None

                # Check run interrupt data for any approval-related info
                if "__interrupt__" in run:
                    interrupt_value = run["__interrupt__"]
                    if isinstance(interrupt_value, dict):
                        # Look for common approval patterns
                        if any(key in str(interrupt_value).lower() for key in ["approve", "approval", "confirm"]):
                            interrupt_info = interrupt_value

                # Check state values for approval-related data
                state_values = state.get("values", {})
                if not interrupt_info:
                    for key, value in state_values.items():
                        if "approval" in key.lower() or "confirm" in key.lower():
                            interrupt_info = {"description": f"Operation requires approval: {key}", "data": value}
                            break

                if interrupt_info:
                    logger.info(f"Found generic interrupt info: {interrupt_info}")

                    # Create a generic approval request
                    description = interrupt_info.get("description", "A sensitive operation requires approval.")

                    # Store pending approval with generic data
                    self.pending_approvals[conversation_id] = {
                        "thread_id": thread_id,
                        "approval_data": interrupt_info,
                        "run": run
                    }

                    await self._send_approval_request(turn_context, description)
                else:
                    # Generic interrupt handling - no approval data found
                    logger.warning("Interrupt detected but no approval request found")
                    logger.debug(f"State values: {state_values}")
                    await turn_context.send_activity(
                        "⏸️ The operation was paused. Please provide additional input."
                    )
        
        except Exception as e:
            logger.error(f"Error handling interrupt: {e}", exc_info=True)
            await turn_context.send_activity(
                "⚠️ An error occurred while processing the approval request."
            )
    
    async def _send_approval_request(self, turn_context: TurnContext, description: str):
        """Send approval request with action buttons"""
        message_text = (
            f"🔔 **Approval Required**\n\n"
            f"{description}\n\n"
            f"Reply with /approve or /reject"
        )
        
        message = MessageFactory.text(message_text)
        message.suggested_actions = SuggestedActions(
            actions=[
                CardAction(
                    title="✅ Approve",
                    type=ActionTypes.im_back,
                    value="/approve"
                ),
                CardAction(
                    title="❌ Reject",
                    type=ActionTypes.im_back,
                    value="/reject"
                )
            ]
        )
        
        await turn_context.send_activity(message)
    
    def _is_approval_response(self, message: str) -> bool:
        """Check if message is an approval response"""
        if not message:
            return False
        
        normalized = message.lower().strip()
        first_word = normalized.split()[0] if normalized.split() else ""
        
        return (
            normalized in self.config.APPROVE_KEYWORDS or
            normalized in self.config.REJECT_KEYWORDS or
            first_word in self.config.APPROVE_KEYWORDS or
            first_word in self.config.REJECT_KEYWORDS
        )
    
    async def _handle_approval_response(self, turn_context: TurnContext, message: str):
        """Handle user's approval or rejection"""
        conversation_id = turn_context.activity.conversation.id
        
        if conversation_id not in self.pending_approvals:
            await turn_context.send_activity(
                "⚠️ No pending approval found. The request may have expired."
            )
            return
        
        pending = self.pending_approvals[conversation_id]
        thread_id = pending["thread_id"]
        
        # Determine if approved or rejected
        normalized = message.lower().strip()
        first_word = normalized.split()[0] if normalized.split() else ""
        
        approved = (
            normalized in self.config.APPROVE_KEYWORDS or
            first_word in self.config.APPROVE_KEYWORDS
        )
        
        logger.info(f"Approval decision: {'APPROVED' if approved else 'REJECTED'}")
        
        try:
            # Send typing indicator
            await turn_context.send_activity(Activity(type=ActivityTypes.typing))
            
            if approved:
                # Resume execution with approval
                logger.info(f"Approving operation for thread {thread_id}")

                try:
                    # For demo purposes with thread resets, we'll use a simpler approach
                    # Instead of trying to resume the interrupted run, we'll send the approval
                    # as input to continue the conversation

                    logger.info("Processing approval by sending confirmation message")

                    # Clear pending approval first
                    del self.pending_approvals[conversation_id]

                    # Send a confirmation message that the operation is approved
                    await turn_context.send_activity("✅ Operation approved! Processing your request...")

                    # Send a simple confirmation message to continue the workflow
                    # This bypasses the complex interrupt handling for demo purposes
                    await self._process_with_langgraph(turn_context, thread_id, "yes, proceed with the approved edit")

                    return

                except Exception as e:
                    logger.error(f"Error processing approval: {e}", exc_info=True)
                    await turn_context.send_activity(
                        "❌ Failed to process the approval. Please try again."
                    )
                    return
            
            else:
                # Rejection - simple handling for demo
                logger.info(f"Rejecting operation for thread {thread_id}")

                # Clear pending approval
                del self.pending_approvals[conversation_id]

                await turn_context.send_activity(
                    "❌ Operation rejected. The action was not performed."
                )
        
        except Exception as e:
            logger.error(f"Error handling approval response: {e}", exc_info=True)
            
            # Clear pending approval on error
            if conversation_id in self.pending_approvals:
                del self.pending_approvals[conversation_id]
            
            await turn_context.send_activity(
                "❌ An error occurred while processing your approval. Please try again."
            )

