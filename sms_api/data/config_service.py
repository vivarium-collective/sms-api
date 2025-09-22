# here, simply write config serialized to tempdir locally then use that to scp upload to configs dir
import abc
import json
import logging
import tempfile
from pathlib import Path

from sms_api.common.ssh.ssh_service import SSHService
from sms_api.config import Settings
from sms_api.data.models import AnalysisConfig, UploadConfirmation
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.models import SimulationConfiguration

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
    async def upload(self, config_id: str, config: SimulationConfiguration | AnalysisConfig) -> UploadConfirmation:
        pass


async def fs_upload(
    config_id: str,
    config: SimulationConfiguration | AnalysisConfig,
    env: Settings,
    ssh: SSHService,
    remote_config_dir: Path | None = None,
) -> UploadConfirmation:
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
