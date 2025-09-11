"""Tool helpers for supervisor handoffs."""

from langchain_core.tools import tool
from langgraph.types import Command, Send

from .state import MessagesState


def create_handoff_tool(*, agent_name: str, description: str | None = None):
    """Create a tool that hands off control to a worker agent via Send."""
    name = f"transfer_to_{agent_name}"
    description = description or f"Ask {agent_name} for help."

    @tool(name, description=description)
    def handoff_tool(state: MessagesState) -> Command:
        return Command(goto=[Send(agent_name, state)], graph=Command.PARENT)

    return handoff_tool


