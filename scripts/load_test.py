"""
FastAPI SSE 并发压测
模拟多用户同时发送消息，测试并发能力
"""
import asyncio
import aiohttp
import time
from typing import List, Dict
import statistics


async def send_message(session: aiohttp.ClientSession, user_id: int, message: str) -> Dict:
    """模拟单个用户发送消息"""
    url = "http://localhost:7860/api/chat"

    start_time = time.perf_counter()
    success = False
    error_msg = None
    chunks_received = 0

    try:
        async with session.post(
            url,
            json={"message": message, "session_id": f"load_test_user_{user_id}"},
            timeout=aiohttp.ClientTimeout(total=60)
        ) as response:
            if response.status == 200:
                async for line in response.content:
                    if line:
                        chunks_received += 1
                success = True
            else:
                error_msg = f"HTTP {response.status}"
    except asyncio.TimeoutError:
        error_msg = "Timeout"
    except Exception as e:
        error_msg = str(e)

    elapsed = time.perf_counter() - start_time

    return {
        'user_id': user_id,
        'success': success,
        'elapsed': elapsed,
        'chunks': chunks_received,
        'error': error_msg
    }


async def run_concurrent_test(num_users: int, message: str):
    """运行并发测试"""
    print(f"\n{'='*60}")
    print(f"并发压测: {num_users} 用户")
    print(f"测试消息: {message}")
    print(f"{'='*60}\n")

    async with aiohttp.ClientSession() as session:
        tasks = [
            send_message(session, i, message)
            for i in range(num_users)
        ]

        start_time = time.perf_counter()
        results = await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start_time

    # 统计结果
    success_count = sum(1 for r in results if r['success'])
    failed_count = num_users - success_count
    success_rate = (success_count / num_users) * 100

    response_times = [r['elapsed'] for r in results if r['success']]

    if response_times:
        response_times.sort()
        avg_time = statistics.mean(response_times)
        p50 = statistics.median(response_times)
        p95 = response_times[int(len(response_times) * 0.95)] if len(response_times) > 1 else response_times[0]
        p99 = response_times[int(len(response_times) * 0.99)] if len(response_times) > 1 else response_times[0]
    else:
        avg_time = p50 = p95 = p99 = 0

    print(f"总耗时: {total_time:.2f}s")
    print(f"成功请求: {success_count}/{num_users} ({success_rate:.1f}%)")
    print(f"失败请求: {failed_count}")

    if response_times:
        print(f"\n响应时间统计:")
        print(f"  平均: {avg_time:.2f}s")
        print(f"  P50: {p50:.2f}s")
        print(f"  P95: {p95:.2f}s")
        print(f"  P99: {p99:.2f}s")

    if failed_count > 0:
        print(f"\n失败原因:")
        errors = {}
        for r in results:
            if not r['success'] and r['error']:
                errors[r['error']] = errors.get(r['error'], 0) + 1
        for error, count in errors.items():
            print(f"  {error}: {count}次")

    return {
        'num_users': num_users,
        'success_rate': success_rate,
        'total_time': round(total_time, 2),
        'avg_response_time': round(avg_time, 2),
        'p50': round(p50, 2),
        'p95': round(p95, 2),
        'p99': round(p99, 2),
    }


async def main():
    """主测试流程"""
    print("\n" + "="*60)
    print("FastAPI SSE 并发压测")
    print("="*60)
    print("\n请确保 FastAPI 服务已启动 (python -m src.api)")
    print("按 Enter 开始测试...")
    input()

    # 测试配置
    test_configs = [
        {'users': 5, 'message': '推荐一款10-20万的新能源车'},
        {'users': 10, 'message': '比亚迪有哪些纯电动车？'},
        {'users': 20, 'message': '对比几款热门SUV'},
    ]

    results = []

    for config in test_configs:
        result = await run_concurrent_test(config['users'], config['message'])
        results.append(result)
        await asyncio.sleep(3)  # 间隔3秒

    # 汇总报告
    print("\n" + "="*60)
    print("压测汇总报告")
    print("="*60)
    print(f"{'并发数':>8} {'成功率':>10} {'总耗时':>10} {'平均响应':>10} {'P95':>8}")
    print("-"*60)

    for r in results:
        print(f"{r['num_users']:>8} {r['success_rate']:>9.1f}% {r['total_time']:>9.1f}s {r['avg_response_time']:>9.1f}s {r['p95']:>7.1f}s")

    print("="*60)


if __name__ == '__main__':
    asyncio.run(main())
