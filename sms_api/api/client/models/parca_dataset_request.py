from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.parca_dataset_request_parca_config_type_0 import ParcaDatasetRequestParcaConfigType0
    from ..models.parca_options import ParcaOptions
    from ..models.simulator_version import SimulatorVersion


T = TypeVar("T", bound="ParcaDatasetRequest")


@_attrs_define
class ParcaDatasetRequest:
    """
    Attributes:
        simulator_version (SimulatorVersion):
        parca_config (Union['ParcaDatasetRequestParcaConfigType0', 'ParcaOptions', Unset]):
    """

    simulator_version: "SimulatorVersion"
    parca_config: Union["ParcaDatasetRequestParcaConfigType0", "ParcaOptions", Unset] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.parca_dataset_request_parca_config_type_0 import ParcaDatasetRequestParcaConfigType0

        simulator_version = self.simulator_version.to_dict()

        parca_config: Union[Unset, dict[str, Any]]
        if isinstance(self.parca_config, Unset):
            parca_config = UNSET
        elif isinstance(self.parca_config, ParcaDatasetRequestParcaConfigType0):
            parca_config = self.parca_config.to_dict()
        else:
            parca_config = self.parca_config.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "simulator_version": simulator_version,
            }
        )
        if parca_config is not UNSET:
            field_dict["parca_config"] = parca_config

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.parca_dataset_request_parca_config_type_0 import ParcaDatasetRequestParcaConfigType0
        from ..models.parca_options import ParcaOptions
        from ..models.simulator_version import SimulatorVersion

        d = dict(src_dict)
        simulator_version = SimulatorVersion.from_dict(d.pop("simulator_version"))

        def _parse_parca_config(data: object) -> Union["ParcaDatasetRequestParcaConfigType0", "ParcaOptions", Unset]:
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                parca_config_type_0 = ParcaDatasetRequestParcaConfigType0.from_dict(data)

                return parca_config_type_0
            except:  # noqa: E722
                pass
            if not isinstance(data, dict):
                raise TypeError()
            parca_config_type_1 = ParcaOptions.from_dict(data)

            return parca_config_type_1

        parca_config = _parse_parca_config(d.pop("parca_config", UNSET))

        parca_dataset_request = cls(
            simulator_version=simulator_version,
            parca_config=parca_config,
        )

        parca_dataset_request.additional_properties = d
        return parca_dataset_request

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
