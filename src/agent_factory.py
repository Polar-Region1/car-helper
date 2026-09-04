from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from src.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL
from src.deepseek_patched import apply_patches
from src.memory import (
    AgentContext,
    build_memory_context,
    forget_user_preference,
    memory_aware_prompt,
    remember_user_preference,
)
from src.tools.neo4j_tools import (
    compare_models,
    explore_schema,
    query_by_brand,
    query_by_conditions,
    query_by_energy_type,
    query_by_maintenance_cost,
    query_by_price_range,
)
from src.tools.web_search import web_search


TOOLS = (
    query_by_brand,
    query_by_price_range,
    query_by_energy_type,
    query_by_conditions,
    compare_models,
    query_by_maintenance_cost,
    explore_schema,
    web_search,
    remember_user_preference,
    forget_user_preference,
)


def create_llm():
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("缺少 DEEPSEEK_API_KEY，请在 .env 中配置。")
    return ChatOpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        model="deepseek-chat",
        temperature=0.7,
        extra_body={"thinking": {"type": "enabled"}},
    )


def create_car_agent(*, checkpointer):
    apply_patches()
    return create_agent(
        model=create_llm(),
        tools=list(TOOLS),
        middleware=[memory_aware_prompt],
        context_schema=AgentContext,
        checkpointer=checkpointer,
    )


def create_agent_context(*, local_store, profile_id, thread_id):
    memories = local_store.list_memories(profile_id, limit=30)
    return AgentContext(
        profile_id=profile_id,
        thread_id=thread_id,
        memory_context=build_memory_context(memories),
        local_store=local_store,
    )
