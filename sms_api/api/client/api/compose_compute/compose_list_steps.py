from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.compose_list_steps_response_200_item import ComposeListStepsResponse200Item
from ...models.http_validation_error import HTTPValidationError
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    source: Union[Unset, str] = "core",
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["source"] = source

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/compose/v1/steps",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[HTTPValidationError, list["ComposeListStepsResponse200Item"]]]:
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in _response_200:
            response_200_item = ComposeListStepsResponse200Item.from_dict(response_200_item_data)

            response_200.append(response_200_item)

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
) -> Response[Union[HTTPValidationError, list["ComposeListStepsResponse200Item"]]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    source: Union[Unset, str] = "core",
) -> Response[Union[HTTPValidationError, list["ComposeListStepsResponse200Item"]]]:
    """List registered process-bigraph steps

    Args:
        source (Union[Unset, str]): 'core' from live link_registry, 'db' from package_db lineage,
            or 'union' for both Default: 'core'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, list['ComposeListStepsResponse200Item']]]
    """

    kwargs = _get_kwargs(
        source=source,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: Union[AuthenticatedClient, Client],
    source: Union[Unset, str] = "core",
) -> Optional[Union[HTTPValidationError, list["ComposeListStepsResponse200Item"]]]:
    """List registered process-bigraph steps

    Args:
        source (Union[Unset, str]): 'core' from live link_registry, 'db' from package_db lineage,
            or 'union' for both Default: 'core'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, list['ComposeListStepsResponse200Item']]
    """

    return sync_detailed(
        client=client,
        source=source,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    source: Union[Unset, str] = "core",
) -> Response[Union[HTTPValidationError, list["ComposeListStepsResponse200Item"]]]:
    """List registered process-bigraph steps

    Args:
        source (Union[Unset, str]): 'core' from live link_registry, 'db' from package_db lineage,
            or 'union' for both Default: 'core'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, list['ComposeListStepsResponse200Item']]]
    """

    kwargs = _get_kwargs(
        source=source,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    source: Union[Unset, str] = "core",
) -> Optional[Union[HTTPValidationError, list["ComposeListStepsResponse200Item"]]]:
    """List registered process-bigraph steps

    Args:
        source (Union[Unset, str]): 'core' from live link_registry, 'db' from package_db lineage,
            or 'union' for both Default: 'core'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, list['ComposeListStepsResponse200Item']]
    """

    return (
        await asyncio_detailed(
            client=client,
            source=source,
        )
    ).parsed
