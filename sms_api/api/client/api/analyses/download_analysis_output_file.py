from http import HTTPStatus
from typing import Any, Optional, Union, cast

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...types import UNSET, Unset
from typing import cast
from typing import Union


def _get_kwargs(
    id: str,
    *,
    variant_id: Union[Unset, int] = 0,
    lineage_seed_id: Union[Unset, int] = 0,
    generation_id: Union[Unset, int] = 1,
    agent_id: Union[Unset, int] = 0,
    filename: str,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["variant_id"] = variant_id

    params["lineage_seed_id"] = lineage_seed_id

    params["generation_id"] = generation_id

    params["agent_id"] = agent_id

    params["filename"] = filename

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v1/ecoli/analyses/{id}/download".format(
            id=id,
        ),
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[Any, HTTPValidationError]]:
    if response.status_code == 200:
        response_200 = response.json()
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
) -> Response[Union[Any, HTTPValidationError]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    id: str,
    *,
    client: Union[AuthenticatedClient, Client],
    variant_id: Union[Unset, int] = 0,
    lineage_seed_id: Union[Unset, int] = 0,
    generation_id: Union[Unset, int] = 1,
    agent_id: Union[Unset, int] = 0,
    filename: str,
) -> Response[Union[Any, HTTPValidationError]]:
    """Download a single file that was generated from a simulation analysis module

    Args:
        id (str):
        variant_id (Union[Unset, int]):  Default: 0.
        lineage_seed_id (Union[Unset, int]):  Default: 0.
        generation_id (Union[Unset, int]):  Default: 1.
        agent_id (Union[Unset, int]):  Default: 0.
        filename (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, HTTPValidationError]]
    """

    kwargs = _get_kwargs(
        id=id,
        variant_id=variant_id,
        lineage_seed_id=lineage_seed_id,
        generation_id=generation_id,
        agent_id=agent_id,
        filename=filename,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    id: str,
    *,
    client: Union[AuthenticatedClient, Client],
    variant_id: Union[Unset, int] = 0,
    lineage_seed_id: Union[Unset, int] = 0,
    generation_id: Union[Unset, int] = 1,
    agent_id: Union[Unset, int] = 0,
    filename: str,
) -> Optional[Union[Any, HTTPValidationError]]:
    """Download a single file that was generated from a simulation analysis module

    Args:
        id (str):
        variant_id (Union[Unset, int]):  Default: 0.
        lineage_seed_id (Union[Unset, int]):  Default: 0.
        generation_id (Union[Unset, int]):  Default: 1.
        agent_id (Union[Unset, int]):  Default: 0.
        filename (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, HTTPValidationError]
    """

    return sync_detailed(
        id=id,
        client=client,
        variant_id=variant_id,
        lineage_seed_id=lineage_seed_id,
        generation_id=generation_id,
        agent_id=agent_id,
        filename=filename,
    ).parsed


async def asyncio_detailed(
    id: str,
    *,
    client: Union[AuthenticatedClient, Client],
    variant_id: Union[Unset, int] = 0,
    lineage_seed_id: Union[Unset, int] = 0,
    generation_id: Union[Unset, int] = 1,
    agent_id: Union[Unset, int] = 0,
    filename: str,
) -> Response[Union[Any, HTTPValidationError]]:
    """Download a single file that was generated from a simulation analysis module

    Args:
        id (str):
        variant_id (Union[Unset, int]):  Default: 0.
        lineage_seed_id (Union[Unset, int]):  Default: 0.
        generation_id (Union[Unset, int]):  Default: 1.
        agent_id (Union[Unset, int]):  Default: 0.
        filename (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, HTTPValidationError]]
    """

    kwargs = _get_kwargs(
        id=id,
        variant_id=variant_id,
        lineage_seed_id=lineage_seed_id,
        generation_id=generation_id,
        agent_id=agent_id,
        filename=filename,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    id: str,
    *,
    client: Union[AuthenticatedClient, Client],
    variant_id: Union[Unset, int] = 0,
    lineage_seed_id: Union[Unset, int] = 0,
    generation_id: Union[Unset, int] = 1,
    agent_id: Union[Unset, int] = 0,
    filename: str,
) -> Optional[Union[Any, HTTPValidationError]]:
    """Download a single file that was generated from a simulation analysis module

    Args:
        id (str):
        variant_id (Union[Unset, int]):  Default: 0.
        lineage_seed_id (Union[Unset, int]):  Default: 0.
        generation_id (Union[Unset, int]):  Default: 1.
        agent_id (Union[Unset, int]):  Default: 0.
        filename (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, HTTPValidationError]
    """

    return (
        await asyncio_detailed(
            id=id,
            client=client,
            variant_id=variant_id,
            lineage_seed_id=lineage_seed_id,
            generation_id=generation_id,
            agent_id=agent_id,
            filename=filename,
        )
    ).parsed
