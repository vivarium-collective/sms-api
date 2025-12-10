import asyncio
import logging
import os
from pathlib import Path
from types import ModuleType
from typing import Any, Literal

from pydantic import BaseModel

from sms_api.common import StrEnumBase
from sms_api.common.ssh.ssh_service import SSHService, SSHServiceManaged
from sms_api.common.storage.file_paths import HPCFilePath
from sms_api.common.utils import unique_id
from sms_api.config import APIFilePath, Settings, get_settings
from sms_api.data.analysis_service import (
    AnalysisService,
    get_html_outputs_local,
)
from sms_api.data.models import (
    AnalysisConfig,
    AnalysisRun,
    ExperimentAnalysisDTO,
    ExperimentAnalysisRequest,
    JobStatus,
    OutputFile,
    OutputFileMetadata,
    PtoolsAnalysisConfig,
    TsvOutputFile,
    TsvOutputFileRequest,
)
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.models import SimulatorVersion

logger = logging.getLogger(__name__)


CACHE_DIR: APIFilePath = APIFilePath(get_settings().cache_dir)
DEFAULT_EXPERIMENT = "sms_multiseed_0-2794dfa74b9cf37c_1759844363435"
DEFAULT_ANALYSIS = "sms_analysis-03ff8218c86170fe_1761645234195"


class PartitionType(StrEnumBase):
    SIMULATION = "simulation"
    ANALYSIS = "analysis"


class PtoolsAnalysisType(StrEnumBase):
    REACTIONS = "ptools_rxns"
    RNA = "ptools_rna"
    PROTEINS = "ptools_proteins"


class PartitionRequest(BaseModel):
    experiment_id: str
    type: Literal[PartitionType.SIMULATION, PartitionType.ANALYSIS]
    variant: int = 0
    lineage_seed: int | None = None
    generation: int | None = None
    agent_id: str | None = None
    name: str | None = None

    def model_post_init(self, context: Any, /) -> None:
        if self.agent_id is not None and "0" not in self.agent_id:
            logger.info(
                f""" \
                The agent id of this instance ({self.agent_id}) does not match the typical pattern
                    found in agent_ids for this simulator. Usually agent ids are "0" for the first
                    generation, then subsequently are "0" * i for the i-th generation.
                """
            )

    @property
    def partitions(self) -> dict[str, str | int | None]:
        data = self.model_dump()
        components = ["lineage_seed", "generation", "agent_id"]
        return dict(zip(components, list(map(lambda c: data.get(c, None), components))))

    def to_dirpath(self, outdir_root: HPCFilePath | Path) -> HPCFilePath | Path:
        """
        :param outdir_root: outdir parent
        :return: HPCFilePath if outdir_root is also HPCFilePath, otherwise the same with Path
        """
        # format for either simulation outdir (no self.name is passed)...
        #   or an analysis outdir (self.name is passed WITH expid)
        identifier = (
            f"/{self.experiment_id}" if self.name is None else f"{self.name}/experiment_id={self.experiment_id}"
        )
        # variant is specified in the path regardless
        identifier += f"/variant={self.variant}"

        # append specified partition components
        for component_name, component_val in self.partitions.items():
            if component_val is not None:
                identifier += f"/{component_name}={component_val}"

        root = outdir_root.remote_path if isinstance(outdir_root, HPCFilePath) else outdir_root
        if isinstance(outdir_root, HPCFilePath):
            return HPCFilePath(remote_path=root / identifier)
        return root / identifier

    @classmethod
    def from_ptools_analysis_request(
        cls, experiment_id: str, config: PtoolsAnalysisConfig, analysis_name: str = DEFAULT_ANALYSIS
    ) -> "PartitionRequest":
        comp_types = ["lineage_seed", "generation", "agent_id"]
        components = dict(zip(comp_types, list(map(lambda ctype: getattr(config, ctype, None), comp_types))))
        return PartitionRequest(
            experiment_id=experiment_id,
            name=analysis_name,
            type=PartitionType.ANALYSIS,
            variant=config.variant,
            **components,
        )


def get_ptools_analysis_request(expid: str = DEFAULT_EXPERIMENT) -> ExperimentAnalysisRequest:
    return ExperimentAnalysisRequest(
        experiment_id=expid, multiseed=[PtoolsAnalysisConfig(name=PtoolsAnalysisType.REACTIONS, n_tp=8, variant=0)]
    )


def get_ptools_analysis_request_config(
    ptools_analysis_request: ExperimentAnalysisRequest, analysis_name: str = DEFAULT_ANALYSIS
) -> AnalysisConfig:
    return ptools_analysis_request.to_config(analysis_name=analysis_name)


