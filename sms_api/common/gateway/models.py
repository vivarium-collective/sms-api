import dataclasses as dc
from enum import StrEnum
from pathlib import Path
from typing import Any

import dotenv
import fastapi
import httpx


@dc.dataclass
class RouterConfig:
    router: fastapi.APIRouter
    prefix: str
    dependencies: list[Any] | None = None

    @property
    def id(self) -> str | None:
        if len(self.prefix) > 1:
            return self.prefix.split("/")[-1]
        else:
            return None

    def include(self, app: fastapi.FastAPI) -> None:
        return app.include_router(self.router, prefix=self.prefix, dependencies=self.dependencies or [])


class ServiceType(StrEnum):
    SIMULATION = "simulation"
    MONGO = "mongo"
    POSTGRES = "postgres"
    AUTH = "auth"


class Namespace(StrEnum):
    DEVELOPMENT = "dev"
    PRODUCTION = "prod"
    TEST = "test"


class ServerMode(StrEnum):
    DEV = "http://localhost:8000"
    PROD = "https://sms.cam.uchc.edu"

    @classmethod
    def detect(cls, env_path: Path) -> str:
        return cls.DEV if dotenv.load_dotenv(env_path) else cls.PROD


class RouterType(StrEnum):
    CORE = "core"
    ANTIBIOTIC = "antibiotic"
    BIOMANUFACTURING = "biomanufacturing"


def get_url(
    path: str | None = None,
    parts: list[str] | None = None,
    router: RouterType | None = None,
    mode: ServerMode = ServerMode.DEV,
):
    url = httpx.URL(mode)
    if path:
        parts = path.split("/")
    path_parts = parts or []
    if router:
        path_parts.insert(0, router)
    if len(path_parts):
        suffix = "/".join(path_parts)
        return url.join(suffix)
    return url
