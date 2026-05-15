from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.process_instance_record import ProcessInstanceRecord
from ...models.process_instance_status import ProcessInstanceStatus
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    status: Union[None, ProcessInstanceStatus, Unset] = UNSET,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    json_status: Union[None, Unset, str]
    if isinstance(status, Unset):
        json_status = UNSET
    elif isinstance(status, ProcessInstanceStatus):
        json_status = status.value
    else:
        json_status = status
    params["status"] = json_status

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/compose/v1/process/instances",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[HTTPValidationError, list["ProcessInstanceRecord"]]]:
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in _response_200:
            response_200_item = ProcessInstanceRecord.from_dict(response_200_item_data)

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
) -> Response[Union[HTTPValidationError, list["ProcessInstanceRecord"]]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    status: Union[None, ProcessInstanceStatus, Unset] = UNSET,
) -> Response[Union[HTTPValidationError, list["ProcessInstanceRecord"]]]:
    """List all process registry instances (optionally filtered by status)

    Args:
        status (Union[None, ProcessInstanceStatus, Unset]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, list['ProcessInstanceRecord']]]
    """

    kwargs = _get_kwargs(
        status=status,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: Union[AuthenticatedClient, Client],
    status: Union[None, ProcessInstanceStatus, Unset] = UNSET,
) -> Optional[Union[HTTPValidationError, list["ProcessInstanceRecord"]]]:
    """List all process registry instances (optionally filtered by status)

    Args:
        status (Union[None, ProcessInstanceStatus, Unset]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, list['ProcessInstanceRecord']]
    """

    return sync_detailed(
        client=client,
        status=status,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    status: Union[None, ProcessInstanceStatus, Unset] = UNSET,
) -> Response[Union[HTTPValidationError, list["ProcessInstanceRecord"]]]:
    """List all process registry instances (optionally filtered by status)

    Args:
        status (Union[None, ProcessInstanceStatus, Unset]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, list['ProcessInstanceRecord']]]
    """

    kwargs = _get_kwargs(
        status=status,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    status: Union[None, ProcessInstanceStatus, Unset] = UNSET,
) -> Optional[Union[HTTPValidationError, list["ProcessInstanceRecord"]]]:
    """List all process registry instances (optionally filtered by status)

    Args:
        status (Union[None, ProcessInstanceStatus, Unset]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, list['ProcessInstanceRecord']]
    """

    return (
        await asyncio_detailed(
            client=client,
            status=status,
        )
    ).parsed
