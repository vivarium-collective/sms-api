import marimo

__generated_with = "0.14.16"
app = marimo.App(width="full")


@app.cell
def _():
    from textwrap import dedent
    from pathlib import Path
    import uuid
    import tempfile
    import random
    import string

    from sms_api.common.ssh.ssh_service import SSHService, get_ssh_service
    from sms_api.common.hpc.slurm_service import SlurmService
    from sms_api.simulation.hpc_utils import get_slurm_submit_file
    from sms_api.config import get_settings, Settings


    # -- sms_api.simulation.hpc_utils -- #

    def get_slurmjob_name(experiment_id: str, simulator_hash: str = "079c43c") -> str:
        random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))  # noqa: S311
        return f"sim-{simulator_hash}-{experiment_id}-{random_suffix}"

    def get_experiment_dir(experiment_id: str, env: Settings) -> Path:
        return Path(f"{env.slurm_base_path}/workspace/outputs/{experiment_id}")


    # -- simulation_service -- #

    def slurm_script(
        config_id: str,
        slurm_job_name: str,
        # vecoli_commit_hash: str | None = None,
        # remote_vecoli_dir: Path | None = None,
        settings: Settings | None = None
    ) -> str:
        """
        :param config_id: config id selected from the dropdown of available
            simulation config JSON files for running vEcoli workflows.

        """
        env = settings or get_settings()
        base_path = Path(env.slurm_base_path)
        remote_workspace_dir = base_path / "workspace"
        # vecoli_dir = remote_vecoli_dir or remote_workspace_dir / "vEcoli"
        vecoli_dir = remote_workspace_dir / "vEcoli"
        config_dir = vecoli_dir / "configs"
        slurm_log_file = base_path / f'prod/htclogs/{slurm_job_name}.out'

        # latest_hash = vecoli_commit_hash or "079c43c"
        latest_hash = "079c43c"

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
            env

            # module load java
            # module load nextflow

            vecoli_dir={vecoli_dir!s}
            latest_hash={latest_hash}
            cd $vecoli_dir

            # cp $(which nextflow) /tmp/nextflow
            # chmod +x /tmp/nextflow
            binds="-B /home/FCAM/svc_vivarium/workspace/vEcoli:/vEcoli"
            binds+=" -B /home/FCAM/svc_vivarium/workspace/outputs:/out"
            binds+=" -B /tmp/nextflow:/usr/bin/nextflow"
            binds+=" -B $JAVA_HOME:$JAVA_HOME"

            image="/home/FCAM/svc_vivarium/prod/images/vecoli-$latest_hash.sif"  
            vecoli_image_root=/vEcoli

            singularity run $binds $image uv run \\
                --env-file $vecoli_image_root/.env \\
                $vecoli_image_root/runscripts/workflow.py \\
                --config $vecoli_image_root/configs/{config_id}.json
        """)

    async def submit_slurm_script(
        script_content: str, 
        slurm_job_name: str, 
        env: Settings | None = None
    ) -> int:
        settings = env or get_settings()
        ssh_service = SSHService(
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

    async def submit_vecoli_job(
        config_id: str, simulator_hash: str, env: Settings, expid: str | None = None
    ) -> int:
        experiment_id = expid or config_id + f'-{str(uuid.uuid4()).split('-')[-1]}'
        experiment_dir = get_experiment_dir(experiment_id=experiment_id, env=env)
        experiment_path_parent = experiment_dir.parent
        experiment_id_dir = experiment_dir.name
        slurmjob_name = get_slurmjob_name(experiment_id=experiment_id, simulator_hash=simulator_hash)

        script = slurm_script(
            config_id=config_id, 
            slurm_job_name=slurmjob_name, 
            settings=env
        )

        print(
            dedent(f"""\
                experimentid: {experiment_id}
                experimentidDir: {experiment_id_dir}
                experiment_dir: {experiment_dir}
                experiment_path_parent: {experiment_path_parent}
                slurmjobName: {slurmjob_name}

            """)
        )
        print(f'Slurm Script:\n{script}')
        try:
            slurmjob_id = await submit_slurm_script(script_content=script, slurm_job_name=slurmjob_name, env=env)
            print(f'Submission Successful!!\nGenerated slurmjob ID: {slurmjob_id}')
            return slurmjob_id
        except Exception as e:
            print(f'Submission NOT Successfull: Something went wrong:\n{e}')
    return get_settings, submit_vecoli_job


@app.cell
async def _(get_settings, submit_vecoli_job):
    async def run_test():
        config_id = "sms_perturb_growth"
        experiment_id = "testflow"
        vecoli_repo_hash = "079c43c"
        env = get_settings()

        print(f'Running test submission with config id: {config_id}\n...and experiment id: {experiment_id}\n...')
        jobid = await submit_vecoli_job(config_id=config_id, simulator_hash=vecoli_repo_hash, env=env, expid=experiment_id)
        print(f'Got slurm jobid: {jobid}')

    await run_test()
    return


@app.cell
def _():
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
