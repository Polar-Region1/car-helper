"""
Neo4j 查询性能测试
测试7个工具的P50/P95/P99耗时
"""
import asyncio
import time
import statistics
from typing import List
import pytest

from src.tools.neo4j_tools import (
    query_by_brand,
    query_by_price_range,
    query_by_energy_type,
    query_by_conditions,
    compare_models,
    query_by_maintenance_cost,
    explore_schema
)


async def measure_query_time(query_func, *args, **kwargs) -> float:
    """测量单次查询耗时（秒）"""
    start = time.perf_counter()
    # 使用 ainvoke 调用 LangChain tool
    await query_func.ainvoke(kwargs)
    return time.perf_counter() - start


async def run_performance_test(query_func, params: dict, test_name: str, iterations: int = 100):
    """运行性能测试并统计P50/P95/P99"""
    print(f"\n{'='*60}")
    print(f"测试: {test_name}")
    print(f"参数: {params}")
    print(f"迭代次数: {iterations}")

    times: List[float] = []

    for i in range(iterations):
        elapsed = await measure_query_time(query_func, **params)
        times.append(elapsed)
        if (i + 1) % 10 == 0:
            print(f"  进度: {i+1}/{iterations}")

    times.sort()
    p50 = statistics.median(times)
    p95 = times[int(len(times) * 0.95)]
    p99 = times[int(len(times) * 0.99)]
    avg = statistics.mean(times)

    print(f"\n结果:")
    print(f"  平均耗时: {avg*1000:.2f}ms")
    print(f"  P50: {p50*1000:.2f}ms")
    print(f"  P95: {p95*1000:.2f}ms")
    print(f"  P99: {p99*1000:.2f}ms")

    return {
        'test_name': test_name,
        'avg_ms': round(avg * 1000, 2),
        'p50_ms': round(p50 * 1000, 2),
        'p95_ms': round(p95 * 1000, 2),
        'p99_ms': round(p99 * 1000, 2),
    }


@pytest.mark.asyncio
async def test_performance_all_tools():
    """完整性能测试（所有7个工具）"""

    test_cases = [
        {
            'func': query_by_brand,
            'params': {'brand': '比亚迪', 'limit': 20},
            'name': 'query_by_brand（品牌查询）'
        },
        {
            'func': query_by_price_range,
            'params': {'price_range': '10-20万', 'limit': 20},
            'name': 'query_by_price_range（价格区间查询）'
        },
        {
            'func': query_by_energy_type,
            'params': {'energy_type': '纯电动', 'limit': 20},
            'name': 'query_by_energy_type（能源类型查询）'
        },
        {
            'func': query_by_conditions,
            'params': {
                'price_range': '10-20万',
                'energy_type': '纯电动',
                'limit': 20
            },
            'name': 'query_by_conditions（多条件组合查询）'
        },
        {
            'func': compare_models,
            'params': {'brand': '比亚迪', 'limit': 5},
            'name': 'compare_models（车型对比）'
        },
        {
            'func': query_by_maintenance_cost,
            'params': {'price_ranges': ['10-20万'], 'limit': 20},
            'name': 'query_by_maintenance_cost（保养成本查询）'
        },
        {
            'func': explore_schema,
            'params': {'node_type': 'Brand', 'limit': 20},
            'name': 'explore_schema（Schema探索）'
        },
    ]

    results = []

    print("\n" + "="*60)
    print("Neo4j 查询性能基准测试")
    print("="*60)

    for test_case in test_cases:
        result = await run_performance_test(
            test_case['func'],
            test_case['params'],
            test_case['name'],
            iterations=100
        )
        results.append(result)
        await asyncio.sleep(0.5)  # 避免过载

    # 汇总报告
    print("\n" + "="*60)
    print("性能测试汇总报告")
    print("="*60)
    print(f"{'工具名称':<40} {'平均':>8} {'P50':>8} {'P95':>8} {'P99':>8}")
    print("-"*60)

    for r in results:
        print(f"{r['test_name']:<40} {r['avg_ms']:>7.1f}ms {r['p50_ms']:>7.1f}ms {r['p95_ms']:>7.1f}ms {r['p99_ms']:>7.1f}ms")

    print("="*60)

    # 断言：所有P95应该<500ms
    for r in results:
        assert r['p95_ms'] < 500, f"{r['test_name']} P95耗时过长: {r['p95_ms']}ms"


if __name__ == '__main__':
    asyncio.run(test_performance_all_tools())
