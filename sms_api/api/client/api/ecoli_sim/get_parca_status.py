from http import HTTPStatus
from typing import Any, Optional, Union, cast

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.hpc_run import HpcRun
from ...models.http_validation_error import HTTPValidationError
from typing import cast


def _get_kwargs(
    *,
    parca_id: int,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["parca_id"] = parca_id

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/core/simulation/parca/status",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[HTTPValidationError, HpcRun]]:
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


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[Union[HTTPValidationError, HpcRun]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    parca_id: int,
) -> Response[Union[HTTPValidationError, HpcRun]]:
    """Get parca calculation status by its ID

    Args:
        parca_id (int):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, HpcRun]]
    """

    kwargs = _get_kwargs(
        parca_id=parca_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: Union[AuthenticatedClient, Client],
    parca_id: int,
) -> Optional[Union[HTTPValidationError, HpcRun]]:
    """Get parca calculation status by its ID

    Args:
        parca_id (int):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, HpcRun]
    """

    return sync_detailed(
        client=client,
        parca_id=parca_id,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    parca_id: int,
) -> Response[Union[HTTPValidationError, HpcRun]]:
    """Get parca calculation status by its ID

    Args:
        parca_id (int):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, HpcRun]]
    """

    kwargs = _get_kwargs(
        parca_id=parca_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    parca_id: int,
) -> Optional[Union[HTTPValidationError, HpcRun]]:
    """Get parca calculation status by its ID

    Args:
        parca_id (int):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, HpcRun]
    """

    return (
        await asyncio_detailed(
            client=client,
            parca_id=parca_id,
        )
    ).parsed
