# Car Helper 重构设计规格

## 目标目录结构

```
src/
├── agent.py              # Agent 入口，注册工具
├── tools/
│   ├── __init__.py
│   ├── neo4j_tools.py    # 7 个参数化查询工具 + 分层采样 + 结果校验
│   └── web_search.py     # Tavily 搜索工具
├── db/
│   ├── __init__.py
│   └── neo4j_conn.py     # Neo4j 单例连接管理
├── prompts/
│   └── system_prompt.py  # 瘦身后的 system prompt（~80行）
└── data_import/          # 数据导入脚本（原 store_data_to_neo4j / insert_data_to_neo4j）
```

## db/neo4j_conn.py — 连接管理

单例模式，所有模块共享同一个 driver：

```python
from neo4j import GraphDatabase

class Neo4jConnection:
    _instance = None

    def __new__(cls, url="bolt://localhost", username="neo4j", password="12345678"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.driver = GraphDatabase.driver(url, auth=(username, password))
        return cls._instance

    def get_session(self):
        return self.driver.session()

    def close(self):
        self.driver.close()
```

## tools/neo4j_tools.py — 7 个查询工具

### T3: query_by_brand

参数: `brand: str`, `limit: int = 500`

```cypher
MATCH (b:品牌)-[:HAS_SERIES]->(s:车系)-[:HAS_MODEL]->(m:车型)
WHERE b.name = $brand
RETURN b.name AS 品牌, s.name AS 车系, m.车名 AS 车型,
       m.`官方指导价` AS 指导价, m.能源类型 AS 能源类型, m.级别 AS 级别,
       m.`上市时间` AS 上市时间
ORDER BY rand()
LIMIT $limit
```

### T4: query_by_price_range

参数: `price_range: str`, `limit: int = 500`

```cypher
MATCH (m:车型)-[:IN_PRICE_RANGE]->(p:价格区间)
WHERE p.name = $price_range
MATCH (s:车系)-[:HAS_MODEL]->(m)
MATCH (b:品牌)-[:HAS_SERIES]->(s)
RETURN b.name AS 品牌, s.name AS 车系, m.车名 AS 车型,
       m.`官方指导价` AS 指导价, m.能源类型 AS 能源类型, m.级别 AS 级别
ORDER BY toFloat(replace(m.`官方指导价`, '万', '')) ASC
LIMIT $limit
```

### T5: query_by_energy_type

参数: `energy_type: str`, `limit: int = 500`

```cypher
MATCH (m:车型)-[:ENERGY_TYPE_IS]->(e:能源类型)
WHERE e.name = $energy_type
MATCH (s:车系)-[:HAS_MODEL]->(m)
MATCH (b:品牌)-[:HAS_SERIES]->(s)
RETURN b.name AS 品牌, s.name AS 车系, m.车名 AS 车型,
       m.`官方指导价` AS 指导价,
       m.`纯电续航里程(km)CLTC` AS 纯电续航, m.级别 AS 级别
ORDER BY toInteger(m.`纯电续航里程(km)CLTC`) DESC
LIMIT $limit
```

### T6: query_by_conditions

参数: `price_range: str = None`, `energy_type: str = None`, `level: str = None`, `brand: str = None`, `limit: int = 500`

骨架固定，WHERE 子句动态拼接（仅允许上述四个参数，防止注入）：

```cypher
MATCH (m:车型)
WHERE 1=1
  [AND m.级别 CONTAINS $level]       -- 仅当 level 有值
  [AND b.name = $brand]              -- 仅当 brand 有值
[OPTIONAL MATCH (m)-[:IN_PRICE_RANGE]->(p:价格区间)
 WHERE p.name = $price_range]        -- 仅当 price_range 有值
[OPTIONAL MATCH (m)-[:ENERGY_TYPE_IS]->(e:能源类型)
 WHERE e.name = $energy_type]        -- 仅当 energy_type 有值
MATCH (s:车系)-[:HAS_MODEL]->(m)
MATCH (b:品牌)-[:HAS_SERIES]->(s)
RETURN b.name AS 品牌, s.name AS 车系, m.车名 AS 车型,
       m.`官方指导价` AS 指导价, m.能源类型 AS 能源类型, m.级别 AS 级别,
       m.`上市时间` AS 上市时间
ORDER BY m.`上市时间` DESC
LIMIT $limit
```

实现时 Python 侧根据参数是否存在动态拼 Cypher 字符串，参数值始终通过 `$param` 传入，不拼接原始字符串。

