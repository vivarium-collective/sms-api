from http import HTTPStatus
from typing import Any, Optional, Union, cast

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.hpc_run import HpcRun
from ...models.http_validation_error import HTTPValidationError
from ...types import UNSET, Unset
from typing import cast
from typing import cast, Union
from typing import Union



def _get_kwargs(
    *,
    simulation_id: int,
    num_events: Union[None, Unset, int] = UNSET,

) -> dict[str, Any]:




    params: dict[str, Any] = {}

    params["simulation_id"] = simulation_id

    json_num_events: Union[None, Unset, int]
    if isinstance(num_events, Unset):
        json_num_events = UNSET
    else:
        json_num_events = num_events
    params["num_events"] = json_num_events


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/core/simulation/run/status",
        "params": params,
    }


    return _kwargs


def _parse_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> Optional[Union[HTTPValidationError, HpcRun]]:
    if response.status_code == 200:
        response_200 = HpcRun.from_dict(response.json())



        return response_200
    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> Response[Union[HTTPValidationError, HpcRun]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    simulation_id: int,
    num_events: Union[None, Unset, int] = UNSET,

) -> Response[Union[HTTPValidationError, HpcRun]]:
    """ Get the simulation status record by its ID

    Args:
        simulation_id (int):
        num_events (Union[None, Unset, int]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, HpcRun]]
     """


    kwargs = _get_kwargs(
        simulation_id=simulation_id,
num_events=num_events,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    *,
    client: Union[AuthenticatedClient, Client],
    simulation_id: int,
    num_events: Union[None, Unset, int] = UNSET,

) -> Optional[Union[HTTPValidationError, HpcRun]]:
    """ Get the simulation status record by its ID

    Args:
        simulation_id (int):
        num_events (Union[None, Unset, int]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, HpcRun]
     """


    return sync_detailed(
        client=client,
simulation_id=simulation_id,
num_events=num_events,

    ).parsed

async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    simulation_id: int,
    num_events: Union[None, Unset, int] = UNSET,

) -> Response[Union[HTTPValidationError, HpcRun]]:
    """ Get the simulation status record by its ID

    Args:
        simulation_id (int):
        num_events (Union[None, Unset, int]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, HpcRun]]
     """


    kwargs = _get_kwargs(
        simulation_id=simulation_id,
num_events=num_events,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    simulation_id: int,
    num_events: Union[None, Unset, int] = UNSET,

) -> Optional[Union[HTTPValidationError, HpcRun]]:
    """ Get the simulation status record by its ID

    Args:
        simulation_id (int):
        num_events (Union[None, Unset, int]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, HpcRun]
     """


    return (await asyncio_detailed(
        client=client,
simulation_id=simulation_id,
num_events=num_events,

    )).parsed
