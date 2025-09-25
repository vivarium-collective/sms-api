from http import HTTPStatus
from typing import Any, Optional, Union, cast

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.body_upload_analysis_module import BodyUploadAnalysisModule
from ...models.http_validation_error import HTTPValidationError
from ...models.upload_analysis_module_response_upload_analysis_module import (
    UploadAnalysisModuleResponseUploadAnalysisModule,
)
from typing import cast


def _get_kwargs(
    *,
    body: BodyUploadAnalysisModule,
    submodule_name: str,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    params: dict[str, Any] = {}

    params["submodule_name"] = submodule_name

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "put",
        "url": "/v1/ecoli/analyses",
        "params": params,
    }

    _kwargs["files"] = body.to_multipart()

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[HTTPValidationError, UploadAnalysisModuleResponseUploadAnalysisModule]]:
    if response.status_code == 200:
        response_200 = UploadAnalysisModuleResponseUploadAnalysisModule.from_dict(response.json())

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
) -> Response[Union[HTTPValidationError, UploadAnalysisModuleResponseUploadAnalysisModule]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: BodyUploadAnalysisModule,
    submodule_name: str,
) -> Response[Union[HTTPValidationError, UploadAnalysisModuleResponseUploadAnalysisModule]]:
    """Upload custom python vEcoli analysis module according to the vEcoli analysis API

    Args:
        submodule_name (str): Submodule name(single, multiseed, etc)
        body (BodyUploadAnalysisModule):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, UploadAnalysisModuleResponseUploadAnalysisModule]]
    """

    kwargs = _get_kwargs(
        body=body,
        submodule_name=submodule_name,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: Union[AuthenticatedClient, Client],
    body: BodyUploadAnalysisModule,
    submodule_name: str,
) -> Optional[Union[HTTPValidationError, UploadAnalysisModuleResponseUploadAnalysisModule]]:
    """Upload custom python vEcoli analysis module according to the vEcoli analysis API

    Args:
        submodule_name (str): Submodule name(single, multiseed, etc)
        body (BodyUploadAnalysisModule):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, UploadAnalysisModuleResponseUploadAnalysisModule]
    """

    return sync_detailed(
        client=client,
        body=body,
        submodule_name=submodule_name,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: BodyUploadAnalysisModule,
    submodule_name: str,
) -> Response[Union[HTTPValidationError, UploadAnalysisModuleResponseUploadAnalysisModule]]:
    """Upload custom python vEcoli analysis module according to the vEcoli analysis API

    Args:
        submodule_name (str): Submodule name(single, multiseed, etc)
        body (BodyUploadAnalysisModule):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, UploadAnalysisModuleResponseUploadAnalysisModule]]
    """

    kwargs = _get_kwargs(
        body=body,
        submodule_name=submodule_name,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    body: BodyUploadAnalysisModule,
    submodule_name: str,
) -> Optional[Union[HTTPValidationError, UploadAnalysisModuleResponseUploadAnalysisModule]]:
    """Upload custom python vEcoli analysis module according to the vEcoli analysis API

    Args:
        submodule_name (str): Submodule name(single, multiseed, etc)
        body (BodyUploadAnalysisModule):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, UploadAnalysisModuleResponseUploadAnalysisModule]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
            submodule_name=submodule_name,
        )
    ).parsed
