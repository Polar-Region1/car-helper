import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from src.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL
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
from src.db.neo4j_conn import Neo4jConnection


Neo4jConnection().ensure_indexes()

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

llm = ChatOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    model="deepseek-chat",
)

agent = create_react_agent(
    model=llm,
    tools=tools,
    prompt=SYSTEM_PROMPT,
    checkpointer=InMemorySaver(),
)


async def chat(query: str) -> str:
    config = {"configurable": {"thread_id": "e2e-test"}}
    full_response = ""
    async for event in agent.astream_events(
        {"messages": [{"role": "user", "content": query}]},
        config=config,
        version="v2",
    ):
        kind = event["event"]
        if kind == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            if chunk.content:
                full_response += chunk.content
    return full_response


# ─── E2E: 知识图谱查询链路 ────────────────────────────

class TestE2EBrandQuery:
    @pytest.mark.asyncio
    async def test_brand_recommendation(self):
        """用户问某品牌车，agent 应调用 query_by_brand 并给出推荐"""
        response = await chat("比亚迪有哪些纯电动车推荐？")
        assert len(response) > 20
        assert "比亚迪" in response


class TestE2EPriceQuery:
    @pytest.mark.asyncio
    async def test_price_range_recommendation(self):
        """用户问价格区间，agent 应调用 query_by_price_range"""
        response = await chat("10到20万有什么SUV值得买？")
        assert len(response) > 20
        assert any(kw in response for kw in ["万", "SUV", "推荐"])


class TestE2EEnergyQuery:
    @pytest.mark.asyncio
    async def test_energy_type_query(self):
        """用户问能源类型，agent 应调用 query_by_energy_type"""
        response = await chat("纯电动车续航最长的有哪些？")
        assert len(response) > 20


class TestE2EComparison:
    @pytest.mark.asyncio
    async def test_brand_comparison(self):
        """用户要对比，agent 应调用 compare_models"""
        response = await chat("帮我对比一下比亚迪各车型的配置和价格")
        assert len(response) > 20
        assert "比亚迪" in response


class TestE2EMaintenance:
    @pytest.mark.asyncio
    async def test_maintenance_cost(self):
        """用户问保养，agent 应调用 query_by_maintenance_cost"""
        response = await chat("10万以内保养成本最低的车有哪些？")
        assert len(response) > 20


class TestE2EMultiCondition:
    @pytest.mark.asyncio
    async def test_multi_condition(self):
        """用户多条件筛选，agent 应调用 query_by_conditions"""
        response = await chat("我想找20-30万的插电混动SUV")
        assert len(response) > 20


# ─── E2E: 网络搜索链路 ────────────────────────────────

class TestE2EWebSearch:
    @pytest.mark.asyncio
    async def test_opinion_query(self):
        """用户问口碑/评测，agent 应调用 web_search"""
        response = await chat("比亚迪秦PLUS最新口碑怎么样？")
        assert len(response) > 20


# ─── E2E: 边界场景 ────────────────────────────────────

class TestE2EEdgeCases:
    @pytest.mark.asyncio
    async def test_vague_question(self):
        """模糊提问，agent 应先探索 schema 或追问"""
        response = await chat("帮我选车")
        assert len(response) > 10

    @pytest.mark.asyncio
    async def test_nonexistent_brand(self):
        """问不存在的品牌，agent 应告知无结果而非幻觉"""
        response = await chat("火星牌汽车有哪些车型？")
        assert len(response) > 0
        assert "火星" in response
