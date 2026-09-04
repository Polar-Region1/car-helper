import uuid

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from src.config import DB_URI, POSTGRES_POOL_SIZE


def create_unique_session_id(session_id=None):
    return session_id or str(uuid.uuid4())


async def create_session_store():
    if not DB_URI:
        raise RuntimeError("缺少 DB_URI，请在 .env 中配置 PostgreSQL 连接。")
    pool = AsyncConnectionPool(
        conninfo=DB_URI,
        min_size=1,
        max_size=POSTGRES_POOL_SIZE,
        kwargs={"autocommit": True, "prepare_threshold": 0},
        open=False,
    )
    await pool.open()
    checkpointer = AsyncPostgresSaver(pool)
    try:
        await checkpointer.setup()
    except Exception:
        await pool.close()
        raise
    return pool, checkpointer


def resume_session(local_store, profile_id):
    sessions = local_store.list_conversations(profile_id)
    if not sessions:
        print("暂无会话历史")
        return None

    for index, session in enumerate(sessions, 1):
        print(
            f"  [{index}]  {session['id'][:8]}... |\n"
            f"标题: {session['title'] or 'N/A'}\n"
            f"创建: {session['create_time'] or 'N/A'}\n"
            f"上次提问: {session['last_query'] or 'N/A'}\n"
        )
    print("-" * 50)

    try:
        choice = input("请输入恢复会话（0取消）: ").strip()
        if choice in {"", "0"}:
            print("已取消")
            return None
        index = int(choice) - 1
    except ValueError:
        print("请输入数字")
        return None

    if 0 <= index < len(sessions):
        return sessions[index]["id"]
    print("编号无效")
    return None
