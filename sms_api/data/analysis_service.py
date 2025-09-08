import logging
import re
from pathlib import Path
from typing import Any

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
