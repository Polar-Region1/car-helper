import src.tools.neo4j_tools as tools_module
from src.tools.neo4j_tools import (
    compare_models,
    explore_schema,
    query_by_conditions,
    query_by_energy_type,
    query_by_price_range,
)


async def test_compare_models_matches_brand_relationship_without_name_filter(monkeypatch):
    captured = {}

    async def fake_query(cypher, params):
        captured.update(cypher=cypher, params=params)
        return [
            {
                "品牌": "特斯拉",
                "车系": "Model Y",
                "车型": "Model Y 2026款 后轮驱动版",
                "指导价": "26.35万",
            }
        ], None

    monkeypatch.setattr(tools_module, "_run_query_threaded", fake_query)
    result = await compare_models.ainvoke({"brand": "特斯拉"})

    assert isinstance(result, dict)
    assert "m.车名 CONTAINS" not in captured["cypher"]
    assert captured["params"]["brand"] == "特斯拉"


async def test_condition_query_always_defines_brand_and_series(monkeypatch):
    captured = {}

    async def fake_query(cypher, params):
        captured.update(cypher=cypher, params=params)
        return [{"品牌": "A", "车系": "S", "车型": "M"}], None

    monkeypatch.setattr(tools_module, "_run_query_threaded", fake_query)
    await query_by_conditions.ainvoke({})

    assert "MATCH (b:品牌)-[:HAS_SERIES]->(s:车系)-[:HAS_MODEL]->(m:车型)" in captured["cypher"]
    assert " WHERE " not in captured["cypher"]


async def test_explore_schema_returns_database_error(monkeypatch):
    async def fake_query(cypher, params):
        return [], "数据库查询暂时不可用，请稍后重试。"

    monkeypatch.setattr(tools_module, "_run_query_threaded", fake_query)
    result = await explore_schema.ainvoke({"node_type": "品牌"})
    assert result == "数据库查询暂时不可用，请稍后重试。"


async def test_required_filters_precede_optional_matches(monkeypatch):
    captured = []

    async def fake_query(cypher, params):
        captured.append(cypher)
        return [{"品牌": "A", "车系": "S", "车型": "M"}], None

    monkeypatch.setattr(tools_module, "_run_query_threaded", fake_query)
    await query_by_price_range.ainvoke({"price_range": "10-20万"})
    await query_by_energy_type.ainvoke({"energy_type": "纯电动"})

    for cypher in captured:
        assert cypher.index("WHERE") < cypher.index("OPTIONAL MATCH")
