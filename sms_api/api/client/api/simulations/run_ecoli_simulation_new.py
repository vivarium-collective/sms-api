from http import HTTPStatus
from typing import Any, Optional, Union, cast

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.simulation import Simulation
from ...types import UNSET, Unset
from typing import cast
from typing import cast, Union
from typing import Union


def _get_kwargs(
    *,
    simulator_id: int,
    experiment_id: str,
    simulation_config_filename: str,
    num_generations: Union[None, Unset, int] = UNSET,
    num_seeds: Union[None, Unset, int] = UNSET,
    description: Union[None, Unset, str] = UNSET,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["simulator_id"] = simulator_id

    params["experiment_id"] = experiment_id

    params["simulation_config_filename"] = simulation_config_filename

    json_num_generations: Union[None, Unset, int]
    if isinstance(num_generations, Unset):
        json_num_generations = UNSET
    else:
        json_num_generations = num_generations
    params["num_generations"] = json_num_generations

    json_num_seeds: Union[None, Unset, int]
    if isinstance(num_seeds, Unset):
        json_num_seeds = UNSET
    else:
        json_num_seeds = num_seeds
    params["num_seeds"] = json_num_seeds

    json_description: Union[None, Unset, str]
    if isinstance(description, Unset):
        json_description = UNSET
    else:
        json_description = description
    params["description"] = json_description

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/v1/simulations-new",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[HTTPValidationError, Simulation]]:
    if response.status_code == 200:
        response_200 = Simulation.from_dict(response.json())

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
) -> Response[Union[HTTPValidationError, Simulation]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    simulator_id: int,
    experiment_id: str,
    simulation_config_filename: str,
    num_generations: Union[None, Unset, int] = UNSET,
    num_seeds: Union[None, Unset, int] = UNSET,
    description: Union[None, Unset, str] = UNSET,
) -> Response[Union[HTTPValidationError, Simulation]]:
    """[New] Launches a vEcoli simulation workflow with simple parameters

     Run a vEcoli simulation workflow with simplified parameters.

    This endpoint reads the workflow configuration from the vEcoli repo on the HPC
    system and allows overriding specific parameters via query params.

    Args:
        simulator_id (int): Database ID of the simulator to use
        experiment_id (str): Unique experiment identifier
        simulation_config_filename (str): Config filename in vEcoli/configs/ on HPC
        num_generations (Union[None, Unset, int]): Number of generations to simulate
        num_seeds (Union[None, Unset, int]): Number of initial seeds (lineages)
        description (Union[None, Unset, str]): Description of the simulation

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, Simulation]]
    """

    kwargs = _get_kwargs(
        simulator_id=simulator_id,
        experiment_id=experiment_id,
        simulation_config_filename=simulation_config_filename,
        num_generations=num_generations,
        num_seeds=num_seeds,
        description=description,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: Union[AuthenticatedClient, Client],
    simulator_id: int,
    experiment_id: str,
    simulation_config_filename: str,
    num_generations: Union[None, Unset, int] = UNSET,
    num_seeds: Union[None, Unset, int] = UNSET,
    description: Union[None, Unset, str] = UNSET,
) -> Optional[Union[HTTPValidationError, Simulation]]:
    """[New] Launches a vEcoli simulation workflow with simple parameters

     Run a vEcoli simulation workflow with simplified parameters.

    This endpoint reads the workflow configuration from the vEcoli repo on the HPC
    system and allows overriding specific parameters via query params.

    Args:
        simulator_id (int): Database ID of the simulator to use
        experiment_id (str): Unique experiment identifier
        simulation_config_filename (str): Config filename in vEcoli/configs/ on HPC
        num_generations (Union[None, Unset, int]): Number of generations to simulate
        num_seeds (Union[None, Unset, int]): Number of initial seeds (lineages)
        description (Union[None, Unset, str]): Description of the simulation

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, Simulation]
    """

    return sync_detailed(
        client=client,
        simulator_id=simulator_id,
        experiment_id=experiment_id,
        simulation_config_filename=simulation_config_filename,
        num_generations=num_generations,
        num_seeds=num_seeds,
        description=description,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    simulator_id: int,
    experiment_id: str,
    simulation_config_filename: str,
    num_generations: Union[None, Unset, int] = UNSET,
    num_seeds: Union[None, Unset, int] = UNSET,
    description: Union[None, Unset, str] = UNSET,
) -> Response[Union[HTTPValidationError, Simulation]]:
    """[New] Launches a vEcoli simulation workflow with simple parameters

     Run a vEcoli simulation workflow with simplified parameters.

    This endpoint reads the workflow configuration from the vEcoli repo on the HPC
    system and allows overriding specific parameters via query params.

    Args:
        simulator_id (int): Database ID of the simulator to use
        experiment_id (str): Unique experiment identifier
        simulation_config_filename (str): Config filename in vEcoli/configs/ on HPC
        num_generations (Union[None, Unset, int]): Number of generations to simulate
        num_seeds (Union[None, Unset, int]): Number of initial seeds (lineages)
        description (Union[None, Unset, str]): Description of the simulation

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, Simulation]]
    """

    kwargs = _get_kwargs(
        simulator_id=simulator_id,
        experiment_id=experiment_id,
        simulation_config_filename=simulation_config_filename,
        num_generations=num_generations,
        num_seeds=num_seeds,
        description=description,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    simulator_id: int,
    experiment_id: str,
    simulation_config_filename: str,
    num_generations: Union[None, Unset, int] = UNSET,
    num_seeds: Union[None, Unset, int] = UNSET,
    description: Union[None, Unset, str] = UNSET,
) -> Optional[Union[HTTPValidationError, Simulation]]:
    """[New] Launches a vEcoli simulation workflow with simple parameters

     Run a vEcoli simulation workflow with simplified parameters.

    This endpoint reads the workflow configuration from the vEcoli repo on the HPC
    system and allows overriding specific parameters via query params.

    Args:
        simulator_id (int): Database ID of the simulator to use
        experiment_id (str): Unique experiment identifier
        simulation_config_filename (str): Config filename in vEcoli/configs/ on HPC
        num_generations (Union[None, Unset, int]): Number of generations to simulate
        num_seeds (Union[None, Unset, int]): Number of initial seeds (lineages)
        description (Union[None, Unset, str]): Description of the simulation

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, Simulation]
    """

    return (
        await asyncio_detailed(
            client=client,
            simulator_id=simulator_id,
            experiment_id=experiment_id,
            simulation_config_filename=simulation_config_filename,
            num_generations=num_generations,
            num_seeds=num_seeds,
            description=description,
        )
    ).parsed
