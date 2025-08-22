from collections.abc import Mapping
from typing import Any, TypeVar, Optional, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast
from typing import cast, Union

if TYPE_CHECKING:
    from ..models.biocyc_component_pgdb import BiocycComponentPgdb
    from ..models.biocyc_reaction import BiocycReaction
    from ..models.biocyc_compound import BiocycCompound


T = TypeVar("T", bound="BiocycComponent")


@_attrs_define
class BiocycComponent:
    """
    Attributes:
        id (str):
        pgdb (BiocycComponentPgdb):
        data (Union['BiocycCompound', 'BiocycReaction']):
    """

    id: str
    pgdb: "BiocycComponentPgdb"
    data: Union["BiocycCompound", "BiocycReaction"]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.biocyc_component_pgdb import BiocycComponentPgdb
        from ..models.biocyc_reaction import BiocycReaction
        from ..models.biocyc_compound import BiocycCompound

        id = self.id

        pgdb = self.pgdb.to_dict()

        data: dict[str, Any]
        if isinstance(self.data, BiocycCompound):
            data = self.data.to_dict()
        else:
            data = self.data.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "id": id,
            "pgdb": pgdb,
            "data": data,
        })

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.biocyc_component_pgdb import BiocycComponentPgdb
        from ..models.biocyc_reaction import BiocycReaction
        from ..models.biocyc_compound import BiocycCompound

        d = dict(src_dict)
        id = d.pop("id")

        pgdb = BiocycComponentPgdb.from_dict(d.pop("pgdb"))

        def _parse_data(data: object) -> Union["BiocycCompound", "BiocycReaction"]:
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                data_type_0 = BiocycCompound.from_dict(data)

                return data_type_0
            except:  # noqa: E722
                pass
            if not isinstance(data, dict):
                raise TypeError()
            data_type_1 = BiocycReaction.from_dict(data)

            return data_type_1

        data = _parse_data(d.pop("data"))

        biocyc_component = cls(
            id=id,
            pgdb=pgdb,
            data=data,
        )

        biocyc_component.additional_properties = d
        return biocyc_component

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
