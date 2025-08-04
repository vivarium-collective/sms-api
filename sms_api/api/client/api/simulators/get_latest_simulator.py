from http import HTTPStatus
from typing import Any, Optional, Union, cast

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.simulator import Simulator
from ...types import UNSET, Unset
from typing import cast
from typing import Union


def _get_kwargs(
    *,
    git_repo_url: Union[Unset, str] = "https://github.com/vivarium-collective/vEcoli",
    git_branch: Union[Unset, str] = "messages",
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["git_repo_url"] = git_repo_url

    params["git_branch"] = git_branch

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/core/simulator/latest",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[HTTPValidationError, Simulator]]:
    if response.status_code == 200:
        response_200 = Simulator.from_dict(response.json())

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
) -> Response[Union[HTTPValidationError, Simulator]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    git_repo_url: Union[Unset, str] = "https://github.com/vivarium-collective/vEcoli",
    git_branch: Union[Unset, str] = "messages",
) -> Response[Union[HTTPValidationError, Simulator]]:
    """Get the latest simulator version

    Args:
        git_repo_url (Union[Unset, str]):  Default: 'https://github.com/vivarium-
            collective/vEcoli'.
        git_branch (Union[Unset, str]):  Default: 'messages'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, Simulator]]
    """

    kwargs = _get_kwargs(
        git_repo_url=git_repo_url,
        git_branch=git_branch,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: Union[AuthenticatedClient, Client],
    git_repo_url: Union[Unset, str] = "https://github.com/vivarium-collective/vEcoli",
    git_branch: Union[Unset, str] = "messages",
) -> Optional[Union[HTTPValidationError, Simulator]]:
    """Get the latest simulator version

    Args:
        git_repo_url (Union[Unset, str]):  Default: 'https://github.com/vivarium-
            collective/vEcoli'.
        git_branch (Union[Unset, str]):  Default: 'messages'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, Simulator]
    """

    return sync_detailed(
        client=client,
        git_repo_url=git_repo_url,
        git_branch=git_branch,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    git_repo_url: Union[Unset, str] = "https://github.com/vivarium-collective/vEcoli",
    git_branch: Union[Unset, str] = "messages",
) -> Response[Union[HTTPValidationError, Simulator]]:
    """Get the latest simulator version

    Args:
        git_repo_url (Union[Unset, str]):  Default: 'https://github.com/vivarium-
            collective/vEcoli'.
        git_branch (Union[Unset, str]):  Default: 'messages'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, Simulator]]
    """

    kwargs = _get_kwargs(
        git_repo_url=git_repo_url,
        git_branch=git_branch,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    git_repo_url: Union[Unset, str] = "https://github.com/vivarium-collective/vEcoli",
    git_branch: Union[Unset, str] = "messages",
) -> Optional[Union[HTTPValidationError, Simulator]]:
    """Get the latest simulator version

    Args:
        git_repo_url (Union[Unset, str]):  Default: 'https://github.com/vivarium-
            collective/vEcoli'.
        git_branch (Union[Unset, str]):  Default: 'messages'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, Simulator]
    """

    return (
        await asyncio_detailed(
            client=client,
            git_repo_url=git_repo_url,
            git_branch=git_branch,
        )
    ).parsed
