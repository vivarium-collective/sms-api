from collections.abc import Mapping
from typing import Any, TypeVar, Optional, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..types import UNSET, Unset
from typing import cast
from typing import cast, Union
from typing import Union

if TYPE_CHECKING:
    from ..models.simulator_version import SimulatorVersion
    from ..models.ecoli_workflow_request_variant_config import EcoliWorkflowRequestVariantConfig
    from ..models.ecoli_workflow_request_config_overrides_type_0 import EcoliWorkflowRequestConfigOverridesType0


T = TypeVar("T", bound="EcoliWorkflowRequest")


@_attrs_define
class EcoliWorkflowRequest:
    """:param config_id: (str) filename (without '.json') of the given sim config
    :param config_overrides: (Optional[dict[str, Any]]) overrides any key within the file found at {config_id}.json

        Attributes:
            simulator (SimulatorVersion):
            parca_dataset_id (int):
            variant_config (Union[Unset, EcoliWorkflowRequestVariantConfig]):
            config_id (Union[None, Unset, str]):
            config_overrides (Union['EcoliWorkflowRequestConfigOverridesType0', None, Unset]):
    """

    simulator: "SimulatorVersion"
    parca_dataset_id: int
    variant_config: Union[Unset, "EcoliWorkflowRequestVariantConfig"] = UNSET
    config_id: Union[None, Unset, str] = UNSET
    config_overrides: Union["EcoliWorkflowRequestConfigOverridesType0", None, Unset] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.simulator_version import SimulatorVersion
        from ..models.ecoli_workflow_request_variant_config import EcoliWorkflowRequestVariantConfig
        from ..models.ecoli_workflow_request_config_overrides_type_0 import EcoliWorkflowRequestConfigOverridesType0

        simulator = self.simulator.to_dict()

        parca_dataset_id = self.parca_dataset_id

        variant_config: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.variant_config, Unset):
            variant_config = self.variant_config.to_dict()

        config_id: Union[None, Unset, str]
        if isinstance(self.config_id, Unset):
            config_id = UNSET
        else:
            config_id = self.config_id

        config_overrides: Union[None, Unset, dict[str, Any]]
        if isinstance(self.config_overrides, Unset):
            config_overrides = UNSET
        elif isinstance(self.config_overrides, EcoliWorkflowRequestConfigOverridesType0):
            config_overrides = self.config_overrides.to_dict()
        else:
            config_overrides = self.config_overrides

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "simulator": simulator,
            "parca_dataset_id": parca_dataset_id,
        })
        if variant_config is not UNSET:
            field_dict["variant_config"] = variant_config
        if config_id is not UNSET:
            field_dict["config_id"] = config_id
        if config_overrides is not UNSET:
            field_dict["config_overrides"] = config_overrides

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.simulator_version import SimulatorVersion
        from ..models.ecoli_workflow_request_variant_config import EcoliWorkflowRequestVariantConfig
        from ..models.ecoli_workflow_request_config_overrides_type_0 import EcoliWorkflowRequestConfigOverridesType0

        d = dict(src_dict)
        simulator = SimulatorVersion.from_dict(d.pop("simulator"))

        parca_dataset_id = d.pop("parca_dataset_id")

        _variant_config = d.pop("variant_config", UNSET)
        variant_config: Union[Unset, EcoliWorkflowRequestVariantConfig]
        if isinstance(_variant_config, Unset):
            variant_config = UNSET
        else:
            variant_config = EcoliWorkflowRequestVariantConfig.from_dict(_variant_config)

        def _parse_config_id(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        config_id = _parse_config_id(d.pop("config_id", UNSET))

        def _parse_config_overrides(data: object) -> Union["EcoliWorkflowRequestConfigOverridesType0", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                config_overrides_type_0 = EcoliWorkflowRequestConfigOverridesType0.from_dict(data)

                return config_overrides_type_0
            except:  # noqa: E722
                pass
            return cast(Union["EcoliWorkflowRequestConfigOverridesType0", None, Unset], data)

        config_overrides = _parse_config_overrides(d.pop("config_overrides", UNSET))

        ecoli_workflow_request = cls(
            simulator=simulator,
            parca_dataset_id=parca_dataset_id,
            variant_config=variant_config,
            config_id=config_id,
            config_overrides=config_overrides,
        )

        ecoli_workflow_request.additional_properties = d
        return ecoli_workflow_request

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
