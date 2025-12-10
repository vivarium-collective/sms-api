from enum import StrEnum
from typing import cast


class StrEnumBase(StrEnum):
    @classmethod
    def keys(cls) -> list[str]:
        return cast(list[str], vars(cls)["_member_names_"])

    @classmethod
    def member_keys(cls) -> list[str]:
        return cast(list[str], vars(cls)["_member_names_"])

    @classmethod
    def values(cls) -> list[str]:
        vals: list[str] = []
        for key in cls.member_keys():
            val = getattr(cls, key, None)
            if val is not None:
                vals.append(val)
        return vals

    @classmethod
    def to_dict(cls) -> dict[str, str]:
        return dict(zip(cls.keys(), cls.values()))

    @classmethod
    def to_list(cls) -> list[str]:
        return cls.values()
