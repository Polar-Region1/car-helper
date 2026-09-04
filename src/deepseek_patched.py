"""Compatibility patch for DeepSeek ``reasoning_content`` streaming.

This module touches private ``langchain-openai`` helpers and therefore must stay
small, version-tested and idempotent.
"""

from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_openai.chat_models import base


_PATCH_MARKER = "_car_helper_reasoning_patch"


def apply_patches():
    if getattr(base, _PATCH_MARKER, False):
        return

    original_to_message = base._convert_dict_to_message
    original_to_dict = base._convert_message_to_dict
    original_format = base._format_message_content
    original_delta = base._convert_delta_to_message_chunk

    def convert_dict_to_message(payload):
        message = original_to_message(payload)
        if isinstance(message, AIMessage) and "reasoning_content" in payload:
            message.additional_kwargs["reasoning_content"] = payload["reasoning_content"]
        return message

    def convert_message_to_dict(message, api="chat/completions"):
        payload = original_to_dict(message, api)
        if isinstance(message, AIMessage):
            reasoning = message.additional_kwargs.get("reasoning_content")
            if reasoning:
                payload["reasoning_content"] = reasoning
        return payload

    def format_message_content(content, api="chat/completions", role=None):
        result = original_format(content, api, role)
        if isinstance(content, list) and isinstance(result, list):
            for block in content:
                if (
                    isinstance(block, dict)
                    and block.get("type") == "reasoning_content"
                    and block not in result
                ):
                    result.append(block)
        return result

    def convert_delta_to_message_chunk(payload, default_class):
        message = original_delta(payload, default_class)
        if isinstance(message, AIMessageChunk) and "reasoning_content" in payload:
            message.additional_kwargs["reasoning_content"] = payload["reasoning_content"]
        return message

    base._convert_dict_to_message = convert_dict_to_message
    base._convert_message_to_dict = convert_message_to_dict
    base._format_message_content = format_message_content
    base._convert_delta_to_message_chunk = convert_delta_to_message_chunk
    setattr(base, _PATCH_MARKER, True)
