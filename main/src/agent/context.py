"""Context schema for the ReAct agent system."""

from typing import Optional
from typing_extensions import TypedDict


class Context(TypedDict):
    """Context schema for the ReAct agent system."""
    model: str
    system_prompt: str
    max_steps: Optional[int]
    is_last_step: Optional[bool]
