import ast
import asyncio
import json
import logging
import re
import sys
import time
from contextlib import asynccontextmanager
from uuid import UUID

if sys.platform == "win32":
    import uvicorn.loops.asyncio as _uvicorn_asyncio

    _uvicorn_asyncio.asyncio_loop_factory = (
        lambda use_subprocess=False: asyncio.SelectorEventLoop
    )

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.agent_factory import create_agent_context, create_car_agent
from src.config import APP_HOST, APP_PORT, CORS_ORIGINS, LOCAL_DB_PATH, PROJECT_ROOT
from src.db.neo4j_conn import Neo4jConnection
from src.session import (
    create_session_store,
    create_unique_session_id,
)
from src.storage import MemoryValidationError, create_local_store


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,128}$")
CAR_QUERY_TOOLS = {
    "query_by_brand",
    "query_by_price_range",
    "query_by_energy_type",
    "query_by_conditions",
    "compare_models",
    "query_by_maintenance_cost",
}


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str | None = Field(default=None, max_length=128)


class MemoryUpdateRequest(BaseModel):
    value: str = Field(min_length=1, max_length=500)


def _validate_session_id(session_id):
    if not SESSION_ID_PATTERN.fullmatch(session_id):
        raise HTTPException(status_code=422, detail="Invalid session_id")
    return session_id


def _sse(data: dict, event: str = "message"):
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


def _unwrap_tool_result(result):
    payload = getattr(result, "content", result)
    if isinstance(payload, dict):
        return payload
    if not isinstance(payload, str):
        return None
    for parser in (json.loads, ast.literal_eval):
        try:
            parsed = parser(payload)
        except (ValueError, SyntaxError, TypeError, json.JSONDecodeError):
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def _extract_cars_from_result(result):
    payload = _unwrap_tool_result(result)
    if not payload or not isinstance(payload.get("数据"), list):
        return []

    cars = []
    for item in payload["数据"][:20]:
        if not isinstance(item, dict):
            continue
        name = " ".join(
            str(item.get(field, "")).strip()
            for field in ("品牌", "车系", "车型")
            if item.get(field)
        )
        if not name:
            continue
        energy = item.get("能源类型") or "未知"
        cars.append(
            {
                "name": name,
                "price": item.get("指导价") or "暂无报价",
                "energy": energy,
                "level": item.get("级别") or "未知",
                "badge": "新能源"
                if any(keyword in str(energy) for keyword in ("纯电", "插电", "增程"))
                else None,
            }
        )
    return cars


def _message_content_to_text(content):
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


@asynccontextmanager
async def _locked_session(app: FastAPI, session_id: str):
    """Serialize a session while safely retiring unused per-session locks."""
    async with app.state.session_locks_guard:
        entry = app.state.session_locks.setdefault(
            session_id,
            {"lock": asyncio.Lock(), "users": 0},
        )
        entry["users"] += 1
    try:
        async with entry["lock"]:
            yield
    finally:
        async with app.state.session_locks_guard:
            entry["users"] -= 1
            if entry["users"] == 0:
                app.state.session_locks.pop(session_id, None)


@asynccontextmanager
async def lifespan(app: FastAPI):
    local_store = await asyncio.to_thread(create_local_store, LOCAL_DB_PATH)
    profile = await asyncio.to_thread(local_store.get_default_profile)
    pool, checkpointer = await create_session_store()
    try:
        app.state.local_store = local_store
        app.state.profile = profile
        app.state.pool = pool
        app.state.checkpointer = checkpointer
        app.state.agent = create_car_agent(checkpointer=checkpointer)
        app.state.session_locks = {}
        app.state.session_locks_guard = asyncio.Lock()
        yield
    finally:
        await pool.close()
        Neo4jConnection.close_if_initialized()


