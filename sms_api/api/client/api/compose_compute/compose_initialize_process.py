from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.compose_initialize_process_body import ComposeInitializeProcessBody
from ...models.compose_initialize_process_response_compose_initialize_process import (
    ComposeInitializeProcessResponseComposeInitializeProcess,
)
from ...models.http_validation_error import HTTPValidationError
from ...types import Response


def _get_kwargs(
    process_name: str,
    *,
    body: ComposeInitializeProcessBody,
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
) -> Optional[Union[ComposeInitializeProcessResponseComposeInitializeProcess, HTTPValidationError]]:
    if response.status_code == 200:
        response_200 = ComposeInitializeProcessResponseComposeInitializeProcess.from_dict(response.json())

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
) -> Response[Union[ComposeInitializeProcessResponseComposeInitializeProcess, HTTPValidationError]]:
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
    body: ComposeInitializeProcessBody,
) -> Response[Union[ComposeInitializeProcessResponseComposeInitializeProcess, HTTPValidationError]]:
    """Instantiate a process with a config; returns a UUID instance ID

    Args:
        process_name (str):
        body (ComposeInitializeProcessBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ComposeInitializeProcessResponseComposeInitializeProcess, HTTPValidationError]]
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
    body: ComposeInitializeProcessBody,
) -> Optional[Union[ComposeInitializeProcessResponseComposeInitializeProcess, HTTPValidationError]]:
    """Instantiate a process with a config; returns a UUID instance ID

    Args:
        process_name (str):
        body (ComposeInitializeProcessBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ComposeInitializeProcessResponseComposeInitializeProcess, HTTPValidationError]
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
    body: ComposeInitializeProcessBody,
) -> Response[Union[ComposeInitializeProcessResponseComposeInitializeProcess, HTTPValidationError]]:
    """Instantiate a process with a config; returns a UUID instance ID

    Args:
        process_name (str):
        body (ComposeInitializeProcessBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ComposeInitializeProcessResponseComposeInitializeProcess, HTTPValidationError]]
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
    body: ComposeInitializeProcessBody,
) -> Optional[Union[ComposeInitializeProcessResponseComposeInitializeProcess, HTTPValidationError]]:
    """Instantiate a process with a config; returns a UUID instance ID

    Args:
        process_name (str):
        body (ComposeInitializeProcessBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ComposeInitializeProcessResponseComposeInitializeProcess, HTTPValidationError]
    """

    return (
        await asyncio_detailed(
            process_name=process_name,
            client=client,
            body=body,
        )
    ).parsed
