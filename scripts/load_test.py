"""Concurrent SSE load test for a running local Car Helper API."""

import argparse
import asyncio
import codecs
import json
import math
import statistics
import time

import aiohttp


def _parse_sse(raw):
    event = "message"
    data = []
    for line in raw.splitlines():
        if line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            data.append(line[5:].strip())
    if not data:
        return event, {}
    return event, json.loads("\n".join(data))


async def send_message(session, base_url, user_id, message, timeout):
    started = time.perf_counter()
    events = []
    error = None
    buffer = ""
    decoder = codecs.getincrementaldecoder("utf-8")()

    def consume_text(text, *, final=False):
        nonlocal buffer, error
        buffer += text.replace("\r\n", "\n")
        frames = buffer.split("\n\n")
        buffer = frames.pop()
        if final and buffer.strip():
            frames.append(buffer)
            buffer = ""
        for frame in frames:
            event, payload = _parse_sse(frame)
            events.append(event)
            if event == "error":
                error = payload.get("message", "SSE error")

    try:
        async with session.post(
            f"{base_url}/api/chat",
            json={"message": message, "session_id": f"load_test_{user_id:04d}"},
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as response:
            if response.status != 200:
                error = f"HTTP {response.status}"
            else:
                async for chunk in response.content.iter_any():
                    consume_text(decoder.decode(chunk))
                consume_text(decoder.decode(b"", final=True), final=True)
    except TimeoutError:
        error = "timeout"
    except Exception as exc:
        error = type(exc).__name__

    elapsed = time.perf_counter() - started
    success = error is None and "done" in events and "content" in events
    return {"success": success, "elapsed": elapsed, "error": error, "events": events}


async def run(args):
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(
            *(
                send_message(session, args.url, index, args.message, args.timeout)
                for index in range(args.users)
            )
        )

    successful = [result["elapsed"] for result in results if result["success"]]
    failures = [result["error"] or "incomplete SSE" for result in results if not result["success"]]
    report = {
        "users": args.users,
        "successes": len(successful),
        "failures": len(failures),
        "success_rate": round(len(successful) / args.users * 100, 2),
        "average_seconds": round(statistics.mean(successful), 2) if successful else None,
        "p95_seconds": round(sorted(successful)[math.ceil(len(successful) * 0.95) - 1], 2)
        if successful
        else None,
        "errors": failures,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:7860")
    parser.add_argument("--users", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--message", default="推荐一款10-20万的新能源车")
    args = parser.parse_args(argv)
    if not 1 <= args.users <= 100:
        parser.error("--users 必须在 1 到 100 之间")
    if args.timeout <= 0:
        parser.error("--timeout 必须大于 0")
    if not args.message.strip():
        parser.error("--message 不能为空")
    return args


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
