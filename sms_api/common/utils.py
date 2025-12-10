import datetime
import re
import secrets
import time
from typing import Literal

import numpy as np
from wordfilter import Wordfilter  # type: ignore[import-untyped]
from wordfreq import top_n_list

DEFAULT_DATA_ID_PREFIX = "sms"


class DataId(str):
    def __init__(self, content: str):
        super().__init__()
        self.content = content

    @property
    def timestamp(self) -> str:
        return self.content.split("_")[-1]

    @property
    def identifier(self) -> str:
        return self.content.split("-")[0]


def i_random(start: int = 0, stop: int = 100_000) -> int:
    return np.random.randint(start, stop)


def unique_token(i: int, salt: str, bank_size: int = 150_000) -> str:
    english_bank = safe_word_list(bank_size)
    return f"{english_bank[i].replace("'", '')}_{hash(salt + str(i)) & 0xFFFF}"


def new_token(experiment_id: str) -> str:
    i = i_random()
    return unique_token(i=i, salt=experiment_id)


def safe_word_list(bank_size: int = 150_000) -> list[str]:
    ALPHA = re.compile(r"^[a-zA-Z]+$")
    wf = Wordfilter()
    words = top_n_list("en", n=bank_size)
    return [w for w in [w for w in words if not wf.blacklisted(w)] if ALPHA.match(w)]


def get_data_id(exp_id: str, scope: Literal["experiment", "analysis"], prefix: str | None = None) -> str:
    return f"{prefix or DEFAULT_DATA_ID_PREFIX}_{scope}-{exp_id}-{new_token(exp_id)}"


def unique_id(data_id: str | None = None, scope: str | None = None) -> str:
    timestamp = int(time.time() * 1000)
    tag = secrets.token_hex(8)[:4]
    unique = f"{data_id}-" if data_id is not None else f"{scope or 'smsapi'}-"
    unique += f"{tag}_{timestamp}"
    return unique


def timestamp() -> str:
    return str(datetime.datetime.now())
