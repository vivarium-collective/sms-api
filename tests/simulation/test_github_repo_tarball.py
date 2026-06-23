"""Tests for the simulator workspace export (repo@commit tarball) helpers."""

from collections.abc import AsyncIterator

import httpx
import pytest

from sms_api.simulation.github_repo import repo_tarball_url, stream_repo_tarball
from sms_api.simulation.models import SimulatorVersion


def _sim() -> SimulatorVersion:
    return SimulatorVersion(
        git_commit_hash="abc1234",
        git_repo_url="https://github.com/org/repo",
        git_branch="main",
        database_id=5,
    )


def test_repo_tarball_url_builds_github_tarball_endpoint() -> None:
    assert repo_tarball_url(_sim()) == "https://api.github.com/repos/org/repo/tarball/abc1234"


def test_repo_tarball_url_strips_dot_git_suffix() -> None:
    sv = SimulatorVersion(
        git_commit_hash="def5678",
        git_repo_url="https://github.com/org/repo.git",
        git_branch="main",
        database_id=6,
    )
    assert repo_tarball_url(sv) == "https://api.github.com/repos/org/repo/tarball/def5678"


class _FakeStream:
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = chunks

    async def __aenter__(self) -> "_FakeStream":
        return self

    async def __aexit__(self, *exc: object) -> bool:
        return False

    def raise_for_status(self) -> None:
        pass

    async def aiter_bytes(self) -> AsyncIterator[bytes]:
        for c in self._chunks:
            yield c


class _FakeClient:
    captured: dict[str, object] = {}

    def __init__(self, *args: object, **kwargs: object) -> None:
        _FakeClient.captured["follow_redirects"] = kwargs.get("follow_redirects")

    async def __aenter__(self) -> "_FakeClient":
        return self

    async def __aexit__(self, *exc: object) -> bool:
        return False

    def stream(self, method: str, url: str, headers: dict[str, str] | None = None) -> _FakeStream:
        _FakeClient.captured.update(method=method, url=url, headers=headers)
        return _FakeStream([b"tar", b"ball"])


@pytest.mark.asyncio
async def test_stream_repo_tarball_streams_github_tarball(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(httpx, "AsyncClient", _FakeClient)

    chunks = [c async for c in stream_repo_tarball(_sim(), token="tok")]  # noqa: S106

    assert b"".join(chunks) == b"tarball"
    # Followed GitHub's tarball redirect, with the auth header, GET to the tarball URL.
    assert _FakeClient.captured["follow_redirects"] is True
    assert _FakeClient.captured["method"] == "GET"
    assert _FakeClient.captured["url"] == "https://api.github.com/repos/org/repo/tarball/abc1234"
    headers = _FakeClient.captured["headers"]
    assert isinstance(headers, dict)
    assert headers["Authorization"] == "token tok"
