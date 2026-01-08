import asyncio
import datetime
from random import randint

import pytest
from httpx import ASGITransport, AsyncClient

from sms_api.api.main import app
from sms_api.common.ssh.ssh_service import SSHSessionService
from sms_api.config import get_settings
from sms_api.simulation.database_service import DatabaseServiceSQL
from sms_api.simulation.hpc_utils import get_slurmjob_name
from sms_api.simulation.models import ExperimentRequest, Simulation, SimulationConfig
from sms_api.simulation.simulation_service import SimulationServiceHpc


@pytest.mark.asyncio
async def test_list_simulations(
    experiment_request: ExperimentRequest, database_service: DatabaseServiceSQL, ssh_session_service: SSHSessionService
) -> None:
    n = 3
    inserted_sims = []
    for i in range(n):
        name_i = f"pytest_fixture_config_{i}"
        config_i = SimulationConfig(
            experiment_id=name_i,
            sim_data_path="/pytest/kb/simData.cPickle",
            suffix_time=False,
            parca_options={"cpus": 3},
            generations=randint(1, 1000),
            max_duration=10800,
            initial_global_time=0,
            time_step=1,
            single_daughters=True,
            emitter="parquet",
            emitter_arg={"outdir": "/pytest/api_outputs"},
        )
        last_updated_i = str(datetime.datetime.now())
        job_name_i = get_slurmjob_name(experiment_id=name_i)
        job_id_i = randint(10000, 1000000)
        sim_i = await database_service.insert_ecoli_simulation(
            name=name_i,
            config=config_i,
            last_updated=last_updated_i,
            job_name=job_name_i,
            job_id=job_id_i,
            metadata={"requester": f"{name_i}:{i}", "context": "pytest"},
        )
        inserted_sims.append(sim_i.model_dump())
    all_sims = await database_service.list_ecoli_simulations()
    assert len(inserted_sims) == n
    assert len(inserted_sims) == len(all_sims)


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_run_simulation(
    base_router: str,
    experiment_request: ExperimentRequest,
    ecoli_simulation: Simulation,
    database_service: DatabaseServiceSQL,
    simulation_service_slurm: SimulationServiceHpc,
    ssh_session_service: SSHSessionService,
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(f"{base_router}/simulations", json=experiment_request.model_dump())
        response.raise_for_status()
        sim_response = response.json()
        for key in sim_response:
            assert key in list(ecoli_simulation.model_fields)


@pytest.mark.asyncio
async def test_get_simulation(database_service: DatabaseServiceSQL) -> None:
    i = -1
    name_i = "pytest_fixture_config"
    config_i = SimulationConfig(
        experiment_id=name_i,
        sim_data_path="/pytest/kb/simData.cPickle",
        suffix_time=False,
        parca_options={"cpus": 3},
        generations=randint(1, 1000),
        max_duration=10800,
        initial_global_time=0,
        time_step=1,
        single_daughters=True,
        emitter="parquet",
        emitter_arg={"outdir": "/pytest/api_outputs"},
    )
    last_updated_i = str(datetime.datetime.now())
    job_name_i = get_slurmjob_name(experiment_id=name_i)
    job_id_i = randint(10000, 1000000)
    sim_i = await database_service.insert_ecoli_simulation(
        name=name_i,
        config=config_i,
        last_updated=last_updated_i,
        job_name=job_name_i,
        job_id=job_id_i,
        metadata={"requester": f"{name_i}:{i}", "context": "pytest"},
    )

    fetched_i = await database_service.get_ecoli_simulation(database_id=sim_i.database_id)
    assert fetched_i.model_dump() == sim_i.model_dump()


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_get_simulation_status(
    base_router: str,
    experiment_request: ExperimentRequest,
    database_service: DatabaseServiceSQL,
    simulation_service_slurm: SimulationServiceHpc,
    ssh_session_service: SSHSessionService,
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        sim_response = await client.post(f"{base_router}/simulations", json=experiment_request.model_dump())
        sim_response.raise_for_status()
        sim_response = sim_response.json()

        await asyncio.sleep(3)

        status_response = await client.get(f"{base_router}/simulations/{sim_response['database_id']}/status")
        status_response.raise_for_status()
        status_response = status_response.json()
        assert list(status_response.keys()) == ["id", "status"]


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_get_simulation_log(
    base_router: str,
    experiment_request: ExperimentRequest,
    database_service: DatabaseServiceSQL,
    simulation_service_slurm: SimulationServiceHpc,
    ssh_session_service: SSHSessionService,
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        sim_response = await client.post(f"{base_router}/simulations", json=experiment_request.model_dump())
        sim_response.raise_for_status()
        sim_response = sim_response.json()

        await asyncio.sleep(3)

        status_response = await client.post(f"{base_router}/simulations/{sim_response['database_id']}/log")
        status_response.raise_for_status()

        assert isinstance(status_response.text, str)


@pytest.mark.asyncio
async def test_get_metadata() -> None:
    pass


@pytest.mark.asyncio
async def test_get_state_data() -> None:
    pass


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_run_fetch_simulation(
    base_router: str,
    experiment_request: ExperimentRequest,
    database_service: DatabaseServiceSQL,
    simulation_service_slurm: SimulationServiceHpc,
    ssh_session_service: SSHSessionService,
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(f"{base_router}/simulations", json=experiment_request.model_dump())
        response.raise_for_status()
        sim_response = response.json()
        db_id = sim_response["database_id"]

        fetch_response = await client.get(f"{base_router}/simulations/{db_id}")
        fetch_response.raise_for_status()
        assert fetch_response.json() == sim_response


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_fetch_simulation(
    base_router: str,
    experiment_request: ExperimentRequest,
    database_service: DatabaseServiceSQL,
    simulation_service_slurm: SimulationServiceHpc,
    ssh_session_service: SSHSessionService,
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(f"{base_router}/simulations", json=experiment_request.model_dump())
        response.raise_for_status()
        sim_response = response.json()
        db_id = sim_response["database_id"]

        fetch_response = await client.get(f"{base_router}/simulations/{db_id}")
        fetch_response.raise_for_status()
        assert fetch_response.json() == sim_response


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_fetch_simulation_data(
    base_router: str, database_service: DatabaseServiceSQL, ssh_session_service: SSHSessionService
) -> None:
    transport = ASGITransport(app=app)
    df = await fetch_simulation_data(
        base_url="http://testserver",
        base_router=base_router,
        params={"experiment_id": "sms_multigeneration", "lineage_seed": 6, "generation": 1},
        observable_list=["bulk", "listeners__rnap_data__termination_loss"],
        transport=transport,
    )
    print(df)
    print(df.shape)
    assert sorted(df.columns) == sorted(["bulk", "time", "listeners__rnap_data__termination_loss"])
