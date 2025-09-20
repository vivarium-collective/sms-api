# here, simply write config serialized to tempdir locally then use that to scp upload to configs dir
import abc
import json
import logging
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, override

from pydantic import Field

from sms_api.common.ssh.ssh_service import get_ssh_service, SSHService
from sms_api.config import Settings
from sms_api.data.models import AnalysisConfig, UploadConfirmation
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.models import SimulationConfiguration, UploadedSimulationConfig, BaseModel


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class IConfigService(abc.ABC):
    env: Settings
    db_service: DatabaseService
    logger: logging.Logger

    def __init__(self, env: Settings, db_service: DatabaseService) -> None:
        self.env = env
        self.db_service = db_service
        self.logger = logger

    @abc.abstractmethod
    async def upload(
        self,
        config_id: str,
        config: SimulationConfiguration | AnalysisConfig
    ) -> UploadConfirmation:
        pass


class SimulationConfigService(IConfigService):
    @override
    async def upload(
        self,
        config_id: str,
        sim_config: SimulationConfiguration
    ) -> UploadConfirmation:
        if not sim_config.experiment_id:
            raise Exception("No experiment ID provided")
        if sim_config.experiment_id.startswith("<P"):
            raise Exception("Experiment id is invalid (still using the placeholder value)")

        ssh = get_ssh_service(self.env)

        try:
            # store config in db
            user_suffix = str(uuid.uuid4()).split("-")[-1]  # TODO: let this be a reference instead to the user's id
            if config_id is None:
                config_id = "simconfig"
            confid = f"{config_id}-{user_suffix}"
            sim_config.experiment_id = f"{sim_config.experiment_id}-{user_suffix}"
            sim_config.emitter_arg["out_dir"] = self.env.simulation_outdir
            sim_config.daughter_outdir = self.env.simulation_outdir
            await self.db_service.insert_simulation_config(config_id=confid, config=sim_config)

            # # upload config to hpc(vEcoli dir)
            # with tempfile.TemporaryDirectory() as tmpdir:
            #     fname = f"{confid}.json"
            #     local = Path(tmpdir).absolute() / fname
            #     remote = Path(self.env.slurm_base_path) / "workspace" / "vEcoli" / "configs" / fname
            #     # write temp local
            #     with open(local, "w") as f:
            #         json.dump(sim_config.model_dump(), f, indent=3)
            #     # upload temp local to remote(vEcoli configs dir)
            #     await ssh.scp_upload(local_file=local, remote_path=remote)
            # uploaded = UploadConfirmation(filename=fname, home=self.env.slurm_base_path)
            # return uploaded
            return await fs_upload(config_id=config_id, config=sim_config, env=self.env, ssh=ssh, remote_config_dir=None)

        except Exception as e:
            logger.exception("Error uploading simulation config")
            raise Exception(str(e)) from e


async def fs_upload(config_id: str, config: SimulationConfiguration | AnalysisConfig, env: Settings, ssh: SSHService, remote_config_dir: Path | None = None) -> UploadConfirmation:
    # upload config to hpc(vEcoli dir)
    with tempfile.TemporaryDirectory() as tmpdir:
        fname = f"{config_id}.json"
        local = Path(tmpdir).absolute() / fname
        remote = remote_config_dir or Path(env.slurm_base_path) / "workspace" / "vEcoli" / "configs" / fname

        # write temp local
        with open(local, "w") as f:
            json.dump(config.model_dump(), f, indent=3)

        # upload temp local to remote(vEcoli configs dir)
        await ssh.scp_upload(local_file=local, remote_path=remote)

    uploaded = UploadConfirmation(filename=fname, home=env.slurm_base_path)
    return uploaded
