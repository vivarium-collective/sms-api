"""Tests for sms_api.common.streaming.stream_json_with_heartbeats and SSE primitives."""

import asyncio
import json

import pytest

from sms_api.common.streaming import SSE_RESPONSE_HEADERS, format_sse_event, stream_json_with_heartbeats


async def _collect(gen) -> bytes:  # type: ignore[no-untyped-def]
    return b"".join([chunk async for chunk in gen])


@pytest.mark.asyncio
async def test_fast_work_returns_immediate_json_array() -> None:
    async def fast() -> list[dict[str, str]]:
        return [{"filename": "a.tsv", "content": "x"}]

    out = await _collect(stream_json_with_heartbeats(fast(), heartbeat_interval=0.5))
    payload = json.loads(out)
    assert payload == [{"filename": "a.tsv", "content": "x"}]


@pytest.mark.asyncio
async def test_slow_work_emits_heartbeats_then_result() -> None:
    async def slow() -> dict[str, bool]:
        await asyncio.sleep(0.3)
        return {"ok": True}

    out = await _collect(stream_json_with_heartbeats(slow(), heartbeat_interval=0.05))
    # leading whitespace = heartbeats; trailing JSON object = result
    assert out.startswith(b" \n")
    assert b" \n" in out[: out.index(b"{")]
    assert json.loads(out) == {"ok": True}


@pytest.mark.asyncio
async def test_failure_body_is_json_object_not_array() -> None:
    async def boom() -> None:
        raise ValueError("kaboom")

    out = await _collect(stream_json_with_heartbeats(boom(), heartbeat_interval=0.05))
    payload = json.loads(out)
    assert payload["error"] == "ValueError"
    assert payload["message"] == "kaboom"


@pytest.mark.asyncio
async def test_failure_with_to_dict_merges_payload() -> None:
    class StructuredError(Exception):
        def to_dict(self) -> dict[str, object]:
            return {"job_id": 1234, "status": "FAILED"}

    async def boom() -> None:
        raise StructuredError("structured")

    out = await _collect(stream_json_with_heartbeats(boom(), heartbeat_interval=0.05))
    payload = json.loads(out)
    assert payload["error"] == "StructuredError"
    assert payload["job_id"] == 1234
    assert payload["status"] == "FAILED"


# ---- SSE primitives ---------------------------------------------------


def test_format_sse_event_basic_shape() -> None:
    out = format_sse_event("status", {"phase": "running", "n": 3})
    assert out.endswith(b"\n\n"), "SSE message must end in a blank line"
    text = out.decode("utf-8")
    lines = text.rstrip("\n").split("\n")
    assert lines[0] == "event: status"
    assert lines[1].startswith("data: ")
    assert json.loads(lines[1][len("data: ") :]) == {"phase": "running", "n": 3}


def test_format_sse_event_jsonable_encodes_pydantic_models() -> None:
    from pydantic import BaseModel

    class Item(BaseModel):
        filename: str
        n: int

    out = format_sse_event("result", [Item(filename="a", n=1)])
    data = json.loads(out.decode("utf-8").split("data: ", 1)[1])
    assert data == [{"filename": "a", "n": 1}]


def test_sse_response_headers_disable_buffering() -> None:
    assert SSE_RESPONSE_HEADERS["Cache-Control"] == "no-cache"
    assert SSE_RESPONSE_HEADERS["X-Accel-Buffering"] == "no"


# ---- pydantic result encoding (legacy) --------------------------------


@pytest.mark.asyncio
async def test_pydantic_result_is_jsonable_encoded() -> None:
    from pydantic import BaseModel

    class Item(BaseModel):
        filename: str
        n: int

    async def work() -> list[Item]:
        return [Item(filename="a", n=1), Item(filename="b", n=2)]

    out = await _collect(stream_json_with_heartbeats(work(), heartbeat_interval=0.5))
    payload = json.loads(out)
    assert payload == [{"filename": "a", "n": 1}, {"filename": "b", "n": 2}]
