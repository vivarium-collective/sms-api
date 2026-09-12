from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.task_dto import TaskDTO
from ...models.task_run_request import TaskRunRequest
from ...types import Response


def _get_kwargs(
    *,
    body: TaskRunRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/v1/tasks",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[HTTPValidationError, TaskDTO]]:
    if response.status_code == 200:
        response_200 = TaskDTO.from_dict(response.json())

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
) -> Response[Union[HTTPValidationError, TaskDTO]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: TaskRunRequest,
) -> Response[Union[HTTPValidationError, TaskDTO]]:
    """Submit a self-contained repo-path script to the in-region task compute (viva-api#631)

    Args:
        body (TaskRunRequest): Request to run a self-contained script on the in-region task
            compute
            (viva-api#631). Slice 1: ``script`` is a path to a script already in the
            image (e.g. an fss-combine / ptools-regather turnkey script that lives in the
            repo). ``memory_class`` routes the instance via the same mechanism as
            analyses (viva-api#629).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, TaskDTO]]
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
    body: TaskRunRequest,
) -> Optional[Union[HTTPValidationError, TaskDTO]]:
    """Submit a self-contained repo-path script to the in-region task compute (viva-api#631)

    Args:
        body (TaskRunRequest): Request to run a self-contained script on the in-region task
            compute
            (viva-api#631). Slice 1: ``script`` is a path to a script already in the
            image (e.g. an fss-combine / ptools-regather turnkey script that lives in the
            repo). ``memory_class`` routes the instance via the same mechanism as
            analyses (viva-api#629).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, TaskDTO]
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: TaskRunRequest,
) -> Response[Union[HTTPValidationError, TaskDTO]]:
    """Submit a self-contained repo-path script to the in-region task compute (viva-api#631)

    Args:
        body (TaskRunRequest): Request to run a self-contained script on the in-region task
            compute
            (viva-api#631). Slice 1: ``script`` is a path to a script already in the
            image (e.g. an fss-combine / ptools-regather turnkey script that lives in the
            repo). ``memory_class`` routes the instance via the same mechanism as
            analyses (viva-api#629).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, TaskDTO]]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    body: TaskRunRequest,
) -> Optional[Union[HTTPValidationError, TaskDTO]]:
    """Submit a self-contained repo-path script to the in-region task compute (viva-api#631)

    Args:
        body (TaskRunRequest): Request to run a self-contained script on the in-region task
            compute
            (viva-api#631). Slice 1: ``script`` is a path to a script already in the
            image (e.g. an fss-combine / ptools-regather turnkey script that lives in the
            repo). ``memory_class`` routes the instance via the same mechanism as
            analyses (viva-api#629).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, TaskDTO]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
