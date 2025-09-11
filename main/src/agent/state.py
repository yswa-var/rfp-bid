"""Shared state types for the multi-agent system."""

from typing import List, Optional, Any, Union
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage
from langchain_core.documents import Document


class MessagesState(TypedDict):
    """State schema for the multi-agent system."""
    messages: List[BaseMessage]
    chunks: List[Document]
    pdf_paths: List[str]
    uploaded_files: List[Any]  # Files uploaded through LangGraph Studio UI
    task_completed: bool  # Track if current task is completed
    iteration_count: int  # Track iterations to prevent infinite loops
    confidence_score: Optional[int]  # Confidence score from document analysis
    follow_up_questions: List[str]  # Follow-up questions from the assistant
    parsed_response: Optional[Any]  # Structured response from Pydantic parser


