import abc
import json
import logging
import tempfile
from pathlib import Path
from textwrap import dedent
from typing import Any

from sms_api.common.hpc.slurm_service import SlurmService
from sms_api.common.ssh.ssh_service import SSHService, get_ssh_service
from sms_api.config import Settings, get_settings
from sms_api.data.models import AnalysisConfig
from sms_api.data.utils import write_json_for_slurm
from sms_api.simulation.hpc_utils import get_slurm_submit_file, get_slurmjob_name


# TODO: create interface for this

def _script(slurm_log_file: Path, slurm_job_name: str, env: Settings, latest_hash: str, experiment_id: str) -> str:
    base_path = Path(env.slurm_base_path)
    remote_workspace_dir = base_path / "workspace"
    vecoli_dir = remote_workspace_dir / "vEcoli"
    config_dir = vecoli_dir / "configs"

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
        
        CONFIG_PATH=$1  # the JSON file path
        
        ### configure working dir and binds
        vecoli_dir={vecoli_dir!s}
        latest_hash={latest_hash}

        ### bind vecoli and outputs dest dir
        binds="-B $HOME/workspace/vEcoli:/vEcoli"
        binds+=" -B $HOME/workspace/api_outputs:/out"

        ### bind java and nextflow
        binds+=" -B $JAVA_HOME:$JAVA_HOME"
        binds+=" -B $HOME/.local/bin:$HOME/.local/bin"

        # image="/home/FCAM/svc_vivarium/prod/images/vecoli-$latest_hash.sif"
        image=$HOME/workspace/images/vecoli-$latest_hash.sif
        vecoli_image_root=/vEcoli

        # make the output dir if not exists
        mkdir -p {remote_workspace_dir!s}/api_outputs/{experiment_id}

        ### run bound singularity
        singularity run $binds $image bash -c "
            export JAVA_HOME=$HOME/.local/bin/java-22
            export PATH=$JAVA_HOME/bin:$HOME/.local/bin:$PATH
            uv run --env-file /vEcoli/.env /vEcoli/runscripts/analysis.py --config /vEcoli/configs/{experiment_id}.json
        "

        ### zip the file
        cd {remote_workspace_dir!s}
        uv run python scripts/archive_dir.py api_outputs/{experiment_id}
        
        # echo "Using config at: $CONFIG_PATH"
        # python my_hpc_script.py --config "$CONFIG_PATH"
    """)


async def _submit(
    config: AnalysisConfig,
    experiment_id: str,
    script_content: str,
    slurm_job_name: str,
    env: Settings,
    ssh: SSHService | None = None
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

        base_path = Path(env.slurm_base_path)
        remote_workspace_dir = base_path / "workspace"
        vecoli_dir = remote_workspace_dir / "vEcoli"
        config_dir = vecoli_dir / "configs"
        config_path = write_json_for_slurm(data=config.model_dump(), outdir=config_dir, filename=f"{experiment_id}.json")

        slurm_jobid = await slurm_service.submit_job(
            local_sbatch_file=local_submit_file, remote_sbatch_file=slurm_submit_file
        )
        return slurm_jobid


async def dispatch_job(
    experiment_id: str,
    config: AnalysisConfig,
    simulator_hash: str,
    env: Settings,
    logger: logging.Logger
) -> int:
    slurmjob_name = get_slurmjob_name(experiment_id=experiment_id, simulator_hash=simulator_hash)
    base_path = Path(env.slurm_base_path)
    slurm_log_file = base_path / f"prod/htclogs/{experiment_id}.out"

    slurm_script = _script(
        slurm_log_file=slurm_log_file,
        slurm_job_name=slurmjob_name,
        env=env,
    )
    ssh = get_ssh_service(env)
    slurmjob_id = await _submit(
        config=config,
        experiment_id=experiment_id,
        script_content=slurm_script,
        slurm_job_name=slurmjob_name,
        env=env,
        ssh=ssh
    )

    return slurmjob_id
