"""Utility functions for the ReAct agent system."""

import os
from langchain_openai import ChatOpenAI


def load_chat_model(model_name: str = None):
    """Load a chat model based on the model name.
    
    Args:
        model_name: Name of the model to load. If None, uses environment variable LLM_MODEL.
        
    Returns:
        Chat model instance
    """
    if model_name is None:
        model_name = os.getenv("LLM_MODEL", "gpt-4o-mini")
    
    # OpenAI models
    if model_name.startswith("gpt-"):
        return ChatOpenAI(
            model=model_name,
            temperature=0,
            api_key=os.getenv("OPENAI_API_KEY"),
        )
    
    # Anthropic models (if available)
    elif model_name.startswith("claude-"):
        try:
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model=model_name,
                temperature=0,
                api_key=os.getenv("ANTHROPIC_API_KEY"),
            )
        except ImportError:
            print("Warning: langchain_anthropic not available, falling back to OpenAI")
            return ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0,
                api_key=os.getenv("OPENAI_API_KEY"),
            )
    
    # Default to OpenAI
    else:
        return ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=os.getenv("OPENAI_API_KEY"),
        )