async def get_ptools_output(
    ssh: SSHServiceManaged,
    analysis_request: ExperimentAnalysisRequest,
    analysis_request_config: AnalysisConfig,
    filename: str = "ptools_rna_multiseed.txt",
) -> TsvOutputFile:
    """
    Read the contents of a given ptools analysis output TSV file as a formalized ``TsvOutputFile`` DTO.

    NOTE: This function assumes that the fp (on line 191) actually exists.
    It should be called AFTER checking for the presence of the analysis run in the first place.

    :param ssh: (``SSHServiceManaged``) ssh service instance
    :param analysis_request: (``ExperimentAnalysisRequest``) request-specified analysis request payload DTO
    :param analysis_request_config: (``AnalysisConfig``) derived analysis request config
    :param filename: (``str``) which analysis output file to fetch
    :return: ``TSVOutputFile``
    """
    # ptools_modname: str = list(analysis_request_config.analysis_options.multiseed.keys())[0]
    ptools_modname: str = next(iter(list(analysis_request_config.analysis_options.multiseed.keys())))
    config = PtoolsAnalysisConfig(name=ptools_modname, n_tp=8)
    analysis_outdir = analysis_request_config.analysis_options.outdir
    if analysis_outdir is None:
        raise ValueError("Outdir is None, meaning an analysis probably has not been run!")

    analysis_name: str = analysis_outdir.split("/")[-1]
    partition: PartitionRequest = PartitionRequest.from_ptools_analysis_request(
        experiment_id=analysis_request.experiment_id, config=config, analysis_name=analysis_name
    )
    env = get_settings()
    outdir = partition.to_dirpath(env.simulation_outdir)
    if not ssh.connected:
        raise RuntimeError("The SSH service is not connected but needs to be!")
    fp: Path = (outdir.remote_path if isinstance(outdir, HPCFilePath) else outdir) / filename

    # cache dir should be source of file
    remote = HPCFilePath(remote_path=fp)
    local_dir = CACHE_DIR / analysis_name
    if not local_dir.exists():
        os.mkdir(str(local_dir))
    else:
        logger.info(f"A cache already exists for {local_dir!s}")

    local = local_dir / filename

    # save to cache dir if not exists
    if not local.exists():
        logger.info(f"{local!s} not yet in the cache, downloading it now...")
        await ssh.scp_download(local_file=local, remote_path=remote)
    else:
        logger.info(f"File already exists in the cache :): {local!s}")

    # read from cache dir
    content = local.read_text()
    return TsvOutputFile(
        filename=filename,
        variant=partition.variant,
        lineage_seed=partition.lineage_seed,
        generation=partition.generation,
        agent_id=partition.agent_id,
        content=content,
    )


async def find_analysis(exp_id: str, db_service: DatabaseService) -> ExperimentAnalysisDTO | None:
    analyses: list[ExperimentAnalysisDTO] = await db_service.list_analyses()
    try:
        return next(a for a in analyses if a.config.analysis_options.experiment_id[0] == exp_id)
    except StopIteration:
        return None


async def run_new_analysis(
    request: ExperimentAnalysisRequest,
    simulator: SimulatorVersion,
    analysis_service: AnalysisService,
    logger: logging.Logger,
    db_service: DatabaseService,
    timestamp: str,
    ssh_service: SSHServiceManaged,
) -> list[OutputFileMetadata | TsvOutputFile]:
    """
    1. check db for record of analysis

    2.a.1. if #1 exists, then get_analysis(). IF #1 exists, then there is a cached file
    2.a.2. get_filepath()
    2.a.3. download cached file as DTO content

    OR

    2.b.1. if #1 does NOT exist, then dispatch analysis job
    2.b.2. insert analysis to db
    2.b.3. get analysis status (poll)
    2.b.4. download ptools tsv to /tmp (or cache dir)
    2.b.5. download cached file as DTO content
    """
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


async def run_analysis(
    request: ExperimentAnalysisRequest,
    simulator: SimulatorVersion,
    analysis_service: AnalysisService,
    logger: logging.Logger,
    db_service: DatabaseService,
    timestamp: str,
    ssh_service: SSHServiceManaged,
) -> list[OutputFileMetadata | TsvOutputFile]:
    """
    1. check db for record of analysis

    2.a.1. if #1 exists, then get_analysis(). IF #1 exists, then there is a cached file
    2.a.2. get_filepath()
    2.a.3. download cached file as DTO content

    OR

    2.b.1. if #1 does NOT exist, then dispatch analysis job
    2.b.2. insert analysis to db
    2.b.3. get analysis status (poll)
    2.b.4. download ptools tsv to /tmp (or cache dir)
    2.b.5. download cached file as DTO content
    """
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


async def get_tsv_filepath(
    requested_filename: str,
    analysis_data: ExperimentAnalysisDTO,
    variant_id: int | None = None,
    lineage_seed_id: int | None = None,
    generation_id: int | None = None,
    agent_id: str | None = None,
) -> HPCFilePath:
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
    filepath: HPCFilePath = fp / requested_filename
    return filepath


async def download_tsv(
    filepath: HPCFilePath,
    ssh: SSHServiceManaged | SSHService,
    filename: str,
    variant_id: int,
    lineage_seed_id: int,
    generation_id: int,
    agent_id: str,
) -> TsvOutputFile:
    tmpdir = CACHE_DIR
    local_cached = tmpdir / filename
    if not local_cached.exists():
        print(f"{local_cached!s} does not yet exist!")
        # download to cache
        await ssh.scp_download(local_file=local_cached, remote_path=filepath)

    # read from cache
    with open(local_cached) as tmp_path:
        file_content = tmp_path.read()

    return TsvOutputFile(
        filename=filename,
        variant=variant_id,
        lineage_seed=lineage_seed_id,
        generation=generation_id,
        agent_id=agent_id,
        content=file_content,
    )


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

    filepath: HPCFilePath = fp / filename

    tmpdir = Path(__file__).parent.parent.parent / ".results_cache"

    local = Path(tmpdir) / filename
    if not local.exists():
        print(f"{local!s} does not yet exist!")
        await ssh.scp_download(local_file=local, remote_path=filepath)
    with open(local) as tmp_path:
        file_content = tmp_path.read()
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
