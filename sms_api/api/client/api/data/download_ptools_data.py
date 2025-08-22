from http import HTTPStatus
from typing import Any, Optional, Union, cast

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.biocyc_data_dto import BiocycDataDTO
from ...models.http_validation_error import HTTPValidationError
from ...types import UNSET, Unset
from typing import cast
from typing import Union


def _get_kwargs(
    *,
    object_id: str,
    organism_id: Union[Unset, str] = "ECOLI",
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["object_id"] = object_id

    params["organism_id"] = organism_id

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/core/download/ptools",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[BiocycDataDTO, HTTPValidationError]]:
    if response.status_code == 200:
        response_200 = BiocycDataDTO.from_dict(response.json())

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
) -> Response[Union[BiocycDataDTO, HTTPValidationError]]:
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
) -> Response[Union[BiocycDataDTO, HTTPValidationError]]:
    """Download data for a given component from the Pathway Tools REST API

    Args:
        object_id (str): Object ID of the component you wish to fetch
        organism_id (Union[Unset, str]):  Default: 'ECOLI'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[BiocycDataDTO, HTTPValidationError]]
    """

    kwargs = _get_kwargs(
        object_id=object_id,
        organism_id=organism_id,
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
) -> Optional[Union[BiocycDataDTO, HTTPValidationError]]:
    """Download data for a given component from the Pathway Tools REST API

    Args:
        object_id (str): Object ID of the component you wish to fetch
        organism_id (Union[Unset, str]):  Default: 'ECOLI'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[BiocycDataDTO, HTTPValidationError]
    """

    return sync_detailed(
        client=client,
        object_id=object_id,
        organism_id=organism_id,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    object_id: str,
    organism_id: Union[Unset, str] = "ECOLI",
) -> Response[Union[BiocycDataDTO, HTTPValidationError]]:
    """Download data for a given component from the Pathway Tools REST API

    Args:
        object_id (str): Object ID of the component you wish to fetch
        organism_id (Union[Unset, str]):  Default: 'ECOLI'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[BiocycDataDTO, HTTPValidationError]]
    """

    kwargs = _get_kwargs(
        object_id=object_id,
        organism_id=organism_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    object_id: str,
    organism_id: Union[Unset, str] = "ECOLI",
) -> Optional[Union[BiocycDataDTO, HTTPValidationError]]:
    """Download data for a given component from the Pathway Tools REST API

    Args:
        object_id (str): Object ID of the component you wish to fetch
        organism_id (Union[Unset, str]):  Default: 'ECOLI'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[BiocycDataDTO, HTTPValidationError]
    """

    return (
        await asyncio_detailed(
            client=client,
            object_id=object_id,
            organism_id=organism_id,
        )
    ).parsed
