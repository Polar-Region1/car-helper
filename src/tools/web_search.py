import os
import sys
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.config import TAVILY_API_KEY
from langchain_tavily import TavilySearch
from langchain_core.tools import tool
import asyncio

logger = logging.getLogger(__name__)

_tavily = TavilySearch(
    max_result=5,
    tavily_api_key=TAVILY_API_KEY,
    search_depth="advanced",
)


@tool
async def web_search(query: str) -> str:
    """搜索互联网获取汽车口碑、评测、新闻、价格优惠等非结构化信息。当用户问口碑、最新消息、价格走势时使用。"""
    try:
        return await asyncio.to_thread(_tavily.invoke, query)
    except Exception as e:
        logger.error("Tavily 搜索失败: %s", e)
        return f"网络搜索暂时不可用，请稍后重试。详情: {e}"