app = FastAPI(title="Car Helper API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(CORS_ORIGINS),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)


@app.post("/api/chat")
async def chat_stream(payload: ChatRequest, request: Request):
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Message cannot be blank")
    session_id = _validate_session_id(payload.session_id or create_unique_session_id())

    async def event_generator():
        start_time = time.perf_counter()
        yield _sse({"session_id": session_id}, "connected")

        try:
            async with _locked_session(request.app, session_id):
                profile_id = request.app.state.profile["profile_id"]
                await asyncio.to_thread(
                    request.app.state.local_store.upsert_conversation,
                    profile_id,
                    session_id,
                    message,
                )
                agent_context = await asyncio.to_thread(
                    create_agent_context,
                    local_store=request.app.state.local_store,
                    profile_id=profile_id,
                    thread_id=session_id,
                )
                config = {"configurable": {"thread_id": session_id}}
                async for event in request.app.state.agent.astream_events(
                    {"messages": [{"role": "user", "content": message}]},
                    config=config,
                    context=agent_context,
                    version="v2",
                ):
                    if await request.is_disconnected():
                        logger.info("Client disconnected from session %s", session_id)
                        return

                    kind = event.get("event")
                    if kind == "on_tool_start":
                        yield _sse({"tool_name": event.get("name", "")}, "tool_start")
                    elif kind == "on_tool_end":
                        tool_name = event.get("name", "")
                        result = event.get("data", {}).get("output")
                        result_payload = _unwrap_tool_result(result) or {}
                        count = len(result_payload.get("数据", []))
                        yield _sse(
                            {"tool_name": tool_name, "result_count": count},
                            "tool_end",
                        )
                        if tool_name in CAR_QUERY_TOOLS:
                            cars = _extract_cars_from_result(result)
                            if cars:
                                yield _sse({"cars": cars}, "cars_data")
                    elif kind == "on_chat_model_stream":
                        chunk = event.get("data", {}).get("chunk")
                        if chunk is None:
                            continue
                        reasoning = chunk.additional_kwargs.get("reasoning_content")
                        if reasoning:
                            yield _sse({"text": str(reasoning)}, "reasoning")
                        content = _message_content_to_text(chunk.content)
                        if content:
                            yield _sse({"text": content}, "content")

                elapsed = round((time.perf_counter() - start_time) * 1000)
                yield _sse({"elapsed_ms": elapsed}, "done")
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("SSE request failed for session %s", session_id)
            yield _sse({"message": "服务暂时不可用，请稍后重试。"}, "error")

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
async def get_sessions(request: Request):
    sessions = await asyncio.to_thread(
        request.app.state.local_store.list_conversations,
        request.app.state.profile["profile_id"],
    )
    return {"sessions": sessions}


@app.get("/api/profile")
async def get_profile(request: Request):
    return request.app.state.profile


@app.get("/api/memories")
async def get_memories(request: Request):
    memories = await asyncio.to_thread(
        request.app.state.local_store.list_memories,
        request.app.state.profile["profile_id"],
    )
    return {"memories": memories}


@app.patch("/api/memories/{memory_id}")
async def update_memory(
    memory_id: UUID,
    payload: MemoryUpdateRequest,
    request: Request,
):
    try:
        memory = await asyncio.to_thread(
            request.app.state.local_store.update_memory,
            request.app.state.profile["profile_id"],
            str(memory_id),
            value=payload.value,
        )
    except MemoryValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    return memory


@app.delete("/api/memories/{memory_id}")
async def remove_memory(memory_id: UUID, request: Request):
    deleted = await asyncio.to_thread(
        request.app.state.local_store.forget,
        request.app.state.profile["profile_id"],
        memory_id=str(memory_id),
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"ok": True}


@app.get("/api/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, request: Request):
    _validate_session_id(session_id)
    owns_session = await asyncio.to_thread(
        request.app.state.local_store.owns_conversation,
        request.app.state.profile["profile_id"],
        session_id,
    )
    if not owns_session:
        raise HTTPException(status_code=404, detail="Session not found")
    config = {"configurable": {"thread_id": session_id}}
    try:
        checkpoint_tuple = await request.app.state.checkpointer.aget_tuple(config)
    except Exception:
        logger.exception("Failed to load session %s", session_id)
        raise HTTPException(status_code=503, detail="Session store unavailable")
    if not checkpoint_tuple or not checkpoint_tuple.checkpoint:
        return {"messages": []}

    raw_messages = checkpoint_tuple.checkpoint.get("channel_values", {}).get("messages", [])
    messages = []
    for message in raw_messages:
        if isinstance(message, dict):
            message_type = message.get("type", "")
            content = message.get("content", "")
        else:
            message_type = getattr(message, "type", "")
            content = getattr(message, "content", "")
        text = _message_content_to_text(content)
        if message_type in {"human", "ai"} and text:
            messages.append(
                {"role": "user" if message_type == "human" else "agent", "content": text}
            )
    return {"messages": messages}


@app.delete("/api/sessions/{session_id}")
async def remove_session(session_id: str, request: Request):
    _validate_session_id(session_id)
    async with _locked_session(request.app, session_id):
        owns_session = await asyncio.to_thread(
            request.app.state.local_store.owns_conversation,
            request.app.state.profile["profile_id"],
            session_id,
        )
        if not owns_session:
            raise HTTPException(status_code=404, detail="Session not found")
        try:
            await request.app.state.checkpointer.adelete_thread(session_id)
        except Exception:
            logger.exception("Failed to delete checkpoint for session %s", session_id)
            raise HTTPException(status_code=503, detail="Session store unavailable")
        await asyncio.to_thread(
            request.app.state.local_store.delete_conversation,
            request.app.state.profile["profile_id"],
            session_id,
        )
    return {"ok": True}


FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
ASSETS_DIR = FRONTEND_DIST / "assets"
if ASSETS_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="frontend-assets")


@app.get("/{path:path}", include_in_schema=False)
async def serve_frontend(path: str):
    if not FRONTEND_DIST.is_dir():
        return {
            "message": "Car Helper API is running; build frontend/ to serve the web UI."
        }
    requested = (FRONTEND_DIST / path).resolve()
    if requested.is_relative_to(FRONTEND_DIST.resolve()) and requested.is_file():
        return FileResponse(requested)
    return FileResponse(FRONTEND_DIST / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=APP_HOST, port=APP_PORT, log_level="info")
