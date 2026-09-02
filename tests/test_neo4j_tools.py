import asyncio
import pytest
from src.tools.neo4j_tools import (
    query_by_brand,
    query_by_price_range,
    query_by_energy_type,
    query_by_conditions,
    compare_models,
    query_by_maintenance_cost,
    explore_schema,
)
from src.db.neo4j_conn import Neo4jConnection


@pytest.fixture(scope="session", autouse=True)
def setup_indexes():
    Neo4jConnection().ensure_indexes()


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ─── explore_schema ────────────────────────────────────

class TestExploreSchema:
    def test_valid_node_type(self):
        result = run(explore_schema.ainvoke({"node_type": "品牌"}))
        assert isinstance(result, list)
        assert len(result) > 0

    def test_invalid_node_type(self):
        result = run(explore_schema.ainvoke({"node_type": "黑客"}))
        assert isinstance(result, str)
        assert "仅允许" in result

    def test_all_allowed_types(self):
        for t in ["品牌", "车系", "车型", "价格区间", "能源类型"]:
            result = run(explore_schema.ainvoke({"node_type": t}))
            assert result is not None


# ─── query_by_brand ────────────────────────────────────

class TestQueryByBrand:
    def test_known_brand(self):
        result = run(query_by_brand.ainvoke({"brand": "比亚迪"}))
        assert isinstance(result, dict)
        assert "数据" in result
        assert len(result["数据"]) > 0

    def test_unknown_brand(self):
        result = run(query_by_brand.ainvoke({"brand": "不存在的品牌XYZ"}))
        assert isinstance(result, str)

    def test_result_fields(self):
        result = run(query_by_brand.ainvoke({"brand": "比亚迪"}))
        record = result["数据"][0]
        for field in ["品牌", "车系", "车型"]:
            assert field in record


# ─── query_by_price_range ──────────────────────────────

class TestQueryByPriceRange:
    def test_valid_range(self):
        result = run(query_by_price_range.ainvoke({"price_range": "10-20万"}))
        assert isinstance(result, dict)
        assert "数据" in result

    def test_invalid_range(self):
        result = run(query_by_price_range.ainvoke({"price_range": "999-1000万"}))
        assert isinstance(result, str)

    def test_all_ranges(self):
        for r in ["0-10万", "10-20万", "20-30万", "30-40万", "40-50万", "50万以上"]:
            result = run(query_by_price_range.ainvoke({"price_range": r}))
            assert result is not None


# ─── query_by_energy_type ──────────────────────────────

class TestQueryByEnergyType:
    def test_electric(self):
        result = run(query_by_energy_type.ainvoke({"energy_type": "纯电动"}))
        assert isinstance(result, dict)
        assert "数据" in result

    def test_gasoline(self):
        result = run(query_by_energy_type.ainvoke({"energy_type": "汽油"}))
        assert isinstance(result, dict)

    def test_invalid_type(self):
        result = run(query_by_energy_type.ainvoke({"energy_type": "核动力"}))
        assert isinstance(result, str)


# ─── query_by_conditions ───────────────────────────────

class TestQueryByConditions:
    def test_brand_and_energy(self):
        result = run(query_by_conditions.ainvoke({
            "brand": "比亚迪",
            "energy_type": "纯电动",
        }))
        assert isinstance(result, dict)
        assert "数据" in result

    def test_price_and_level(self):
        result = run(query_by_conditions.ainvoke({
            "price_range": "10-20万",
            "level": "SUV",
        }))
        assert isinstance(result, dict)
        assert "数据" in result

    def test_single_condition(self):
        result = run(query_by_conditions.ainvoke({"energy_type": "插电式混合动力"}))
        assert isinstance(result, dict)

    def test_no_match(self):
        result = run(query_by_conditions.ainvoke({
            "brand": "不存在的品牌",
            "energy_type": "核动力",
        }))
        assert isinstance(result, str)


# ─── compare_models ────────────────────────────────────

class TestCompareModels:
    def test_known_brand(self):
        result = run(compare_models.ainvoke({"brand": "比亚迪"}))
        assert isinstance(result, dict)
        assert "数据" in result
        record = result["数据"][0]
        assert "百公里加速" in record or "保养成本" in record

    def test_unknown_brand(self):
        result = run(compare_models.ainvoke({"brand": "不存在的品牌"}))
        assert isinstance(result, str)


# ─── query_by_maintenance_cost ─────────────────────────

class TestQueryByMaintenanceCost:
    def test_single_range(self):
        result = run(query_by_maintenance_cost.ainvoke({"price_ranges": ["10-20万"]}))
        assert isinstance(result, dict)
        assert "数据" in result

    def test_multiple_ranges(self):
        result = run(query_by_maintenance_cost.ainvoke({
            "price_ranges": ["0-10万", "10-20万"],
        }))
        assert isinstance(result, dict)

    def test_empty_list(self):
        result = run(query_by_maintenance_cost.ainvoke({"price_ranges": []}))
        assert isinstance(result, str)
