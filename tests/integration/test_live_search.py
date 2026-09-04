import os

import pytest

from src.tools.web_search import web_search


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION") != "1",
        reason="set RUN_INTEGRATION=1 to call Tavily",
    ),
]


async def test_live_search():
    result = await web_search.ainvoke({"query": "比亚迪秦PLUS 最新官方信息"})
    assert result
