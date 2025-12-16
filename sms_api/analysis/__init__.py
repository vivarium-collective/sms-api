from ..config import Settings
from .analysis_service import AnalysisService, connect_ssh
from .analysis_service_fs import AnalysisServiceFS
from .analysis_service_hpc import AnalysisServiceHpc, RemoteScriptService
from .analysis_service_slurm import AnalysisServiceSlurm

__all__ = [
    "AnalysisService",
    "AnalysisServiceFS",
    "AnalysisServiceHpc",
    "AnalysisServiceSlurm",
    "RemoteScriptService",
    "connect_ssh",
    "get_analysis_service",
]


def get_analysis_service(env: Settings) -> AnalysisService | AnalysisServiceHpc | AnalysisServiceSlurm:
    return AnalysisServiceFS(env=env) if not env.remote_job_execution else AnalysisServiceSlurm(env=env)
