"""Shared state types for the multi-agent system."""

from typing import List, Optional, Any
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage
from langchain_core.documents import Document


class MessagesState(TypedDict):
    """State schema for the multi-agent system."""
    messages: List[BaseMessage]
    chunks: List[Document]
    pdf_paths: List[str]
    task_completed: bool  # Track if current task is completed
    iteration_count: int  # Track iterations to prevent infinite loops
    confidence_score: Optional[int]  # Confidence score from document analysis
    follow_up_questions: List[str]  # Follow-up questions from the assistant
    parsed_response: Optional[Any]  # Structured response from Pydantic parser
    
    # Proposal Supervisor state tracking
    teams_completed: Optional[set]  # Set of completed team names
    team_responses: Optional[dict]  # Dictionary of team responses
    team_sequence: Optional[List[str]]  # Planned team execution sequence
    next_team: Optional[str]  # Next team to execute
    rfp_content: Optional[str]  # Current RFP content being processed


class State(TypedDict):
    """State schema for the ReAct agent system."""
    messages: List[BaseMessage]
    is_last_step: Optional[bool]


class InputState(TypedDict):
    """Input state schema for the ReAct agent system."""
    messages: List[BaseMessage]


