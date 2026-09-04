import asyncio
import re
from typing import Annotated, Literal

from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from pydantic import Field

from src.storage import MemoryValidationError, ProfileOwnershipError


MemoryCategory = Literal[
    "budget_preference",
    "energy_preference",
    "body_type_preference",
    "brand_preference",
    "usage_preference",
    "family_context",
    "charging_context",
    "excluded_feature",
    "other",
]
MemoryKey = Annotated[
    str,
    Field(
        min_length=1,
        max_length=64,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="稳定的英文记忆键，例如 preferred_energy",
    ),
]
MemoryValue = Annotated[
    str,
    Field(min_length=1, max_length=500, description="用户明确表达的长期偏好"),
]

_REMEMBER_INTENT_PATTERNS = (
    r"记住",
    r"记一下",
    r"记下来",
    r"帮我记",
    r"保存(?:这个|这项|我的)(?:偏好|习惯|信息|设置)?",
    r"长期(?:保存|记住|保留|记忆)",
    r"(?:以后|今后)(?:都|一直|总是|默认)",
    r"从今(?:以后|往后)",
    r"一直(?:都)?(?:喜欢|偏好|选择|只考虑|不考虑)",
    r"\bremember\b",
)
_FORGET_INTENT_PATTERNS = (
    r"忘记",
    r"别记",
    r"不要记",
    r"不再记",
    r"(?:删除|清除|移除|取消).{0,8}(?:记忆|偏好|记录)",
    r"\bforget\b",
)


def _content_to_text(content) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and isinstance(block.get("text"), str):
            parts.append(block["text"])
    return "".join(parts)


def _latest_user_message(runtime: ToolRuntime) -> str:
    state = runtime.state
    messages = state.get("messages", []) if hasattr(state, "get") else []
    for message in reversed(messages):
        if isinstance(message, dict):
            message_type = message.get("role") or message.get("type")
            content = message.get("content", "")
        else:
            message_type = getattr(message, "type", "")
            content = getattr(message, "content", "")
        if message_type in {"user", "human"}:
            return _content_to_text(content).strip()
    return ""


def _matches_intent(text: str, patterns: tuple[str, ...]) -> bool:
    lowered = text.lower()
    compact = re.sub(r"\s+", "", lowered)
    return any(
        re.search(pattern, lowered) or re.search(pattern, compact)
        for pattern in patterns
    )


@tool
async def remember_user_preference(
    category: MemoryCategory,
    key: MemoryKey,
    value: MemoryValue,
    runtime: ToolRuntime,
) -> dict | str:
    """保存用户明确要求记住的、跨选车会话仍然成立的稳定偏好。

    只有用户明确说“记住”“以后都”“长期偏好”等意思时才能调用。
    当前预算、代他人选车、本轮候选和临时限制不得写入长期记忆。
    """
    context = runtime.context
    if context is None:
        return "长期记忆上下文不可用。"
    user_message = _latest_user_message(runtime)
    if _matches_intent(user_message, _FORGET_INTENT_PATTERNS):
        return "长期记忆未保存：本轮表达的是删除或取消记忆。"
    if not _matches_intent(user_message, _REMEMBER_INTENT_PATTERNS):
        return "长期记忆未保存：用户本轮没有明确要求持久保存该偏好。"
    try:
        memory = await asyncio.to_thread(
            context.local_store.remember,
            context.profile_id,
            category=category,
            key=key,
            value=value,
            source_thread_id=context.thread_id,
        )
    except (MemoryValidationError, ProfileOwnershipError) as exc:
        return f"长期记忆未保存：{exc}"
    return {
        "状态": "已保存",
        "记忆ID": memory["memory_id"],
        "分类": memory["category"],
        "键": memory["key"],
        "内容": memory["value"],
    }


@tool
async def forget_user_preference(
    category: MemoryCategory,
    key: MemoryKey,
    runtime: ToolRuntime,
) -> dict | str:
    """删除用户明确要求忘记的长期偏好；不得用于清除当前会话上下文。"""
    context = runtime.context
    if context is None:
        return "长期记忆上下文不可用。"
    user_message = _latest_user_message(runtime)
    if not _matches_intent(user_message, _FORGET_INTENT_PATTERNS):
        return "长期记忆未删除：用户本轮没有明确要求删除该记忆。"
    try:
        deleted = await asyncio.to_thread(
            context.local_store.forget,
            context.profile_id,
            category=category,
            key=key,
        )
    except MemoryValidationError as exc:
        return f"长期记忆未删除：{exc}"
    return {"状态": "已删除" if deleted else "未找到", "分类": category, "键": key}
