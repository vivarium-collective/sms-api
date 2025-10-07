import logging
import mimetypes
import tempfile
from pathlib import Path
from types import ModuleType

from fastapi import UploadFile

from sms_api.common.ssh.ssh_service import SSHService
from sms_api.config import Settings
from sms_api.data.models import (
    AnalysisRun,
    ExperimentAnalysisDTO,
    ExperimentAnalysisRequest,
    JobStatus,
    OutputFile,
    TsvOutputFile,
    TsvOutputFileRequest,
)
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.models import SimulatorVersion


async def run_analysis(
    request: ExperimentAnalysisRequest,
    simulator: SimulatorVersion,
    analysis_service: ModuleType,
    env: Settings,
    logger: logging.Logger,
    db_service: DatabaseService,
    timestamp: str,
) -> ExperimentAnalysisDTO:
    config = request.to_config()
    slurmjob_name, slurmjob_id = await analysis_service.dispatch(
        config=config,
        analysis_name=request.analysis_name,
        simulator_hash=simulator.git_commit_hash,
        env=env,
        logger=logger,
    )
    analysis_record = await db_service.insert_analysis(
        name=request.analysis_name,
        config=config,
        last_updated=timestamp,
        job_name=slurmjob_name,
        job_id=slurmjob_id,
    )
    return analysis_record


async def get_analysis(db_service: DatabaseService, id: int) -> ExperimentAnalysisDTO:
    return await db_service.get_analysis(database_id=id)


async def list_analyses(db_service: DatabaseService) -> list[ExperimentAnalysisDTO]:
    return await db_service.list_analyses()


async def get_ptools_manifest(
    db_service: DatabaseService, env: Settings, ssh_service: SSHService, id: int, analysis_service: ModuleType
) -> list[TsvOutputFile]:
    analysis_data = await db_service.get_analysis(database_id=id)
    output_id = analysis_data.name
    if int(env.dev_mode):
        return await analysis_service.get_tsv_manifest_local(output_id=output_id, ssh_service=ssh_service)  # type: ignore[no-any-return]
    else:
        return analysis_service.get_tsv_manifest_remote(output_id)  # type: ignore[no-any-return]


async def get_tsv_output(
    request: TsvOutputFileRequest,
    db_service: DatabaseService,
    id: int,
    env: Settings,
    ssh: SSHService,
    analysis_service: ModuleType,
) -> TsvOutputFile:
    variant_id = request.variant
    lineage_seed_id = request.lineage_seed
    generation_id = request.generation
    agent_id = request.agent_id
    filename = request.filename
    analysis_data = await db_service.get_analysis(database_id=id)
    output_id = analysis_data.name
    fp = (
        Path(env.simulation_outdir)
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
    mimetype, _ = mimetypes.guess_type(filepath)

    if int(env.dev_mode):
        _, stdout, stderr = await ssh.run_command(f"cat {filepath!s}")
        return TsvOutputFile(
            filename=filename,
            variant=variant_id,
            lineage_seed=lineage_seed_id,
            generation=generation_id,
            agent_id=agent_id,
            content=stdout,
        )

    return TsvOutputFile(
        filename=filename,
        variant=variant_id,
        lineage_seed=lineage_seed_id,
        generation=generation_id,
        agent_id=agent_id,
        content=analysis_service.read_tsv_file(filepath),
    )


async def get_analysis_status(
    db_service: DatabaseService, ssh_service: SSHService, id: int, env: Settings
) -> AnalysisRun:
    analysis_record = await db_service.get_analysis(database_id=id)
    slurmjob_id = analysis_record.job_id
    # slurmjob_id = get_jobid_by_experiment(experiment_id)
    # ssh_service = get_ssh_service()
    slurm_user = env.slurm_submit_user
    statuses = await ssh_service.run_command(f"sacct -u {slurm_user} | grep {slurmjob_id}")
    status: str = statuses[1].split("\n")[0].split()[-2]
    return AnalysisRun(id=id, status=JobStatus[status])


async def get_analysis_log(db_service: DatabaseService, id: int, env: Settings, ssh_service: SSHService) -> str:
    analysis_record = await db_service.get_analysis(database_id=id)
    slurm_logfile = Path(env.slurm_log_base_path) / f"{analysis_record.job_name}.out"
    ret, stdout, stdin = await ssh_service.run_command(f"cat {slurm_logfile!s}")
    return stdout


async def get_analysis_plots(
    db_service: DatabaseService, id: int, env: Settings, analysis_service: ModuleType, ssh_service: SSHService
) -> list[OutputFile]:
    analysis_data = await db_service.get_analysis(database_id=id)
    output_id = analysis_data.name
    if int(env.dev_mode):
        return await analysis_service.get_html_outputs_local(output_id=output_id, ssh_service=ssh_service)  # type: ignore[no-any-return]
    else:
        return analysis_service.get_html_outputs_remote(output_id=output_id)  # type: ignore[no-any-return]


async def upload_analysis_module(
    file: UploadFile, ssh: SSHService, submodule_name: str, env: Settings
) -> dict[str, object]:
    contents = await file.read()
    with tempfile.TemporaryDirectory() as tmpdirname:
        tmp_path: Path = Path(tmpdirname) / (file.filename or str(file))
        with open(tmp_path, "wb") as tmpfile:
            tmpfile.write(contents)

        result = {"tmp_path": str(tmp_path), "size": len(contents)}

        local = tmp_path
        remote = Path(env.vecoli_config_dir).parent / "ecoli" / "analysis" / submodule_name / file.filename  # type: ignore[operator]
        # ssh = get_ssh_service(ENV)
        await ssh.scp_upload(local_file=local, remote_path=remote)
        return result
