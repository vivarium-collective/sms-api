import datetime
import secrets
import typing
import uuid
from typing import Literal

import numpy as np

from sms_api.common.models import DataId

DEFAULT_DATA_ID_PREFIX = "sms"


class DataString(str):
    def __init__(self, content: str):
        super().__init__()
        self.content = content

    @property
    def timestamp(self) -> str:
        return self.content.split("_")[-1]

    @property
    def identifier(self) -> str:
        return self.content.split("-")[0]


def get_uuid(scope: str | None = None, data_id: str | None = None, n_sections: int = 1) -> str:
    if not scope:
        scope = "smsapi"
    if not data_id:
        data_id = "-".join(list(map(lambda _: get_salt(scope), list(range(n_sections)))))
    else:
        data_id += f"-{get_salt(scope)}"

    item_id = DataId(scope=scope, label=data_id, timestamp=timestamp())
    return item_id.str()


def i_random(start: int = 0, stop: int = 100_000) -> int:
    return np.random.randint(start, stop)


def hashed(data: typing.Any, salt: str | None = None) -> int:
    if salt is None:
        salt = str(uuid.uuid4())
    return int(str(hash(salt + str(data)) & 0xFFFF)[:2])


def get_data_id(
    exp_id: str | None = None, scope: Literal["experiment", "analysis"] | None = None, prefix: str | None = None
) -> str:
    # return f"{prefix or DEFAULT_DATA_ID_PREFIX}_{scope}-{exp_id}-{new_token(exp_id)}"
    return get_uuid(scope=scope)


def get_salt(scope: str) -> str:
    def salt(scope: str) -> str:
        hextag = str(secrets.token_hex(8))[:2]
        return f"{hextag}{hashed(scope, hextag)}"

    return f"{str(secrets.token_hex(8))[:2]}{salt(scope)[:2]}"


def unique_id(data_id: str | None = None, scope: str | None = None) -> str:
    hextag = str(secrets.token_hex(8))[:2]
    item_id = f"{data_id or scope or 'smsapi'}_"
    tag = f"{hextag}{hashed(item_id, hextag)}"
    unique = f"{data_id}_" if data_id is not None else f"{scope or 'smsapi'}_"
    unique += f"{tag}_{timestamp()}"
    return unique


def timestamp() -> str:
    return datetime.datetime.now().strftime("%Y%m%d")
