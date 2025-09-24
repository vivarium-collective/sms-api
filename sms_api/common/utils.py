import secrets
import time


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


def unique_id(data_id: str | None = None, scope: str | None = None) -> str:
    timestamp = int(time.time() * 1000)
    tag = secrets.token_hex(8)
    unique = f"{data_id}-" if data_id is not None else f"{scope or 'smsapi'}-"
    unique += f"{tag}_{timestamp}"
    return unique
