"""Default simulator repository configuration.

This module is kept separate to avoid circular imports.
"""

from sms_api.common import StrEnumBase
from sms_api.simulation.models import SimulationConfigFilename, Simulator


class RepoUrl(StrEnumBase):
    VECOLI_FORK_REPO_URL = "https://github.com/vivarium-collective/vEcoli"
    VECOLI_PUBLIC_REPO_URL = "https://github.com/CovertLab/vEcoli"
    VECOLI_PRIVATE_REPO_URL = ""


ACCEPTED_REPOS = {
    RepoUrl.VECOLI_FORK_REPO_URL: ["messages", "ccam-nextflow", "master", "api-support"],
    RepoUrl.VECOLI_PUBLIC_REPO_URL: ["master", "ptools_viz"],
    RepoUrl.VECOLI_PRIVATE_REPO_URL: ["api-analysis-patch"],
}

AVAILABLE_CONFIG_FILENAMES = [
    SimulationConfigFilename.DEFAULT,
    SimulationConfigFilename.CCAM,
    SimulationConfigFilename.AWS_CDK,
    SimulationConfigFilename.PTOOLS_CCAM,
]
DEFAULT_REPO = RepoUrl.VECOLI_FORK_REPO_URL
DEFAULT_BRANCH = "api-support"
DEFAULT_COMMIT = "203ab2a"  # should be "latest"

DEFAULT_SIMULATOR = Simulator(git_commit_hash=DEFAULT_COMMIT, git_repo_url=DEFAULT_REPO, git_branch=DEFAULT_BRANCH)
