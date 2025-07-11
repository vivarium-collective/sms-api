from http import HTTPStatus
from typing import Any, Optional, Union, cast

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.settings import Settings
from ...types import UNSET, Unset
from typing import cast
from typing import cast, Union
from typing import Union



def _get_kwargs(
    *,
    body: Union['Settings', None],
    experiment_id: Union[Unset, str] = 'experiment_96bb7a2_id_1_20250620-181422',
    database_id: Union[Unset, int] = UNSET,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}




    params: dict[str, Any] = {}

    params["experiment_id"] = experiment_id

    params["database_id"] = database_id


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/core/simulation/results",
        "params": params,
    }

    _kwargs["json"]: Union[None, dict[str, Any]]
    if isinstance(body, Settings):
        _kwargs["json"] = body.to_dict()
    else:
        _kwargs["json"] = body


    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> Optional[Union[Any, HTTPValidationError]]:
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


def _build_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> Response[Union[Any, HTTPValidationError]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: Union['Settings', None],
    experiment_id: Union[Unset, str] = 'experiment_96bb7a2_id_1_20250620-181422',
    database_id: Union[Unset, int] = UNSET,

) -> Response[Union[Any, HTTPValidationError]]:
    """ Get Results

    Args:
        experiment_id (Union[Unset, str]):  Default: 'experiment_96bb7a2_id_1_20250620-181422'.
        database_id (Union[Unset, int]): Database Id of simulation
        body (Union['Settings', None]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, HTTPValidationError]]
     """


    kwargs = _get_kwargs(
        body=body,
experiment_id=experiment_id,
database_id=database_id,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    *,
    client: Union[AuthenticatedClient, Client],
    body: Union['Settings', None],
    experiment_id: Union[Unset, str] = 'experiment_96bb7a2_id_1_20250620-181422',
    database_id: Union[Unset, int] = UNSET,

) -> Optional[Union[Any, HTTPValidationError]]:
    """ Get Results

    Args:
        experiment_id (Union[Unset, str]):  Default: 'experiment_96bb7a2_id_1_20250620-181422'.
        database_id (Union[Unset, int]): Database Id of simulation
        body (Union['Settings', None]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, HTTPValidationError]
     """


    return sync_detailed(
        client=client,
body=body,
experiment_id=experiment_id,
database_id=database_id,

    ).parsed

async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: Union['Settings', None],
    experiment_id: Union[Unset, str] = 'experiment_96bb7a2_id_1_20250620-181422',
    database_id: Union[Unset, int] = UNSET,

) -> Response[Union[Any, HTTPValidationError]]:
    """ Get Results

    Args:
        experiment_id (Union[Unset, str]):  Default: 'experiment_96bb7a2_id_1_20250620-181422'.
        database_id (Union[Unset, int]): Database Id of simulation
        body (Union['Settings', None]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, HTTPValidationError]]
     """


    kwargs = _get_kwargs(
        body=body,
experiment_id=experiment_id,
database_id=database_id,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    body: Union['Settings', None],
    experiment_id: Union[Unset, str] = 'experiment_96bb7a2_id_1_20250620-181422',
    database_id: Union[Unset, int] = UNSET,

) -> Optional[Union[Any, HTTPValidationError]]:
    """ Get Results

    Args:
        experiment_id (Union[Unset, str]):  Default: 'experiment_96bb7a2_id_1_20250620-181422'.
        database_id (Union[Unset, int]): Database Id of simulation
        body (Union['Settings', None]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, HTTPValidationError]
     """


    return (await asyncio_detailed(
        client=client,
body=body,
experiment_id=experiment_id,
database_id=database_id,

    )).parsed
