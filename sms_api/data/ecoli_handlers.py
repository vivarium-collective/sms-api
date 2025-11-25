import asyncio
import logging
from types import ModuleType
from typing import Generator, Any

from fastapi import BackgroundTasks

from sms_api.common.ssh.ssh_service import SSHService, SSHServiceManaged
from sms_api.common.utils import unique_id
from sms_api.config import Settings, get_settings
from sms_api.data.analysis_service import (
    AnalysisService,
    get_html_outputs_local,
)
from sms_api.data.load_outputs import load_seed
from sms_api.data.models import (
    AnalysisRun,
    ExperimentAnalysisDTO,
    ExperimentAnalysisRequest,
    JobStatus,
    OutputFile,
    OutputFileMetadata,
    TsvOutputFile,
    TsvOutputFileRequest, SimulationOutputData,
)
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.models import SimulatorVersion


async def run_analysis(
    request: ExperimentAnalysisRequest,
    simulator: SimulatorVersion,
    analysis_service: AnalysisService,
    logger: logging.Logger,
    db_service: DatabaseService,
    timestamp: str,
    ssh_service: SSHServiceManaged,
) -> list[OutputFileMetadata | TsvOutputFile]:
    # dispatch and process analysis run
    analysis_name = unique_id(scope="sms_analysis")
    config = request.to_config(analysis_name=analysis_name)
    slurmjob_name, slurmjob_id = await analysis_service.dispatch(
        config=config,
        analysis_name=analysis_name,
        simulator_hash=simulator.git_commit_hash,
        logger=logger,
        ssh=ssh_service,
    )
    analysis_record = await db_service.insert_analysis(
        name=analysis_name,
        config=config,
        last_updated=timestamp,
        job_name=slurmjob_name,
        job_id=slurmjob_id,
    )

    # status check
    await asyncio.sleep(3)

    run = await get_analysis_status(
        db_service=db_service,
        ssh_service=ssh_service,
        id=analysis_record.database_id,
    )
    while run.status.lower() not in ["completed", "failed"]:
        await asyncio.sleep(3)
        run = await get_analysis_status(db_service=db_service, ssh_service=ssh_service, id=analysis_record.database_id)
    if run.status.lower() == "failed":
        raise Exception(f"Analysis Run has failed:\n{run}")

    # fetch requested outputs
    requested_outputs = []
    analysis_types = ["single", "multiseed", "multigeneration", "multivariant", "multiexperiment"]
    for analysis_type in analysis_types:
        analyses = getattr(request, analysis_type, None)
        if analyses is not None:
            for analysis in analyses:
                analysis_name = analysis.name
                if "multigeneration" in analysis_name:
                    analysis_name = analysis_name.replace("multigeneration", "multigen")
                fname = f"{analysis_name}_{analysis_type}"
                fname += ".txt" if "ptools" in analysis_name else ".html"
                metadata_kwargs: dict[str, str | int] = {}
                for param in ["variant", "lineage_seed", "agent_id", "generation"]:
                    kwarg_val = getattr(analysis, param, None)
                    if kwarg_val is not None:
                        metadata_kwargs[param] = kwarg_val
                metadata_kwargs["filename"] = fname
                files = [OutputFileMetadata(**metadata_kwargs)]  # type: ignore[arg-type]
                for file_spec in files:
                    output = await get_tsv_output(
                        request=TsvOutputFileRequest(**file_spec.model_dump()),
                        db_service=db_service,
                        id=analysis_record.database_id,
                        ssh=ssh_service,
                    )
                    requested_outputs.append(output)

    return requested_outputs  # type: ignore[return-value]


async def get_analysis(db_service: DatabaseService, id: int) -> ExperimentAnalysisDTO:
    return await db_service.get_analysis(database_id=id)


async def list_analyses(db_service: DatabaseService) -> list[ExperimentAnalysisDTO]:
    return await db_service.list_analyses()


async def get_ptools_manifest(
    db_service: DatabaseService, env: Settings, ssh_service: SSHService, id: int, analysis_service: ModuleType
) -> list[TsvOutputFile]:
    analysis_data = await db_service.get_analysis(database_id=id)
    output_id = analysis_data.name
    return await analysis_service.get_tsv_manifest_local(output_id=output_id, ssh_service=ssh_service)  # type: ignore[no-any-return]


