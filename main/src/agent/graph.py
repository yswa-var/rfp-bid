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

from context import Context
from state import InputState, State
from tools import TOOLS
from utils import load_chat_model
from graph_factory import create_approval_graph

# Define the function that calls the model


async def call_model(
    state: State, runtime: Runtime[Context]
) -> Dict[str, List[AIMessage]]:
    """Call the LLM powering our "agent".

    This function prepares the prompt, initializes the model, and processes the response.

    Args:
        state (State): The current state of the conversation.
        runtime (Runtime[Context]): Runtime context containing configuration.

    Returns:
        dict: A dictionary containing the model's response message.
    """
    try:
        # Initialize the model with tool binding. Change the model or add more tools here.
        model = load_chat_model(runtime.context.model).bind_tools(TOOLS)

        # Format the system prompt. Customize this to change the agent's behavior.
        system_message = runtime.context.system_prompt.format(
            system_time=datetime.now(tz=UTC).isoformat()
        )

        # Get the model's response
        response = await model.ainvoke(
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


# Configuration for the approval system
WRITE_TOOLS = {"apply_edit"}  # Tools that require human approval

# Create the graph using the modular factory
graph = create_approval_graph(
    call_model_func=call_model,
    tools=TOOLS,
    write_tools=WRITE_TOOLS,
    graph_name="ReAct Agent"
)