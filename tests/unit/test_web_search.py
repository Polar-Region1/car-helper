import src.tools.web_search as web_search_module
from src.tools.web_search import web_search


async def test_missing_tavily_key_only_disables_web_search(monkeypatch):
    monkeypatch.setattr(web_search_module, "TAVILY_API_KEY", None)
    monkeypatch.setattr(web_search_module, "_tavily", None)

    result = await web_search.ainvoke({"query": "比亚迪新闻"})

    assert result == "网络搜索未配置，请设置 TAVILY_API_KEY。"
