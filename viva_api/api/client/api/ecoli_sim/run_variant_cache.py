from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.variant_cache_job import VariantCacheJob
from ...models.variant_cache_request import VariantCacheRequest
from ...types import Response


def _get_kwargs(
    *,
    body: VariantCacheRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/v1/parca/variant-cache",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[HTTPValidationError, VariantCacheJob]]:
    if response.status_code == 200:
        response_200 = VariantCacheJob.from_dict(response.json())

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
) -> Response[Union[HTTPValidationError, VariantCacheJob]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: VariantCacheRequest,
) -> Response[Union[HTTPValidationError, VariantCacheJob]]:
    """Stamp native-gene perturbations onto a completed ParCa dataset's cache (backlog item 451)

    Args:
        body (VariantCacheRequest): Backlog item 451: stamp NATIVE-gene translation-efficiency
            perturbations
            onto a COMPLETED ParCa dataset's cache (``scripts/build_variant_cache.py``,
            the sibling mechanism to ``NewGeneCacheRequest`` above -- native-gene
            knockouts/knockdowns/overexpression instead of a new gene's own induction
            level -- see ``SimulationServiceRay.submit_variant_cache_job``). Ray/Batch
            backend only; the source dataset must already have SUCCEEDED (not
            re-validated here, same pure-passthrough philosophy as
            ``NewGeneCacheRequest``).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, VariantCacheJob]]
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
    body: VariantCacheRequest,
) -> Optional[Union[HTTPValidationError, VariantCacheJob]]:
    """Stamp native-gene perturbations onto a completed ParCa dataset's cache (backlog item 451)

    Args:
        body (VariantCacheRequest): Backlog item 451: stamp NATIVE-gene translation-efficiency
            perturbations
            onto a COMPLETED ParCa dataset's cache (``scripts/build_variant_cache.py``,
            the sibling mechanism to ``NewGeneCacheRequest`` above -- native-gene
            knockouts/knockdowns/overexpression instead of a new gene's own induction
            level -- see ``SimulationServiceRay.submit_variant_cache_job``). Ray/Batch
            backend only; the source dataset must already have SUCCEEDED (not
            re-validated here, same pure-passthrough philosophy as
            ``NewGeneCacheRequest``).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, VariantCacheJob]
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: VariantCacheRequest,
) -> Response[Union[HTTPValidationError, VariantCacheJob]]:
    """Stamp native-gene perturbations onto a completed ParCa dataset's cache (backlog item 451)

    Args:
        body (VariantCacheRequest): Backlog item 451: stamp NATIVE-gene translation-efficiency
            perturbations
            onto a COMPLETED ParCa dataset's cache (``scripts/build_variant_cache.py``,
            the sibling mechanism to ``NewGeneCacheRequest`` above -- native-gene
            knockouts/knockdowns/overexpression instead of a new gene's own induction
            level -- see ``SimulationServiceRay.submit_variant_cache_job``). Ray/Batch
            backend only; the source dataset must already have SUCCEEDED (not
            re-validated here, same pure-passthrough philosophy as
            ``NewGeneCacheRequest``).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, VariantCacheJob]]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    body: VariantCacheRequest,
) -> Optional[Union[HTTPValidationError, VariantCacheJob]]:
    """Stamp native-gene perturbations onto a completed ParCa dataset's cache (backlog item 451)

    Args:
        body (VariantCacheRequest): Backlog item 451: stamp NATIVE-gene translation-efficiency
            perturbations
            onto a COMPLETED ParCa dataset's cache (``scripts/build_variant_cache.py``,
            the sibling mechanism to ``NewGeneCacheRequest`` above -- native-gene
            knockouts/knockdowns/overexpression instead of a new gene's own induction
            level -- see ``SimulationServiceRay.submit_variant_cache_job``). Ray/Batch
            backend only; the source dataset must already have SUCCEEDED (not
            re-validated here, same pure-passthrough philosophy as
            ``NewGeneCacheRequest``).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, VariantCacheJob]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
