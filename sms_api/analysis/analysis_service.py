# ================================= new implementation ================================================= #

import abc
import logging
from collections.abc import Awaitable
from functools import wraps
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from sms_api.analysis.models import ExperimentAnalysisRequest, TsvOutputFile
from sms_api.common.ssh.ssh_service import SSHServiceManaged, get_ssh_service_managed
from sms_api.common.storage.file_paths import HPCFilePath
from sms_api.common.utils import get_uuid
from sms_api.config import Settings

__all__ = ["AnalysisService", "connect_ssh"]


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


MAX_ANALYSIS_CPUS = 5


def connect_ssh(func: Callable[..., Any]) -> Callable[..., Awaitable[Any]]:
    @wraps(func)
    async def wrapper(self: "AnalysisService", **kwargs: Any) -> Any:
        try:
            if self.ssh.connected:
                raise RuntimeError()
            await self.ssh.connect()
            return await func(self, **kwargs)
        finally:
            await self.ssh.disconnect()

    return wrapper


class AnalysisService(abc.ABC):
    env: Settings
    ssh: SSHServiceManaged

    def __init__(self, env: Settings):
        self.env = env
        self.ssh = get_ssh_service_managed(self.env)

    @abc.abstractmethod
    async def dispatch_analysis(
        self,
        request: ExperimentAnalysisRequest,
        logger: logging.Logger,
        analysis_name: str,
        simulator_hash: str | None = None,
    ) -> Any:
        """This should execute a new job and provide
        at least some insight into job status.
        """
        pass

    @abc.abstractmethod
    async def get_available_output_paths(self, analysis_name: str) -> list[HPCFilePath]:
        pass

    @abc.abstractmethod
    async def download_analysis_output(
        self, local_cache_dir: Path, requested_filename: str, remote_path: HPCFilePath
    ) -> TsvOutputFile:
        pass

    @classmethod
    def generate_analysis_name(cls, experiment_id: str | None = None, _n_sections: int = 1) -> str:
        dataid: str = get_uuid(scope="analysis", data_id=experiment_id, n_sections=_n_sections)
        return dataid

    @classmethod
    def verify_result(cls, local_result_path: Path, expected_n_tp: int) -> bool:
        tsv_data = pd.read_csv(local_result_path, sep="\t")
        actual_cols = [col for col in tsv_data.columns if col.startswith("t")]
        return len(actual_cols) == expected_n_tp
