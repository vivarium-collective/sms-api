from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.simulation_run import SimulationRun
from ...types import UNSET, Response


def _get_kwargs(
    *,
    experiment_tag: str,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["experiment_tag"] = experiment_tag

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/experiments/status",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[HTTPValidationError, SimulationRun]]:
    if response.status_code == 200:
        response_200 = SimulationRun.from_dict(response.json())

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
) -> Response[Union[HTTPValidationError, SimulationRun]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    experiment_tag: str,
) -> Response[Union[HTTPValidationError, SimulationRun]]:
    """Get the simulation status record by its ID

    Args:
        experiment_tag (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, SimulationRun]]
    """

    kwargs = _get_kwargs(
        experiment_tag=experiment_tag,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: Union[AuthenticatedClient, Client],
    experiment_tag: str,
) -> Optional[Union[HTTPValidationError, SimulationRun]]:
    """Get the simulation status record by its ID

    Args:
        experiment_tag (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, SimulationRun]
    """

    return sync_detailed(
        client=client,
        experiment_tag=experiment_tag,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    experiment_tag: str,
) -> Response[Union[HTTPValidationError, SimulationRun]]:
    """Get the simulation status record by its ID

    Args:
        experiment_tag (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, SimulationRun]]
    """

    kwargs = _get_kwargs(
        experiment_tag=experiment_tag,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    experiment_tag: str,
) -> Optional[Union[HTTPValidationError, SimulationRun]]:
    """Get the simulation status record by its ID

    Args:
        experiment_tag (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, SimulationRun]
    """

    return (
        await asyncio_detailed(
            client=client,
            experiment_tag=experiment_tag,
        )
    ).parsed
