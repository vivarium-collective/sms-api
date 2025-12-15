import logging
import shutil
import time
from pathlib import Path
import uuid
from typing import cast, Callable, Awaitable, Any

from fastapi import APIRouter, FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse, Response

from sms_api.config import get_settings, REPO_ROOT, Settings
from sms_api.dependencies import (
    get_user_sessions,
)


logger = logging.getLogger(__name__)


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


class SessionStartMiddleware(BaseHTTPMiddleware):
    env = get_settings()

    async def dispatch(self, request: Request, call_next: Callable[[Any], Any]) -> Response:
        sessions = get_user_sessions()
        session_id = request.cookies.get("session_id")
        new_session = False

        if session_id is None or session_id not in sessions:
            session_id = str(uuid.uuid4())
            new_session = True
            cache = create_user_cache_dir(self.env, session_id)
            logger.info(f'CREATED CACHE: {cache}')

            sessions[session_id] = {
                "last_seen": time.time()
            }

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

        return cast(Response, response)
