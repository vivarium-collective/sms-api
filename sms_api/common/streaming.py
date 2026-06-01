"""
HTTP response heartbeat streaming.

Long-running synchronous endpoints (notably ``POST /api/v1/analyses``) keep
a single TCP connection open across the RKE ingress, the api pod, an HPC
SSH session, and the SLURM scheduler. Idle-timeouts at any hop will kill
the connection before the SLURM job completes.

``stream_json_with_heartbeats`` wraps an awaitable that returns a
JSON-serializable result and emits whitespace heartbeats into the response
body every ``heartbeat_interval`` seconds until the work completes, at
which point it yields the JSON-encoded result. Leading whitespace is
tolerated by every standard JSON parser, so the response body remains a
valid JSON document from the client's perspective — no client change
beyond opting in to the streaming response.

See ``PTOOLS_LATENCY_MITIGATION.md`` (Path F) for the design context.
"""

import asyncio
import json
from collections.abc import AsyncIterator, Awaitable
from typing import Any

from fastapi.encoders import jsonable_encoder

DEFAULT_HEARTBEAT_INTERVAL = 5.0
_HEARTBEAT_CHUNK = b" \n"


async def stream_json_with_heartbeats(
    work: Awaitable[Any],
    heartbeat_interval: float = DEFAULT_HEARTBEAT_INTERVAL,
) -> AsyncIterator[bytes]:
    """Drive ``work`` to completion while emitting whitespace heartbeats.

    On success, yields the JSON-encoded result as the final chunk.
    On failure, yields a JSON error object as the final chunk. The HTTP
    status code is already 200 by the time we know whether the work
    succeeded, so errors are body-encoded — the caller distinguishes by
    inspecting the JSON shape.
    """
    task: asyncio.Task[Any] = asyncio.ensure_future(work)
    try:
        while not task.done():
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=heartbeat_interval)
            except TimeoutError:
                yield _HEARTBEAT_CHUNK
            except BaseException:
                # The task raised (or was cancelled). Fall through to the result
                # branch below; ``task.result()`` will re-raise it.
                break
        try:
            result = task.result()
        except Exception as exc:
            payload: dict[str, Any] = {
                "error": type(exc).__name__,
                "message": str(exc),
            }
            extra = getattr(exc, "to_dict", None)
            if callable(extra):
                try:
                    extra_payload = extra()
                except Exception:
                    extra_payload = None
                if isinstance(extra_payload, dict):
                    payload.update(extra_payload)
            yield json.dumps(payload).encode("utf-8")
            return
        yield json.dumps(jsonable_encoder(result)).encode("utf-8")
    finally:
        if not task.done():
            task.cancel()
