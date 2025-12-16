from .analysis_service import AnalysisService, connect_ssh
from .analysis_service_hpc import AnalysisServiceHpc, RemoteScriptService
from .analysis_service_slurm import AnalysisServiceSlurm
from .analysis_service_fs import AnalysisServiceFS
from ..config import Settings


__all__ = [
    "AnalysisService",
    "AnalysisServiceHpc",
    "AnalysisServiceSlurm",
    "AnalysisServiceFS",
    "connect_ssh",
    "RemoteScriptService",
    "get_analysis_service"
]


def get_analysis_service(env: Settings) -> AnalysisService | AnalysisServiceHpc | AnalysisServiceSlurm:
    return AnalysisServiceFS(env=env) if not env.remote_job_execution \
        else AnalysisServiceSlurm(env=env)
