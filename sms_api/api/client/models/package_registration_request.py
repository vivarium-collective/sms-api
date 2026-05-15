from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.package_outline import PackageOutline


T = TypeVar("T", bound="PackageRegistrationRequest")


@_attrs_define
class PackageRegistrationRequest:
    """
    Attributes:
        kind (str): 'repo_url', 'local_path', or 'outline'
        url (Union[None, Unset, str]): Git repo URL (required when kind='repo_url')
        ref (Union[None, Unset, str]): Git branch/tag/commit (optional)
        path (Union[None, Unset, str]): Local path (required when kind='local_path')
        outline (Union['PackageOutline', None, Unset]): Inline outline (required when kind='outline')
    """

    kind: str
    url: Union[None, Unset, str] = UNSET
    ref: Union[None, Unset, str] = UNSET
    path: Union[None, Unset, str] = UNSET
    outline: Union["PackageOutline", None, Unset] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.package_outline import PackageOutline

        kind = self.kind

        url: Union[None, Unset, str]
        if isinstance(self.url, Unset):
            url = UNSET
        else:
            url = self.url

        ref: Union[None, Unset, str]
        if isinstance(self.ref, Unset):
            ref = UNSET
        else:
            ref = self.ref

        path: Union[None, Unset, str]
        if isinstance(self.path, Unset):
            path = UNSET
        else:
            path = self.path

        outline: Union[None, Unset, dict[str, Any]]
        if isinstance(self.outline, Unset):
            outline = UNSET
        elif isinstance(self.outline, PackageOutline):
            outline = self.outline.to_dict()
        else:
            outline = self.outline

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "kind": kind,
            }
        )
        if url is not UNSET:
            field_dict["url"] = url
        if ref is not UNSET:
            field_dict["ref"] = ref
        if path is not UNSET:
            field_dict["path"] = path
        if outline is not UNSET:
            field_dict["outline"] = outline

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.package_outline import PackageOutline

        d = dict(src_dict)
        kind = d.pop("kind")

        def _parse_url(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        url = _parse_url(d.pop("url", UNSET))

        def _parse_ref(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        ref = _parse_ref(d.pop("ref", UNSET))

        def _parse_path(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        path = _parse_path(d.pop("path", UNSET))

        def _parse_outline(data: object) -> Union["PackageOutline", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                outline_type_0 = PackageOutline.from_dict(data)

                return outline_type_0
            except:  # noqa: E722
                pass
            return cast(Union["PackageOutline", None, Unset], data)

        outline = _parse_outline(d.pop("outline", UNSET))

        package_registration_request = cls(
            kind=kind,
            url=url,
            ref=ref,
            path=path,
            outline=outline,
        )

        package_registration_request.additional_properties = d
        return package_registration_request

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
