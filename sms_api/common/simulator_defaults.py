"""Default simulator repository configuration.

This module is kept separate to avoid circular imports.
"""

from sms_api.common import StrEnumBase
from sms_api.config import get_settings
from sms_api.simulation.models import Simulator


class SimulationConfigPublic(StrEnumBase):
    DEFAULT = "api_simulation_default.json"
    CCAM = "api_simulation_default_ccam.json"
    AWS_CDK = "api_simulation_default_aws_cdk.json"
    BASELINE = "api_simulation_ptools_ccam.json"
    VIO_WITH_MET = ""
    VIO_NO_MET = ""
    MEC = ""


class SimulationConfigPrivate(StrEnumBase):
    BASELINE = "api_simulation_default.json"
    VIO_WITH_MET = "api_test_violacein_with_metabolism.json"
    VIO_NO_MET = "api_test_violacein_no_metabolism.json"
    MEC = "api_final_mec.json"


class RepoUrl(StrEnumBase):
    VECOLI_FORK_REPO_URL = "https://github.com/vivarium-collective/vEcoli"
    VECOLI_PUBLIC_REPO_URL = "https://github.com/CovertLab/vEcoli"
    VECOLI_PRIVATE_REPO_URL = "https://github.com/CovertLabEcoli/vEcoli-private"


ACCEPTED_REPOS = {
    RepoUrl.VECOLI_FORK_REPO_URL: ["messages", "ccam-nextflow", "master", "api-support"],
    RepoUrl.VECOLI_PUBLIC_REPO_URL: ["master", "ptools_viz"],
    RepoUrl.VECOLI_PRIVATE_REPO_URL: ["api-analysis-patch", "master"],
}

NAMESPACE = get_settings().deployment_namespace
PUBLIC_MODE = "rke" in NAMESPACE

SimulationConfigFilename: type[SimulationConfigPublic] | type[SimulationConfigPrivate] = (
    SimulationConfigPublic if PUBLIC_MODE else SimulationConfigPrivate
)
SimulationConfigFilenameType = SimulationConfigPublic | SimulationConfigPrivate


AVAILABLE_CONFIG_FILENAMES_CCAM = SimulationConfigPublic.values()
AVAILABLE_CONFIG_FILENAMES_STANFORD_DEV = SimulationConfigPrivate.values()
AVAILABLE_CONFIG_FILENAMES = (
    AVAILABLE_CONFIG_FILENAMES_CCAM if "rke" in NAMESPACE else AVAILABLE_CONFIG_FILENAMES_STANFORD_DEV
)

DEFAULT_REPO = RepoUrl.VECOLI_FORK_REPO_URL if PUBLIC_MODE else RepoUrl.VECOLI_PRIVATE_REPO_URL
DEFAULT_BRANCH = "api-support" if PUBLIC_MODE else "api-analysis-patch"
DEFAULT_COMMIT = "203ab2a" if PUBLIC_MODE else "2f3ead"  # should be "latest"
DEFAULT_SIMULATOR = Simulator(git_commit_hash=DEFAULT_COMMIT, git_repo_url=DEFAULT_REPO, git_branch=DEFAULT_BRANCH)
