import logging
import re
import tempfile
from pathlib import Path
from textwrap import dedent
from typing import Any

from sms_api.common.gateway.models import Namespace
from sms_api.common.gateway.utils import get_local_simulation_outdir, get_simulation_outdir
from sms_api.common.hpc.slurm_service import SlurmService
from sms_api.common.ssh.ssh_service import SSHService, get_ssh_service
from sms_api.config import Settings, get_settings
from sms_api.simulation.hpc_utils import get_experiment_dir, get_slurm_submit_file, get_slurmjob_name

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class AnalysisService:
    settings: Settings

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def get_file_path(
        self, experiment_id: str, filename: str, remote: bool = True, logger_instance: logging.Logger | None = None
    ) -> Path:
        """Fetches the filepath of a specified simulation analysis output as defined by simulation config.json"""
        if "." not in filename:
            raise ValueError("You must pass the filename including extension")

        if int(self.settings.dev_mode):
            remote = False

        outdir = get_simulation_outdir(
            experiment_id=experiment_id,
            remote=remote,
            group=self.settings.hpc_group,
            user=self.settings.hpc_user,
            namespace=self.settings.deployment if len(self.settings.deployment) else Namespace.PRODUCTION,
        )
        if outdir is None:
            log = logger_instance or logger
            log.debug(f"{outdir} was requested but does not exist. Defaulting to local dir.")
            outdir = get_local_simulation_outdir(experiment_id=experiment_id)

        analysis_dir = outdir / "analyses"
        for root, _, filenames in analysis_dir.walk():
            for f in filenames:
                if filename == f:
                    return root / f
        raise FileNotFoundError(f"Could not find {filename}")

    def get_file_paths(
        self, experiment_id: str, remote: bool = True, logger_instance: logging.Logger | None = None
    ) -> list[Path]:
        outdir = get_simulation_outdir(
            experiment_id=experiment_id,
            remote=remote,
            group=self.settings.hpc_group,
            user=self.settings.hpc_user,
            namespace=self.settings.deployment if len(self.settings.deployment) else Namespace.PRODUCTION,
        )
        if outdir is None:
            log = logger_instance or logger
            log.debug(f"{outdir} was requested but does not exist. Defaulting to local dir.")
            outdir = get_local_simulation_outdir(experiment_id=experiment_id)

        paths = []
        analysis_dir = outdir / "analyses"
        for root, _, filenames in analysis_dir.walk():
            for f in filenames:
                fp = root / f
                if fp.exists():
                    paths.append(fp)
        return paths

    def get_analysis_dir(self, outdir: Path, experiment_id: str) -> Path:
        return outdir / experiment_id / "analyses"

    def get_analysis_paths(self, analysis_dir: Path) -> set[Path]:
        paths = set()
        for root, _, files in analysis_dir.walk():
            for fname in files:
                fp = root / fname
                if fp.exists():
                    paths.add(fp)
        return paths

    def get_manifest_template(self, analysis_paths: set[Path]) -> dict[str, list[Any]]:
        ids: dict[str, list[Any]] = {}
        for path in analysis_paths:
            # output_id = re.sub(r"^.*?analyses?/", "", str(path)).replace('/', '.').split('.plots')[0]
            output_id = re.sub(r"^.*?analyses?/", "", str(path)).replace("/", ".").split(".plots")[0].replace(".", "/")
            ids[output_id] = []
        return ids

    def get_manifest(self, analysis_paths: set[Path], template: dict[str, list[Any]]) -> dict[str, list[str]]:
        for path in analysis_paths:
            for key in template:
                if key in str(path):
                    template[key].append(path.name)
        return {k.replace("/", "."): v for k, v in template.items()}

    async def submit_analysis_job(
        self,
        config_id: str,
        simulator_hash: str,
        env: Settings,
        experiment_id: str,
    ) -> int:
        ssh = get_ssh_service(self.settings)
        return await submit_analysis_job(
            config_id=config_id,
            simulator_hash=simulator_hash,
            env=self.settings,
            experiment_id=experiment_id,
            ssh=ssh,
            logger=logger,
        )


