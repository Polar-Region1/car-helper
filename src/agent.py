import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import nest_asyncio
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

from src.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL
from src.db.neo4j_conn import Neo4jConnection
from src.deepseek_patched import apply_patches
from src.session import create_unique_session_id, store_session_id, store_session_to_db, resume_session
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

nest_asyncio.apply()

# ─── DeepSeek Thinking Mode 适配 ─────────────────────────
apply_patches()

# ─── LLM 初始化（启用 thinking 模式）─────────────────────
llm = ChatOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    model="deepseek-chat",
    temperature=0.7,
    extra_body={"thinking": {"type": "enabled"}},
)

# ─── 工具注册 ────────────────────────────────────────────
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

# ─── 会话管理 ────────────────────────────────────────────
session_id = create_unique_session_id()

# ─── Neo4j 索引初始化 ────────────────────────────────────
Neo4jConnection().ensure_indexes()


async def main():
    # PostgreSQL 持久化
    pool, checkpointer = await store_session_to_db()
    config = {"configurable": {"thread_id": session_id}}

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )

    try:
        while True:
            query = await asyncio.to_thread(input, "USER_INPUT >>> ")

            if query.strip().lower() == "/exit":
                # 退出前持久化最后一条提问
                try:
                    state = await agent.aget_state(config)
                    messages = state.values.get("messages", [])
                    for msg in reversed(messages):
                        if isinstance(msg, HumanMessage):
                            store_session_id(session_id, msg.content)
                            break
                except Exception:
                    store_session_id(session_id, "(unknown)")
                print("会话已保存，再见！")
                break

            if query.strip().lower() == "/resume":
                old_id = await asyncio.to_thread(resume_session)
                if old_id:
                    config["configurable"]["thread_id"] = old_id
                    print(f"已恢复会话: {old_id[:8]}...")
                continue

            print("\n🤖 Agent: ", end="", flush=True)
            reasoning_started = False
            content_started = False

            async for event in agent.astream_events(
                {"messages": [{"role": "user", "content": query}]},
                config=config,
                version="v2",
            ):
                kind = event["event"]

                if kind == "on_tool_start" and event["data"]["input"]:
                    print(f"\n🔧 正在调用工具：{event['name']} ...\n")

                elif kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]

                    # reasoning_content（thinking 模式输出）
                    reasoning = chunk.additional_kwargs.get("reasoning_content")
                    if reasoning:
                        if not reasoning_started:
                            print("\n💭 思考过程：\n", flush=True)
                            reasoning_started = True
                        print(reasoning, end="", flush=True)

                    # 正式回答内容
                    if chunk.content:
                        if reasoning_started and not content_started:
                            print("\n\n" + "=" * 40 + "\n", flush=True)
                            content_started = True
                        elif not content_started:
                            content_started = True
                        print(chunk.content, end="", flush=True)

            print("\n" + "-" * 30)

    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
