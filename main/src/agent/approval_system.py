"""Modular approval system for LangGraph agents.

This module provides a reusable approval system that can be easily integrated
into any LangGraph project requiring human-in-the-loop approval for certain operations.
"""

from typing import Any, Dict, List, Set, Callable, Optional
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.types import interrupt


class ApprovalSystem:
    """Configurable approval system for LangGraph agents.
    
    This class provides a flexible way to add human approval workflows
    to any LangGraph agent with customizable tool filtering and descriptions.
    """
    
    def __init__(
        self,
        write_tools: Optional[Set[str]] = None,
        approval_checker: Optional[Callable[[str], bool]] = None,
        description_generator: Optional[Callable[[str, Dict[str, Any]], str]] = None,
        approval_keywords: Optional[Set[str]] = None
    ):
        """Initialize the approval system.
        
        Args:
            write_tools: Set of tool names that require approval (default: {"apply_edit"})
            approval_checker: Custom function to check if a tool requires approval
            description_generator: Custom function to generate approval descriptions
            approval_keywords: Set of keywords that indicate approval (default: {"yes", "y", "approve", "approved", "true"})
        """
        self.write_tools = write_tools or {"apply_edit"}
        self.approval_keywords = approval_keywords or {"yes", "y", "approve", "approved", "true"}
        
        # Use custom checker if provided, otherwise use default
        self.requires_approval = approval_checker or self._default_approval_checker
        
        # Use custom description generator if provided, otherwise use default
        self.generate_description = description_generator or self._default_description_generator
    
    def _default_approval_checker(self, tool_name: str) -> bool:
        """Default function to check if a tool requires approval.
        
        Args:
            tool_name: Name of the tool being called
            
        Returns:
            True if the tool requires approval, False otherwise
        """
        return tool_name in self.write_tools
    
    def _default_description_generator(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """Default function to generate approval descriptions.
        
        Args:
            tool_name: Name of the tool being called
            tool_args: Arguments for the tool
            
        Returns:
            Human-readable description of the operation
        """
        if tool_name == "apply_edit":
            anchor = tool_args.get("anchor", [])
            new_text = tool_args.get("new_text", "")
            return (
                f"**Edit Operation**\n"
                f"- Location: {anchor}\n"
                f"- New text: {new_text[:100]}{'...' if len(new_text) > 100 else ''}\n\n"
                f"Do you approve this change? (yes/no)"
            )
        else:
            return f"Approve {tool_name} with args: {tool_args}? (yes/no)"
    
    def get_tools_needing_approval(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get tool calls that require approval.
        
        Args:
            tool_calls: List of tool calls from the AI message
            
        Returns:
            List of tool calls that require approval
        """
        return [
            tc for tc in tool_calls 
            if self.requires_approval(tc["name"])
        ]
    
    def is_approval_response(self, response: Any) -> bool:
        """Check if a response indicates approval.
        
        Args:
            response: The approval response (usually a string)
            
        Returns:
            True if the response indicates approval, False otherwise
        """
        if isinstance(response, str):
            return response.lower().strip() in self.approval_keywords
        return False
    
    async def request_approval(
        self, 
        tool_name: str, 
        tool_call_id: str, 
        tool_args: Dict[str, Any]
    ) -> Any:
        """Request human approval for an operation.
        
        Args:
            tool_name: Name of the tool being called
            tool_call_id: ID of the tool call
            tool_args: Arguments for the tool
            
        Returns:
            The approval response from the human
        """
        description = self.generate_description(tool_name, tool_args)
        
        approval_data = {
            "type": "approval_request",
            "tool_name": tool_name,
            "tool_call_id": tool_call_id,
            "args": tool_args,
            "description": description
        }
        
        return interrupt(approval_data)
    
    def create_rejection_messages(
        self, 
        tool_calls: List[Dict[str, Any]], 
        rejected_tool_id: str, 
        rejected_tool_name: str
    ) -> List[ToolMessage]:
        """Create rejection messages for all tool calls.
        
        Args:
            tool_calls: List of all tool calls
            rejected_tool_id: ID of the rejected tool call
            rejected_tool_name: Name of the rejected tool
            
        Returns:
            List of ToolMessage objects for all tool calls
        """
        tool_messages = []
        
        for tc in tool_calls:
            if tc["id"] == rejected_tool_id:
                # This is the rejected tool
                tool_messages.append(ToolMessage(
                    content=f"Operation cancelled by user. The {tc['name']} operation was not executed.",
                    tool_call_id=tc["id"],
                    name=tc["name"]
                ))
            else:
                # Other tool calls should also get rejection messages
                tool_messages.append(ToolMessage(
                    content=f"Skipped due to user rejection of {rejected_tool_name}.",
                    tool_call_id=tc["id"],
                    name=tc["name"]
                ))
        
        return tool_messages


def create_approval_node(approval_system: ApprovalSystem):
    """Create an approval node function for use in LangGraph.
    
    Args:
        approval_system: Configured ApprovalSystem instance
        
    Returns:
        Async function that can be used as a LangGraph node
    """
    async def approval_node(state) -> Dict[str, Any]:
        """Request human approval for critical operations.
        
        This node pauses execution and asks for human approval before
        executing write operations.
        
        Args:
            state: The current state of the conversation.
            
        Returns:
            dict: Updated state with approved operation or rejection message.
        """
        last_message = state.messages[-1]
        
        if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
            return {}
        
        # Check if any tool calls require approval
        tool_calls_needing_approval = approval_system.get_tools_needing_approval(last_message.tool_calls)
        
        if not tool_calls_needing_approval:
            # No approval needed, proceed to tools
            return {}
        
        # For now, handle the first tool call that needs approval
        tool_call = tool_calls_needing_approval[0]
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_call_id = tool_call["id"]
        
        # Request approval
        approval = await approval_system.request_approval(tool_name, tool_call_id, tool_args)
        
        # Process approval response
        if approval_system.is_approval_response(approval):
            # Approval granted - proceed with the operation
            return {"pending_operation": None}
        else:
            # Approval denied - create tool messages for all tool calls
            tool_messages = approval_system.create_rejection_messages(
                last_message.tool_calls, tool_call_id, tool_name
            )
            
            return {
                "messages": tool_messages,
                "pending_operation": None
            }
    
    return approval_node


def create_approval_router(approval_system: ApprovalSystem):
    """Create a routing function for approval decisions.
    
    Args:
        approval_system: Configured ApprovalSystem instance
        
    Returns:
        Function that can be used as a LangGraph conditional edge
    """
    def route_approval(state) -> str:
        """Route after approval node.
        
        If approval was granted, go to tools. If rejected, go back to call_model.
        
        Args:
            state: The current state.
            
        Returns:
            str: Next node to call.
        """
        # Check if the last message is a rejection (ToolMessage added by approval_node)
        if state.messages and isinstance(state.messages[-1], ToolMessage):
            # Rejection message was added, go back to model
            return "call_model"
        
        # Approval granted, proceed to execute tools
        return "tools"
    
    return route_approval


def create_model_output_router(approval_system: ApprovalSystem):
    """Create a routing function for model output decisions.
    
    Args:
        approval_system: Configured ApprovalSystem instance
        
    Returns:
        Function that can be used as a LangGraph conditional edge
    """
    def route_model_output(state) -> str:
        """Determine the next node based on the model's output.

        This function checks if the model's last message contains tool calls
        and routes to approval if needed.

        Args:
            state: The current state of the conversation.

        Returns:
            str: The name of the next node to call.
        """
        last_message = state.messages[-1]
        
        # Ensure we have an AIMessage - this should always be the case after call_model
        if not isinstance(last_message, AIMessage):
            raise ValueError(
                f"Expected AIMessage in output edges, but got {type(last_message).__name__}. "
                f"This indicates the call_model function did not return an AIMessage."
            )
        
        # If there is no tool call, then we finish
        if not last_message.tool_calls:
            return "__end__"
        
        # Check if any tool calls require approval
        needs_approval = any(
            approval_system.requires_approval(tc["name"]) for tc in last_message.tool_calls
        )
        
        if needs_approval:
            return "approval_node"
        
        # No approval needed, execute tools directly
        return "tools"
    
    return route_model_output