def analysis_slurm_script(
    config_id: str,
    slurm_job_name: str,
    experiment_id: str,
    # vecoli_commit_hash: str | None = None,
    # remote_vecoli_dir: Path | None = None,
    settings: Settings | None = None,
    logger: logging.Logger | None = None,
) -> str:
    env = settings or get_settings()
    base_path = Path(env.slurm_base_path)
    remote_workspace_dir = base_path / "workspace"
    vecoli_dir = remote_workspace_dir / "vEcoli"
    # slurm_log_file = base_path / f"prod/htclogs/{slurm_job_name}.out"
    slurm_log_file = base_path / f"prod/htclogs/{experiment_id}.out"
    experiment_outdir = f"/home/FCAM/svc_vivarium/workspace/api_outputs/{config_id}"

    config_dir = vecoli_dir / "configs"
    # latest_hash = vecoli_commit_hash or "079c43c"
    latest_hash = "079c43c"

    # --- in python script func: ---
    # experiment_id = f'sim-{simulator_hash}-{config_id}-{uuid.uuid4()}'

    # --- in slurm script: ---
    # config_dir=$HOME/workspace/vEcoli/configs
    # expid={experiment_id}
    # jq --arg expid "$expid" '.experiment_id = $expid' "$config_dir/${config_id}.json" > "$config_dir/${expid}.json"
    # ...BINDS, ETC...
    # singularity run $binds $image bash -c '
    #     export JAVA_HOME=$HOME/.local/bin/java-22
    #     export PATH=$JAVA_HOME/bin:$HOME/.local/bin:$PATH
    #     uv run --env-file /vEcoli/.env /vEcoli/runscripts/workflow.py --config /vEcoli/configs/$expid.json
    # '

    return dedent(f"""\
        #!/bin/bash
        #SBATCH --job-name={slurm_job_name}
        #SBATCH --time=30:00
        #SBATCH --cpus-per-task 2
        #SBATCH --mem=8GB
        #SBATCH --partition={env.slurm_partition}
        #SBATCH --qos={env.slurm_qos}
        #SBATCH --output={slurm_log_file!s}
        #SBATCH --nodelist={env.slurm_node_list}

        set -e

        ### set up java and nextflow
        local_bin=$HOME/.local/bin
        export JAVA_HOME=$local_bin/java-22
        export PATH=$JAVA_HOME/bin:$local_bin:$PATH
        # export NEXTFLOW=$local_bin/nextflow
        # export PATH=$JAVA_HOME/bin:$PATH:$(dirname "$NEXTFLOW")

        ### create request-specific config .json
        cd $HOME/workspace/vEcoli
        expid={experiment_id}
        config_id={config_id}
        config_dir={config_dir!s}
        experiment_config=$config_dir/$expid.json
        # jq --arg expid "$expid" '.experiment_id = $expid' "$config_dir/$config_id.json" > "$config_dir/$expid.json"

        ### Check if the experiment dir exists, remove if so:
        # if [ -d {experiment_outdir} ]; then rm -rf {experiment_outdir}; fi

        ### configure working dir and binds
        vecoli_dir={vecoli_dir!s}
        latest_hash={latest_hash}
        # cd $vecoli_dir

        ### bind vecoli and outputs dest dir
        binds="-B $HOME/workspace/vEcoli:/vEcoli"
        binds+=" -B $HOME/workspace/api_outputs:/out"

        ### bind java and nextflow
        binds+=" -B $JAVA_HOME:$JAVA_HOME"
        binds+=" -B $HOME/.local/bin:$HOME/.local/bin"

        # image="/home/FCAM/svc_vivarium/prod/images/vecoli-$latest_hash.sif"
        image=$HOME/workspace/images/vecoli-$latest_hash.sif
        vecoli_image_root=/vEcoli

        ### remove unique sim config on exit, regardless of job outcome
        # trap 'rm -f {config_dir!s}/{experiment_id}.json' EXIT

        # make the output dir if not exists
        mkdir -p {remote_workspace_dir!s}/api_outputs/{config_id}

        ### run bound singularity
        singularity run $binds $image bash -c "
            export JAVA_HOME=$HOME/.local/bin/java-22
            export PATH=$JAVA_HOME/bin:$HOME/.local/bin:$PATH
            uv run --env-file /vEcoli/.env /vEcoli/runscripts/analysis.py --config /vEcoli/configs/{experiment_id}.json
        "

        ### zip the file
        cd {remote_workspace_dir!s}
        uv run python scripts/archive_dir.py api_outputs/{config_id}
    """)


async def submit_slurm_script(
    script_content: str, slurm_job_name: str, env: Settings | None = None, ssh: SSHService | None = None
) -> int:
    settings = env or get_settings()
    ssh_service = ssh or SSHService(
        hostname=settings.slurm_submit_host,
        username=settings.slurm_submit_user,
        key_path=Path(settings.slurm_submit_key_path),
        known_hosts=Path(settings.slurm_submit_known_hosts) if settings.slurm_submit_known_hosts else None,
    )
    slurm_service = SlurmService(ssh_service=ssh_service)

    slurm_submit_file = get_slurm_submit_file(slurm_job_name=slurm_job_name)
    with tempfile.TemporaryDirectory() as tmpdir:
        local_submit_file = Path(tmpdir) / f"{slurm_job_name}.sbatch"
        with open(local_submit_file, "w") as f:
            f.write(script_content)

        slurm_jobid = await slurm_service.submit_job(
            local_sbatch_file=local_submit_file, remote_sbatch_file=slurm_submit_file
        )
        return slurm_jobid


def log(msg: str, logger: logging.Logger | None = None) -> None:
    logfunc = logger.info if logger else print
    return logfunc(msg)


async def submit_analysis_job(
    config_id: str,
    simulator_hash: str,
    env: Settings,
    experiment_id: str,
    ssh: SSHService | None = None,
    logger: logging.Logger | None = None,
) -> int:
    # experiment_id = expid or create_experiment_id(config_id=config_id, simulator_hash=simulator_hash)
    experiment_dir = get_experiment_dir(experiment_id=experiment_id, env=env)
    experiment_path_parent = experiment_dir.parent
    experiment_id_dir = experiment_dir.name
    slurmjob_name = get_slurmjob_name(experiment_id=experiment_id, simulator_hash=simulator_hash)
    # slurmjob_name = "dev"

    script = analysis_slurm_script(
        config_id=config_id, slurm_job_name=slurmjob_name, experiment_id=experiment_id, settings=env, logger=logger
    )

    msg = dedent(f"""\
        Submitting with the following params:
        ====================================
        >> experimentid: {experiment_id}
        >> experimentidDir: {experiment_id_dir}
        >> experiment_dir: {experiment_dir}
        >> experiment_path_parent: {experiment_path_parent}
        >> slurmjobName: {slurmjob_name}
        >> slurmscript:\n{script}
        ====================================
    """)
    log(msg, logger)
    log("", logger)

    slurmjob_id = await submit_slurm_script(script_content=script, slurm_job_name=slurmjob_name, env=env, ssh=ssh)
    log(f"Submission Successful!!\nGenerated slurmjob ID: {slurmjob_id}", logger)

    return slurmjob_id