### T7: compare_models

参数: `brand: str`, `limit: int = 500`

```cypher
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
```

### T8: query_by_maintenance_cost

参数: `price_ranges: list[str]`, `limit: int = 500`

```cypher
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
```

### T9: explore_schema

参数: `node_type: str`（允许值: 品牌/车系/车型/价格区间/能源类型）, `limit: int = 10`

```cypher
MATCH (n:$node_type) RETURN n LIMIT $limit
```

实现时 `node_type` 通过白名单校验（仅允许上述 5 个值），防止任意标签注入。

## 分层采样 — stratified_sample

在 tools/neo4j_tools.py 中实现，每个查询工具返回结果前先过采样。

采样顺序（优先级从高到低）：

1. **品牌覆盖** — 每个品牌至少取 1 条（优先最新上市）
2. **能源类型覆盖** — 补充尚未覆盖的能源类型
3. **价格区间覆盖** — 补充尚未覆盖的价格段
4. **上市时间填充** — 剩余配额按上市时间倒序填满

```python
def stratified_sample(records: list[dict], max_count: int = 20) -> list[dict]:
    if len(records) <= max_count:
        return records

    brand_buckets = defaultdict(list)
    for r in records:
        brand_buckets[r.get("品牌", "未知")].append(r)

    sampled = []
    # 维度1: 品牌
    for brand, cars in brand_buckets.items():
        cars.sort(key=lambda x: x.get("上市时间", ""), reverse=True)
        sampled.append(cars[0])

    # 维度2: 能源类型
    energy_covered = {r.get("能源类型") for r in sampled}
    for r in records:
        if len(sampled) >= max_count:
            break
        if r.get("能源类型") not in energy_covered:
            sampled.append(r)
            energy_covered.add(r.get("能源类型"))

    # 维度3: 价格区间
    if len(sampled) < max_count:
        price_covered = set()
        for r in sampled:
            price = r.get("指导价", "")
            if price and price != "暂无报价":
                bucket = price  # 或按万位分桶
                price_covered.add(bucket)
        for r in records:
            if len(sampled) >= max_count:
                break
            price = r.get("指导价", "")
            if price and price != "暂无报价" and price not in price_covered:
                sampled.append(r)
                price_covered.add(price)

    # 维度4: 上市时间填充
    if len(sampled) < max_count:
        remaining = [r for r in records if r not in sampled]
        remaining.sort(key=lambda x: x.get("上市时间", ""), reverse=True)
        sampled.extend(remaining[: max_count - len(sampled)])

    return sampled[:max_count]
```

## 采样统计 — sample_stats

```python
def sample_stats(records, sampled):
    def unique(field, data):
        return len(set(r.get(field, "?") for r in data))

    return {
        "原始条数": len(records),
        "采样条数": len(sampled),
        "品牌覆盖": f"{unique('品牌', sampled)}/{unique('品牌', records)}",
        "能源覆盖": f"{unique('能源类型', sampled)}/{unique('能源类型', records)}",
    }
```

调试时打印此统计，便于调 max_count。生产环境可关闭。

## 结果校验 — validate_result

```python
def validate_result(data, tool_name):
    if not data:
        return f"[{tool_name}] 未查询到结果，请尝试调整筛选条件（如更换品牌、价格区间、能源类型等）"

    # 检查关键字段是否全缺失
    required_fields = ["品牌", "车系", "车型"]
    for record in data:
        missing = [f for f in required_fields if not record.get(f) or record.get(f) == "NONE"]
        if len(missing) == len(required_fields):
            return f"[{tool_name}] 查询结果关键字段全缺失，数据可能异常"

    return data
```

## System Prompt 瘦身方向

删除：全部 Cypher 示例（8 个场景 × 完整语句）、Cypher 语法注意事项、实体属性详细表

保留/改写：
- 角色定义（1 句）
- 知识图谱结构概要（节点数+关系数，3 行）
- 工具列表改为描述每个工具的适用场景（不含内部实现）
- 工具使用策略（结构化→query 工具，非结构化→web_search）
- 回答格式要求（免责声明、信息不足时追问）
- 目标：~80 行

## Web Search 工具迁移

从 agent.py 中抽出 TavilySearch 实例化逻辑到 tools/web_search.py，参数和行为不变。

## 数据流（重构后）

```
Neo4j → Cypher模板(LIMIT 500) → Python分层采样(→20条) → validate_result → LLM → 用户
```
