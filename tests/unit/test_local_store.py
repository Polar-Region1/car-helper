import sqlite3

import pytest

import src.storage.local_store as local_store_module
from src.storage import LocalStore, MemoryValidationError, ProfileOwnershipError


def create_store(tmp_path):
    store = LocalStore(tmp_path / "var" / "car_helper.db")
    store.initialize()
    return store


def test_default_profile_is_stable(tmp_path):
    store = create_store(tmp_path)
    first = store.get_default_profile()
    store.initialize()
    second = store.get_default_profile()

    assert first["profile_id"] == second["profile_id"]
    assert first["display_name"] == "本地用户"


def test_conversation_title_stays_on_first_query(tmp_path):
    store = create_store(tmp_path)
    profile_id = store.get_default_profile()["profile_id"]

    store.upsert_conversation(profile_id, "session_123", "第一次提问")
    store.upsert_conversation(profile_id, "session_123", "第二次提问")

    sessions = store.list_conversations(profile_id)
    assert sessions == [
        {
            "id": "session_123",
            "title": "第一次提问",
            "last_query": "第二次提问",
            "create_time": sessions[0]["create_time"],
            "update_time": sessions[0]["update_time"],
        }
    ]
    assert store.owns_conversation(profile_id, "session_123") is True
    assert store.delete_conversation(profile_id, "session_123") is True
    assert store.list_conversations(profile_id) == []


def test_memory_update_supersedes_old_value_and_can_be_forgotten(tmp_path):
    store = create_store(tmp_path)
    profile_id = store.get_default_profile()["profile_id"]
    store.upsert_conversation(profile_id, "session_123", "记住我只考虑纯电车")

    first = store.remember(
        profile_id,
        category="energy_preference",
        key="preferred_energy",
        value="纯电动",
        source_thread_id="session_123",
    )
    second = store.remember(
        profile_id,
        category="energy_preference",
        key="preferred_energy",
        value="插电式混合动力",
        source_thread_id="session_123",
    )

    assert first["memory_id"] != second["memory_id"]
    assert store.get_memory(profile_id, first["memory_id"])["status"] == "superseded"
    assert [item["value"] for item in store.list_memories(profile_id)] == [
        "插电式混合动力"
    ]
    assert store.forget(profile_id, memory_id=second["memory_id"]) is True
    assert store.list_memories(profile_id) == []


def test_deleting_source_conversation_keeps_memory(tmp_path):
    store = create_store(tmp_path)
    profile_id = store.get_default_profile()["profile_id"]
    store.upsert_conversation(profile_id, "session_123", "记住我不喜欢SUV")
    memory = store.remember(
        profile_id,
        category="excluded_feature",
        key="excluded_body_type",
        value="SUV",
        source_thread_id="session_123",
    )

    store.delete_conversation(profile_id, "session_123")

    saved = store.get_memory(profile_id, memory["memory_id"])
    assert saved["source_thread_id"] is None


def test_memory_content_can_be_updated_without_changing_its_identity(tmp_path):
    store = create_store(tmp_path)
    profile_id = store.get_default_profile()["profile_id"]
    store.upsert_conversation(profile_id, "session_123", "记住我喜欢纯电车")
    memory = store.remember(
        profile_id,
        category="energy_preference",
        key="preferred_energy",
        value="纯电动",
        source_thread_id="session_123",
    )

    updated = store.update_memory(
        profile_id,
        memory["memory_id"],
        value="插电式混合动力",
    )

    assert updated["memory_id"] == memory["memory_id"]
    assert updated["category"] == memory["category"]
    assert updated["key"] == memory["key"]
    assert updated["value"] == "插电式混合动力"
    assert updated["source_type"] == "confirmed"
    assert updated["source_thread_id"] == "session_123"


def test_memory_update_is_profile_scoped_and_validated(tmp_path):
    store = create_store(tmp_path)
    profile_id = store.get_default_profile()["profile_id"]
    store.upsert_conversation(profile_id, "session_123", "记住我喜欢纯电车")
    memory = store.remember(
        profile_id,
        category="energy_preference",
        key="preferred_energy",
        value="纯电动",
        source_thread_id="session_123",
    )

    assert store.update_memory("another_profile", memory["memory_id"], value="混动") is None
    with pytest.raises(MemoryValidationError, match="长度"):
        store.update_memory(profile_id, memory["memory_id"], value="   ")
    assert store.get_memory(profile_id, memory["memory_id"])["value"] == "纯电动"


def test_expired_memory_does_not_consume_active_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(local_store_module, "MAX_ACTIVE_MEMORIES", 1)
    store = create_store(tmp_path)
    profile_id = store.get_default_profile()["profile_id"]
    store.upsert_conversation(profile_id, "session_123", "记住偏好")
    store.remember(
        profile_id,
        category="brand_preference",
        key="preferred_brand",
        value="大众",
        source_thread_id="session_123",
        expires_at="2000-01-01T00:00:00+00:00",
    )

    current = store.remember(
        profile_id,
        category="energy_preference",
        key="preferred_energy",
        value="纯电动",
        source_thread_id="session_123",
    )

    assert current["value"] == "纯电动"
    assert [memory["value"] for memory in store.list_memories(profile_id)] == ["纯电动"]


def test_conversation_thread_cannot_move_between_profiles(tmp_path):
    store = create_store(tmp_path)
    first_profile = store.get_default_profile()["profile_id"]
    with store._connect() as connection:
        connection.execute(
            """
            INSERT INTO profiles (
                profile_id, display_name, is_default, created_at, updated_at
            ) VALUES ('profile_2', '第二用户', 0, 'now', 'now')
            """
        )
    store.upsert_conversation(first_profile, "session_123", "第一次提问")

    with pytest.raises(ProfileOwnershipError):
        store.upsert_conversation("profile_2", "session_123", "尝试接管会话")


def test_newer_schema_version_is_rejected(tmp_path):
    database_path = tmp_path / "future.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            f"PRAGMA user_version = {local_store_module.SCHEMA_VERSION + 1}"
        )

    with pytest.raises(RuntimeError, match="高于程序支持版本"):
        LocalStore(database_path).initialize()
