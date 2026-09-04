import asyncio
import logging

from langchain_core.tools import tool
from langchain_tavily import TavilySearch

from src.config import TAVILY_API_KEY


logger = logging.getLogger(__name__)
_tavily = None


def _get_tavily():
    global _tavily
    if not TAVILY_API_KEY:
        return None
    if _tavily is None:
        _tavily = TavilySearch(
            max_results=5,
            tavily_api_key=TAVILY_API_KEY,
            search_depth="advanced",
        )
    return _tavily


@tool
async def web_search(query: str):
    """搜索汽车口碑、评测、新闻、优惠等当前网络信息。"""
    query = query.strip()
    if not query:
        return "网络搜索需要非空关键词。"
    tavily = _get_tavily()
    if tavily is None:
        return "网络搜索未配置，请设置 TAVILY_API_KEY。"
    try:
        return await asyncio.wait_for(tavily.ainvoke(query), timeout=25)
    except TimeoutError:
        logger.warning("Tavily search timed out")
        return "网络搜索超时，请稍后重试。"
    except Exception:
        logger.exception("Tavily search failed")
        return "网络搜索暂时不可用，请稍后重试。"
