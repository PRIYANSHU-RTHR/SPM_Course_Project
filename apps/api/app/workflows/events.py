"""In-process event bus for workflow progress (node start/end, run status).

Graph runs happen in worker threads; SSE subscribers are coroutines. `publish` is thread-safe
and hands each event to every subscriber's event loop with `call_soon_threadsafe`. Every event
is also kept per thread so a late subscriber replays the history before the live tail, with
no gap between the two (both happen under one lock).

shortcut: history lives in memory only. After a restart the checkpointer still has the run's
state, but the timeline restarts empty (`PlanWorkflows.subscribe` sends the final status).
"""

import asyncio
import contextlib
import threading
import time
from collections import defaultdict
from collections.abc import AsyncIterator, Callable
from typing import Any

from langgraph.errors import GraphInterrupt

from app.schemas.workflow import TERMINAL_STATUSES

Event = dict[str, Any]


def is_terminal(event: Event) -> bool:
    return event.get("type") == "run" and event.get("status") in TERMINAL_STATUSES


class EventBus:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._seq = 0
        self._history: dict[str, list[Event]] = defaultdict(list)
        self._subscribers: dict[str, set[tuple[asyncio.AbstractEventLoop, asyncio.Queue[Event]]]]
        self._subscribers = defaultdict(set)

    def publish(self, event: Event) -> Event:
        """Stamp `seq`, store, fan out. Callable from any thread."""
        with self._lock:
            self._seq += 1
            event = {**event, "seq": self._seq}
            thread_id = event["thread_id"]
            self._history[thread_id].append(event)
            subscribers = list(self._subscribers[thread_id])
        for loop, queue in subscribers:
            # The subscriber's loop may already be gone (client disconnected mid-publish).
            with contextlib.suppress(RuntimeError):
                loop.call_soon_threadsafe(queue.put_nowait, event)
        return event

    def history(self, thread_id: str) -> list[Event]:
        with self._lock:
            return list(self._history.get(thread_id, ()))

    def current_node(self, thread_id: str) -> str | None:
        """The node that started last and has not ended yet."""
        open_nodes: list[str] = []
        for e in self.history(thread_id):
            if e["type"] != "node":
                continue
            if e["phase"] == "start":
                open_nodes.append(e["node"])
            elif e["node"] in open_nodes:
                open_nodes.remove(e["node"])
        return open_nodes[-1] if open_nodes else None

    async def subscribe(self, thread_id: str, after_seq: int = 0) -> AsyncIterator[Event]:
        """Past events with seq > after_seq, then live ones; ends after a terminal run event."""
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[Event] = asyncio.Queue()
        key = (loop, queue)
        with self._lock:
            past = [e for e in self._history.get(thread_id, ()) if e["seq"] > after_seq]
            self._subscribers[thread_id].add(key)
        try:
            last = after_seq
            for event in past:
                last = event["seq"]
                yield event
                if is_terminal(event):
                    return
            while True:
                event = await queue.get()
                if event["seq"] <= last:  # published between the snapshot and registering
                    continue
                last = event["seq"]
                yield event
                if is_terminal(event):
                    return
        finally:
            with self._lock:
                self._subscribers[thread_id].discard(key)


NodeResult = tuple[Any, str]  # (state update or Command, one-line summary for the timeline)
Publish = Callable[[Event], Any]


def timed(name: str, fn: Callable[[Any], NodeResult], publish: Publish) -> Callable[[Any], Any]:
    """Wrap a graph node: publish start/end events with duration and the node's summary.
    An interrupt ends the node as 'waiting'; it starts again on resume."""

    def node(state: Any) -> Any:
        base = {"thread_id": state["thread_id"], "type": "node", "node": name}
        publish({**base, "phase": "start"})
        started = time.perf_counter()

        def end(summary: str) -> None:
            ms = round((time.perf_counter() - started) * 1000, 1)
            publish({**base, "phase": "end", "duration_ms": ms, "summary": summary})

        try:
            update, summary = fn(state)
        except GraphInterrupt:
            end("waiting for PM review")
            raise
        end(summary)
        return update

    return node
