"""In-process workflow event bus: replay, live tail, cross-thread publish, close on finish."""

import asyncio
import threading

from app.workflows.events import EventBus


def _node(thread_id: str, node: str, phase: str) -> dict:
    return {"thread_id": thread_id, "type": "node", "node": node, "phase": phase}


def _run(thread_id: str, status: str) -> dict:
    return {"thread_id": thread_id, "type": "run", "status": status}


def test_replay_then_live_from_another_thread_then_close() -> None:
    bus = EventBus()
    bus.publish(_node("t1", "decompose", "start"))
    bus.publish(_node("other", "decompose", "start"))  # different run: never delivered

    async def consume() -> list[dict]:
        seen = []
        async for event in bus.subscribe("t1"):
            seen.append(event)
            if len(seen) == 1:  # replayed; now publish the rest from a worker thread
                threading.Thread(
                    target=lambda: [
                        bus.publish(_node("t1", "decompose", "end")),
                        bus.publish(_run("t1", "waiting")),  # not terminal: keep streaming
                        bus.publish(_run("t1", "committed")),
                        bus.publish(_node("t1", "late", "start")),  # after the end: not sent
                    ]
                ).start()
        return seen

    seen = asyncio.run(asyncio.wait_for(consume(), timeout=5))

    assert [(e.get("node"), e.get("phase"), e.get("status")) for e in seen] == [
        ("decompose", "start", None),
        ("decompose", "end", None),
        (None, None, "waiting"),
        (None, None, "committed"),
    ]
    assert [e["seq"] for e in seen] == [1, 3, 4, 5]


def test_finished_run_replays_and_closes_and_respects_last_event_id() -> None:
    bus = EventBus()
    for event in (_node("t1", "commit", "start"), _node("t1", "commit", "end")):
        bus.publish(event)
    bus.publish(_run("t1", "rejected"))

    async def collect(after: int) -> list[int]:
        return [e["seq"] async for e in bus.subscribe("t1", after)]

    assert asyncio.run(collect(0)) == [1, 2, 3]
    assert asyncio.run(collect(2)) == [3]


def test_current_node_is_the_last_one_started_and_not_ended() -> None:
    bus = EventBus()
    assert bus.current_node("t1") is None
    bus.publish(_node("t1", "estimate", "start"))
    bus.publish(_node("t1", "estimate", "end"))
    bus.publish(_node("t1", "schedule", "start"))

    assert bus.current_node("t1") == "schedule"
