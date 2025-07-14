from http import HTTPStatus
from typing import Any, Optional, Union, cast

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

<<<<<<<< HEAD:sms_api/api/client/api/simulations_parca/get_parca_status.py
from ...models.hpc_run import HpcRun
from ...models.http_validation_error import HTTPValidationError
========
from ...models.ecoli_simulation import EcoliSimulation
>>>>>>>> 13d96f4 (cherry picked jims changes):sms_api/api/client/api/simulations_v_ecoli/get_simulation_versions.py
from typing import cast



def _get_kwargs(
<<<<<<<< HEAD:sms_api/api/client/api/simulations_parca/get_parca_status.py
    *,
    parca_id: int,
========
>>>>>>>> 13d96f4 (cherry picked jims changes):sms_api/api/client/api/simulations_v_ecoli/get_simulation_versions.py

) -> dict[str, Any]:




    params: dict[str, Any] = {}

    params["parca_id"] = parca_id


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
<<<<<<<< HEAD:sms_api/api/client/api/simulations_parca/get_parca_status.py
        "url": "/core/simulation/parca/status",
        "params": params,
========
        "url": "/core/simulation/run/versions",
>>>>>>>> 13d96f4 (cherry picked jims changes):sms_api/api/client/api/simulations_v_ecoli/get_simulation_versions.py
    }


    return _kwargs


<<<<<<<< HEAD:sms_api/api/client/api/simulations_parca/get_parca_status.py
def _parse_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> Optional[Union[HTTPValidationError, HpcRun]]:
    if response.status_code == 200:
        response_200 = HpcRun.from_dict(response.json())
========
def _parse_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> Optional[list['EcoliSimulation']]:
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in (_response_200):
            response_200_item = EcoliSimulation.from_dict(response_200_item_data)
>>>>>>>> 13d96f4 (cherry picked jims changes):sms_api/api/client/api/simulations_v_ecoli/get_simulation_versions.py



            response_200.append(response_200_item)

        return response_200
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


<<<<<<<< HEAD:sms_api/api/client/api/simulations_parca/get_parca_status.py
def _build_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> Response[Union[HTTPValidationError, HpcRun]]:
========
def _build_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> Response[list['EcoliSimulation']]:
>>>>>>>> 13d96f4 (cherry picked jims changes):sms_api/api/client/api/simulations_v_ecoli/get_simulation_versions.py
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
<<<<<<<< HEAD:sms_api/api/client/api/simulations_parca/get_parca_status.py
    parca_id: int,

) -> Response[Union[HTTPValidationError, HpcRun]]:
    """ Get parca calculation status by its ID

    Args:
        parca_id (int):
========

) -> Response[list['EcoliSimulation']]:
    """ Get list of vEcoli simulations
>>>>>>>> 13d96f4 (cherry picked jims changes):sms_api/api/client/api/simulations_v_ecoli/get_simulation_versions.py

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
<<<<<<<< HEAD:sms_api/api/client/api/simulations_parca/get_parca_status.py
        Response[Union[HTTPValidationError, HpcRun]]
========
        Response[list['EcoliSimulation']]
>>>>>>>> 13d96f4 (cherry picked jims changes):sms_api/api/client/api/simulations_v_ecoli/get_simulation_versions.py
     """


    kwargs = _get_kwargs(
<<<<<<<< HEAD:sms_api/api/client/api/simulations_parca/get_parca_status.py
        parca_id=parca_id,
========
>>>>>>>> 13d96f4 (cherry picked jims changes):sms_api/api/client/api/simulations_v_ecoli/get_simulation_versions.py

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    *,
    client: Union[AuthenticatedClient, Client],
<<<<<<<< HEAD:sms_api/api/client/api/simulations_parca/get_parca_status.py
    parca_id: int,

) -> Optional[Union[HTTPValidationError, HpcRun]]:
    """ Get parca calculation status by its ID

    Args:
        parca_id (int):
========

) -> Optional[list['EcoliSimulation']]:
    """ Get list of vEcoli simulations
>>>>>>>> 13d96f4 (cherry picked jims changes):sms_api/api/client/api/simulations_v_ecoli/get_simulation_versions.py

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
<<<<<<<< HEAD:sms_api/api/client/api/simulations_parca/get_parca_status.py
        Union[HTTPValidationError, HpcRun]
========
        list['EcoliSimulation']
>>>>>>>> 13d96f4 (cherry picked jims changes):sms_api/api/client/api/simulations_v_ecoli/get_simulation_versions.py
     """


    return sync_detailed(
        client=client,
<<<<<<<< HEAD:sms_api/api/client/api/simulations_parca/get_parca_status.py
parca_id=parca_id,
========
>>>>>>>> 13d96f4 (cherry picked jims changes):sms_api/api/client/api/simulations_v_ecoli/get_simulation_versions.py

    ).parsed

async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
<<<<<<<< HEAD:sms_api/api/client/api/simulations_parca/get_parca_status.py
    parca_id: int,

) -> Response[Union[HTTPValidationError, HpcRun]]:
    """ Get parca calculation status by its ID

    Args:
        parca_id (int):
========

) -> Response[list['EcoliSimulation']]:
    """ Get list of vEcoli simulations
>>>>>>>> 13d96f4 (cherry picked jims changes):sms_api/api/client/api/simulations_v_ecoli/get_simulation_versions.py

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
<<<<<<<< HEAD:sms_api/api/client/api/simulations_parca/get_parca_status.py
        Response[Union[HTTPValidationError, HpcRun]]
========
        Response[list['EcoliSimulation']]
>>>>>>>> 13d96f4 (cherry picked jims changes):sms_api/api/client/api/simulations_v_ecoli/get_simulation_versions.py
     """


    kwargs = _get_kwargs(
<<<<<<<< HEAD:sms_api/api/client/api/simulations_parca/get_parca_status.py
        parca_id=parca_id,
========
>>>>>>>> 13d96f4 (cherry picked jims changes):sms_api/api/client/api/simulations_v_ecoli/get_simulation_versions.py

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
<<<<<<<< HEAD:sms_api/api/client/api/simulations_parca/get_parca_status.py
    parca_id: int,

) -> Optional[Union[HTTPValidationError, HpcRun]]:
    """ Get parca calculation status by its ID

    Args:
        parca_id (int):
========

) -> Optional[list['EcoliSimulation']]:
    """ Get list of vEcoli simulations
>>>>>>>> 13d96f4 (cherry picked jims changes):sms_api/api/client/api/simulations_v_ecoli/get_simulation_versions.py

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
<<<<<<<< HEAD:sms_api/api/client/api/simulations_parca/get_parca_status.py
        Union[HTTPValidationError, HpcRun]
========
        list['EcoliSimulation']
>>>>>>>> 13d96f4 (cherry picked jims changes):sms_api/api/client/api/simulations_v_ecoli/get_simulation_versions.py
     """


    return (await asyncio_detailed(
        client=client,
<<<<<<<< HEAD:sms_api/api/client/api/simulations_parca/get_parca_status.py
parca_id=parca_id,
========
>>>>>>>> 13d96f4 (cherry picked jims changes):sms_api/api/client/api/simulations_v_ecoli/get_simulation_versions.py

    )).parsed
