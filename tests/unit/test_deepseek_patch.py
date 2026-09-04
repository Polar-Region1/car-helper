from langchain_core.messages import AIMessageChunk
from langchain_openai.chat_models import base

from src.deepseek_patched import apply_patches


def test_reasoning_patch_is_effective_and_idempotent():
    apply_patches()
    patched_converter = base._convert_delta_to_message_chunk
    apply_patches()

    message = base._convert_delta_to_message_chunk(
        {"role": "assistant", "content": "", "reasoning_content": "分析"},
        AIMessageChunk,
    )

    assert base._convert_delta_to_message_chunk is patched_converter
    assert message.additional_kwargs["reasoning_content"] == "分析"
