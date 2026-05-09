from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.process_initialize_request import ProcessInitializeRequest
from ...models.process_instance import ProcessInstance
from ...types import Response


def _get_kwargs(
    process_name: str,
    *,
    body: ProcessInitializeRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": f"/compose/v1/process/{process_name}/initialize",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[HTTPValidationError, ProcessInstance]]:
    if response.status_code == 200:
        response_200 = ProcessInstance.from_dict(response.json())

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
) -> Response[Union[HTTPValidationError, ProcessInstance]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    process_name: str,
    *,
    client: Union[AuthenticatedClient, Client],
    body: ProcessInitializeRequest,
) -> Response[Union[HTTPValidationError, ProcessInstance]]:
    """Instantiate a process with a config; returns a UUID instance ID

    Args:
        process_name (str):
        body (ProcessInitializeRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, ProcessInstance]]
    """

    kwargs = _get_kwargs(
        process_name=process_name,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    process_name: str,
    *,
    client: Union[AuthenticatedClient, Client],
    body: ProcessInitializeRequest,
) -> Optional[Union[HTTPValidationError, ProcessInstance]]:
    """Instantiate a process with a config; returns a UUID instance ID

    Args:
        process_name (str):
        body (ProcessInitializeRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, ProcessInstance]
    """

    return sync_detailed(
        process_name=process_name,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    process_name: str,
    *,
    client: Union[AuthenticatedClient, Client],
    body: ProcessInitializeRequest,
) -> Response[Union[HTTPValidationError, ProcessInstance]]:
    """Instantiate a process with a config; returns a UUID instance ID

    Args:
        process_name (str):
        body (ProcessInitializeRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, ProcessInstance]]
    """

    kwargs = _get_kwargs(
        process_name=process_name,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    process_name: str,
    *,
    client: Union[AuthenticatedClient, Client],
    body: ProcessInitializeRequest,
) -> Optional[Union[HTTPValidationError, ProcessInstance]]:
    """Instantiate a process with a config; returns a UUID instance ID

    Args:
        process_name (str):
        body (ProcessInitializeRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, ProcessInstance]
    """

    return (
        await asyncio_detailed(
            process_name=process_name,
            client=client,
            body=body,
        )
    ).parsed
