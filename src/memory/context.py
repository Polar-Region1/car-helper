from dataclasses import dataclass

from src.storage import LocalStore


@dataclass(frozen=True)
class AgentContext:
    profile_id: str
    thread_id: str
    memory_context: str
    local_store: LocalStore


def build_memory_context(memories: list[dict]):
    if not memories:
        return ""
    lines = ["# 当前用户已确认的长期记忆"]
    for memory in memories:
        lines.append(f"- {memory['category']}/{memory['key']}: {memory['value']}")
    lines.extend(
        [
            "",
            "使用规则：当前用户本轮明确表达的要求优先于长期记忆；仅在相关时使用这些偏好，"
            "不要主动复述整份记忆。",
        ]
    )
    return "\n".join(lines)
