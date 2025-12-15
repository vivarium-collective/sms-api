import abc
import logging
import shutil
import time
import uuid
from collections.abc import Awaitable
from pathlib import Path
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from sms_api.config import Settings, get_settings
from sms_api.dependencies import (
    get_user_sessions,
)

__all__ = [
    "SMSMiddleware",
    "SMSMiddlewareApiRouterRedirect",
    "SMSMiddlewareInitSession",
    "clear_user_cache",
    "create_user_cache_dir",
    "get_user_cache_dirpath",
    "remove_user_cache_dir",
]

logger = logging.getLogger(__name__)


ResponseCallback = Callable[[Request], Awaitable[Response]]


class SMSMiddleware(abc.ABC, BaseHTTPMiddleware):
    env = get_settings()

    @abc.abstractmethod
    async def dispatch(self, request: Request, call_next: ResponseCallback) -> Response:
        pass


class SMSMiddlewareInitSession(SMSMiddleware):
    async def dispatch(self, request: Request, call_next: ResponseCallback) -> Response:
        sessions = get_user_sessions()
        session_id = request.cookies.get("session_id")
        new_session = False

        if session_id is None or session_id not in sessions:
            session_id = str(uuid.uuid4())
            new_session = True
            cache = create_user_cache_dir(self.env, session_id)
            logger.info(f"CREATED CACHE: {cache}")

            sessions[session_id] = {"last_seen": time.time()}

        # touch session
        sessions[session_id]["last_seen"] = time.time()
        # attach to request state
        request.state.session_id = session_id
        response = await call_next(request)

        if new_session:
            response.set_cookie(
                "session_id",
                session_id,
                httponly=True,
                samesite="lax",
            )

        return response


class SMSMiddlewareApiRouterRedirect(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: ResponseCallback) -> Response:
        if request.url.path.startswith("/v1/ecoli/"):
            rest_of_path = request.url.path[len("/v1/ecoli") :]
            request.scope["path"] = "/api/v1" + rest_of_path
        return await call_next(request)


def get_user_cache_dirpath(env: Settings, session_id: str) -> Path:
    return Path(env.cache_dir) / session_id


def create_user_cache_dir(env: Settings, session_id: str) -> Path:
    cache_dir = get_user_cache_dirpath(env, session_id)
    if not cache_dir.exists():
        cache_dir.mkdir()
    return cache_dir


def remove_user_cache_dir(env: Settings, session_id: str) -> None:
    cache_dir = get_user_cache_dirpath(env, session_id)
    if cache_dir.exists():
        cache_dir.rmdir()


def clear_user_cache(env: Settings) -> None:
    # 1️⃣ Explicit logout (唯一 true event)
    cache_root = Path(env.cache_dir)
    for path in [fp for fp in cache_root.iterdir() if fp.is_dir()]:
        shutil.rmtree(path)
