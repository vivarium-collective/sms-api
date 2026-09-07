from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.simulator import Simulator
from ...models.simulator_version import SimulatorVersion
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    body: Simulator,
    force: Union[Unset, bool] = False,
    include_submit_image: Union[None, Unset, bool] = UNSET,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    params: dict[str, Any] = {}

    params["force"] = force

    json_include_submit_image: Union[None, Unset, bool]
    if isinstance(include_submit_image, Unset):
        json_include_submit_image = UNSET
    else:
        json_include_submit_image = include_submit_image
    params["include_submit_image"] = json_include_submit_image

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/core/v1/simulator/upload",
        "params": params,
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[HTTPValidationError, SimulatorVersion]]:
    if response.status_code == 200:
        response_200 = SimulatorVersion.from_dict(response.json())

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
) -> Response[Union[HTTPValidationError, SimulatorVersion]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: Simulator,
    force: Union[Unset, bool] = False,
    include_submit_image: Union[None, Unset, bool] = UNSET,
) -> Response[Union[HTTPValidationError, SimulatorVersion]]:
    r"""Upload a new simulator (vEcoli) version.

     ``include_submit_image``: also build the Nextflow HEAD image beside the task
    image (base + JRE + the nextflow binary, pushed as ``<repo>:<sha>-submit``).

    Only the process that runs ``nextflow run`` needs a JVM -- Batch TASKS run the
    plain science image, which already carries the AWS CLI Nextflow needs to stage
    an S3 work dir. So this is a thin derived layer.

    **Omitted now means \"build it where possible\"**, changed once the Nextflow path
    became operational. It was off on the reasoning that \"every build would otherwise
    pay for it\"; measured across four builds that cost is **+72 MB and +15 s** (ECR
    dedups the ~5.7 GB base the two images share), against a dispatch that otherwise
    fails at the container image pull plus a full rebuild. vEcoli's build path has
    always built its own ``-submit`` image unconditionally, so this makes the paths agree.

    Three-valued: ``true`` DEMANDS the image and 400s on a backend that cannot build
    one; omitted builds it where the backend can and skips quietly where it cannot;
    ``false`` skips it.

    Args:
        force (Union[Unset, bool]):  Default: False.
        include_submit_image (Union[None, Unset, bool]):
        body (Simulator):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, SimulatorVersion]]
    """

    kwargs = _get_kwargs(
        body=body,
        force=force,
        include_submit_image=include_submit_image,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: Union[AuthenticatedClient, Client],
    body: Simulator,
    force: Union[Unset, bool] = False,
    include_submit_image: Union[None, Unset, bool] = UNSET,
) -> Optional[Union[HTTPValidationError, SimulatorVersion]]:
    r"""Upload a new simulator (vEcoli) version.

     ``include_submit_image``: also build the Nextflow HEAD image beside the task
    image (base + JRE + the nextflow binary, pushed as ``<repo>:<sha>-submit``).

    Only the process that runs ``nextflow run`` needs a JVM -- Batch TASKS run the
    plain science image, which already carries the AWS CLI Nextflow needs to stage
    an S3 work dir. So this is a thin derived layer.

    **Omitted now means \"build it where possible\"**, changed once the Nextflow path
    became operational. It was off on the reasoning that \"every build would otherwise
    pay for it\"; measured across four builds that cost is **+72 MB and +15 s** (ECR
    dedups the ~5.7 GB base the two images share), against a dispatch that otherwise
    fails at the container image pull plus a full rebuild. vEcoli's build path has
    always built its own ``-submit`` image unconditionally, so this makes the paths agree.

    Three-valued: ``true`` DEMANDS the image and 400s on a backend that cannot build
    one; omitted builds it where the backend can and skips quietly where it cannot;
    ``false`` skips it.

    Args:
        force (Union[Unset, bool]):  Default: False.
        include_submit_image (Union[None, Unset, bool]):
        body (Simulator):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, SimulatorVersion]
    """

    return sync_detailed(
        client=client,
        body=body,
        force=force,
        include_submit_image=include_submit_image,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    body: Simulator,
    force: Union[Unset, bool] = False,
    include_submit_image: Union[None, Unset, bool] = UNSET,
) -> Response[Union[HTTPValidationError, SimulatorVersion]]:
    r"""Upload a new simulator (vEcoli) version.

     ``include_submit_image``: also build the Nextflow HEAD image beside the task
    image (base + JRE + the nextflow binary, pushed as ``<repo>:<sha>-submit``).

    Only the process that runs ``nextflow run`` needs a JVM -- Batch TASKS run the
    plain science image, which already carries the AWS CLI Nextflow needs to stage
    an S3 work dir. So this is a thin derived layer.

    **Omitted now means \"build it where possible\"**, changed once the Nextflow path
    became operational. It was off on the reasoning that \"every build would otherwise
    pay for it\"; measured across four builds that cost is **+72 MB and +15 s** (ECR
    dedups the ~5.7 GB base the two images share), against a dispatch that otherwise
    fails at the container image pull plus a full rebuild. vEcoli's build path has
    always built its own ``-submit`` image unconditionally, so this makes the paths agree.

    Three-valued: ``true`` DEMANDS the image and 400s on a backend that cannot build
    one; omitted builds it where the backend can and skips quietly where it cannot;
    ``false`` skips it.

    Args:
        force (Union[Unset, bool]):  Default: False.
        include_submit_image (Union[None, Unset, bool]):
        body (Simulator):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, SimulatorVersion]]
    """

    kwargs = _get_kwargs(
        body=body,
        force=force,
        include_submit_image=include_submit_image,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    body: Simulator,
    force: Union[Unset, bool] = False,
    include_submit_image: Union[None, Unset, bool] = UNSET,
) -> Optional[Union[HTTPValidationError, SimulatorVersion]]:
    r"""Upload a new simulator (vEcoli) version.

     ``include_submit_image``: also build the Nextflow HEAD image beside the task
    image (base + JRE + the nextflow binary, pushed as ``<repo>:<sha>-submit``).

    Only the process that runs ``nextflow run`` needs a JVM -- Batch TASKS run the
    plain science image, which already carries the AWS CLI Nextflow needs to stage
    an S3 work dir. So this is a thin derived layer.

    **Omitted now means \"build it where possible\"**, changed once the Nextflow path
    became operational. It was off on the reasoning that \"every build would otherwise
    pay for it\"; measured across four builds that cost is **+72 MB and +15 s** (ECR
    dedups the ~5.7 GB base the two images share), against a dispatch that otherwise
    fails at the container image pull plus a full rebuild. vEcoli's build path has
    always built its own ``-submit`` image unconditionally, so this makes the paths agree.

    Three-valued: ``true`` DEMANDS the image and 400s on a backend that cannot build
    one; omitted builds it where the backend can and skips quietly where it cannot;
    ``false`` skips it.

    Args:
        force (Union[Unset, bool]):  Default: False.
        include_submit_image (Union[None, Unset, bool]):
        body (Simulator):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, SimulatorVersion]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
            force=force,
            include_submit_image=include_submit_image,
        )
    ).parsed
