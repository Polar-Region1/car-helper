import asyncio
import logging
from collections import defaultdict
from langchain_core.tools import tool
from src.db.neo4j_conn import Neo4jConnection, Neo4jConnectionError

logger = logging.getLogger(__name__)

ALLOWED_NODE_TYPES = {"品牌", "车系", "车型", "价格区间", "能源类型"}


# ─── 同步辅助函数（完全保持原样，无需改动）─────────────────

def stratified_sample(records: list[dict], max_count: int = 20) -> list[dict]:
    if len(records) <= max_count:
        return records

    brand_buckets = defaultdict(list)
    for r in records:
        brand_buckets[r.get("品牌", "未知")].append(r)

    sampled = []

    # 维度1: 品牌覆盖（最多占一半配额，留空间给后续维度）
    brand_cap = max(max_count // 2, 1)
    for brand, cars in brand_buckets.items():
        if len(sampled) >= brand_cap:
            break
        cars.sort(key=lambda x: x.get("上市时间", ""), reverse=True)
        sampled.append(cars[0])

    # 维度2: 能源类型覆盖
    energy_covered = {r.get("能源类型") for r in sampled}
    for r in records:
        if len(sampled) >= max_count:
            break
        if r.get("能源类型") not in energy_covered:
            sampled.append(r)
            energy_covered.add(r.get("能源类型"))

    # 维度3: 价格区间覆盖
    if len(sampled) < max_count:
        price_covered = set()
        for r in sampled:
            price = r.get("指导价", "")
            if price and price not in ("暂无报价", "NONE", ""):
                price_covered.add(price)
        for r in records:
            if len(sampled) >= max_count:
                break
            price = r.get("指导价", "")
            if price and price not in ("暂无报价", "NONE", "") and price not in price_covered:
                sampled.append(r)
                price_covered.add(price)

    # 维度4: 上市时间填充
    if len(sampled) < max_count:
        sampled_set = set(id(r) for r in sampled)
        remaining = [r for r in records if id(r) not in sampled_set]
        remaining.sort(key=lambda x: x.get("上市时间", ""), reverse=True)
        sampled.extend(remaining[: max_count - len(sampled)])

    return sampled[:max_count]


def sample_stats(records, sampled):
    def unique(field, data):
        return len(set(r.get(field, "?") for r in data))

    return {
        "原始条数": len(records),
        "采样条数": len(sampled),
        "品牌覆盖": f"{unique('品牌', sampled)}/{unique('品牌', records)}",
        "能源覆盖": f"{unique('能源类型', sampled)}/{unique('能源类型', records)}",
    }


def validate_result(data, tool_name):
    if not data:
        return f"[{tool_name}] 未查询到结果，请尝试调整筛选条件（如更换品牌、价格区间、能源类型等）"

    required_fields = ["品牌", "车系", "车型"]
    for record in data:
        missing = [f for f in required_fields if not record.get(f) or record.get(f) == "NONE"]
        if len(missing) == len(required_fields):
            return f"[{tool_name}] 查询结果关键字段全缺失，数据可能异常"

    return data


# ─── 内部查询执行（改造为异步，将同步调用放入线程池）────────

async def _run_query_threaded(cypher: str, params: dict) -> list[dict]:
    def sync_query():
        try:
            conn = Neo4jConnection()
            with conn.get_session() as session:
                result = session.run(cypher, params)
                return result.data()
        except Neo4jConnectionError as e:
            logger.error("数据库连接错误: %s", e)
            return [{"error": str(e)}]
        except Exception as e:
            logger.error("查询执行异常: %s", e)
            return [{"error": f"数据库查询失败，请稍后重试。详情: {e}"}]

    return await asyncio.to_thread(sync_query)


async def _query_with_sample_threaded(cypher: str, params: dict, tool_name: str, max_count: int = 20):
    raw = await _run_query_threaded(cypher, params)

    if raw and isinstance(raw, list) and len(raw) > 0 and "error" in raw[0]:
        return raw[0]["error"]

    validated = validate_result(raw, tool_name)
    if isinstance(validated, str):
        return validated
    sampled = stratified_sample(validated, max_count)
    stats = sample_stats(raw, sampled)
    return {"数据": sampled, "采样统计": stats}


# ─── 7 个工具（全部改为 async def）────────────────────────

@tool
async def query_by_brand(brand: str, limit: int = 500) -> dict | str:
    """根据品牌查询车型。当用户问"某品牌有哪些车"时使用。brand 为品牌名称。"""
    cypher = """
    MATCH (b:品牌)-[:HAS_SERIES]->(s:车系)-[:HAS_MODEL]->(m:车型)
    WHERE b.name = $brand
    RETURN b.name AS 品牌, s.name AS 车系, m.车名 AS 车型,
           m.`官方指导价` AS 指导价, m.能源类型 AS 能源类型, m.级别 AS 级别,
           m.`上市时间` AS 上市时间
    ORDER BY rand()
    LIMIT $limit
    """
    return await _query_with_sample_threaded(cypher, {"brand": brand, "limit": limit}, "query_by_brand")


@tool
async def query_by_price_range(price_range: str, limit: int = 500) -> dict | str:
    """根据价格区间查询车型。price_range 取值: 0-10万, 10-20万, 20-30万, 30-40万, 40-50万, 50万以上。"""
    cypher = """
    MATCH (m:车型)-[:IN_PRICE_RANGE]->(p:价格区间)
    WHERE p.name = $price_range
    MATCH (s:车系)-[:HAS_MODEL]->(m)
    MATCH (b:品牌)-[:HAS_SERIES]->(s)
    RETURN b.name AS 品牌, s.name AS 车系, m.车名 AS 车型,
           m.`官方指导价` AS 指导价, m.能源类型 AS 能源类型, m.级别 AS 级别
    ORDER BY toFloat(replace(m.`官方指导价`, '万', '')) ASC
    LIMIT $limit
    """
    return await _query_with_sample_threaded(cypher, {"price_range": price_range, "limit": limit}, "query_by_price_range")


@tool
async def query_by_energy_type(energy_type: str, limit: int = 500) -> dict | str:
    """根据能源类型查询车型。energy_type 取值: 汽油, 纯电动, 插电式混合动力, 增程式, 其他。"""
    cypher = """
    MATCH (m:车型)-[:ENERGY_TYPE_IS]->(e:能源类型)
    WHERE e.name = $energy_type
    MATCH (s:车系)-[:HAS_MODEL]->(m)
    MATCH (b:品牌)-[:HAS_SERIES]->(s)
    RETURN b.name AS 品牌, s.name AS 车系, m.车名 AS 车型,
           m.`官方指导价` AS 指导价,
           m.`纯电续航里程(km)CLTC` AS 纯电续航, m.级别 AS 级别
    ORDER BY toInteger(m.`纯电续航里程(km)CLTC`) DESC
    LIMIT $limit
    """
    return await _query_with_sample_threaded(cypher, {"energy_type": energy_type, "limit": limit}, "query_by_energy_type")


@tool
async def query_by_conditions(
    price_range: str = None,
    energy_type: str = None,
    level: str = None,
    brand: str = None,
    limit: int = 500,
) -> dict | str:
    """多条件组合查询车型。可同时指定价格区间、能源类型、车型级别、品牌中的任意组合。level 为模糊匹配（如'SUV'会匹配所有SUV级别）。"""
    # 动态拼接 WHERE 子句，仅允许四个参数，值始终通过 $param 传入
    match_clauses = ["MATCH (m:车型)"]
    where_parts = ["1=1"]

    if level:
        where_parts.append("m.级别 CONTAINS $level")
    if brand:
        match_clauses.append("MATCH (b:品牌)-[:HAS_SERIES]->(s:车系)-[:HAS_MODEL]->(m)")
        where_parts.append("b.name = $brand")
    else:
        match_clauses.append("MATCH (s:车系)-[:HAS_MODEL]->(m)")
        if brand is None:
            match_clauses.append("MATCH (b:品牌)-[:HAS_SERIES]->(s)")

    if price_range:
        match_clauses.append("MATCH (m)-[:IN_PRICE_RANGE]->(p:价格区间)")
        where_parts.append("p.name = $price_range")
    if energy_type:
        match_clauses.append("MATCH (m)-[:ENERGY_TYPE_IS]->(e:能源类型)")
        where_parts.append("e.name = $energy_type")

    cypher = (
        " ".join(match_clauses)
        + " WHERE " + " AND ".join(where_parts)
        + """
        RETURN b.name AS 品牌, s.name AS 车系, m.车名 AS 车型,
               m.`官方指导价` AS 指导价, m.能源类型 AS 能源类型, m.级别 AS 级别,
               m.`上市时间` AS 上市时间
        ORDER BY m.`上市时间` DESC
        LIMIT $limit
        """
    )

    params = {"limit": limit}
    if price_range:
        params["price_range"] = price_range
    if energy_type:
        params["energy_type"] = energy_type
    if level:
        params["level"] = level
    if brand:
        params["brand"] = brand

    return await _query_with_sample_threaded(cypher, params, "query_by_conditions")


@tool
async def compare_models(brand: str, limit: int = 500) -> dict | str:
    """对比某品牌下不同车型的详细配置。返回价格、续航、加速、尺寸、保养成本等。brand 为品牌名称。"""
    cypher = """
    MATCH (b:品牌)-[:HAS_SERIES]->(s:车系)-[:HAS_MODEL]->(m:车型)
    WHERE b.name = $brand AND m.车名 CONTAINS $brand
    RETURN b.name AS 品牌, s.name AS 车系, m.车名 AS 车型,
           m.`官方指导价` AS 指导价, m.能源类型 AS 能源类型, m.级别 AS 级别,
           m.`纯电续航里程(km)CLTC` AS 纯电续航,
           m.`官方百公里加速时间(s)` AS 百公里加速,
           m.`长x宽x高(mm)` AS 车身尺寸, m.`车身结构` AS 车身结构,
           m.`整车保修期限` AS 保修期限,
           m.`6万公里保养总成本预估` AS 保养成本
    ORDER BY m.能源类型, toFloat(replace(m.`官方指导价`, '万', '')) ASC
    LIMIT $limit
    """
    return await _query_with_sample_threaded(cypher, {"brand": brand, "limit": limit}, "compare_models")


@tool
async def query_by_maintenance_cost(price_ranges: list[str], limit: int = 500) -> dict | str:
    """查询指定价格区间内保养成本最低的车型。price_ranges 为价格区间列表，如 ['0-10万', '10-20万']。"""
    cypher = """
    MATCH (m:车型)-[:IN_PRICE_RANGE]->(p:价格区间)
    WHERE p.name IN $price_ranges
      AND m.`6万公里保养总成本预估` <> 'NONE'
      AND m.`6万公里保养总成本预估` <> ''
    MATCH (s:车系)-[:HAS_MODEL]->(m)
    MATCH (b:品牌)-[:HAS_SERIES]->(s)
    RETURN b.name AS 品牌, s.name AS 车系, m.车名 AS 车型,
           m.`官方指导价` AS 指导价,
           m.`6万公里保养总成本预估` AS 保养成本,
           m.能源类型 AS 能源类型, m.级别 AS 级别
    ORDER BY toFloat(replace(m.`6万公里保养总成本预估`, '元', '')) ASC
    LIMIT $limit
    """
    return await _query_with_sample_threaded(cypher, {"price_ranges": price_ranges, "limit": limit}, "query_by_maintenance_cost")


@tool
async def explore_schema(node_type: str, limit: int = 15) -> list[dict] | str:
    """安全地探索知识图谱中的节点样例。node_type 仅允许: 品牌, 车系, 车型, 价格区间, 能源类型。默认返回 10 条。"""
    if node_type not in ALLOWED_NODE_TYPES:
        return f"[explore_schema] node_type 仅允许: {', '.join(ALLOWED_NODE_TYPES)}，收到: '{node_type}'"

    cypher = f"MATCH (n:`{node_type}`) RETURN n LIMIT $limit"
    raw = await _run_query_threaded(cypher, {"limit": limit})

    if not raw:
        return f"[explore_schema] 节点类型 '{node_type}' 未查询到数据"

    result = [dict(record["n"]) for record in raw]
    return result