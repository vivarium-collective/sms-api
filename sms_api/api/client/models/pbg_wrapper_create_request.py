from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.pbg_config_param import PbgConfigParam
    from ..models.pbg_port_schema import PbgPortSchema


T = TypeVar("T", bound="PbgWrapperCreateRequest")


@_attrs_define
class PbgWrapperCreateRequest:
    """
    Attributes:
        source_repo_url (str): GitHub URL of the simulator to wrap, e.g. https://github.com/vivarium-collective/mem3dg
        source_ref (Union[Unset, str]): Git branch/tag/commit to target Default: 'main'.
        tool_name (Union[None, Unset, str]): Override the derived tool name (default: inferred from repo name)
        extra_instructions (Union[None, Unset, str]): Optional extra context for the wrapper agent
        process_type (Union[Unset, str]): 'Process' (time-stepped) or 'Step' (event-driven/stateless) Default:
            'Process'.
        input_ports (Union[Unset, list['PbgPortSchema']]): Input port definitions for the scaffold path (unused when
            use_agent=True)
        output_ports (Union[Unset, list['PbgPortSchema']]): Output port definitions for the scaffold path (unused when
            use_agent=True)
        config_params (Union[Unset, list['PbgConfigParam']]): Config parameter definitions for the scaffold path (unused
            when use_agent=True)
        use_agent (Union[Unset, bool]): When True (default), invoke the Claude API pbg-expert agent to generate the
            wrapper. When False (or when COMPOSE_PBG_ANTHROPIC_API_KEY is not configured), fall back to deterministic
            template-based scaffolding using the port/config definitions above. Default: True.
    """

    source_repo_url: str
    source_ref: Union[Unset, str] = "main"
    tool_name: Union[None, Unset, str] = UNSET
    extra_instructions: Union[None, Unset, str] = UNSET
    process_type: Union[Unset, str] = "Process"
    input_ports: Union[Unset, list["PbgPortSchema"]] = UNSET
    output_ports: Union[Unset, list["PbgPortSchema"]] = UNSET
    config_params: Union[Unset, list["PbgConfigParam"]] = UNSET
    use_agent: Union[Unset, bool] = True
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        source_repo_url = self.source_repo_url

        source_ref = self.source_ref

        tool_name: Union[None, Unset, str]
        if isinstance(self.tool_name, Unset):
            tool_name = UNSET
        else:
            tool_name = self.tool_name

        extra_instructions: Union[None, Unset, str]
        if isinstance(self.extra_instructions, Unset):
            extra_instructions = UNSET
        else:
            extra_instructions = self.extra_instructions

        process_type = self.process_type

        input_ports: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.input_ports, Unset):
            input_ports = []
            for input_ports_item_data in self.input_ports:
                input_ports_item = input_ports_item_data.to_dict()
                input_ports.append(input_ports_item)

        output_ports: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.output_ports, Unset):
            output_ports = []
            for output_ports_item_data in self.output_ports:
                output_ports_item = output_ports_item_data.to_dict()
                output_ports.append(output_ports_item)

        config_params: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.config_params, Unset):
            config_params = []
            for config_params_item_data in self.config_params:
                config_params_item = config_params_item_data.to_dict()
                config_params.append(config_params_item)

        use_agent = self.use_agent

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "source_repo_url": source_repo_url,
            }
        )
        if source_ref is not UNSET:
            field_dict["source_ref"] = source_ref
        if tool_name is not UNSET:
            field_dict["tool_name"] = tool_name
        if extra_instructions is not UNSET:
            field_dict["extra_instructions"] = extra_instructions
        if process_type is not UNSET:
            field_dict["process_type"] = process_type
        if input_ports is not UNSET:
            field_dict["input_ports"] = input_ports
        if output_ports is not UNSET:
            field_dict["output_ports"] = output_ports
        if config_params is not UNSET:
            field_dict["config_params"] = config_params
        if use_agent is not UNSET:
            field_dict["use_agent"] = use_agent

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.pbg_config_param import PbgConfigParam
        from ..models.pbg_port_schema import PbgPortSchema

        d = dict(src_dict)
        source_repo_url = d.pop("source_repo_url")

        source_ref = d.pop("source_ref", UNSET)

        def _parse_tool_name(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        tool_name = _parse_tool_name(d.pop("tool_name", UNSET))

        def _parse_extra_instructions(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        extra_instructions = _parse_extra_instructions(d.pop("extra_instructions", UNSET))

        process_type = d.pop("process_type", UNSET)

        input_ports = []
        _input_ports = d.pop("input_ports", UNSET)
        for input_ports_item_data in _input_ports or []:
            input_ports_item = PbgPortSchema.from_dict(input_ports_item_data)

            input_ports.append(input_ports_item)

        output_ports = []
        _output_ports = d.pop("output_ports", UNSET)
        for output_ports_item_data in _output_ports or []:
            output_ports_item = PbgPortSchema.from_dict(output_ports_item_data)

            output_ports.append(output_ports_item)

        config_params = []
        _config_params = d.pop("config_params", UNSET)
        for config_params_item_data in _config_params or []:
            config_params_item = PbgConfigParam.from_dict(config_params_item_data)

            config_params.append(config_params_item)

        use_agent = d.pop("use_agent", UNSET)

        pbg_wrapper_create_request = cls(
            source_repo_url=source_repo_url,
            source_ref=source_ref,
            tool_name=tool_name,
            extra_instructions=extra_instructions,
            process_type=process_type,
            input_ports=input_ports,
            output_ports=output_ports,
            config_params=config_params,
            use_agent=use_agent,
        )

        pbg_wrapper_create_request.additional_properties = d
        return pbg_wrapper_create_request

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
