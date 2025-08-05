import logging
from pathlib import Path

from sms_api.common.gateway.utils import get_simulation_outdir
from sms_api.config import Settings, get_settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class AnalysisService:
    settings: Settings

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def get_file_path(self, experiment_id: str, filename: str) -> Path:
        """Fetches the filepath of a specified simulation analysis output as defined by simulation config.json"""
        if "." not in filename:
            raise ValueError("You must pass the filename including extension")

        outdir = get_simulation_outdir(experiment_id)
        analysis_dir = outdir / "analyses"
        for root, _, filenames in analysis_dir.walk():
            for f in filenames:
                if filename == f:
                    return root / f
        raise FileNotFoundError(f"Could not find {filename}")


def test_get_file_path() -> None:
    svc = AnalysisService()
    expid = "sms_single"
    filename = "ptools_rna.txt"
    fp = svc.get_file_path(expid, filename)
    print(fp)
    print(f"Exists: {fp.exists()}")
