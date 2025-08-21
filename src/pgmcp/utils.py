
from typing import cast

from fastmcp.client.sampling import SamplingMessage
from mcp.types import PromptMessage, TextContent


def convert_sample_message_from_prompt_message(prompt_message: PromptMessage) -> SamplingMessage:
    """Convert a FastMCP PromptMessage to a FactMCP SamplingMessage."""
    if not isinstance(prompt_message, PromptMessage):
        raise ValueError(f"Expected PromptMessage, got {type(prompt_message)}")
    content = str(prompt_message.content)
    if not content:
        raise ValueError("PromptMessage content cannot be empty.")
    if not prompt_message.role:
        raise ValueError("PromptMessage role cannot be empty.")
    content = cast(TextContent, prompt_message.content)
    return SamplingMessage(role=prompt_message.role, content=content)


