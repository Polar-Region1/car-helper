"""Validate and import the local vehicle dataset into Neo4j.

Running this module without ``--apply`` only validates input files. Database
writes are explicit, and replacing existing data requires a second confirmation
flag so an accidental import cannot clear the graph.
"""

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path

from src.db.neo4j_conn import Neo4jConnection


PIPELINE_ROOT = Path(__file__).resolve().parent.parent
ENTITIES_ROOT = PIPELINE_ROOT / "entities"
RELATIONSHIPS_ROOT = PIPELINE_ROOT / "relationships"


@dataclass(frozen=True)
class DataBundle:
    brands: list[str]
    series: list[str]
    models: list[dict]
    energy_types: list[str]
    price_ranges: list[str]
    brand_series: list[dict]
    series_models: list[dict]
    model_energy: list[dict]
    model_prices: list[dict]
    warnings: tuple[str, ...] = ()

    def counts(self):
        return {
            "品牌": len(self.brands),
            "车系": len(self.series),
            "车型": len(self.models),
            "能源类型": len(self.energy_types),
            "价格区间": len(self.price_ranges),
            "品牌-车系关系": len(self.brand_series),
            "车系-车型关系": len(self.series_models),
            "车型-能源关系": len(self.model_energy),
            "车型-价格关系": len(self.model_prices),
        }


def _read_single_column(path: Path, expected_header: str):
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.reader(file))
    if not rows or rows[0] != [expected_header]:
        raise ValueError(f"{path} 表头应为 {expected_header!r}")
    values = [row[0].strip() for row in rows[1:] if row and row[0].strip()]
    return list(dict.fromkeys(values))


def _read_models(path: Path):
    with path.open("r", encoding="utf-8") as file:
        models = json.load(file)
    if not isinstance(models, list) or not all(isinstance(item, dict) for item in models):
        raise ValueError(f"{path} 必须是对象数组")
    names = [item.get("车名") for item in models]
    if any(not isinstance(name, str) or not name.strip() for name in names):
        raise ValueError(f"{path} 存在缺少车名的车型")
    # Source names are not globally unique. A stable row id preserves every
    # source record while making repeated imports idempotent.
    return [dict(item, _source_id=f"model-{index}") for index, item in enumerate(models)]


def _read_text_relationships(path: Path, left_label: str, right_label: str, relation: str):
    prefix = f"{left_label} "
    separator = f" {right_label} "
    suffix = f" {relation}"
    relationships = []
    with path.open("r", encoding="utf-8-sig") as file:
        header = file.readline().strip()
        if header != "实体一 名称一 实体二 名称二 关系":
            raise ValueError(f"{path} 表头格式错误")
        for line_number, raw_line in enumerate(file, 2):
            line = raw_line.strip()
            if not line:
                continue
            if not line.startswith(prefix) or not line.endswith(suffix) or separator not in line:
                raise ValueError(f"{path}:{line_number} 关系格式错误")
            left, right = line[len(prefix) : -len(suffix)].split(separator, 1)
            relationships.append({"left": left, "right": right})
    return relationships


def _read_csv_relationships(path: Path, expected_fields: set[str], mapper):
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if set(reader.fieldnames or ()) != expected_fields:
            raise ValueError(f"{path} 表头格式错误: {reader.fieldnames}")
        return [mapper(row) for row in reader]


def _attach_model_ids(models, relationships, *, model_field, relationship_name):
    """Bind positional relationship rows to the stable id of their source model."""
    if len(models) != len(relationships):
        raise ValueError(
            f"{relationship_name} 与车型数据条数不一致："
            f"{len(relationships)} != {len(models)}"
        )

    bound = []
    for index, (model, relationship) in enumerate(zip(models, relationships)):
        if model["车名"] != relationship[model_field]:
            raise ValueError(
                f"{relationship_name} 第 {index + 1} 条与车型顺序不一致"
            )
        bound.append(dict(relationship, model_id=model["_source_id"]))
    return bound


