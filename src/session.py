import os
import uuid
import json
import time
import logging
from src.config import SESSION_ID_PATH, DB_URI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger(__name__)


def create_unique_session_id(session_id=None):
    if session_id:
        return session_id
    return str(uuid.uuid4())


def store_session_id(session_id, last_query):
    session_store_dict = {"session_ids": []}

    if not os.path.exists(SESSION_ID_PATH):
        _write_to_json(session_store_dict)

    session_infos = _read_from_json()

    if session_id in session_infos:
        original_last_query = session_infos[session_id]["last_query"]
        if last_query != original_last_query:
            session_infos[session_id]["last_query"] = last_query
            session_infos[session_id]["update_time"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    else:
        session_infos["session_ids"].append(session_id)
        session_infos[session_id] = {
            "create_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "update_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "last_query": last_query,
        }

    _write_to_json(session_infos)


async def store_session_to_db():
    connection_kwargs = {
        "autocommit": True,
        "prepare_threshold": 0,
    }
    pool = AsyncConnectionPool(
        conninfo=DB_URI,
        max_size=20,
        kwargs=connection_kwargs,
        open=False,
    )
    await pool.open()
    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()
    return pool, checkpointer


def resume_session():
    all_session_info = _read_from_json()
    session_ids = all_session_info.get("session_ids", [])

    if not session_ids:
        print("暂无会话历史")
        return None

    for i, sid in enumerate(session_ids, 1):
        session_data = all_session_info.get(sid, {})
        print(
            f"  [{i}]  {sid[:8]}... | \n"
            f"创建: {session_data.get('create_time', 'N/A')}\n"
            f"上次提问: {session_data.get('last_query', 'N/A')}\n\n"
        )
    print("-" * 50)

    try:
        choice = input("请输入恢复会话（0取消）: ").strip()
        if choice == "0" or choice == "":
            print("已取消")
            return None
        idx = int(choice) - 1
        if 0 <= idx < len(session_ids):
            return session_ids[idx]
        else:
            print("编号无效")
            return None
    except ValueError:
        print("请输入数字")
        return None


def _write_to_json(info):
    with open(SESSION_ID_PATH, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)


def delete_session(session_id):
    data = _read_from_json()
    if session_id not in data.get("session_ids", []):
        return False
    data["session_ids"].remove(session_id)
    data.pop(session_id, None)
    _write_to_json(data)
    return True


def _read_from_json():
    with open(SESSION_ID_PATH, "r", encoding="utf-8") as f:
        return json.load(f)
