import asyncio
import logging
from pathlib import Path
from types import ModuleType

from sms_api.common.ssh.ssh_service import SSHService, SSHServiceManaged
from sms_api.common.storage.file_paths import HPCFilePath
from sms_api.common.utils import get_data_id
from sms_api.config import REPO_ROOT, Settings, get_settings
from sms_api.data.analysis_utils import get_html_outputs_local
from sms_api.data.sim_analysis_service import AnalysisServiceHpc
from sms_api.data.models import (
    AnalysisRun,
    ExperimentAnalysisDTO,
    ExperimentAnalysisRequest,
    JobStatus,
    OutputFile,
    OutputFileMetadata,
    TsvOutputFile,
    TsvOutputFileRequest,
)
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.models import SimulatorVersion


async def run_analysis(
    request: ExperimentAnalysisRequest,
    simulator: SimulatorVersion,
    analysis_service: AnalysisServiceHpc,
    logger: logging.Logger,
    db_service: DatabaseService,
    timestamp: str,
) -> list[OutputFileMetadata | TsvOutputFile]:
    """
    TODO: first check if its in the db: if not, then do the dispatch/insert/poll workflow,
       otherwise, skip to the download section
    """
    # 0. TODO: first check if analysis with same analysis options specs exist in db. If so,
    #       SKIP directly to reading from cache

    # 1. -- collect params --
    analysis_name = get_data_id(exp_id=request.experiment_id, scope="analysis")
    config = request.to_config(analysis_name=analysis_name, env=analysis_service.env)

    # 2. -- dispatch slurm job --
    slurmjob_name, slurmjob_id = await analysis_service.dispatch_analysis(
        request=request,
        logger=logger,
        simulator_hash=simulator.git_commit_hash,
        analysis_name=analysis_name
    )

    # 3. -- insert analysis to db --
    analysis_record = await db_service.insert_analysis(
        name=analysis_name,
        config=config,
        last_updated=timestamp,
        job_name=slurmjob_name,
        job_id=slurmjob_id,
    )

    # 4. -- status poll --
    await asyncio.sleep(3)
    run = await get_analysis_status(
        db_service=db_service,
        ssh_service=analysis_service.ssh,
        id=analysis_record.database_id,
    )
    while run.status.lower() not in ["completed", "failed"]:
        await asyncio.sleep(3)
        # run = await get_analysis_status(
        #   db_service=db_service,
        #   ssh_service=analysis_service.ssh,
        #   id=analysis_record.database_id)

        run = await analysis_service.get_analysis_status(
            slurmjob_id=slurmjob_id,
            analysis_db_id=analysis_record.database_id
        )
    if run.status.lower() == "failed":
        raise Exception(f"Analysis Run has failed:\n{run}")

    # 5. -- fetch requested outputs --
    # 5a. recurse outdir for available paths
    available_paths: list[HPCFilePath] = await analysis_service.available_output_filepaths(analysis_name)

    results = []
    for path in available_paths:
        # 5b. check if path is relevant to request
        # 5c1. if it is relevant, check if exists in cache...
        # 5c2. if it isnt in the cache, check in cold store. If in cold store,
        #   parse dto from cold store and background task cp to cache
        # 5c3. if it is in the cache, parse dto from cache and background task cp from cache to cold store
        # 6. parse dto as per 5c3 by using the request (analysis name, exp id, etc)...
        #   along with the path filename to decipher dto name attr
        # 7. append dto to results
        pass

    # requested_outputs = []
    # analysis_types = ["single", "multiseed", "multigeneration", "multivariant", "multiexperiment"]
    # for analysis_type in analysis_types:
    #     analyses = getattr(request, analysis_type, None)
    #     if analyses is not None:
    #         for analysis in analyses:
    #             analysis_name = analysis.name
    #             if "multigeneration" in analysis_name:
    #                 analysis_name = analysis_name.replace("multigeneration", "multigen")
    #             fname = f"{analysis_name}_{analysis_type}"
    #             fname += ".txt" if "ptools" in analysis_name else ".html"
    #             metadata_kwargs: dict[str, str | int] = {}
    #             for param in ["variant", "lineage_seed", "agent_id", "generation"]:
    #                 kwarg_val = getattr(analysis, param, None)
    #                 if kwarg_val is not None:
    #                     metadata_kwargs[param] = kwarg_val
    #             metadata_kwargs["filename"] = fname
    #             files = [OutputFileMetadata(**metadata_kwargs)]  # type: ignore[arg-type]
    #             for file_spec in files:
    #                 output = await get_tsv_output(
    #                     request=TsvOutputFileRequest(**file_spec.model_dump()),
    #                     db_service=db_service,
    #                     id=analysis_record.database_id,
    #                     ssh=analysis_service.ssh,
    #                 )
    #                 requested_outputs.append(output)

    # 8. -- return results --
    return results


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
    if not ssh.connected:
        await ssh.connect()

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

    filepath: HPCFilePath = fp / filename

    # tmpdir = "/tmp"
    cache_dir = f"{REPO_ROOT}/.results_cache"
    local = Path(cache_dir) / filename
    if not local.exists():
        print(f"{local!s} does not yet exist!")
        if not ssh.connected:
            await ssh.connect()
        try:
            await ssh.scp_download(local_file=local, remote_path=filepath)
        except Exception:
            print(f"There was an issue downloading {filepath!s} to {local!s}")

    file_content = local.read_text()
    return TsvOutputFile(
        filename=filename,
        variant=variant_id,
        lineage_seed=lineage_seed_id,
        generation=generation_id,
        agent_id=agent_id,
        content=file_content,
    )


async def get_analysis_status(db_service: DatabaseService, ssh_service: SSHServiceManaged, id: int) -> AnalysisRun:
    analysis_record = await db_service.get_analysis(database_id=id)
    slurmjob_id = analysis_record.job_id
    # slurmjob_id = get_jobid_by_experiment(experiment_id)
    # ssh_service = get_ssh_service()
    slurm_user = get_settings().slurm_submit_user
    if not ssh_service.connected:
        await ssh_service.connect()
    try:
        statuses = await ssh_service.run_command(f"sacct -u {slurm_user} | grep {slurmjob_id}")
    except Exception:
        statuses = await ssh_service.run_command(f"sacct -j {slurmjob_id}")
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
