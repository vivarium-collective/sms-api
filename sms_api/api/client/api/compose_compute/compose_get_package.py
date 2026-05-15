from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.registered_package import RegisteredPackage
from ...types import Response


def _get_kwargs(
    package_id: int,
) -> dict[str, Any]:
    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": f"/compose/v1/packages/{package_id}",
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[HTTPValidationError, RegisteredPackage]]:
    if response.status_code == 200:
        response_200 = RegisteredPackage.from_dict(response.json())

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
) -> Response[Union[HTTPValidationError, RegisteredPackage]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    package_id: int,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Response[Union[HTTPValidationError, RegisteredPackage]]:
    """Get a single registered package by ID

    Args:
        package_id (int):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, RegisteredPackage]]
    """

    kwargs = _get_kwargs(
        package_id=package_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    package_id: int,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Optional[Union[HTTPValidationError, RegisteredPackage]]:
    """Get a single registered package by ID

    Args:
        package_id (int):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, RegisteredPackage]
    """

    return sync_detailed(
        package_id=package_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    package_id: int,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Response[Union[HTTPValidationError, RegisteredPackage]]:
    """Get a single registered package by ID

    Args:
        package_id (int):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, RegisteredPackage]]
    """

    kwargs = _get_kwargs(
        package_id=package_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    package_id: int,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Optional[Union[HTTPValidationError, RegisteredPackage]]:
    """Get a single registered package by ID

    Args:
        package_id (int):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, RegisteredPackage]
    """

    return (
        await asyncio_detailed(
            package_id=package_id,
            client=client,
        )
    ).parsed
