import asyncio
import sys

from src.agent_factory import create_agent_context, create_car_agent
from src.config import LOCAL_DB_PATH
from src.session import (
    create_session_store,
    create_unique_session_id,
    resume_session,
)
from src.storage import create_local_store


async def stream_answer(agent, config, context, query):
    print("\n🤖 Agent: ", end="", flush=True)
    reasoning_started = False
    content_started = False

    async for event in agent.astream_events(
        {"messages": [{"role": "user", "content": query}]},
        config=config,
        context=context,
        version="v2",
    ):
        kind = event["event"]
        if kind == "on_tool_start" and event.get("data", {}).get("input"):
            print(f"\n🔧 正在调用工具：{event.get('name', '')} ...\n")
        elif kind == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            reasoning = chunk.additional_kwargs.get("reasoning_content")
            if reasoning:
                if not reasoning_started:
                    print("\n💭 思考过程：\n", flush=True)
                    reasoning_started = True
                print(reasoning, end="", flush=True)
            if chunk.content:
                if reasoning_started and not content_started:
                    print("\n\n" + "=" * 40 + "\n", flush=True)
                content_started = True
                print(chunk.content, end="", flush=True)

    print("\n" + "-" * 30)


async def main():
    session_id = create_unique_session_id()
    local_store = await asyncio.to_thread(create_local_store, LOCAL_DB_PATH)
    profile = await asyncio.to_thread(local_store.get_default_profile)
    profile_id = profile["profile_id"]
    pool, checkpointer = await create_session_store()
    try:
        agent = create_car_agent(checkpointer=checkpointer)
        while True:
            query = await asyncio.to_thread(input, "USER_INPUT >>> ")
            command = query.strip().lower()

            if command == "/exit":
                print("会话已保存，再见！")
                break
            if command == "/resume":
                restored_id = await asyncio.to_thread(
                    resume_session,
                    local_store,
                    profile_id,
                )
                if restored_id:
                    session_id = restored_id
                    print(f"已恢复会话: {restored_id[:8]}...")
                continue
            if not query.strip():
                continue

            await asyncio.to_thread(
                local_store.upsert_conversation,
                profile_id,
                session_id,
                query,
            )
            context = await asyncio.to_thread(
                create_agent_context,
                local_store=local_store,
                profile_id=profile_id,
                thread_id=session_id,
            )
            config = {"configurable": {"thread_id": session_id}}
            try:
                await stream_answer(agent, config, context, query)
            except Exception as exc:
                print(f"\n请求失败：{exc}")
    finally:
        await pool.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.run(main(), loop_factory=asyncio.SelectorEventLoop)
    else:
        asyncio.run(main())
