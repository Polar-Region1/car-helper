import asyncio
import json
import logging
import os
import sys
import time
from contextlib import asynccontextmanager

# Windows: psycopg 异步必须用 SelectorEventLoop，但 uvicorn 在 Windows 上
# 默认用 ProactorEventLoop，需要 patch 其 loop factory
if sys.platform == "win32":
    import uvicorn.loops.asyncio as _uvloop_asyncio

    _uvloop_asyncio.asyncio_loop_factory = lambda use_subprocess=False: asyncio.SelectorEventLoop

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

from src.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DB_URI
from src.db.neo4j_conn import Neo4jConnection
from src.deepseek_patched import apply_patches
from src.session import create_unique_session_id, store_session_id, delete_session
from src.tools.neo4j_tools import (
    query_by_brand,
    query_by_price_range,
    query_by_energy_type,
    query_by_conditions,
    compare_models,
    query_by_maintenance_cost,
    explore_schema,
)
from src.tools.web_search import web_search
from src.prompts.system_prompt import SYSTEM_PROMPT

apply_patches()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ─── LLM 初始化 ──────────────────────────────────────────
llm = ChatOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    model="deepseek-chat",
    temperature=0.7,
    extra_body={"thinking": {"type": "enabled"}},
)

tools = [
    query_by_brand,
    query_by_price_range,
    query_by_energy_type,
    query_by_conditions,
    compare_models,
    query_by_maintenance_cost,
    explore_schema,
    web_search,
]

# ─── Neo4j 索引 ──────────────────────────────────────────
Neo4jConnection().ensure_indexes()

# ─── 会话缓存 ────────────────────────────────────────────
_agent_cache: dict[str, tuple] = {}


async def _get_or_create_agent(session_id: str):
    if session_id in _agent_cache:
        return _agent_cache[session_id]

    from src.session import store_session_to_db
    pool, checkpointer = await store_session_to_db()
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )
    _agent_cache[session_id] = (pool, checkpointer, agent)
    return pool, checkpointer, agent


async def _close_all_agents():
    for pool, _, _ in _agent_cache.values():
        try:
            await pool.close()
        except Exception:
            pass
    _agent_cache.clear()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await _close_all_agents()


app = FastAPI(title="Car Helper API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件
web_dir = os.path.join(os.path.dirname(__file__), "web")
if os.path.isdir(web_dir):
    app.mount("/static", StaticFiles(directory=web_dir), name="static")


def _sse(data: dict, event: str = "message") -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _extract_cars_from_result(result_str: str) -> list:
    """从工具返回结果中提取车型数据"""
    import json

    cars = []

    try:
        # 尝试直接解析JSON（工具返回的是字典转字符串）
        result_dict = eval(result_str)  # 或用 ast.literal_eval

        if isinstance(result_dict, dict) and "数据" in result_dict:
            raw_data = result_dict["数据"]

            for item in raw_data[:20]:  # 最多20个
                try:
                    name = f"{item.get('品牌', '')} {item.get('车系', '')} {item.get('车型', '')}".strip()
                    price = item.get('官方指导价', '暂无报价')
                    energy = item.get('能源类型', '未知')
                    level = item.get('级别', '未知')

                    # 简单判断badge
                    badge = None
                    if '新能源' in energy or '纯电' in energy:
                        badge = '新能源'

                    cars.append({
                        "name": name,
                        "price": price,
                        "energy": energy,
                        "level": level,
                        "badge": badge
                    })
                except Exception as e:
                    logger.debug(f"Failed to parse car item: {e}")
                    continue

    except Exception as e:
        logger.debug(f"Failed to parse result as dict: {e}")

    return cars


@app.post("/api/chat")
async def chat_stream(request: Request):
    body = await request.json()
    message = body.get("message", "").strip()
    session_id = body.get("session_id", "")
    if not session_id:
        session_id = create_unique_session_id()

    if not message:
        return StreamingResponse(
            iter([_sse({"message": "消息不能为空"}, "error")]),
            media_type="text/event-stream",
        )

    async def event_generator():
        start_time = time.time()
        yield _sse({"session_id": session_id}, "connected")
        # 让 SSE header 先发出去
        await asyncio.sleep(0)

        try:
            pool, checkpointer, agent = await _get_or_create_agent(session_id)
            config = {"configurable": {"thread_id": session_id}}

            store_session_id(session_id, message)

            reasoning_started = False
            content_started = False

            async for event in agent.astream_events(
                {"messages": [{"role": "user", "content": message}]},
                config=config,
                version="v2",
            ):
                kind = event["event"]

                if kind == "on_tool_start":
                    tool_name = event.get("name", "")
                    yield _sse({"tool_name": tool_name}, "tool_start")
                    await asyncio.sleep(0)

                elif kind == "on_tool_end":
                    tool_name = event.get("name", "")
                    result = event.get("data", {}).get("output")
                    try:
                        if hasattr(result, "__dict__"):
                            result_str = str(result)
                        else:
                            result_str = result
                    except Exception:
                        result_str = str(result)

                    yield _sse(
                        {"tool_name": tool_name, "result": result_str},
                        "tool_end",
                    )

                    # 如果是车型查询工具，尝试提取结构化数据
                    if tool_name in ["query_by_brand", "query_by_price_range", "query_by_energy_type", "query_by_conditions"]:
                        try:
                            # 尝试解析工具返回的结果为车型列表
                            cars_data = _extract_cars_from_result(result_str)
                            if cars_data:
                                yield _sse({"cars": cars_data}, "cars_data")
                        except Exception as e:
                            logger.debug(f"Failed to extract cars data: {e}")

                    await asyncio.sleep(0)

                elif kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]

                    reasoning = chunk.additional_kwargs.get("reasoning_content")
                    if reasoning:
                        if not reasoning_started:
                            reasoning_started = True
                        yield _sse({"text": reasoning}, "reasoning")
                        await asyncio.sleep(0)

                    if chunk.content:
                        if reasoning_started and not content_started:
                            content_started = True
                        elif not content_started:
                            content_started = True
                        yield _sse({"text": chunk.content}, "content")
                        await asyncio.sleep(0)

            elapsed = round((time.time() - start_time) * 1000)
            yield _sse({"elapsed_ms": elapsed}, "done")

        except Exception as e:
            logger.error("SSE error: %s", e, exc_info=True)
            yield _sse({"message": f"服务内部错误: {e}"}, "error")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/sessions")
