import os

import pytest

from src.tools.neo4j_tools import compare_models, query_by_brand


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION") != "1",
        reason="set RUN_INTEGRATION=1 to query the configured Neo4j instance",
    ),
]


async def test_live_brand_query():
    result = await query_by_brand.ainvoke({"brand": "比亚迪", "limit": 100})
    assert isinstance(result, dict)
    assert result["数据"]


async def test_live_comparison_supports_brandless_model_names():
    result = await compare_models.ainvoke({"brand": "特斯拉", "limit": 100})
    assert isinstance(result, dict)
    assert any("Model" in row["车型"] for row in result["数据"])
