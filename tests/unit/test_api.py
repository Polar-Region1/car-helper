import asyncio

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessageChunk

import src.api as api_module
from src.storage import MemoryValidationError


class FakePool:
    async def close(self):
        return None


class FakeCheckpointer:
    def __init__(self):
        self.deleted = []

    async def aget_tuple(self, config):
        return None

    async def adelete_thread(self, thread_id):
        self.deleted.append(thread_id)


class FakeAgent:
    async def astream_events(self, payload, config, context, version):
        assert context.profile_id == "profile_123"
        assert context.thread_id == config["configurable"]["thread_id"]
        yield {"event": "on_tool_start", "name": "query_by_brand", "data": {"input": {}}}
        yield {
            "event": "on_tool_end",
            "name": "query_by_brand",
            "data": {
                "output": {
                    "数据": [
                        {
                            "品牌": "比亚迪",
                            "车系": "秦",
                            "车型": "秦PLUS",
                            "指导价": "12.98万",
                            "能源类型": "插电式混合动力",
                            "级别": "紧凑型车",
                        }
                    ]
                }
            },
        }
        yield {
            "event": "on_chat_model_stream",
            "data": {
                "chunk": AIMessageChunk(
                    content="推荐结果",
                    additional_kwargs={"reasoning_content": "检索完成"},
                )
            },
        }


class FakeLocalStore:
    def __init__(self):
        self.conversations = set()
        self.memories = [
            {
                "memory_id": "11111111-1111-1111-1111-111111111111",
                "category": "energy_preference",
                "key": "preferred_energy",
                "value": "纯电动",
            }
        ]

    def get_default_profile(self):
        return {"profile_id": "profile_123", "display_name": "本地用户"}

    def upsert_conversation(self, profile_id, thread_id, query):
        assert profile_id == "profile_123"
        self.conversations.add(thread_id)

    def list_conversations(self, profile_id):
        return []

    def owns_conversation(self, profile_id, thread_id):
        return thread_id in self.conversations

    def delete_conversation(self, profile_id, thread_id):
        self.conversations.discard(thread_id)
        return True

    def list_memories(self, profile_id, limit=100):
        return self.memories[:limit]

    def update_memory(self, profile_id, memory_id, *, value):
        value = value.strip()
        if not value:
            raise MemoryValidationError("记忆内容长度必须在 1 到 500 个字符之间。")
        for index, memory in enumerate(self.memories):
            if memory["memory_id"] == memory_id:
                updated = {**memory, "value": value, "source_type": "confirmed"}
                self.memories[index] = updated
                return updated
        return None

    def forget(self, profile_id, *, memory_id=None, category=None, key=None):
        before = len(self.memories)
        self.memories = [item for item in self.memories if item["memory_id"] != memory_id]
        return len(self.memories) < before


def configure_app(monkeypatch, local_store=None):
    checkpointer = FakeCheckpointer()
    local_store = local_store or FakeLocalStore()

    async def fake_session_store():
        return FakePool(), checkpointer

    monkeypatch.setattr(api_module, "create_session_store", fake_session_store)
    monkeypatch.setattr(api_module, "create_local_store", lambda path: local_store)
    monkeypatch.setattr(api_module, "create_car_agent", lambda checkpointer: FakeAgent())
    return local_store, checkpointer


def test_extract_cars_accepts_dict_and_uses_normalized_price_key():
    cars = api_module._extract_cars_from_result(
        {"数据": [{"品牌": "A", "车系": "S", "车型": "M", "指导价": "9.9万"}]}
    )
    assert cars[0]["price"] == "9.9万"


def test_chat_stream_emits_complete_event_contract(monkeypatch):
    configure_app(monkeypatch)

    with TestClient(api_module.app) as client:
        response = client.post(
            "/api/chat",
            json={"message": "比亚迪有什么车", "session_id": "session_123"},
        )

    assert response.status_code == 200
    for event in ("connected", "tool_start", "tool_end", "cars_data", "reasoning", "content", "done"):
        assert f"event: {event}" in response.text
    assert "12.98万" in response.text


def test_invalid_session_id_is_rejected(monkeypatch):
    configure_app(monkeypatch)
    with TestClient(api_module.app) as client:
        response = client.post(
            "/api/chat",
            json={"message": "hello", "session_id": "../escape"},
        )
    assert response.status_code == 422


def test_profile_and_memory_endpoints_use_local_identity(monkeypatch):
    local_store, _ = configure_app(monkeypatch)

    with TestClient(api_module.app) as client:
        profile = client.get("/api/profile")
        memories = client.get("/api/memories")
        updated = client.patch(
            "/api/memories/11111111-1111-1111-1111-111111111111",
            json={"value": "插电式混合动力"},
        )
        deleted = client.delete(
            "/api/memories/11111111-1111-1111-1111-111111111111"
        )

    assert profile.json()["profile_id"] == "profile_123"
    assert memories.json()["memories"][0]["value"] == "纯电动"
    assert updated.status_code == 200
    assert updated.json()["value"] == "插电式混合动力"
    assert updated.json()["source_type"] == "confirmed"
    assert deleted.status_code == 200
    assert local_store.memories == []


def test_memory_update_rejects_blank_content_and_unknown_id(monkeypatch):
    configure_app(monkeypatch)

    with TestClient(api_module.app) as client:
        blank = client.patch(
            "/api/memories/11111111-1111-1111-1111-111111111111",
            json={"value": "   "},
        )
        missing = client.patch(
            "/api/memories/22222222-2222-2222-2222-222222222222",
            json={"value": "纯电动"},
        )

    assert blank.status_code == 422
    assert missing.status_code == 404


async def test_session_lock_is_shared_with_waiters_and_retired_afterward():
    class State:
        session_locks = {}
        session_locks_guard = asyncio.Lock()

    class App:
        state = State()

    active = 0
    max_active = 0
    first_entered = asyncio.Event()
    release_first = asyncio.Event()

    async def worker(wait=False):
        nonlocal active, max_active
        async with api_module._locked_session(App(), "session_123"):
            active += 1
            max_active = max(max_active, active)
            if wait:
                first_entered.set()
                await release_first.wait()
            active -= 1

    first = asyncio.create_task(worker(wait=True))
    await first_entered.wait()
    second = asyncio.create_task(worker())
    await asyncio.sleep(0)
    third = asyncio.create_task(worker())
    release_first.set()
    await asyncio.gather(first, second, third)

    assert max_active == 1
    assert State.session_locks == {}
