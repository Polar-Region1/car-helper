from langchain.tools import ToolRuntime

from src.memory import AgentContext, build_memory_context
from src.memory.middleware import build_system_prompt
from src.memory.tools import forget_user_preference, remember_user_preference
from src.storage import LocalStore


def create_runtime(store, profile_id, message):
    return ToolRuntime(
        state={"messages": [{"role": "user", "content": message}]},
        context=AgentContext(profile_id, "session_123", "", store),
        config={},
        stream_writer=lambda _: None,
        tool_call_id="tool_call_1",
        store=None,
    )


def test_memory_context_is_bounded_to_structured_facts():
    context = build_memory_context(
        [
            {
                "category": "energy_preference",
                "key": "preferred_energy",
                "value": "纯电动",
            }
        ]
    )
    prompt = build_system_prompt(context)

    assert "energy_preference/preferred_energy: 纯电动" in prompt
    assert "本轮明确表达的要求优先" in prompt


def test_memory_tool_schema_hides_runtime_context():
    remember_schema = remember_user_preference.tool_call_schema.model_json_schema()
    forget_schema = forget_user_preference.tool_call_schema.model_json_schema()

    assert set(remember_schema["properties"]) == {"category", "key", "value"}
    assert set(forget_schema["properties"]) == {"category", "key"}


async def test_memory_tools_use_injected_profile_and_thread(tmp_path):
    store = LocalStore(tmp_path / "car_helper.db")
    store.initialize()
    profile_id = store.get_default_profile()["profile_id"]
    store.upsert_conversation(profile_id, "session_123", "请记住我只考虑纯电车")
    runtime = create_runtime(store, profile_id, "请记住我以后都只考虑纯电车")

    remembered = await remember_user_preference.coroutine(
        category="energy_preference",
        key="preferred_energy",
        value="纯电动",
        runtime=runtime,
    )
    forget_runtime = create_runtime(store, profile_id, "请忘记我只考虑纯电车这项偏好")
    forgotten = await forget_user_preference.coroutine(
        category="energy_preference",
        key="preferred_energy",
        runtime=forget_runtime,
    )

    assert remembered["状态"] == "已保存"
    assert forgotten["状态"] == "已删除"
    assert store.list_memories(profile_id) == []


async def test_temporary_purchase_constraints_cannot_be_persisted(tmp_path):
    store = LocalStore(tmp_path / "car_helper.db")
    store.initialize()
    profile_id = store.get_default_profile()["profile_id"]
    store.upsert_conversation(profile_id, "session_123", "这次预算20万，给父母买车")

    for message, category, key, value in (
        ("这次预算20万", "budget_preference", "preferred_budget", "20万元"),
        ("给父母买车，想要SUV", "family_context", "buyer_context", "给父母买车"),
    ):
        result = await remember_user_preference.coroutine(
            category=category,
            key=key,
            value=value,
            runtime=create_runtime(store, profile_id, message),
        )
        assert result.startswith("长期记忆未保存")

    assert store.list_memories(profile_id) == []


async def test_memory_cannot_be_forgotten_without_explicit_user_intent(tmp_path):
    store = LocalStore(tmp_path / "car_helper.db")
    store.initialize()
    profile_id = store.get_default_profile()["profile_id"]
    store.upsert_conversation(profile_id, "session_123", "请记住我以后都只考虑纯电车")
    store.remember(
        profile_id,
        category="energy_preference",
        key="preferred_energy",
        value="纯电动",
        source_thread_id="session_123",
    )

    result = await forget_user_preference.coroutine(
        category="energy_preference",
        key="preferred_energy",
        runtime=create_runtime(store, profile_id, "这次可以看看混动车"),
    )

    assert result.startswith("长期记忆未删除")
    assert len(store.list_memories(profile_id)) == 1
