from src.tools.neo4j_tools import sample_stats, stratified_sample, validate_result


def test_stratified_sample_is_bounded_unique_and_diverse():
    price_ranges = ["0-10万", "10-20万", "20-30万", "30-40万", "40-50万", "50万以上"]
    energy_types = ["汽油", "纯电动", "插电式混合动力", "增程式", "其他"]
    records = [
        {
            "品牌": f"品牌{index % 14}",
            "车系": f"车系{index}",
            "车型": f"车型{index}",
            "价格区间": price_ranges[index % len(price_ranges)],
            "能源类型": energy_types[index % len(energy_types)],
            "上市时间": f"2026.{(index % 12) + 1:02d}",
        }
        for index in range(60)
    ]

    sampled = stratified_sample(records, 20)

    assert len(sampled) == 20
    assert len({id(record) for record in sampled}) == 20
    assert {record["能源类型"] for record in sampled} == set(energy_types)
    assert {record["价格区间"] for record in sampled} == set(price_ranges)


def test_sample_stats_excludes_missing_categories():
    records = [
        {"品牌": "A", "车系": "S", "车型": "M", "能源类型": None},
        {"品牌": "B", "车系": "T", "车型": "N", "能源类型": "NONE"},
    ]
    stats = sample_stats(records, records[:1])
    assert stats["能源覆盖"] == "0/0"


def test_validate_result_only_rejects_when_all_identifiers_are_missing():
    partially_valid = [
        {"品牌": None, "车系": None, "车型": None},
        {"品牌": "比亚迪", "车系": "秦", "车型": "秦PLUS"},
    ]
    assert validate_result(partially_valid, "test") == partially_valid
    assert isinstance(validate_result([{"品牌": None}], "test"), str)