async def get_tsv_output(
    request: TsvOutputFileRequest,
    db_service: DatabaseService,
    id: int,
    ssh: SSHServiceManaged,
) -> TsvOutputFile:
    variant_id = request.variant
    lineage_seed_id = request.lineage_seed
    generation_id = request.generation
    agent_id = request.agent_id
    filename = request.filename
    analysis_data = await db_service.get_analysis(database_id=id)
    output_id = analysis_data.name
    fp = (
        get_settings().simulation_outdir
        / output_id
        / f"experiment_id={analysis_data.config.analysis_options.experiment_id[0]}"
    )
    if variant_id is not None:
        fp = fp / f"variant={variant_id}"
    if lineage_seed_id is not None:
        fp = fp / f"lineage_seed={lineage_seed_id}"
    if generation_id is not None:
        fp = fp / f"generation={generation_id}"
    if agent_id is not None:
        fp = fp / f"agent_id={agent_id}"

    filepath = fp / filename

    _, stdout, stderr = await ssh.run_command(f"cat {filepath!s}")
    return TsvOutputFile(
        filename=filename,
        variant=variant_id,
        lineage_seed=lineage_seed_id,
        generation=generation_id,
        agent_id=agent_id,
        content=stdout,
    )


async def get_analysis_status(db_service: DatabaseService, ssh_service: SSHServiceManaged, id: int) -> AnalysisRun:
    analysis_record = await db_service.get_analysis(database_id=id)
    slurmjob_id = analysis_record.job_id
    # slurmjob_id = get_jobid_by_experiment(experiment_id)
    # ssh_service = get_ssh_service()
    slurm_user = get_settings().slurm_submit_user
    statuses = await ssh_service.run_command(f"sacct -u {slurm_user} | grep {slurmjob_id}")
    status: str = statuses[1].split("\n")[0].split()[-2]
    return AnalysisRun(id=id, status=JobStatus[status])


async def get_analysis_log(db_service: DatabaseService, id: int, ssh_service: SSHService) -> str:
    analysis_record = await db_service.get_analysis(database_id=id)
    slurm_logfile = get_settings().slurm_log_base_path / f"{analysis_record.job_name}.out"
    ret, stdout, stdin = await ssh_service.run_command(f"cat {slurm_logfile!s}")
    return stdout


async def get_analysis_plots(db_service: DatabaseService, id: int, ssh_service: SSHServiceManaged) -> list[OutputFile]:
    analysis_data = await db_service.get_analysis(database_id=id)
    output_id = analysis_data.name
    return await get_html_outputs_local(output_id=output_id, ssh_service=ssh_service)


async def get_simulation_data(
    ssh: SSHService,
    db_service: DatabaseService,
    id: int,
    lineage_seed: int,
    # generation: int,
    variant: int,
    # agent_id: int,
    # observables: list[str],
    bg_tasks: BackgroundTasks,
    # sim_id: str
) -> SimulationOutputData:
    # simulation = await db_service.get_ecoli_simulation(database_id=id)
    # experiment_id = simulation.config.experiment_id
    # sim_id = simulation.name
    env = get_settings()
    outdir_root = env.simulation_outdir.remote_path
    experiment_id = "wcecoli_fig2_setD4_scaled-c6263425684df8c0_1763578699104-449b7de3d0de10a5_1763578788396"
    sim_id = "wcecoli_figure2_setD4"
    data = await load_seed(
        outdir_root=outdir_root,
        expid=experiment_id,
        seed=lineage_seed,
        sim_name=sim_id,
        variant=variant,
        ssh=ssh
    )
    data['experiment_id'] = experiment_id

    return SimulationOutputData(**data)


async def test_load_seed():
    env = get_settings()
    outdir_root = env.simulation_outdir.remote_path
    expid = "wcecoli_fig2_setD4_scaled-c6263425684df8c0_1763578699104-449b7de3d0de10a5_1763578788396"
    sim_id = "wcecoli_figure2_setD4"
    seed = 3
    variant = 0
    data = await load_seed(
        outdir_root=outdir_root,
        expid=expid,
        seed=seed,
        sim_name=sim_id,
        variant=variant
    )
    print(data)