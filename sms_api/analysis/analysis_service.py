# ================================= new implementation ================================================= #
import asyncio
import copy
import dataclasses
import hashlib
import io
import json
import logging
import re
import tempfile
from pathlib import Path
from textwrap import dedent
from typing import Any

import pandas as pd

from sms_api.analysis.models import (
    PTOOLS_CANONICAL_N_TP,
    AnalysisConfig,
    AnalysisJobFailedException,
    AnalysisRun,
    ExperimentAnalysisDTO,
    ExperimentAnalysisRequest,
    PtoolsAnalysisConfig,
    PtoolsAnalysisType,
    TsvOutputFile,
)
from sms_api.common.hpc.slurm_service import SlurmService
from sms_api.common.models import JobStatus, SSHTarget
from sms_api.common.ssh.ssh_service import SSHSession
from sms_api.common.storage.file_paths import HPCFilePath
from sms_api.common.utils import capture_slurm_script
from sms_api.config import Settings
from sms_api.dependencies import get_ssh_session_service
from sms_api.simulation.hpc_utils import get_slurm_submit_file, get_slurmjob_name
from sms_api.simulation.models import SimulatorVersion

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


MAX_ANALYSIS_CPUS = 4
MAX_ANALYSIS_MEM = "24GB"


@dataclasses.dataclass
class RequestPayload:
    data: dict[str, Any]

    def hash(self) -> str:
        normalized = normalize_json(_strip_request_n_tp(self.data))
        b_rep = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(b_rep).hexdigest()


def normalize_json(obj: Any) -> Any:
    """Recursively sort dict keys in JSON-like object."""
    if isinstance(obj, dict):
        return {k: normalize_json(obj[k]) for k in sorted(obj)}
    elif isinstance(obj, list):
        return [normalize_json(x) for x in obj]
    else:
        return obj


_PTOOLS_DOMAINS = ("single", "multidaughter", "multigeneration", "multiseed")

# Path B1: aggregation mode used when re-binning adjacent time columns at
# response time. vEcoli (api-support branch) computes each column as the
# AVG of values whose ``time`` falls in that uniform-width bin, so coarsening
# is mean-of-means. Sim time is uniform, so this is exact within float
# rounding; see PTOOLS_LATENCY_MITIGATION.md §"Cons (B1)" for the row-uniformity
# caveat.
_PTOOLS_AGGREGATION_MODE: dict[str, str] = {
    PtoolsAnalysisType.REACTIONS.value: "mean",
    PtoolsAnalysisType.RNA.value: "mean",
    PtoolsAnalysisType.PROTEINS.value: "mean",
}
_PTOOLS_MODULE_NAMES = frozenset(_PTOOLS_AGGREGATION_MODE)


def reaggregate_ptools_columns(
    csv_text: str,
    target_n_tp: int,
    source_n_tp: int = PTOOLS_CANONICAL_N_TP,
    mode: str = "mean",
    separator: str = "\t",
) -> str:
    """Coarsen a ptools TSV from ``source_n_tp`` time bins to ``target_n_tp``.

    Path B1 — see PTOOLS_LATENCY_MITIGATION.md. The TSV's first column is the
    feature/index column (rows are gene/protein/reaction ids). All remaining
    columns are time-bin values. ``target_n_tp`` must divide ``source_n_tp``.

    Each output column is the mean (or sum) of ``source_n_tp // target_n_tp``
    contiguous source columns. The output column name is the source column
    name of the first source column in the group, preserving vEcoli's
    "bin-start time" naming convention.
    """
    if target_n_tp <= 0:
        raise ValueError(f"target_n_tp must be positive, got {target_n_tp}")
    if source_n_tp % target_n_tp != 0:
        raise ValueError(
            f"target_n_tp ({target_n_tp}) must divide source_n_tp ({source_n_tp}); only divisors are supported."
        )
    if target_n_tp == source_n_tp:
        return csv_text
    if mode not in ("mean", "sum"):
        raise ValueError(f"mode must be 'mean' or 'sum', got {mode!r}")

    df = pd.read_csv(io.StringIO(csv_text), sep=separator)
    if df.shape[1] < 2:
        return csv_text
    index_col = df.columns[0]
    time_cols = list(df.columns[1:])
    if len(time_cols) != source_n_tp:
        # Defensive: the TSV doesn't have the expected number of columns. Skip
        # re-aggregation rather than mangle the response. The caller will see
        # the canonical-resolution file and can decide what to do.
        logger.warning(
            "reaggregate_ptools_columns: expected %d time columns, found %d; returning canonical TSV unchanged.",
            source_n_tp,
            len(time_cols),
        )
        return csv_text

    group_size = source_n_tp // target_n_tp
    groups = [time_cols[i * group_size : (i + 1) * group_size] for i in range(target_n_tp)]
    new_cols: dict[str, Any] = {str(index_col): df[index_col]}
    for group in groups:
        new_name = str(group[0])
        block = df[group]
        if mode == "mean":
            new_cols[new_name] = block.mean(axis=1)
        else:
            new_cols[new_name] = block.sum(axis=1)
    out_df = pd.DataFrame(new_cols)
    return out_df.to_csv(sep=separator, index=False)


