"""Define a custom Reasoning and Action agent.

Works with a chat model with tool calling support.
"""

from datetime import UTC, datetime
from typing import Any, Dict, List, Literal, cast

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.runtime import Runtime
from langgraph.types import Command, interrupt

from react_agent.context import Context
from react_agent.state import InputState, State
from react_agent.tools import TOOLS
from react_agent.utils import load_chat_model

# Define the function that calls the model


async def call_model(
    state: State, runtime: Runtime = None
) -> Dict[str, List[AIMessage]]:
    """Call the LLM powering our "agent".

    This function prepares the prompt, initializes the model, and processes the response.

    Args:
        state (State): The current state of the conversation.
        runtime (Runtime): Runtime context (optional).

    Returns:
        dict: A dictionary containing the model's response message.
    """
    try:
        # Use default system prompt and model
        from . import prompts
        system_message = prompts.SYSTEM_PROMPT.format(
            system_time=datetime.now(tz=UTC).isoformat()
        )

        # Get the model's response
        response = await load_chat_model("openai/gpt-3.5-turbo").bind_tools(TOOLS).ainvoke(
            [{"role": "system", "content": system_message}, *state.messages]
        )

        # Ensure we got an AIMessage
        if not isinstance(response, AIMessage):
            raise ValueError(f"Model returned {type(response).__name__}, expected AIMessage")

        # Handle the case when it's the last step and the model still wants to use a tool
        if state.is_last_step and response.tool_calls:
            return {
                "messages": [
                    AIMessage(
                        id=response.id,
                        content="Sorry, I could not find an answer to your question in the specified number of steps.",
                    )
                ]
            }

        # Return the model's response as a list to be added to existing messages
        return {"messages": [response]}
    
    except Exception as e:
        # If there's an error, return an error message as AIMessage
        error_message = AIMessage(
            content=f"An error occurred while calling the model: {str(e)}"
        )
        return {"messages": [error_message]}


# List of tools that require human approval (write operations)
WRITE_TOOLS = {"apply_edit"}  # Add more write tools here as needed


def requires_approval(tool_name: str) -> bool:
    """Check if a tool requires human approval.
    
    Args:
        tool_name: Name of the tool being called
        
    Returns:
        True if the tool requires approval, False otherwise
    """
    return tool_name in WRITE_TOOLS


async def approval_node(state: State) -> Dict[str, Any]:
    """Request human approval for critical operations.
    
    This node pauses execution and asks for human approval before
    executing write operations on the document.
    
    Args:
        state (State): The current state of the conversation.
        
    Returns:
        dict: Updated state with approved operation or rejection message.
    """
    last_message = state.messages[-1]
    
    if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
        return {}
    
    # Check if any tool calls require approval
    tool_calls_needing_approval = [
        tc for tc in last_message.tool_calls 
        if requires_approval(tc["name"])
    ]
    
    if not tool_calls_needing_approval:
        # No approval needed, proceed to tools
        return {}
    
    # For now, handle the first tool call that needs approval
    tool_call = tool_calls_needing_approval[0]
    tool_name = tool_call["name"]
    tool_args = tool_call["args"]
    
    # Create a human-readable description of the operation
    if tool_name == "apply_edit":
        anchor = tool_args.get("anchor", [])
        new_text = tool_args.get("new_text", "")
        description = (
            f"**Edit Operation**\n"
            f"- Location: {anchor}\n"
            f"- New text: {new_text[:100]}{'...' if len(new_text) > 100 else ''}\n\n"
            f"Do you approve this change? (yes/no)"
        )
    else:
        description = f"Approve {tool_name} with args: {tool_args}? (yes/no)"
    
    # Interrupt and wait for human approval
    approval = interrupt(
        {
            "type": "approval_request",
            "tool_name": tool_name,
            "tool_call_id": tool_call["id"],
            "args": tool_args,
            "description": description
        }
    )
    
    # Process approval response
    if isinstance(approval, str):
        approval = approval.lower().strip()
    
    if approval in ["yes", "y", "approve", "approved", "true"]:
        # Approval granted - proceed with the operation
        return {"pending_operation": None}
    else:
        # Approval denied - create tool messages for all tool calls
        # We need to respond to ALL tool calls, not just the rejected one
        tool_messages = []
        
        for tc in last_message.tool_calls:
            if tc["id"] == tool_call["id"]:
                # This is the rejected tool
                tool_messages.append(ToolMessage(
                    content=f"Operation cancelled by user. The {tc['name']} operation was not executed.",
                    tool_call_id=tc["id"],
                    name=tc["name"]
                ))
            else:
                # Other tool calls should also get rejection messages
                tool_messages.append(ToolMessage(
                    content=f"Skipped due to user rejection of {tool_name}.",
                    tool_call_id=tc["id"],
                    name=tc["name"]
                ))
        
        return {
            "messages": tool_messages,
            "pending_operation": None
        }


def route_model_output(state: State) -> Literal["__end__", "tools", "approval_node"]:
    """Determine the next node based on the model's output.

    This function checks if the model's last message contains tool calls
    and routes to approval if needed.

    Args:
        state (State): The current state of the conversation.

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
        requires_approval(tc["name"]) for tc in last_message.tool_calls
    )
    
    if needs_approval:
        return "approval_node"
    
    # No approval needed, execute tools directly
    return "tools"


def route_approval(state: State) -> Literal["tools", "call_model"]:
    """Route after approval node.
    
    If approval was granted, go to tools. If rejected, go back to call_model.
    
    Args:
        state (State): The current state.
        
    Returns:
        str: Next node to call.
    """
    # Check if the last message is a rejection (ToolMessage added by approval_node)
    if state.messages and isinstance(state.messages[-1], ToolMessage):
        # Rejection message was added, go back to model
        return "call_model"
    
    # Approval granted, proceed to execute tools
    return "tools"


# Define and build the graph

builder = StateGraph(State, input_schema=InputState)

# Define the nodes
builder.add_node(call_model)
builder.add_node("approval_node", approval_node)
builder.add_node("tools", ToolNode(TOOLS))

# Set the entrypoint as `call_model`
# This means that this node is the first one called
builder.add_edge("__start__", "call_model")

# Add a conditional edge to determine the next step after `call_model`
builder.add_conditional_edges(
    "call_model",
    # After call_model finishes running, the next node(s) are scheduled
    # based on the output from route_model_output
    route_model_output,
)

# Add conditional edge from approval_node
builder.add_conditional_edges(
    "approval_node",
    route_approval,
)

# Add a normal edge from `tools` to `call_model`
# This creates a cycle: after using tools, we always return to the model
builder.add_edge("tools", "call_model")

# Compile the builder into an executable graph
graph = builder.compile(name="ReAct Agent")
