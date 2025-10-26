"""
Agent Runner - Handles communication with LangGraph agent
"""

import sys
import os
from typing import Dict, Any, Optional, List
import asyncio
import logging
from datetime import datetime

# Add the main directory to Python path to import the agent
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'main', 'src'))

from langgraph_sdk import get_client
from langgraph_sdk.schema import Command
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage

logger = logging.getLogger(__name__)


def make_serializable(obj: Any) -> Any:
    """
    Convert LangChain objects to JSON-serializable format.
    Handles messages, nested dicts, and lists recursively.
    """
    if isinstance(obj, BaseMessage):
        # Convert LangChain message to dict
        return {
            "type": obj.__class__.__name__,
            "content": obj.content,
            "additional_kwargs": obj.additional_kwargs if hasattr(obj, 'additional_kwargs') else {}
        }
    elif isinstance(obj, dict):
        return {key: make_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [make_serializable(item) for item in obj]
    elif isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    else:
        # For other objects, try to convert to string
        try:
            return str(obj)
        except:
            return f"<{obj.__class__.__name__}>"


class AgentRunner:
    """Handles running the LangGraph agent and managing conversations"""
    
    def __init__(self, langgraph_url: Optional[str] = None):
        """
        Initialize agent runner - always uses local mode
        
        Args:
            langgraph_url: URL of LangGraph server (unused, kept for compatibility)
        """
        self.langgraph_url = langgraph_url or os.getenv(
            "LANGGRAPH_URL", 
            "http://localhost:2024"
        )
        self.assistant_id = os.getenv("ASSISTANT_ID", "agent")  # Use 'agent' as registered in langgraph.json
        self._client = None
        self._use_remote = False
        
        # Always use local mode
        logger.info("Using local graph execution mode")
        self._init_local_graph()
    
    def _init_remote_client(self):
        """Initialize remote LangGraph client"""
        try:
            self._client = get_client(url=self.langgraph_url)
            self._use_remote = True  # Remote connection succeeded
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
    
    async def process_message_stream(
        self,
        session_id: str,
        thread_id: str,
        message: str,
        document_context: Dict[str, Any] = None,
        selected_agent: str = "supervisor",
        event_callback = None  # Callback for real-time events
    ) -> Dict[str, Any]:
        """Process message with streaming execution trail"""
        try:
            if self._use_remote:
                return await self._process_remote_stream(thread_id, message, document_context, selected_agent, event_callback)
            else:
                return await self._process_local_stream(thread_id, message, document_context, selected_agent, event_callback)
        except Exception as e:
            logger.error(f"Error processing message with streaming: {e}", exc_info=True)
            if event_callback:
                await event_callback({
                    "type": "error",
                    "error": str(e),
                    "timestamp": asyncio.get_event_loop().time()
                })
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
    
    async def _process_remote_stream(
        self, 
        thread_id: str, 
        message: str, 
        document_context: Dict[str, Any] = None,
        selected_agent: str = "supervisor",
        event_callback = None
    ) -> Dict[str, Any]:
        """Process message using remote LangGraph server with streaming"""
        from datetime import datetime
        
        # Ensure thread exists (create if it doesn't)
        try:
            await self._client.threads.get(thread_id)
            logger.debug(f"Using existing thread {thread_id}")
        except Exception:
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
            logger.info(f"Remote stream: Forcing route to: {selected_agent}")
        
        # Run the agent with streaming
        logger.info(f"Running agent with streaming input: {message[:100]}...")
        
        try:
            stream = self._client.runs.stream(
                thread_id=thread_id,
                assistant_id=self.assistant_id,
                input=input_data,
                config={
                    "recursion_limit": 100,
                    "configurable": {"selected_agent": selected_agent}
                },
                stream_mode="updates"  # Stream state updates per node
            )
            
            final_result = None
            chunk_count = 0
            last_messages = []  # Collect messages from chunks as backup
            
            async for chunk in stream:
                chunk_count += 1
                logger.info(f"Received stream chunk {chunk_count}: {type(chunk)}")
                
                # Collect data from chunk
                chunk_data = getattr(chunk, 'data', chunk)
                
                # Try to extract messages from this chunk for backup
                # Chunks come as {node_name: node_output}, need to look inside
                if isinstance(chunk_data, dict):
                    # Check if messages are at top level
                    if 'messages' in chunk_data:
                        last_messages = chunk_data.get('messages', [])
                        logger.info(f"Chunk {chunk_count} has {len(last_messages)} messages at top level")
                    else:
                        # Messages might be inside node outputs
                        for node_name, node_output in chunk_data.items():
                            if isinstance(node_output, dict) and 'messages' in node_output:
                                last_messages = node_output.get('messages', [])
                                logger.info(f"Chunk {chunk_count} node '{node_name}' has {len(last_messages)} messages")
                
                # Send event to frontend via callback
                if event_callback:
                    try:
                        # Handle different chunk types from LangGraph SDK
                        event_type = getattr(chunk, 'event', 'unknown')
                        event_data = getattr(chunk, 'data', {})
                        
                        # Extract node name if available
                        node_name = None
                        if isinstance(event_data, dict):
                            # For updates mode, data is typically {node_name: node_output}
                            if len(event_data) > 0:
                                node_name = list(event_data.keys())[0]
                        
                        await event_callback({
                            "type": "node_update" if event_type == "updates" else "stream_chunk",
                            "node": node_name,
                            "event": event_type,
                            "data": event_data,
                            "timestamp": datetime.now().isoformat()
                        })
                        logger.info(f"Emitted trail event for node: {node_name}")
                    except Exception as callback_error:
                        logger.error(f"Error in stream callback: {callback_error}", exc_info=True)
                
                final_result = chunk_data
            
            logger.info(f"Agent streaming completed. Chunks: {chunk_count}, Result keys: {final_result.keys() if isinstance(final_result, dict) else 'N/A'}")
            
        except Exception as stream_error:
            logger.error(f"Error during streaming: {stream_error}", exc_info=True)
            raise
        
        # After streaming completes, get the final state
        # Simpler approach: Just get the state snapshot which has all the values
        try:
            state_snapshot = await self._client.threads.get_state(thread_id)
            logger.info(f"Retrieved state snapshot after streaming. Type: {type(state_snapshot)}")
            
            # Use state_snapshot which has the actual values
            if state_snapshot and hasattr(state_snapshot, 'values'):
                # values is a method, not a property - need to call it
                state_values = state_snapshot.values if not callable(state_snapshot.values) else state_snapshot.values()
                logger.info(f"State values type: {type(state_values)}")
                
                if isinstance(state_values, dict):
                    logger.info(f"State values keys: {list(state_values.keys())}")
                else:
                    logger.info(f"State values type not dict: {type(state_values)}")
                
                if isinstance(state_values, dict) and "__interrupt__" in state_values and state_values["__interrupt__"]:
                    interrupt = state_values["__interrupt__"][0]
                    approval_data = interrupt.get("value", {})
                    
                    return {
                        "message": approval_data.get("description", "Approval required"),
                        "requires_approval": True,
                        "approval_data": approval_data
                    }
                
                # Extract messages from final state
                if isinstance(state_values, dict):
                    messages = state_values.get("messages", [])
                    logger.info(f"Found {len(messages)} messages in state")
                    
                    if messages:
                        last_message = messages[-1]
                        logger.info(f"Last message type: {type(last_message)}")
                        
                        # Handle both dict and object message formats
                        if isinstance(last_message, dict):
                            content = last_message.get("content", "")
                            logger.info(f"Dict message content length: {len(str(content))}")
                        else:
                            content = getattr(last_message, 'content', None)
                            logger.info(f"Object message content: {content[:100] if content else 'None'}")
                        
                        if content:
                            logger.info(f"✅ Extracted final message: {content[:200]}...")
                            return {
                                "message": content,
                                "requires_approval": False
                            }
                        else:
                            logger.warning("Content is empty or None")
                    else:
                        logger.warning("No messages found in state_values")
                else:
                    logger.warning(f"state_values is not a dict, cannot extract messages")
                        
        except Exception as state_error:
            logger.error(f"Error getting final state: {state_error}", exc_info=True)
            # Fallback to stream final_result if state retrieval fails
        
        # Fallback 1: try to extract from final_result if state retrieval failed
        logger.info(f"Attempting fallback extraction from final_result: {type(final_result)}")
        if final_result:
            if isinstance(final_result, dict):
                logger.info(f"Final result keys: {final_result.keys()}")
                messages = final_result.get("messages", [])
                logger.info(f"Final result has {len(messages)} messages")
                if messages:
                    last_message = messages[-1]
                    content = last_message.get("content", "") if isinstance(last_message, dict) else str(last_message)
                    
                    if content:
                        logger.info(f"✅ Extracted from fallback 1: {content[:200]}...")
                        return {
                            "message": content,
                            "requires_approval": False
                        }
        
        # Fallback 2: Use messages collected from stream chunks
        logger.info(f"Attempting fallback 2 from stream chunks: {len(last_messages)} messages")
        if last_messages:
            last_message = last_messages[-1]
            content = last_message.get("content", "") if isinstance(last_message, dict) else getattr(last_message, 'content', "")
            
            if content:
                logger.info(f"✅ Extracted from fallback 2 (stream chunks): {content[:200]}...")
                return {
                    "message": content,
                    "requires_approval": False
                }
        
        logger.error("❌ Failed to extract message from state, final_result, and stream chunks")
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
    
    async def _process_local_stream(
        self, 
        thread_id: str, 
        message: str,
        document_context: Dict[str, Any] = None,
        selected_agent: str = "supervisor",
        event_callback = None
    ) -> Dict[str, Any]:
        """Process message using local graph with streaming"""
        from langchain_core.messages import HumanMessage, AIMessage
        from datetime import datetime
        
        # Create config with thread_id for checkpointing
        config = {
            "configurable": {
                "thread_id": thread_id,
                "selected_agent": selected_agent
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
            logger.info(f"Local stream: Forcing route to: {selected_agent}")
        
        # Run the graph with streaming
        try:
            final_result = None
            async for chunk in self._graph.astream(
                input_data,
                config=config,
                stream_mode="updates"
            ):
                # chunk is dict: {node_name: node_output}
                for node_name, node_data in chunk.items():
                    if event_callback:
                        # Convert to JSON-serializable format before sending
                        serializable_data = make_serializable(node_data)
                        await event_callback({
                            "type": "node_update",
                            "node": node_name,
                            "data": serializable_data,
                            "timestamp": datetime.now().isoformat()
                        })
                final_result = chunk
            
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
            if final_result:
                # Get the latest state value since final_result is chunked
                state_value = state.values if state else final_result
                if state_value and "messages" in state_value:
                    messages = state_value["messages"]
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
            logger.error(f"Error in local graph streaming execution: {e}", exc_info=True)
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
