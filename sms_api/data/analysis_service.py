import logging
from pathlib import Path

from sms_api.common.gateway.models import Namespace
from sms_api.common.gateway.utils import get_local_simulation_outdir, get_simulation_outdir
from sms_api.config import Settings, get_settings

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


def test_get_file_paths() -> None:
    svc = AnalysisService()
    expid = "sms_single"
    paths = svc.get_file_paths(experiment_id=expid)
    print(paths)


def test_get_file_path() -> None:
    svc = AnalysisService()
    expid = "sms_single"
    filename = "ptools_rna.txt"
    fp = svc.get_file_path(expid, filename)
    print(fp)
    print(f"Exists: {fp.exists()}")
