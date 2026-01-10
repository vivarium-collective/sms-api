from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...types import UNSET, Response, Unset


def _get_kwargs(
    id: int,
    *,
    body: Union[None, list[str]],
    lineage_seed: Union[Unset, int] = 6,
    generation: Union[Unset, int] = 1,
    variant: Union[Unset, int] = 0,
    agent_id: Union[Unset, int] = 0,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    params: dict[str, Any] = {}

    params["lineage_seed"] = lineage_seed

    params["generation"] = generation

    params["variant"] = variant

    params["agent_id"] = agent_id

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": f"/api/v1/simulations/{id}/data",
        "params": params,
    }

    _kwargs["json"]: Union[None, list[str]]
    if isinstance(body, list):
        _kwargs["json"] = body

    else:
        _kwargs["json"] = body

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
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
    id: int,
    *,
    client: Union[AuthenticatedClient, Client],
    body: Union[None, list[str]],
    lineage_seed: Union[Unset, int] = 6,
    generation: Union[Unset, int] = 1,
    variant: Union[Unset, int] = 0,
    agent_id: Union[Unset, int] = 0,
) -> Response[Union[Any, HTTPValidationError]]:
    """Get/Stream simulation data

    Args:
        id (int): Database ID of the simulation.
        lineage_seed (Union[Unset, int]):  Default: 6.
        generation (Union[Unset, int]):  Default: 1.
        variant (Union[Unset, int]):  Default: 0.
        agent_id (Union[Unset, int]):  Default: 0.
        body (Union[None, list[str]]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, HTTPValidationError]]
    """

    kwargs = _get_kwargs(
        id=id,
        body=body,
        lineage_seed=lineage_seed,
        generation=generation,
        variant=variant,
        agent_id=agent_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    id: int,
    *,
    client: Union[AuthenticatedClient, Client],
    body: Union[None, list[str]],
    lineage_seed: Union[Unset, int] = 6,
    generation: Union[Unset, int] = 1,
    variant: Union[Unset, int] = 0,
    agent_id: Union[Unset, int] = 0,
) -> Optional[Union[Any, HTTPValidationError]]:
    """Get/Stream simulation data

    Args:
        id (int): Database ID of the simulation.
        lineage_seed (Union[Unset, int]):  Default: 6.
        generation (Union[Unset, int]):  Default: 1.
        variant (Union[Unset, int]):  Default: 0.
        agent_id (Union[Unset, int]):  Default: 0.
        body (Union[None, list[str]]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, HTTPValidationError]
    """

    return sync_detailed(
        id=id,
        client=client,
        body=body,
        lineage_seed=lineage_seed,
        generation=generation,
        variant=variant,
        agent_id=agent_id,
    ).parsed


async def asyncio_detailed(
    id: int,
    *,
    client: Union[AuthenticatedClient, Client],
    body: Union[None, list[str]],
    lineage_seed: Union[Unset, int] = 6,
    generation: Union[Unset, int] = 1,
    variant: Union[Unset, int] = 0,
    agent_id: Union[Unset, int] = 0,
) -> Response[Union[Any, HTTPValidationError]]:
    """Get/Stream simulation data

    Args:
        id (int): Database ID of the simulation.
        lineage_seed (Union[Unset, int]):  Default: 6.
        generation (Union[Unset, int]):  Default: 1.
        variant (Union[Unset, int]):  Default: 0.
        agent_id (Union[Unset, int]):  Default: 0.
        body (Union[None, list[str]]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, HTTPValidationError]]
    """

    kwargs = _get_kwargs(
        id=id,
        body=body,
        lineage_seed=lineage_seed,
        generation=generation,
        variant=variant,
        agent_id=agent_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    id: int,
    *,
    client: Union[AuthenticatedClient, Client],
    body: Union[None, list[str]],
    lineage_seed: Union[Unset, int] = 6,
    generation: Union[Unset, int] = 1,
    variant: Union[Unset, int] = 0,
    agent_id: Union[Unset, int] = 0,
) -> Optional[Union[Any, HTTPValidationError]]:
    """Get/Stream simulation data

    Args:
        id (int): Database ID of the simulation.
        lineage_seed (Union[Unset, int]):  Default: 6.
        generation (Union[Unset, int]):  Default: 1.
        variant (Union[Unset, int]):  Default: 0.
        agent_id (Union[Unset, int]):  Default: 0.
        body (Union[None, list[str]]):

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
            body=body,
            lineage_seed=lineage_seed,
            generation=generation,
            variant=variant,
            agent_id=agent_id,
        )
    ).parsed
