"""
Agent Runner - Handles communication with LangGraph agent
"""

import sys
import os
from typing import Dict, Any, Optional, List
import asyncio
import logging

# Add the main directory to Python path to import the agent
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'main', 'src'))

from langgraph_sdk import get_client
from langgraph_sdk.schema import Command

logger = logging.getLogger(__name__)


class AgentRunner:
    """Handles running the LangGraph agent and managing conversations"""
    
    def __init__(self, langgraph_url: Optional[str] = None):
        """
        Initialize agent runner
        
        Args:
            langgraph_url: URL of LangGraph server (defaults to remote)
        """
        self.langgraph_url = langgraph_url or os.getenv(
            "LANGGRAPH_URL", 
            "http://localhost:2024"
        )
        self.assistant_id = os.getenv("ASSISTANT_ID", "agent")  # Use 'agent' as registered in langgraph.json
        self._client = None
        
        # Check if local mode is explicitly requested
        if os.getenv("USE_LOCAL_GRAPH", "").lower() == "true":
            logger.info("USE_LOCAL_GRAPH=true, using local graph execution")
            self._init_local_graph()
        else:
            # Try remote for MVP
            logger.info(f"Attempting to connect to remote LangGraph server at {self.langgraph_url}")
            self._init_remote_client()
            
            # Fall back to local if remote fails
            if self._client is None:
                logger.info("Remote connection failed, falling back to local graph...")
                self._init_local_graph()
    
    def _init_remote_client(self):
        """Initialize remote LangGraph client"""
        try:
            self._client = get_client(url=self.langgraph_url)
            self._use_remote = True
            logger.info(f"✅ Connected to LangGraph server at {self.langgraph_url}")
        except Exception as e:
            logger.warning(f"❌ Failed to connect to LangGraph server: {e}")
            logger.info("💡 TIP: Start LangGraph server with 'cd main && langgraph up'")
            self._client = None
            self._use_remote = False
            logger.info("Falling back to local graph execution")
            self._init_local_graph()
    
    def _init_local_graph(self):
        """Initialize local graph for direct execution"""
        try:
            from agent.graph import create_supervisor_system
            from langgraph.checkpoint.memory import MemorySaver
            
            # Create the graph with a checkpointer for state management
            checkpointer = MemorySaver()
            self._graph = create_supervisor_system(checkpointer=checkpointer)
            self._use_remote = False
            
            logger.info("Using local graph execution with supervisor system and memory checkpointer")
        except ImportError as e:
            logger.error(f"Failed to import local graph: {e}")
            raise RuntimeError("Cannot initialize agent - no local or remote graph available")
    
    async def process_message(
        self, 
        session_id: str,
        thread_id: str,
        message: str,
        document_context: Dict[str, Any] = None,
        selected_agent: str = "supervisor"  # Add selected agent parameter
    ) -> Dict[str, Any]:
        """
        Process a user message through the agent with optional agent selection
        """
        try:
            if self._use_remote:
                return await self._process_remote(thread_id, message, document_context, selected_agent)
            else:
                return await self._process_local(thread_id, message, document_context, selected_agent)
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return {
                "message": f"Sorry, I encountered an error: {str(e)}",
                "requires_approval": False,
                "error": str(e)
            }
    
    async def _process_remote(self, thread_id: str, message: str, document_context: Dict[str, Any] = None, selected_agent: str = "supervisor") -> Dict[str, Any]:
        """Process message using remote LangGraph server with agent selection"""
        
        # Ensure thread exists (create if it doesn't)
        try:
            await self._client.threads.get(thread_id)
            logger.debug(f"Using existing thread {thread_id}")
        except Exception:
            # Thread doesn't exist, create it
            logger.info(f"Creating new thread {thread_id}")
            await self._client.threads.create(
                thread_id=thread_id,
                metadata={"platform": "web"}
            )
        
        input_data = {
            "messages": [{"role": "user", "content": message}]
        }
        
        # Add document context if available
        if document_context and document_context.get("loaded"):
            input_data.update({
                "document_loaded": True,
                "document_path": document_context["document_path"],
                "document_name": document_context["document_name"]
            })
        
        # Add selected agent to input data for routing
        if selected_agent and selected_agent != "supervisor":
            input_data["selected_agent"] = selected_agent
            logger.info(f"Remote: Forcing route to: {selected_agent}")
    
        # Run the agent with increased recursion limit
        logger.info(f"Running agent with input: {message[:100]}...")
        result = await self._client.runs.wait(
            thread_id,
            self.assistant_id,
            input=input_data,  # Use input_data instead of hardcoded messages
            config={
                "recursion_limit": 100,  # Increase from default 25 to 100
                "configurable": {
                    "selected_agent": selected_agent  # Also add to config
                }
            }
        )
        logger.info(f"Agent completed. Result keys: {result.keys() if result else 'None'}")
        
        # Check for interrupts (approval requests)
        if "__interrupt__" in result and result["__interrupt__"]:
            interrupt = result["__interrupt__"][0]
            approval_data = interrupt.get("value", {})
            
            return {
                "message": approval_data.get("description", "Approval required"),
                "requires_approval": True,
                "approval_data": approval_data
            }
        
        # Extract the last message from the agent
        messages = result.get("messages", [])
        if messages:
            last_message = messages[-1]
            content = last_message.get("content", "No response")
            
            return {
                "message": content,
                "requires_approval": False
            }
        
        return {
            "message": "No response from agent",
            "requires_approval": False
        }
    
    async def _process_local(self, thread_id: str, message: str, document_context: Dict[str, Any] = None, selected_agent: str = "supervisor") -> Dict[str, Any]:
        """Process message using local graph with agent selection"""
        from langchain_core.messages import HumanMessage, AIMessage
        
        # Create config with thread_id for checkpointing
        config = {
            "configurable": {
                "thread_id": thread_id,
                "selected_agent": selected_agent  # Add to config
            }
        }
        
        # Prepare input with document context if available
        input_data = {
            "messages": [HumanMessage(content=message)]
        }
        
        # Add document context to the state if available
        if document_context and document_context.get("loaded"):
            input_data.update({
                "document_loaded": True,
                "document_path": document_context["document_path"],
                "document_name": document_context["document_name"]
            })
        
        # Add selected agent to metadata if not supervisor
        if selected_agent and selected_agent != "supervisor":
            input_data["selected_agent"] = selected_agent
            logger.info(f"Forcing route to: {selected_agent}")
        
        # Run the graph
        try:
            # Invoke the graph - it will stop at interrupts
            result = await self._graph.ainvoke(
                input_data,
                config=config
            )
            
            # Check if execution was interrupted (approval needed)
            state = await self._graph.aget_state(config)
            
            # Check if there are pending tasks (interrupts)
            if state.next:  # next contains the nodes that are pending
                # There's an interrupt - check for approval data
                if state.tasks:
                    for task in state.tasks:
                        if task.interrupts:
                            # Found an interrupt
                            interrupt_data = task.interrupts[0]
                            approval_data = interrupt_data.value
                            
                            return {
                                "message": approval_data.get("description", "Approval required"),
                                "requires_approval": True,
                                "approval_data": approval_data
                            }
            
            # No interrupt - extract the response message
            if result and "messages" in result:
                messages = result["messages"]
                if messages:
                    last_message = messages[-1]
                    if isinstance(last_message, AIMessage):
                        return {
                            "message": last_message.content,
                            "requires_approval": False
                        }
            
            return {
                "message": "Processed successfully",
                "requires_approval": False
            }
            
        except Exception as e:
            logger.error(f"Error in local graph execution: {e}", exc_info=True)
            raise
        
        
    async def resume_with_approval(
        self,
        session_id: str,
        thread_id: str,
        approved: bool
    ) -> Dict[str, Any]:
        """
        Resume agent execution after approval decision

        Args:
            session_id: Session identifier
            thread_id: LangGraph thread ID
            approved: Whether the operation was approved

        Returns:
            Dict containing the final response
        """
        try:
            from langchain_core.messages import AIMessage

            approval_response = "yes" if approved else "no"

            if self._use_remote:
                # Resume using Command for remote execution
                result = await self._client.runs.wait(
                    thread_id,
                    self.assistant_id,
                    command={"resume": approval_response}
                )

                # Extract response
                messages = result.get("messages", [])
                if messages:
                    last_message = messages[-1]
                    content = last_message.get("content", "Operation completed")

                    return {
                        "message": content,
                        "requires_approval": False
                    }
            else:
                # For local execution, use proper interrupt handling
                config = {
                    "configurable": {
                        "thread_id": thread_id
                    }
                }

                try:
                    # Use Command to resume from interrupt
                    from langgraph.types import Command

                    result = await self._graph.ainvoke(
                        Command(resume=approval_response),
                        config=config
                    )

                    # Extract the response from the result
                    if result and "messages" in result:
                        messages = result["messages"]
                        if messages:
                            last_message = messages[-1]
                            if isinstance(last_message, AIMessage):
                                return {
                                    "message": last_message.content,
                                    "requires_approval": False
                                }

                    # Check the final state for any messages
                    final_state = await self._graph.aget_state(config)
                    if final_state and "messages" in final_state:
                        messages = final_state["messages"]
                        if messages:
                            last_message = messages[-1]
                            if isinstance(last_message, AIMessage) and last_message.content:
                                return {
                                    "message": last_message.content,
                                    "requires_approval": False
                                }

                except Exception as resume_error:
                    logger.warning(f"Resume method failed: {resume_error}")

                    # Fallback: Get the final state and return appropriate message
                    try:
                        final_state = await self._graph.aget_state(config)
                        if final_state and "messages" in final_state:
                            messages = final_state["messages"]
                            if messages:
                                last_message = messages[-1]
                                if isinstance(last_message, AIMessage) and last_message.content:
                                    return {
                                        "message": last_message.content,
                                        "requires_approval": False
                                    }
                    except Exception as state_error:
                        logger.error(f"Failed to get final state: {state_error}")

                # Fallback response based on approval status
                if approved:
                    return {
                        "message": "✅ Operation approved and executed successfully",
                        "requires_approval": False
                    }
                else:
                    return {
                        "message": "❌ Operation cancelled by user",
                        "requires_approval": False
                    }

        except Exception as e:
            logger.error(f"Error resuming with approval: {e}", exc_info=True)
            return {
                "message": f"Sorry, I encountered an error. Please try again.",
                "requires_approval": False,
                "error": str(e)
            }
