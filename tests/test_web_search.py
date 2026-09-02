import asyncio
import pytest
from src.tools.web_search import web_search


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class TestWebSearch:
    def test_basic_search(self):
        result = run(web_search.ainvoke({"query": "比亚迪秦PLUS 2024评测"}))
        assert result is not None
        assert len(str(result)) > 0

    def test_empty_query(self):
        result = run(web_search.ainvoke({"query": ""}))
        assert result is not None
