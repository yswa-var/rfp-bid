"""Define the configurable parameters for the agent."""

from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from typing import Annotated
from dotenv import load_dotenv

load_dotenv()

from . import prompts


@dataclass(kw_only=True)
class Context:
    """The context for the agent."""

    system_prompt: str = field(
        default=prompts.SYSTEM_PROMPT,
        metadata={
            "description": "The system prompt to use for the agent's interactions. "
            "This prompt sets the context and behavior for the agent."
        },
    )

    model: Annotated[str, {"__template_metadata__": {"kind": "llm"}}] = field(
        default="openai/gpt-3.5-turbo",
        metadata={
            "description": "The name of the language model to use for the agent's main interactions. "
            "Should be in the form: provider/model-name."
        },
    )

    def __post_init__(self) -> None:
        """Fetch env vars for attributes that were not passed as args."""
        for f in fields(self):
            if not f.init:
                continue

            if getattr(self, f.name) == f.default:
                # For model, check MODEL env var and format it properly
                if f.name == "model":
                    env_model = os.environ.get("MODEL", f.default)
                    # If env model doesn't have provider prefix, add it
                    if "/" not in env_model:
                        env_model = f"openai/{env_model}"
                    setattr(self, f.name, env_model)
                else:
                    setattr(self, f.name, os.environ.get(f.name.upper(), f.default))
