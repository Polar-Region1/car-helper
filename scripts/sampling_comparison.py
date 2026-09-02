"""
采样算法质量对比
对比四维贪心采样 vs 随机采样的覆盖率
"""
import asyncio
import random
import sys
from pathlib import Path
from typing import List, Dict, Set

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.neo4j_conn import Neo4jConnection


def stratified_sample(results: List[Dict], target_size: int = 20) -> List[Dict]:
    """四维贪心采样（复制自neo4j_tools.py的实现）"""
    if len(results) <= target_size:
        return results

    sampled = []
    remaining = results.copy()

    # 维度1: 品牌覆盖
    brands_seen: Set[str] = set()
    for item in remaining[:]:
        brand = item.get('brand', '未知')
        if brand not in brands_seen:
            sampled.append(item)
            brands_seen.add(brand)
            remaining.remove(item)
            if len(sampled) >= target_size:
                return sampled

    # 维度2: 能源类型覆盖
    energy_seen: Set[str] = set()
    for item in remaining[:]:
        energy = item.get('energy_type', '未知')
        if energy not in energy_seen:
            sampled.append(item)
            energy_seen.add(energy)
            remaining.remove(item)
            if len(sampled) >= target_size:
                return sampled

    # 维度3: 价格区间覆盖
    price_seen: Set[str] = set()
    for item in remaining[:]:
        price_range = item.get('price_range', '未知')
        if price_range not in price_seen:
            sampled.append(item)
            price_seen.add(price_range)
            remaining.remove(item)
            if len(sampled) >= target_size:
                return sampled

    # 维度4: 上市时间填充（倒序）
    remaining.sort(key=lambda x: x.get('launch_date', ''), reverse=True)
    sampled.extend(remaining[:target_size - len(sampled)])

    return sampled


def random_sample(results: List[Dict], target_size: int = 20) -> List[Dict]:
    """随机采样"""
    if len(results) <= target_size:
        return results
    return random.sample(results, target_size)


def calculate_coverage(sampled: List[Dict]) -> Dict[str, float]:
    """计算覆盖率指标"""
    brands = set(item.get('brand', '未知') for item in sampled)
    energy_types = set(item.get('energy_type', '未知') for item in sampled)
    price_ranges = set(item.get('price_range', '未知') for item in sampled)

    return {
        'brand_count': len(brands),
        'energy_count': len(energy_types),
        'price_count': len(price_ranges),
        'total_items': len(sampled)
    }


async def get_large_dataset() -> List[Dict]:
    """获取大数据集用于测试（>100条）"""
    def sync_query():
        conn = Neo4jConnection()
        with conn.get_session() as session:
            query = """
            MATCH (b:品牌)-[:HAS_SERIES]->(s:车系)-[:HAS_MODEL]->(m:车型)
            RETURN m.车名 AS model_name,
                   m.上市时间 AS launch_date,
                   b.name AS brand,
                   m.能源类型 AS energy_type,
                   m.官方指导价 AS price_range
            LIMIT 500
            """
            result = session.run(query)
            return result.data()

    return await asyncio.to_thread(sync_query)


async def run_comparison(iterations: int = 50):
    """运行对比测试"""
    print("\n" + "="*60)
    print("采样算法质量对比测试")
    print("="*60)

    # 获取测试数据
    print("\n正在获取测试数据集（500条）...")
    dataset = await get_large_dataset()
    print(f"数据集大小: {len(dataset)} 条")

    # 计算原始数据的多样性基准
    original_coverage = calculate_coverage(dataset)
    print(f"\n原始数据集多样性:")
    print(f"  品牌数: {original_coverage['brand_count']}")
    print(f"  能源类型数: {original_coverage['energy_count']}")
    print(f"  价格区间数: {original_coverage['price_count']}")

    # 运行多次采样测试
    print(f"\n运行 {iterations} 次采样测试...")

    stratified_results = []
    random_results = []

    for i in range(iterations):
        # 四维贪心采样
        stratified_sampled = stratified_sample(dataset, target_size=20)
        stratified_cov = calculate_coverage(stratified_sampled)
        stratified_results.append(stratified_cov)

        # 随机采样
        random_sampled = random_sample(dataset, target_size=20)
        random_cov = calculate_coverage(random_sampled)
        random_results.append(random_cov)

        if (i + 1) % 10 == 0:
            print(f"  进度: {i+1}/{iterations}")

    # 统计平均覆盖率
    def avg_coverage(results: List[Dict]) -> Dict[str, float]:
        return {
            'brand_count': sum(r['brand_count'] for r in results) / len(results),
            'energy_count': sum(r['energy_count'] for r in results) / len(results),
            'price_count': sum(r['price_count'] for r in results) / len(results),
        }

    stratified_avg = avg_coverage(stratified_results)
    random_avg = avg_coverage(random_results)

    # 输出对比报告
    print("\n" + "="*60)
    print("采样质量对比报告（平均值，50次迭代）")
    print("="*60)
    print(f"{'指标':<20} {'四维贪心':>12} {'随机采样':>12} {'优势':>12}")
    print("-"*60)

    metrics = [
        ('品牌覆盖数', 'brand_count'),
        ('能源类型覆盖数', 'energy_count'),
        ('价格区间覆盖数', 'price_count'),
    ]

    for label, key in metrics:
        stratified_val = stratified_avg[key]
        random_val = random_avg[key]
        improvement = ((stratified_val - random_val) / random_val * 100) if random_val > 0 else 0

        print(f"{label:<20} {stratified_val:>12.1f} {random_val:>12.1f} {improvement:>11.1f}%")

    print("="*60)

    # 计算覆盖率百分比
    stratified_brand_rate = (stratified_avg['brand_count'] / original_coverage['brand_count']) * 100
    random_brand_rate = (random_avg['brand_count'] / original_coverage['brand_count']) * 100

    print(f"\n品牌覆盖率对比:")
    print(f"  四维贪心: {stratified_brand_rate:.1f}% ({stratified_avg['brand_count']:.1f}/{original_coverage['brand_count']})")
    print(f"  随机采样: {random_brand_rate:.1f}% ({random_avg['brand_count']:.1f}/{original_coverage['brand_count']})")
    print(f"  提升: +{stratified_brand_rate - random_brand_rate:.1f} 百分点")

    print("\n结论:")
    if stratified_avg['brand_count'] > random_avg['brand_count']:
        print(f"  ✓ 四维贪心采样在品牌覆盖上优于随机采样 {improvement:.1f}%")
    print(f"  ✓ 将500条压缩至20条，品牌覆盖率仍达 {stratified_brand_rate:.1f}%")


async def main():
    await run_comparison(iterations=50)


if __name__ == '__main__':
    asyncio.run(main())
