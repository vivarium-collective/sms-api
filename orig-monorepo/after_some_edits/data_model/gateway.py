import dataclasses as dc
from typing import Any, Callable

import fastapi

from sms_api.data_model.base import BaseClass


@dc.dataclass
class RouterConfig(BaseClass):
    router: fastapi.APIRouter
    prefix: str
    dependencies: list[Callable[[str], Any]] | None = None

    @property
    def id(self):
        if len(self.prefix) > 1:
            return self.prefix.split("/")[-1]

    def include(self, app: fastapi.FastAPI) -> None:
        return app.include_router(
            self.router,
            prefix=self.prefix,
            dependencies=self.dependencies,  # type: ignore
        )
