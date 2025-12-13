import datetime
import secrets
import string
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


def get_uuid(
    scope: str | None = None, data_id: str | None = None, n_sections: int = 1, return_string: bool = True
) -> str | DataId:
    if not scope:
        scope = "smsapi"
    if not data_id:
        data_id = "-".join(list(map(lambda _: get_salt(scope), list(range(n_sections)))))
    else:
        data_id += f"-{get_salt(scope)}"

    data_id = DataId(scope=scope, label=data_id, timestamp=timestamp())
    return data_id.str() if return_string else data_id


def i_random(start: int = 0, stop: int = 100_000) -> int:
    return np.random.randint(start, stop)


def hashed(data: typing.Any, salt: str | None = None) -> int:
    if salt is None:
        salt = str(uuid.uuid4())
    return int(str(hash(salt + str(data)) & 0xFFFF)[:2])


def unique_token(i: int, salt: str, bank_size: int = 150_000) -> str:
    english_bank = safe_word_list(bank_size)
    return f"{english_bank[i].replace("'", '')}_{hash(salt + str(i)) & 0xFFFF}"


def new_token(experiment_id: str) -> str:
    i = i_random()
    return unique_token(i=i, salt=experiment_id)


class EnglishAlphabet:
    @property
    def lowercase(self):
        return string.ascii_lowercase

    @property
    def uppercase(self):
        return string.ascii_uppercase


def safe_word_list(bank_size: int = 150_000) -> list[str]:
    words = []
    alphabet = EnglishAlphabet().lowercase
    prefixes = [f"{hashed(bank_size)}" for _ in range(50_000)]
    for idx, prefix in enumerate(prefixes):
        i = int(prefix[:1])
        j = int(prefix[1:])
        word = f"{alphabet[i]}{alphabet[j]}"
        words.append(word)
    return words


def get_data_id(exp_id: str, scope: Literal["experiment", "analysis"], prefix: str | None = None) -> str:
    return f"{prefix or DEFAULT_DATA_ID_PREFIX}_{scope}-{exp_id}-{new_token(exp_id)}"


def get_salt(scope: str):
    def salt(scope: str):
        hextag = str(secrets.token_hex(8))[:2]
        return f"{hextag}{hashed(scope, hextag)}"

    return f"{str(secrets.token_hex(8))[:2]}{salt(scope)[:2]}"


def test_get_uuid():
    scope = "analysis"
    data_id = "myexperiment_id"
    uid = get_uuid(scope)
    print()

    uid2 = get_uuid(scope, data_id)
    print()


def unique_id(data_id: str | None = None, scope: str | None = None) -> str:
    hextag = str(secrets.token_hex(8))[:2]
    item_id = f"{data_id or scope or 'smsapi'}_"
    tag = f"{hextag}{hashed(item_id, hextag)}"
    unique = f"{data_id}_" if data_id is not None else f"{scope or 'smsapi'}_"
    unique += f"{tag}_{timestamp()}"
    return unique


def timestamp() -> str:
    return datetime.datetime.now().strftime("%Y%m%d")


def test_unique_id():
    dataid = "test"
    unique = unique_id(dataid)
    assert len(unique.replace(f"{dataid}_", "")) == (4 + 1 + 8)  # (tag + sep + date)
    print(unique)
