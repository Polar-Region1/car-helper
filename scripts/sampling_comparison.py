"""Compare the production sampler with random sampling on live read-only data."""

import argparse
import random

from src.db.neo4j_conn import Neo4jConnection
from src.tools.neo4j_tools import sample_stats, stratified_sample


QUERY = """
MATCH (b:品牌)-[:HAS_SERIES]->(s:车系)-[:HAS_MODEL]->(m:车型)
OPTIONAL MATCH (m)-[:IN_PRICE_RANGE]->(p:价格区间)
RETURN DISTINCT b.name AS 品牌, s.name AS 车系, m.车名 AS 车型,
       m.能源类型 AS 能源类型, m.`官方指导价` AS 指导价,
       p.name AS 价格区间, m.`上市时间` AS 上市时间
ORDER BY rand()
LIMIT $limit
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", type=int, default=500)
    parser.add_argument("--sample-size", type=int, default=20)
    parser.add_argument("--iterations", type=int, default=50)
    args = parser.parse_args()
    if args.sample_size < 1 or args.candidates < args.sample_size:
        parser.error("候选数必须不小于正数采样数")
    if args.iterations < 1:
        parser.error("--iterations 必须大于 0")

    with Neo4jConnection().get_session() as session:
        records = session.run(QUERY, limit=args.candidates).data()
    if len(records) <= args.sample_size:
        raise SystemExit("候选数据不足，无法比较采样算法")

    stratified = stratified_sample(records, args.sample_size)
    random_samples = [random.sample(records, args.sample_size) for _ in range(args.iterations)]
    random_stats = [sample_stats(records, sample) for sample in random_samples]
    print("生产采样：", sample_stats(records, stratified))
    print("随机采样平均覆盖：")
    for key in ("品牌覆盖", "能源覆盖", "价格区间覆盖"):
        counts = [int(stats[key].split("/")[0]) for stats in random_stats]
        print(f"  {key}: {sum(counts) / len(counts):.2f}")


if __name__ == "__main__":
    main()
