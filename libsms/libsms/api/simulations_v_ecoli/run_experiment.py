from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.body_run_experiment import BodyRunExperiment
from ...models.ecoli_experiment_dto import EcoliExperimentDTO
from ...models.http_validation_error import HTTPValidationError
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    body: BodyRunExperiment,
    config_id: Union[Unset, str] = "sms",
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    params: dict[str, Any] = {}

    params["config_id"] = config_id

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/experiments/launch",
        "params": params,
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[EcoliExperimentDTO, HTTPValidationError]]:
    if response.status_code == 200:
        response_200 = EcoliExperimentDTO.from_dict(response.json())

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
) -> Response[Union[EcoliExperimentDTO, HTTPValidationError]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: BodyRunExperiment,
    config_id: Union[Unset, str] = "sms",
) -> Response[Union[EcoliExperimentDTO, HTTPValidationError]]:
    """Launches a nextflow-powered vEcoli simulation workflow

    Args:
        config_id (Union[Unset, str]): Configuration ID of an existing available vecoli simulation
            configuration JSON Default: 'sms'.
        body (BodyRunExperiment):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[EcoliExperimentDTO, HTTPValidationError]]
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
    body: BodyRunExperiment,
    config_id: Union[Unset, str] = "sms",
) -> Optional[Union[EcoliExperimentDTO, HTTPValidationError]]:
    """Launches a nextflow-powered vEcoli simulation workflow

    Args:
        config_id (Union[Unset, str]): Configuration ID of an existing available vecoli simulation
            configuration JSON Default: 'sms'.
        body (BodyRunExperiment):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[EcoliExperimentDTO, HTTPValidationError]
    """

    return sync_detailed(
        client=client,
        body=body,
        config_id=config_id,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: BodyRunExperiment,
    config_id: Union[Unset, str] = "sms",
) -> Response[Union[EcoliExperimentDTO, HTTPValidationError]]:
    """Launches a nextflow-powered vEcoli simulation workflow

    Args:
        config_id (Union[Unset, str]): Configuration ID of an existing available vecoli simulation
            configuration JSON Default: 'sms'.
        body (BodyRunExperiment):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[EcoliExperimentDTO, HTTPValidationError]]
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
    body: BodyRunExperiment,
    config_id: Union[Unset, str] = "sms",
) -> Optional[Union[EcoliExperimentDTO, HTTPValidationError]]:
    """Launches a nextflow-powered vEcoli simulation workflow

    Args:
        config_id (Union[Unset, str]): Configuration ID of an existing available vecoli simulation
            configuration JSON Default: 'sms'.
        body (BodyRunExperiment):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[EcoliExperimentDTO, HTTPValidationError]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
            config_id=config_id,
        )
    ).parsed
