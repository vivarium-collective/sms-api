from http import HTTPStatus
from typing import Any, Optional, Union, cast

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...types import UNSET, Unset
from typing import cast
from typing import cast, Union
from typing import Union


def _get_kwargs(
    *,
    experiment_id: str,
    filename: Union[None, Unset, str] = UNSET,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["experiment_id"] = experiment_id

    json_filename: Union[None, Unset, str]
    if isinstance(filename, Unset):
        json_filename = UNSET
    else:
        json_filename = filename
    params["filename"] = json_filename

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/core/download/parquet",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[Any, HTTPValidationError]]:
    if response.status_code == 200:
        response_200 = cast(Any, None)
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
) -> Response[Union[Any, HTTPValidationError]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    experiment_id: str,
    filename: Union[None, Unset, str] = UNSET,
) -> Response[Union[Any, HTTPValidationError]]:
    """Download zip file containing pqs that were generated from the parquet emitter

    Args:
        experiment_id (str): Experiment ID for the simulation (from config.json).
        filename (Union[None, Unset, str]): Name you wish to assign to the downloaded zip file

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, HTTPValidationError]]
    """

    kwargs = _get_kwargs(
        experiment_id=experiment_id,
        filename=filename,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: Union[AuthenticatedClient, Client],
    experiment_id: str,
    filename: Union[None, Unset, str] = UNSET,
) -> Optional[Union[Any, HTTPValidationError]]:
    """Download zip file containing pqs that were generated from the parquet emitter

    Args:
        experiment_id (str): Experiment ID for the simulation (from config.json).
        filename (Union[None, Unset, str]): Name you wish to assign to the downloaded zip file

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, HTTPValidationError]
    """

    return sync_detailed(
        client=client,
        experiment_id=experiment_id,
        filename=filename,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    experiment_id: str,
    filename: Union[None, Unset, str] = UNSET,
) -> Response[Union[Any, HTTPValidationError]]:
    """Download zip file containing pqs that were generated from the parquet emitter

    Args:
        experiment_id (str): Experiment ID for the simulation (from config.json).
        filename (Union[None, Unset, str]): Name you wish to assign to the downloaded zip file

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, HTTPValidationError]]
    """

    kwargs = _get_kwargs(
        experiment_id=experiment_id,
        filename=filename,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    experiment_id: str,
    filename: Union[None, Unset, str] = UNSET,
) -> Optional[Union[Any, HTTPValidationError]]:
    """Download zip file containing pqs that were generated from the parquet emitter

    Args:
        experiment_id (str): Experiment ID for the simulation (from config.json).
        filename (Union[None, Unset, str]): Name you wish to assign to the downloaded zip file

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, HTTPValidationError]
    """

    return (
        await asyncio_detailed(
            client=client,
            experiment_id=experiment_id,
            filename=filename,
        )
    ).parsed
