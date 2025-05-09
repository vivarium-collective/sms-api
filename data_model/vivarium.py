import dataclasses as dc
import datetime
from typing import Any, Dict

from vivarium.vivarium import Vivarium

from api.data_model.base import BaseClass


@dc.dataclass
class VivariumDocument(BaseClass):
    state: Dict[str, Any] = dc.field(default_factory=dict)
    composition: str = dc.field(default="")


# new vivarium confirmation
@dc.dataclass
class VivariumMetadata:
    vivarium_id: str
    location: str | None = None


@dc.dataclass
class VivariumApiError(Exception):
    reason: str

    @property
    def timestamp(self):
        return str(datetime.datetime.now())
    

@dc.dataclass
class DocumentLookupError(VivariumApiError):
    pass