def load_and_validate_data():
    brands = _read_single_column(ENTITIES_ROOT / "brands.txt", "品牌")
    series = _read_single_column(ENTITIES_ROOT / "model_series.txt", "车系")
    models = _read_models(ENTITIES_ROOT / "models.json")
    energy_types = _read_single_column(ENTITIES_ROOT / "energy_type.csv", "能源类型")
    price_ranges = _read_single_column(ENTITIES_ROOT / "price_range.csv", "价格区间")

    brand_series = _read_text_relationships(
        RELATIONSHIPS_ROOT / "brand_and_model_series_relationships.txt",
        "品牌",
        "车系",
        "HAS_SERIES",
    )
    series_models = _read_text_relationships(
        RELATIONSHIPS_ROOT / "model_series_and_model_relationship.txt",
        "车系",
        "车型",
        "HAS_MODEL",
    )
    model_energy = _read_csv_relationships(
        RELATIONSHIPS_ROOT / "relationships.csv",
        {"关系", "名称一", "名称二", "实体一", "实体二"},
        lambda row: {"left": row["名称一"], "right": row["名称二"]},
    )
    model_prices = _read_csv_relationships(
        RELATIONSHIPS_ROOT / "price_range_relationships.csv",
        {"实体一", "名称一", "实体二", "名称二", "关系"},
        lambda row: {"left": row["名称一"], "right": row["名称二"]},
    )

    # These files are generated from models.json in the same order. Binding the
    # relationship rows to _source_id avoids fan-out when multiple source rows
    # legitimately share the same display name.
    series_models = _attach_model_ids(
        models,
        series_models,
        model_field="right",
        relationship_name="车系-车型关系",
    )
    model_energy = _attach_model_ids(
        models,
        model_energy,
        model_field="left",
        relationship_name="车型-能源关系",
    )
    priced_models = [
        model
        for model in models
        if model.get("官方指导价") not in {None, "", "NONE", "None", "暂无", "暂无报价"}
    ]
    model_prices = _attach_model_ids(
        priced_models,
        model_prices,
        model_field="left",
        relationship_name="车型-价格关系",
    )

    model_names = {item["车名"] for item in models}
    reference_checks = (
        ("品牌-车系", "brand_series", brand_series, set(brands), set(series)),
        ("车系-车型", "series_models", series_models, set(series), model_names),
        ("车型-能源", "model_energy", model_energy, model_names, set(energy_types)),
        ("车型-价格", "model_prices", model_prices, model_names, set(price_ranges)),
    )
    validated_relationships = {}
    warnings = []
    for label, key, rows, left_values, right_values in reference_checks:
        missing_left = {row["left"] for row in rows if row["left"] not in left_values}
        missing_right = {row["right"] for row in rows if row["right"] not in right_values}
        if missing_left or missing_right:
            warnings.append(
                f"{label} 跳过无效引用：左侧 {len(missing_left)} 个，右侧 {len(missing_right)} 个"
            )
        validated_relationships[key] = [
            row
            for row in rows
            if row["left"] in left_values and row["right"] in right_values
        ]

    return DataBundle(
        brands,
        series,
        models,
        energy_types,
        price_ranges,
        validated_relationships["brand_series"],
        validated_relationships["series_models"],
        validated_relationships["model_energy"],
        validated_relationships["model_prices"],
        tuple(warnings),
    )


def _batches(items, batch_size):
    for start in range(0, len(items), batch_size):
        yield items[start : start + batch_size]


def import_data(bundle: DataBundle, *, replace: bool, batch_size: int):
    node_jobs = (
        ("UNWIND $rows AS row MERGE (:品牌 {name: row})", bundle.brands),
        ("UNWIND $rows AS row MERGE (:车系 {name: row})", bundle.series),
        (
            "UNWIND $rows AS row MERGE (m:车型 {_source_id: row._source_id}) SET m += row",
            bundle.models,
        ),
        ("UNWIND $rows AS row MERGE (:能源类型 {name: row})", bundle.energy_types),
        ("UNWIND $rows AS row MERGE (:价格区间 {name: row})", bundle.price_ranges),
    )
    relationship_jobs = (
        (
            "UNWIND $rows AS row MATCH (a:品牌 {name: row.left}), (b:车系 {name: row.right}) "
            "MERGE (a)-[:HAS_SERIES]->(b)",
            bundle.brand_series,
        ),
        (
            "UNWIND $rows AS row MATCH (a:车系 {name: row.left}), "
            "(b:车型 {_source_id: row.model_id}) "
            "MERGE (a)-[:HAS_MODEL]->(b)",
            bundle.series_models,
        ),
        (
            "UNWIND $rows AS row MATCH (a:车型 {_source_id: row.model_id}), "
            "(b:能源类型 {name: row.right}) "
            "MERGE (a)-[:ENERGY_TYPE_IS]->(b)",
            bundle.model_energy,
        ),
        (
            "UNWIND $rows AS row MATCH (a:车型 {_source_id: row.model_id}), "
            "(b:价格区间 {name: row.right}) "
            "MERGE (a)-[:IN_PRICE_RANGE]->(b)",
            bundle.model_prices,
        ),
    )

    connection = Neo4jConnection()
    with connection.get_session() as session:
        transaction = session.begin_transaction()
        try:
            existing = transaction.run(
                "MATCH (m:车型) RETURN count(m) AS total, count(m._source_id) AS managed"
            ).single()
            if (
                not replace
                and existing
                and existing["total"] > 0
                and existing["managed"] != existing["total"]
            ):
                raise RuntimeError(
                    "现有车型不是由新版导入器管理；首次迁移必须显式使用 --replace。"
                )
            if replace:
                transaction.run("MATCH (n) DETACH DELETE n").consume()
            for statement, rows in (*node_jobs, *relationship_jobs):
                for batch in _batches(rows, batch_size):
                    transaction.run(statement, rows=batch).consume()
            transaction.commit()
        except Exception:
            transaction.rollback()
            raise


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Validate and import the Car Helper dataset")
    parser.add_argument("--apply", action="store_true", help="write validated data to Neo4j")
    parser.add_argument("--replace", action="store_true", help="replace all existing graph data")
    parser.add_argument(
        "--confirm-replace",
        action="store_true",
        help="required together with --apply --replace",
    )
    parser.add_argument("--batch-size", type=int, default=1000)
    args = parser.parse_args(argv)
    if args.batch_size < 1 or args.batch_size > 5000:
        parser.error("--batch-size 必须在 1 到 5000 之间")
    if args.replace and not (args.apply and args.confirm_replace):
        parser.error("替换数据库必须同时提供 --apply --replace --confirm-replace")
    return args


def main(argv=None):
    args = parse_args(argv)
    bundle = load_and_validate_data()
    print("数据文件校验通过：")
    for label, count in bundle.counts().items():
        print(f"  {label}: {count:,}")
    for warning in bundle.warnings:
        print(f"  警告: {warning}")
    if not args.apply:
        print("未提供 --apply，仅执行校验，数据库未修改。")
        return
    import_data(bundle, replace=args.replace, batch_size=args.batch_size)
    print("Neo4j 导入完成。")


if __name__ == "__main__":
    main()
