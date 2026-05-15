from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.pbg_wrapper_create_request import PbgWrapperCreateRequest
from ...models.pbg_wrapper_record import PbgWrapperRecord
from ...types import Response


def _get_kwargs(
    *,
    body: PbgWrapperCreateRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/compose/v1/wrappers",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[HTTPValidationError, PbgWrapperRecord]]:
    if response.status_code == 200:
        response_200 = PbgWrapperRecord.from_dict(response.json())

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
) -> Response[Union[HTTPValidationError, PbgWrapperRecord]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: PbgWrapperCreateRequest,
) -> Response[Union[HTTPValidationError, PbgWrapperRecord]]:
    """Generate a pbg-<tool> wrapper for an arbitrary simulator repo

     Submit a simulator's GitHub URL to generate a process-bigraph wrapper package.

    Returns immediately with a ``wrapper_id``. The wrapper is generated
    asynchronously — poll ``GET /compose/v1/wrappers/{wrapper_id}/status``
    until ``status == 'available'``.

    Once available the new processes appear in ``GET /compose/v1/processes``
    and can be referenced in ``POST /compose/v1/simulation/run`` documents.

    Args:
        body (PbgWrapperCreateRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, PbgWrapperRecord]]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: Union[AuthenticatedClient, Client],
    body: PbgWrapperCreateRequest,
) -> Optional[Union[HTTPValidationError, PbgWrapperRecord]]:
    """Generate a pbg-<tool> wrapper for an arbitrary simulator repo

     Submit a simulator's GitHub URL to generate a process-bigraph wrapper package.

    Returns immediately with a ``wrapper_id``. The wrapper is generated
    asynchronously — poll ``GET /compose/v1/wrappers/{wrapper_id}/status``
    until ``status == 'available'``.

    Once available the new processes appear in ``GET /compose/v1/processes``
    and can be referenced in ``POST /compose/v1/simulation/run`` documents.

    Args:
        body (PbgWrapperCreateRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, PbgWrapperRecord]
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: PbgWrapperCreateRequest,
) -> Response[Union[HTTPValidationError, PbgWrapperRecord]]:
    """Generate a pbg-<tool> wrapper for an arbitrary simulator repo

     Submit a simulator's GitHub URL to generate a process-bigraph wrapper package.

    Returns immediately with a ``wrapper_id``. The wrapper is generated
    asynchronously — poll ``GET /compose/v1/wrappers/{wrapper_id}/status``
    until ``status == 'available'``.

    Once available the new processes appear in ``GET /compose/v1/processes``
    and can be referenced in ``POST /compose/v1/simulation/run`` documents.

    Args:
        body (PbgWrapperCreateRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, PbgWrapperRecord]]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    body: PbgWrapperCreateRequest,
) -> Optional[Union[HTTPValidationError, PbgWrapperRecord]]:
    """Generate a pbg-<tool> wrapper for an arbitrary simulator repo

     Submit a simulator's GitHub URL to generate a process-bigraph wrapper package.

    Returns immediately with a ``wrapper_id``. The wrapper is generated
    asynchronously — poll ``GET /compose/v1/wrappers/{wrapper_id}/status``
    until ``status == 'available'``.

    Once available the new processes appear in ``GET /compose/v1/processes``
    and can be referenced in ``POST /compose/v1/simulation/run`` documents.

    Args:
        body (PbgWrapperCreateRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, PbgWrapperRecord]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
