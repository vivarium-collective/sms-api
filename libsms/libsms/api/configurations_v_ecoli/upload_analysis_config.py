from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.simulation_configuration import SimulationConfiguration
from ...models.uploaded_analysis_config import UploadedAnalysisConfig
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    body: SimulationConfiguration,
    config_id: Union[None, Unset, str] = UNSET,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    params: dict[str, Any] = {}

    json_config_id: Union[None, Unset, str]
    if isinstance(config_id, Unset):
        json_config_id = UNSET
    else:
        json_config_id = config_id
    params["config_id"] = json_config_id

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/configs/upload/analysis",
        "params": params,
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[HTTPValidationError, UploadedAnalysisConfig]]:
    if response.status_code == 200:
        response_200 = UploadedAnalysisConfig.from_dict(response.json())

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
) -> Response[Union[HTTPValidationError, UploadedAnalysisConfig]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: SimulationConfiguration,
    config_id: Union[None, Unset, str] = UNSET,
) -> Response[Union[HTTPValidationError, UploadedAnalysisConfig]]:
    """Upload Analysis Config

     Upload analysis config JSON

    Args:
        config_id (Union[None, Unset, str]):
        body (SimulationConfiguration):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, UploadedAnalysisConfig]]
    """

    kwargs = _get_kwargs(
        body=body,
        config_id=config_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: Union[AuthenticatedClient, Client],
    body: SimulationConfiguration,
    config_id: Union[None, Unset, str] = UNSET,
) -> Optional[Union[HTTPValidationError, UploadedAnalysisConfig]]:
    """Upload Analysis Config

     Upload analysis config JSON

    Args:
        config_id (Union[None, Unset, str]):
        body (SimulationConfiguration):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, UploadedAnalysisConfig]
    """

    return sync_detailed(
        client=client,
        body=body,
        config_id=config_id,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: SimulationConfiguration,
    config_id: Union[None, Unset, str] = UNSET,
) -> Response[Union[HTTPValidationError, UploadedAnalysisConfig]]:
    """Upload Analysis Config

     Upload analysis config JSON

    Args:
        config_id (Union[None, Unset, str]):
        body (SimulationConfiguration):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, UploadedAnalysisConfig]]
    """

    kwargs = _get_kwargs(
        body=body,
        config_id=config_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    body: SimulationConfiguration,
    config_id: Union[None, Unset, str] = UNSET,
) -> Optional[Union[HTTPValidationError, UploadedAnalysisConfig]]:
    """Upload Analysis Config

     Upload analysis config JSON

    Args:
        config_id (Union[None, Unset, str]):
        body (SimulationConfiguration):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, UploadedAnalysisConfig]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
            config_id=config_id,
        )
    ).parsed