def ptools_aggregation_mode(module_name: str) -> str:
    """Return the per-module re-aggregation mode (mean/sum). Defaults to mean."""
    return _PTOOLS_AGGREGATION_MODE.get(module_name, "mean")


def _force_canonical_n_tp(requested_analyses: dict[str, dict[str, Any]]) -> None:
    """Rewrite every ptools module's ``n_tp`` to ``PTOOLS_CANONICAL_N_TP`` in-place.

    Path B1 — the user's requested ``n_tp`` is applied at response time by
    re-aggregating adjacent time columns, so SLURM always runs at the canonical
    resolution and the cache key (which excludes ``n_tp``) maps a single SLURM
    artifact to many ``n_tp`` requests.
    """
    for module_options in requested_analyses.values():
        for module_name, module_params in list(module_options.items()):
            if module_name in _PTOOLS_MODULE_NAMES and isinstance(module_params, dict):
                module_params["n_tp"] = PTOOLS_CANONICAL_N_TP


_FORK_BRANCH = "api-support"
_RKE_NAMESPACES = frozenset({"sms-api-rke", "sms-api-rke-dev"})


def is_fork_simulator(simulator: SimulatorVersion) -> bool:
    """True iff the simulator points at the vEcoli fork that hosts ptools (~/sms/vecoli_fork, api-support branch)."""
    return simulator.git_branch == _FORK_BRANCH


def should_eagerly_materialize_ptools(simulator: SimulatorVersion, settings: Settings) -> bool:
    """Path D gate. Only RKE deployments running the fork simulator pre-warm the ptools cache.

    Other deployments (Stanford / K8s) don't host ptools; other simulators (mainline vEcoli)
    don't expose the ptools_{rxns,rna,proteins} analysis modules.
    """
    return settings.deployment_namespace in _RKE_NAMESPACES and is_fork_simulator(simulator)


def build_canonical_ptools_request(experiment_id: str) -> ExperimentAnalysisRequest:
    """Build the request that materializes all three ptools modules at canonical resolution.

    Path D — invoked at simulation completion. ``n_tp`` is set to ``PTOOLS_CANONICAL_N_TP``
    explicitly for honesty; ``_force_canonical_n_tp`` would coerce it anyway.
    """
    return ExperimentAnalysisRequest(
        experiment_id=experiment_id,
        single=[
            PtoolsAnalysisConfig(name=PtoolsAnalysisType.REACTIONS.value, n_tp=PTOOLS_CANONICAL_N_TP),
            PtoolsAnalysisConfig(name=PtoolsAnalysisType.RNA.value, n_tp=PTOOLS_CANONICAL_N_TP),
            PtoolsAnalysisConfig(name=PtoolsAnalysisType.PROTEINS.value, n_tp=PTOOLS_CANONICAL_N_TP),
        ],
    )


