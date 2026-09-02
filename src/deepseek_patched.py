from langchain_openai.chat_models import base
from langchain_core.messages import AIMessage, AIMessageChunk


_original_to_message = base._convert_dict_to_message
def _new_convert_dict_to_message(_dict):
    msg = _original_to_message(_dict)
    if isinstance(msg, AIMessage) and "reasoning_content" in _dict:
        msg.additional_kwargs["reasoning_content"] = _dict["reasoning_content"]
    return msg

_original_to_dict = base._convert_message_to_dict
def _new_convert_message_to_dict(message, api="chat/completions"):
    msg_dict = _original_to_dict(message, api)
    if isinstance(message, AIMessage) and "reasoning_content" in message.additional_kwargs:
        msg_dict["reasoning_content"] = message.additional_kwargs["reasoning_content"]
    return msg_dict

_original_format = base._format_message_content
def _new_format_message_content(content, api="chat/completions", role=None):
    result = _original_format(content, api, role)
    if content and isinstance(content, list) and isinstance(result, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "reasoning_content":
                result.append(block)
    return result

_original_delta = base._convert_delta_to_message_chunk
def _new_convert_delta_to_message_chunk(_dict, default_class):
    msg = _original_delta(_dict, default_class)
    if isinstance(msg, AIMessageChunk) and "reasoning_content" in _dict:
        msg.additional_kwargs["reasoning_content"] = _dict["reasoning_content"]
    return msg


def apply_patches():
    base._convert_dict_to_message = _new_convert_dict_to_message
    base._convert_message_to_dict = _new_convert_message_to_dict
    base._format_message_content = _new_format_message_content
    base._convert_delta_to_message_chunk = _new_convert_delta_to_message_chunk
