from http import HTTPStatus
from typing import Any, Optional, Union, cast

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.biocyc_component import BiocycComponent
from ...models.biocyc_data import BiocycData
from ...models.http_validation_error import HTTPValidationError
from ...types import UNSET, Unset
from typing import cast
from typing import cast, Union
from typing import Union


def _get_kwargs(
    *,
    object_id: str,
    organism_id: Union[Unset, str] = "ECOLI",
    raw: Union[Unset, bool] = False,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["object_id"] = object_id

    params["organism_id"] = organism_id

    params["raw"] = raw

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/ptools/component",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[HTTPValidationError, Union["BiocycComponent", "BiocycData"]]]:
    if response.status_code == 200:

        def _parse_response_200(data: object) -> Union["BiocycComponent", "BiocycData"]:
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                response_200_type_0 = BiocycData.from_dict(data)

                return response_200_type_0
            except:  # noqa: E722
                pass
            if not isinstance(data, dict):
                raise TypeError()
            response_200_type_1 = BiocycComponent.from_dict(data)

            return response_200_type_1

        response_200 = _parse_response_200(response.json())

        return response_200
    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[Union[HTTPValidationError, Union["BiocycComponent", "BiocycData"]]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    object_id: str,
    organism_id: Union[Unset, str] = "ECOLI",
    raw: Union[Unset, bool] = False,
) -> Response[Union[HTTPValidationError, Union["BiocycComponent", "BiocycData"]]]:
    """Download data for a given component from the Pathway Tools REST API

    Args:
        object_id (str): Object ID of the component you wish to fetch
        organism_id (Union[Unset, str]):  Default: 'ECOLI'.
        raw (Union[Unset, bool]): If True, return an object containing both the BioCyc component
            and the request params/data Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, Union['BiocycComponent', 'BiocycData']]]
    """

    kwargs = _get_kwargs(
        object_id=object_id,
        organism_id=organism_id,
        raw=raw,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: Union[AuthenticatedClient, Client],
    object_id: str,
    organism_id: Union[Unset, str] = "ECOLI",
    raw: Union[Unset, bool] = False,
) -> Optional[Union[HTTPValidationError, Union["BiocycComponent", "BiocycData"]]]:
    """Download data for a given component from the Pathway Tools REST API

    Args:
        object_id (str): Object ID of the component you wish to fetch
        organism_id (Union[Unset, str]):  Default: 'ECOLI'.
        raw (Union[Unset, bool]): If True, return an object containing both the BioCyc component
            and the request params/data Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, Union['BiocycComponent', 'BiocycData']]
    """

    return sync_detailed(
        client=client,
        object_id=object_id,
        organism_id=organism_id,
        raw=raw,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    object_id: str,
    organism_id: Union[Unset, str] = "ECOLI",
    raw: Union[Unset, bool] = False,
) -> Response[Union[HTTPValidationError, Union["BiocycComponent", "BiocycData"]]]:
    """Download data for a given component from the Pathway Tools REST API

    Args:
        object_id (str): Object ID of the component you wish to fetch
        organism_id (Union[Unset, str]):  Default: 'ECOLI'.
        raw (Union[Unset, bool]): If True, return an object containing both the BioCyc component
            and the request params/data Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, Union['BiocycComponent', 'BiocycData']]]
    """

    kwargs = _get_kwargs(
        object_id=object_id,
        organism_id=organism_id,
        raw=raw,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    object_id: str,
    organism_id: Union[Unset, str] = "ECOLI",
    raw: Union[Unset, bool] = False,
) -> Optional[Union[HTTPValidationError, Union["BiocycComponent", "BiocycData"]]]:
    """Download data for a given component from the Pathway Tools REST API

    Args:
        object_id (str): Object ID of the component you wish to fetch
        organism_id (Union[Unset, str]):  Default: 'ECOLI'.
        raw (Union[Unset, bool]): If True, return an object containing both the BioCyc component
            and the request params/data Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, Union['BiocycComponent', 'BiocycData']]
    """

    return (
        await asyncio_detailed(
            client=client,
            object_id=object_id,
            organism_id=organism_id,
            raw=raw,
        )
    ).parsed