def canonical_ptools_cache_dir(env: Settings, experiment_id: str) -> Path:
    """Return the on-disk cache directory the canonical Path-D request will populate.

    The cache key is the same hash the user-facing handler computes
    (``RequestPayload(request.model_dump()).hash()``), so a Path-D pre-warm and a
    later user request collide on the same directory — that's the idempotency mechanism.
    """
    request = build_canonical_ptools_request(experiment_id=experiment_id)
    payload_hash = RequestPayload(data=request.model_dump()).hash()
    return Path(env.cache_dir) / payload_hash


def _strip_request_n_tp(data: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``data`` with ``n_tp`` removed from every ptools module config.

    Path B1: the cache key must be independent of ``n_tp`` so that re-parameterizing
    the timepoint count does not trigger a fresh SLURM job. The actual ``n_tp`` is
    applied at response-assembly time via column re-aggregation.
    """
    cleaned = copy.deepcopy(data)
    for domain in _PTOOLS_DOMAINS:
        modules = cleaned.get(domain)
        if not isinstance(modules, list):
            continue
        for mod in modules:
            if isinstance(mod, dict):
                mod.pop("n_tp", None)
    return cleaned


class AnalysisServiceSlurm:
    env: Settings

    def __init__(self, env: Settings):
        self.env = env

    @property
    def slurm_service(self) -> SlurmService:
        return SlurmService()

    async def complete_config_template(
        self, simulator_hash: str, request: ExperimentAnalysisRequest, analysis_name: str
    ) -> AnalysisConfig:
        # 2. Read the config file from the remote HPC system
        settings = self.env
        remote_config_path = (
            settings.hpc_repo_base_path.remote_path / simulator_hash / "vEcoli" / "configs" / "api_analysis_ptools.json"
        )
        async with get_ssh_session_service(SSHTarget.SLURM).session() as ssh:
            returncode, stdout, stderr = await ssh.run_command(f"cat {remote_config_path}")
            if returncode != 0:
                raise ValueError(f"Failed to read config file {remote_config_path}: {stderr}")

        # 3. Replace placeholders in the config template
        config_file_str = stdout
        config_file_str = config_file_str.replace("EXPERIMENT_ID_PLACEHOLDER", request.experiment_id)
        config_file_str = config_file_str.replace("HPC_SIM_BASE_PATH_PLACEHOLDER", str(settings.hpc_sim_base_path))
        config_file_str = config_file_str.replace(
            "EXPERIMENT_OUTDIR_PLACEHOLDER", str(settings.hpc_sim_base_path / request.experiment_id)
        )
        config_file_str = config_file_str.replace("ANALYSIS_OUTDIR_PLACEHOLDER", str(settings.analysis_outdir))
        config_file_str = config_file_str.replace("ANALYSIS_NAME_PLACEHOLDER", analysis_name)

        config_data: dict[str, Any] = json.loads(config_file_str)
        # analysis_config = AnalysisConfig(**config_data)
        # analysis_config.analysis_options.multiseed = {'ptools_rxns': {'n_tp': 10}, 'ptools_rna': {'n_tp': 10}, 'ptools_proteins': {'n_tp': 10}}  # noqa: E501

        domains = ["single", "multidaughter", "multigeneration", "multiseed"]
        requested_analyses: dict[str, dict[str, Any]] = dict(zip(domains, [{} for _ in domains], strict=False))
        for domain in requested_analyses:
            requested = getattr(request, domain)
            if requested is not None:
                for module_config in requested:
                    requested_analyses[domain].update(module_config.to_dict())
        _force_canonical_n_tp(requested_analyses)
        config_data["analysis_options"].update(requested_analyses)

        # Propagate DuckDB filters into analysis_options (where vEcoli reads them).
        # vEcoli's analysis.py does config[key] (not .get()), so all filter keys
        # must be present even if None to avoid KeyError.
        opts = config_data["analysis_options"]
        for key in ("variant", "generation", "agent_id"):
            opts.setdefault(key, None)
        if request.generation_start is not None or request.generation_end is not None:
            start = request.generation_start if request.generation_start is not None else 0
            end = (request.generation_end + 1) if request.generation_end is not None else 1000
            opts["generation_range"] = [start, end]
        if request.seeds is not None:
            opts["lineage_seed"] = request.seeds

        analysis_config = AnalysisConfig(**config_data)
        return analysis_config

    async def dispatch_analysis(
        self,
        request: ExperimentAnalysisRequest,
        logger: logging.Logger,
        analysis_name: str,
        ssh: SSHSession,
        simulator_hash: str,
    ) -> tuple[str, int, AnalysisConfig]:
        # collect params
        slurmjob_name, slurm_log_file = self._collect_slurm_parameters(
            request=request, simulator_hash=simulator_hash, analysis_name=analysis_name
        )
        experiment_id = request.experiment_id
        # analysis_config = request.to_config(analysis_name=analysis_name, env=self.env)

        analysis_config = await self.complete_config_template(
            simulator_hash=simulator_hash, request=request, analysis_name=analysis_name
        )

        # gen script
        slurm_script = generate_slurm_script(
            env=self.env,
            slurm_log_file=slurm_log_file,
            slurm_job_name=slurmjob_name,
            simulator_hash=simulator_hash,
            config=analysis_config,
            analysis_name=analysis_name,
        )
        capture_slurm_script(slurm_script, "analysis.sbatch")

        # submit script
        slurmjob_id = await self._submit_slurm_script(
            config=analysis_config,
            experiment_id=experiment_id,
            script_content=slurm_script,
            slurm_job_name=slurmjob_name,
            ssh=ssh,
        )
        return slurmjob_name, slurmjob_id, analysis_config

    async def poll_status(self, dto: ExperimentAnalysisDTO, ssh: SSHSession) -> AnalysisRun:
        db_id = dto.database_id
        identifier = dto.job_id
        if identifier is None:
            raise ValueError("There is no job id yet associated with this record.")

        await asyncio.sleep(3)
        run = await self.get_analysis_status(job_id=identifier, db_id=db_id, ssh=ssh)
        while run.status.lower() not in ["completed", "failed"]:
            await asyncio.sleep(3)
            run = await self.get_analysis_status(job_id=identifier, db_id=db_id, ssh=ssh)
        if run.status.lower() == "failed":
            # Fetch the job log for error details
            error_log = await self._fetch_job_log(job_name=dto.job_name, ssh=ssh)
            run.error_log = error_log
            raise AnalysisJobFailedException(run=run)
        return run

    async def _fetch_job_log(self, job_name: str | None, ssh: SSHSession) -> str | None:
        """Fetch the SLURM job log file content for debugging failed jobs."""
        if not job_name:
            return None
        try:
            log_file = self.env.slurm_log_base_path / f"{job_name}.out"
            ret, stdout, stderr = await ssh.run_command(f"tail -200 {log_file!s}")
            if ret == 0 and stdout:
                return stdout
            return f"Could not fetch log: exit={ret}, stderr={stderr}"
        except Exception as e:
            logger.warning(f"Failed to fetch job log for {job_name}: {e}")
            return f"Error fetching log: {e}"

    async def get_available_output_paths(self, remote_analysis_outdir: HPCFilePath) -> list[HPCFilePath]:
        """Get available output file paths from the remote analysis directory.

        Only returns files with text-based extensions that can be read and returned.
        """
        cmd = f'find "{remote_analysis_outdir!s}" -type f'
        async with get_ssh_session_service(SSHTarget.SLURM).session() as ssh:
            ret, out, err = await ssh.run_command(cmd)
        # Filter to only include text-based file types
        accepted_extensions = ["txt", "tsv", "csv", "html"]
        paths = []
        for fp in out.splitlines():
            extension = fp.split(".")[-1].lower()
            if extension in accepted_extensions:
                paths.append(HPCFilePath(remote_path=Path(fp)))
        return paths

    async def download_analysis_output(
        self,
        local_dir: Path,
        remote_path: HPCFilePath,
        target_n_tp_by_module: dict[str, int] | None = None,
    ) -> TsvOutputFile:
        requested_filename = remote_path.remote_path.parts[-1]
        if not requested_filename.endswith(".tsv"):
            logger.info(f"wrong filename: {requested_filename}")

        # Parse partition metadata (variant, lineage_seed, generation) from directory path.
        # vEcoli single analyses produce output at:
        #   outdir/<domain>/variant[X]/lineage_seed[Y]/generation[Z]/<module>.tsv
        metadata = parse_partition_metadata(remote_path.remote_path)
        variant = metadata.get("variant")
        lineage_seed = metadata.get("lineage_seed")
        generation = metadata.get("generation")

        # Use a unique local filename that includes partition info to prevent overwrites
        # when multiple (seed, generation) combos produce files with the same module name.
        local_name = requested_filename
        parts = []
        if variant is not None:
            parts.append(f"v{variant}")
        if lineage_seed is not None:
            parts.append(f"s{lineage_seed}")
        if generation is not None:
            parts.append(f"g{generation}")
        if parts:
            stem = Path(requested_filename).stem
            suffix = Path(requested_filename).suffix
            local_name = f"{stem}_{'_'.join(parts)}{suffix}"

        local = local_dir / local_name
        if not local.exists():
            async with get_ssh_session_service(SSHTarget.SLURM).session() as ssh:
                await ssh.scp_download(local_file=local, remote_path=remote_path)

        # The cached file is always at the canonical n_tp resolution. If the
        # caller asked for a different (divisor) n_tp for this module, coarsen
        # the columns here. See PTOOLS_LATENCY_MITIGATION.md §"Corrected Path B (B1)".
        file_content = local.read_text()
        module_name = Path(requested_filename).stem
        target_n_tp = (target_n_tp_by_module or {}).get(module_name)
        if target_n_tp is not None and target_n_tp != PTOOLS_CANONICAL_N_TP:
            file_content = reaggregate_ptools_columns(
                csv_text=file_content,
                target_n_tp=target_n_tp,
                source_n_tp=PTOOLS_CANONICAL_N_TP,
                mode=ptools_aggregation_mode(module_name),
            )
        output = TsvOutputFile(
            filename=requested_filename,
            content=file_content,
            variant=variant if variant is not None else 0,
            lineage_seed=lineage_seed,
            generation=generation,
        )
        return output

    async def get_analysis_status(self, job_id: int, db_id: int, ssh: SSHSession) -> AnalysisRun:
        slurm_service = SlurmService()
        slurm_jobs = await slurm_service.get_job_status_scontrol(ssh, job_ids=[job_id])

        if not slurm_jobs:
            # Job not yet in sacct, status unknown
            return AnalysisRun(id=db_id, status=JobStatus.UNKNOWN, job_id=job_id)

        slurm_job = slurm_jobs[0]
        status = JobStatus.from_slurm_state(slurm_job.job_state)
        return AnalysisRun(id=db_id, status=status, job_id=job_id)

    @classmethod
    def _verify_result(cls, local_result_path: Path, expected_n_tp: int) -> bool:
        tsv_data = pd.read_csv(local_result_path, sep="\t")
        actual_cols = [col for col in tsv_data.columns if col.startswith("t")]
        return len(actual_cols) == expected_n_tp

    def _generate_slurm_script(
        self,
        slurm_log_file: HPCFilePath,
        slurm_job_name: str,
        latest_hash: str,
        config: AnalysisConfig,
        analysis_name: str,
    ) -> str:
        return generate_slurm_script(
            env=self.env,
            slurm_log_file=slurm_log_file,
            slurm_job_name=slurm_job_name,
            simulator_hash=latest_hash,
            config=config,
            analysis_name=analysis_name,
        )

    async def _submit_slurm_script(
        self, config: AnalysisConfig, experiment_id: str, script_content: str, slurm_job_name: str, ssh: SSHSession
    ) -> int:
        slurm_submit_file = get_slurm_submit_file(slurm_job_name=slurm_job_name)

        with tempfile.TemporaryDirectory() as tmpdir:
            local_submit_file = Path(tmpdir) / f"{slurm_job_name}.sbatch"
            with open(local_submit_file, "w") as f:
                f.write(script_content)

            slurm_jobid = await self.slurm_service.submit_job(
                ssh, local_sbatch_file=local_submit_file, remote_sbatch_file=slurm_submit_file
            )
            return slurm_jobid

    def _collect_slurm_parameters(
        self, request: ExperimentAnalysisRequest, analysis_name: str, simulator_hash: str
    ) -> tuple[str, HPCFilePath]:
        # SLURM params
        slurmjob_name = get_slurmjob_name(experiment_id=analysis_name, simulator_hash=simulator_hash)
        slurm_log_file = self.env.slurm_log_base_path / f"{slurmjob_name}.out"

        return slurmjob_name, slurm_log_file


def generate_slurm_script(
    env: Settings,
    slurm_log_file: HPCFilePath,
    slurm_job_name: str,
    simulator_hash: str,
    config: AnalysisConfig,
    analysis_name: str,
) -> str:
    qos_clause = f"#SBATCH --qos={env.slurm_qos}" if env.slurm_qos else ""
    nodelist_clause = f"#SBATCH --nodelist={env.slurm_node_list}" if env.slurm_node_list else ""

    image_path = env.hpc_image_base_path / f"vecoli-{simulator_hash}.sif"
    vecoli_repo_path = env.hpc_repo_base_path / simulator_hash / "vEcoli"
    simulation_outdir_base = env.simulation_outdir
    analysis_outdir = env.analysis_outdir / analysis_name

    return dedent(f"""\
        #!/bin/bash
        #SBATCH --job-name={slurm_job_name}
        #SBATCH --time=30:00
        #SBATCH --cpus-per-task {MAX_ANALYSIS_CPUS}
        #SBATCH --mem={MAX_ANALYSIS_MEM}
        #SBATCH --partition={env.slurm_partition}
        {qos_clause}
        #SBATCH --mail-type=ALL
        {nodelist_clause}
        #SBATCH -o {slurm_log_file!s}
        #SBATCH -e {slurm_log_file!s}

        set -e

        ### set up java and nextflow
        local_bin=$HOME/.local/bin
        export JAVA_HOME=$local_bin/java-22
        export PATH=$JAVA_HOME/bin:$local_bin:$PATH
        ## export UV_PROJECT_ENVIRONMENT=disabled

        ### configure working dir and binds
        image={image_path!s}
        tmp_config=$(mktemp)
        echo '{json.dumps(config.model_dump())}' > \"$tmp_config\"

        ### binds - use same paths inside and outside container (like workflow script)
        binds="-B {vecoli_repo_path!s}:{vecoli_repo_path!s}"
        binds+=" -B {simulation_outdir_base!s}:{simulation_outdir_base!s}"
        binds+=" -B {analysis_outdir!s}:{analysis_outdir!s}"

        ### remove existing dir if needed and recreate
        analysis_outdir={analysis_outdir!s}
        if [ -d \"$analysis_outdir\" ]; then
            rm -rf \"$analysis_outdir\"
        fi
        mkdir -p {analysis_outdir!s}

        ### execute analysis (same pattern as workflow script)
        cd {vecoli_repo_path!s}
        singularity run $binds $image uv run --no-cache \\
            --env-file {vecoli_repo_path!s}/.env \\
            {vecoli_repo_path!s}/runscripts/analysis.py --config \"$tmp_config\"

        ### optionally, remove uploaded fp
        rm -f \"$config_fp\"
    """)


# Regex for vEcoli partition directory segments: key=value or key[value]
_PARTITION_RE = re.compile(r"(variant|lineage_seed|generation|agent_id)[=\[](\d+)\]?")


def parse_partition_metadata(path: Path) -> dict[str, int]:
    """Extract variant/lineage_seed/generation/agent_id from vEcoli partition directory paths.

    vEcoli analysis output paths look like:
        .../single/variant[0]/lineage_seed[0]/generation[5]/ptools_rna.tsv
    or sometimes:
        .../variant=0/lineage_seed=0/generation=5/ptools_rna.tsv
    """
    metadata: dict[str, int] = {}
    for part in path.parts:
        m = _PARTITION_RE.match(part)
        if m:
            metadata[m.group(1)] = int(m.group(2))
    return metadata
