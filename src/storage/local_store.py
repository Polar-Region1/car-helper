import json
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path


SCHEMA_VERSION = 1
MAX_ACTIVE_MEMORIES = 100
MAX_MEMORY_VALUE_LENGTH = 500
MEMORY_CATEGORIES = frozenset(
    {
        "budget_preference",
        "energy_preference",
        "body_type_preference",
        "brand_preference",
        "usage_preference",
        "family_context",
        "charging_context",
        "excluded_feature",
        "other",
    }
)
MEMORY_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


class ProfileOwnershipError(ValueError):
    """Raised when a conversation belongs to another local profile."""


class MemoryValidationError(ValueError):
    """Raised when a long-term memory violates storage policy."""


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _encode_memory_value(value: str) -> str:
    value = value.strip()
    if not value or len(value) > MAX_MEMORY_VALUE_LENGTH:
        raise MemoryValidationError(
            f"记忆内容长度必须在 1 到 {MAX_MEMORY_VALUE_LENGTH} 个字符之间。"
        )
    return json.dumps(value, ensure_ascii=False)


class LocalStore:
    """SQLite-backed local identity, conversation directory and memory store."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version > SCHEMA_VERSION:
                raise RuntimeError(
                    f"本地数据库版本 {version} 高于程序支持版本 {SCHEMA_VERSION}。"
                )
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS profiles (
                    profile_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    is_default INTEGER NOT NULL DEFAULT 0 CHECK (is_default IN (0, 1)),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE UNIQUE INDEX IF NOT EXISTS one_default_profile
                ON profiles(is_default) WHERE is_default = 1;

                CREATE TABLE IF NOT EXISTS conversations (
                    thread_id TEXT PRIMARY KEY,
                    profile_id TEXT NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    last_query TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS conversations_by_profile
                ON conversations(profile_id, updated_at DESC);

                CREATE TABLE IF NOT EXISTS memories (
                    memory_id TEXT PRIMARY KEY,
                    profile_id TEXT NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,
                    category TEXT NOT NULL,
                    memory_key TEXT NOT NULL,
                    value_json TEXT NOT NULL,
                    confidence REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
                    source_type TEXT NOT NULL CHECK (source_type IN ('explicit', 'confirmed')),
                    source_thread_id TEXT REFERENCES conversations(thread_id) ON DELETE SET NULL,
                    status TEXT NOT NULL CHECK (status IN ('active', 'superseded')),
                    expires_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE UNIQUE INDEX IF NOT EXISTS one_active_memory_per_key
                ON memories(profile_id, category, memory_key) WHERE status = 'active';

                CREATE INDEX IF NOT EXISTS active_memories_by_profile
                ON memories(profile_id, status, updated_at DESC);
                """
            )
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            if not connection.execute(
                "SELECT 1 FROM profiles WHERE is_default = 1"
            ).fetchone():
                now = _now()
                connection.execute(
                    """
                    INSERT INTO profiles (
                        profile_id, display_name, is_default, created_at, updated_at
                    ) VALUES (?, ?, 1, ?, ?)
                    """,
                    (str(uuid.uuid4()), "本地用户", now, now),
                )

    def get_default_profile(self):
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT profile_id, display_name, created_at, updated_at
                FROM profiles WHERE is_default = 1
                """
            ).fetchone()
        if row is None:
            raise RuntimeError("本地默认用户尚未初始化。")
        return dict(row)

    def upsert_conversation(self, profile_id: str, thread_id: str, query: str):
        query = query.strip()
        if not query:
            raise ValueError("会话问题不能为空。")
        now = _now()
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT profile_id FROM conversations WHERE thread_id = ?",
                (thread_id,),
            ).fetchone()
            if existing and existing["profile_id"] != profile_id:
                raise ProfileOwnershipError("该会话属于其他本地用户。")
            connection.execute(
                """
                INSERT INTO conversations (
                    thread_id, profile_id, title, last_query, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(thread_id) DO UPDATE SET
                    last_query = excluded.last_query,
                    updated_at = excluded.updated_at
                """,
                (thread_id, profile_id, query, query, now, now),
            )

    def list_conversations(self, profile_id: str):
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT thread_id AS id, title, last_query,
                       created_at AS create_time, updated_at AS update_time
                FROM conversations
                WHERE profile_id = ?
                ORDER BY updated_at DESC
                """,
                (profile_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def owns_conversation(self, profile_id: str, thread_id: str):
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT 1 FROM conversations
                WHERE profile_id = ? AND thread_id = ?
                """,
                (profile_id, thread_id),
            ).fetchone()
        return row is not None

    def delete_conversation(self, profile_id: str, thread_id: str):
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM conversations WHERE profile_id = ? AND thread_id = ?",
                (profile_id, thread_id),
            )
        return cursor.rowcount > 0

    def remember(
        self,
        profile_id: str,
        *,
        category: str,
        key: str,
        value: str,
        source_thread_id: str,
        source_type: str = "explicit",
        confidence: float = 1.0,
        expires_at: str | None = None,
    ):
        if category not in MEMORY_CATEGORIES:
            raise MemoryValidationError("不支持的长期记忆分类。")
        if not MEMORY_KEY_PATTERN.fullmatch(key):
            raise MemoryValidationError("记忆键必须使用小写英文、数字和下划线。")
        if source_type not in {"explicit", "confirmed"}:
            raise MemoryValidationError("不支持的记忆来源类型。")
        if not 0 <= confidence <= 1:
            raise MemoryValidationError("记忆置信度必须在 0 到 1 之间。")

        encoded_value = _encode_memory_value(value)
        now = _now()
        with self._connect() as connection:
            if not connection.execute(
                """
                SELECT 1 FROM conversations
                WHERE profile_id = ? AND thread_id = ?
                """,
                (profile_id, source_thread_id),
            ).fetchone():
                raise ProfileOwnershipError("记忆来源会话不属于当前用户。")

            current = connection.execute(
                """
                SELECT memory_id, value_json FROM memories
                WHERE profile_id = ? AND category = ? AND memory_key = ?
                  AND status = 'active'
                """,
                (profile_id, category, key),
            ).fetchone()
            if current and current["value_json"] == encoded_value:
                connection.execute(
                    """
                    UPDATE memories SET source_thread_id = ?, source_type = ?,
                        confidence = ?, updated_at = ?, expires_at = ?
                    WHERE memory_id = ?
                    """,
                    (
                        source_thread_id,
                        source_type,
                        confidence,
                        now,
                        expires_at,
                        current["memory_id"],
                    ),
                )
                memory_id = current["memory_id"]
            else:
                if current:
                    connection.execute(
                        """
                        UPDATE memories SET status = 'superseded', updated_at = ?
                        WHERE memory_id = ?
                        """,
                        (now, current["memory_id"]),
                    )
                active_count = connection.execute(
                    """
                    SELECT count(*) FROM memories
                    WHERE profile_id = ? AND status = 'active'
                      AND (expires_at IS NULL OR expires_at > ?)
                    """,
                    (profile_id, now),
                ).fetchone()[0]
                if active_count >= MAX_ACTIVE_MEMORIES:
                    raise MemoryValidationError("长期记忆数量已达到上限。")
                memory_id = str(uuid.uuid4())
                connection.execute(
                    """
                    INSERT INTO memories (
                        memory_id, profile_id, category, memory_key, value_json,
                        confidence, source_type, source_thread_id, status,
                        expires_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)
                    """,
                    (
                        memory_id,
                        profile_id,
                        category,
                        key,
                        encoded_value,
                        confidence,
                        source_type,
                        source_thread_id,
                        expires_at,
                        now,
                        now,
                    ),
                )
        return self.get_memory(profile_id, memory_id)

    def get_memory(self, profile_id: str, memory_id: str):
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT memory_id, category, memory_key, value_json, confidence,
                       source_type, source_thread_id, status, expires_at,
                       created_at, updated_at
                FROM memories WHERE profile_id = ? AND memory_id = ?
                """,
                (profile_id, memory_id),
            ).fetchone()
        return self._decode_memory(row) if row else None

    def list_memories(self, profile_id: str, *, limit: int = 100):
        limit = max(1, min(limit, MAX_ACTIVE_MEMORIES))
        now = _now()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT memory_id, category, memory_key, value_json, confidence,
                       source_type, source_thread_id, status, expires_at,
                       created_at, updated_at
                FROM memories
                WHERE profile_id = ? AND status = 'active'
                  AND (expires_at IS NULL OR expires_at > ?)
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (profile_id, now, limit),
            ).fetchall()
        return [self._decode_memory(row) for row in rows]

    def update_memory(self, profile_id: str, memory_id: str, *, value: str):
        encoded_value = _encode_memory_value(value)
        now = _now()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE memories
                SET value_json = ?, source_type = 'confirmed', confidence = 1.0,
                    updated_at = ?
                WHERE profile_id = ? AND memory_id = ? AND status = 'active'
                  AND (expires_at IS NULL OR expires_at > ?)
                """,
                (encoded_value, now, profile_id, memory_id, now),
            )
        if cursor.rowcount == 0:
            return None
        return self.get_memory(profile_id, memory_id)

    def forget(
        self,
        profile_id: str,
        *,
        memory_id: str | None = None,
        category: str | None = None,
        key: str | None = None,
    ):
        if memory_id:
            statement = "DELETE FROM memories WHERE profile_id = ? AND memory_id = ?"
            params = (profile_id, memory_id)
        elif category and key:
            statement = (
                "DELETE FROM memories WHERE profile_id = ? AND category = ? "
                "AND memory_key = ? AND status = 'active'"
            )
            params = (profile_id, category, key)
        else:
            raise MemoryValidationError("删除记忆需要 memory_id 或分类与键。")
        with self._connect() as connection:
            cursor = connection.execute(statement, params)
        return cursor.rowcount > 0

    @staticmethod
    def _decode_memory(row):
        memory = dict(row)
        memory["key"] = memory.pop("memory_key")
        memory["value"] = json.loads(memory.pop("value_json"))
        return memory


def create_local_store(path: str | Path):
    store = LocalStore(path)
    store.initialize()
    return store