async def list_sessions():
    """列出本地 session_id.json 中的会话历史"""
    from src.session import _read_from_json
    try:
        data = _read_from_json()
        sessions = []
        for sid in data.get("session_ids", []):
            info = data.get(sid, {})
            sessions.append({
                "id": sid,
                "last_query": info.get("last_query", ""),
                "create_time": info.get("create_time", ""),
                "update_time": info.get("update_time", ""),
            })
        sessions.sort(key=lambda x: x["update_time"], reverse=True)
        return {"sessions": sessions}
    except Exception:
        return {"sessions": []}


@app.get("/api/sessions/{session_id}/messages")
async def get_session_messages(session_id: str):
    """从 PostgreSQL checkpointer 恢复指定会话的消息历史"""
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from psycopg_pool import AsyncConnectionPool

    pool = None
    try:
        pool = AsyncConnectionPool(
            conninfo=DB_URI,
            max_size=5,
            kwargs={"autocommit": True, "prepare_threshold": 0},
            open=False,
        )
        await pool.open()
        checkpointer = AsyncPostgresSaver(pool)
        config = {"configurable": {"thread_id": session_id}}
        checkpoint_tuple = await checkpointer.aget_tuple(config)

        if not checkpoint_tuple or not checkpoint_tuple.checkpoint:
            return {"messages": []}

        channels = checkpoint_tuple.checkpoint.get("channel_values", {})
        raw_messages = channels.get("messages", [])

        messages = []
        for msg in raw_messages:
            msg_type = getattr(msg, "type", None) or msg.get("type", "")
            content = getattr(msg, "content", None) or msg.get("content", "")
            if msg_type in ("human", "ai") and content:
                role = "user" if msg_type == "human" else "agent"
                messages.append({"role": role, "content": content})

        return {"messages": messages}
    except Exception as e:
        logger.error("load session messages error: %s", e, exc_info=True)
        return {"messages": [], "error": str(e)}
    finally:
        if pool:
            await pool.close()


@app.delete("/api/sessions/{session_id}")
async def remove_session(session_id: str):
    """删除指定会话（本地 JSON + agent 缓存）"""
    _agent_cache.pop(session_id, None)
    deleted = delete_session(session_id)
    if deleted:
        return {"ok": True}
    return {"ok": False, "detail": "Session not found"}


@app.get("/")
async def serve_index():
    index_path = os.path.join(web_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Car Helper API is running."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860, log_level="info")
