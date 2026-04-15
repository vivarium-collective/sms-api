import base64
import json
import os
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

from sms_api.common.storage.file_paths import HPCFilePath


def _parse_docker_config_json(path: str) -> tuple[str, str]:
    """Parse a Docker config.json file to extract GitHub credentials.

    Args:
        path: Path to the .dockerconfigjson file

    Returns:
        Tuple of (username, token) extracted from ghcr.io auth
    """
    if not path or not os.path.exists(path):
        return "", ""

    try:
        with open(path) as f:
            config = json.load(f)

        # Look for ghcr.io or github.com auth
        auths = config.get("auths", {})
        for registry in ["ghcr.io", "https://ghcr.io", "github.com", "https://github.com"]:
            if registry in auths:
                auth_b64 = auths[registry].get("auth", "")
                if auth_b64:
                    # auth is base64(username:token)
                    decoded = base64.b64decode(auth_b64).decode("utf-8")
                    if ":" in decoded:
                        username, token = decoded.split(":", 1)
                        return username, token
    except Exception:
        return "", ""

    return "", ""


KV_DRIVER = Literal["file", "s3", "gcs"]
TS_DRIVER = Literal["zarr", "n5", "zarr3"]
STORAGE_BACKEND = Literal["gcs", "s3", "qumulo"]

# -- load dev env -- #
REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
DEV_ENV_PATH = os.path.join(REPO_ROOT, "assets", "dev", "config", ".dev_env")
load_dotenv(DEV_ENV_PATH)  # NOTE: create an env config at this filepath if dev

ENV_CONFIG_ENV_FILE = "CONFIG_ENV_FILE"
ENV_SECRET_ENV_FILE = "SECRET_ENV_FILE"  # noqa: S105 Possible hardcoded password assigned to: "ENV_SECRET_ENV_FILE"

if os.getenv(ENV_CONFIG_ENV_FILE) is not None and os.path.exists(str(os.getenv(ENV_CONFIG_ENV_FILE))):
    load_dotenv(os.getenv(ENV_CONFIG_ENV_FILE))

if os.getenv(ENV_SECRET_ENV_FILE) is not None and os.path.exists(str(os.getenv(ENV_SECRET_ENV_FILE))):
    load_dotenv(os.getenv(ENV_SECRET_ENV_FILE))


class Namespace(StrEnum):
    DEVELOPMENT = "dev"
    PRODUCTION = "prod"
    TEST = "test"


class APIFilePath(Path):
    pass


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    storage_backend: STORAGE_BACKEND = "s3"

    # GCS configuration
    storage_gcs_bucket: str = "files.biosimulations.dev"
    storage_gcs_endpoint_url: str = "https://storage.googleapis.com"
    storage_gcs_region: str = "us-east4"
    storage_gcs_credentials_file: str = ""

    # Local storage configuration
    storage_local_cache_dir: str = "./local_cache"

    # AWS S3 configuration
    storage_s3_bucket: str = ""
    storage_s3_region: str = "us-east-1"
    storage_s3_access_key_id: str = ""
    storage_s3_secret_access_key: str = ""
    storage_s3_session_token: str = ""

    # Qumulo S3-compatible storage configuration
    storage_qumulo_endpoint_url: str = ""
    storage_qumulo_bucket: str = ""
    storage_qumulo_access_key_id: str = ""
    storage_qumulo_secret_access_key: str = ""
    storage_qumulo_verify_ssl: bool = True

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "biosimulations"
    mongodb_collection_omex: str = "BiosimOmex"
    mongodb_collection_sims: str = "BiosimSims"
    mongodb_collection_compare: str = "BiosimCompare"

    postgres_user: str = "<USER>"
    postgres_password: str = ""
    postgres_database: str = "sms"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_pool_size: int = 10  # number of connections in the pool
    postgres_max_overflow: int = 5  # maximum number of connections that can be created beyond the pool size
    postgres_pool_timeout: int = 30  # timeout for acquiring a connection from the pool in seconds
    postgres_pool_recycle: int = 1800  # recycle connections every seconds

    slurm_submit_host: str = ""
    slurm_submit_user: str = ""  # "svc_vivarium"
    slurm_submit_key_path: str = ""  # "/Users/jimschaff/.ssh/id_rsa"
    slurm_submit_known_hosts: str | None = None
    slurm_partition: str = ""
    slurm_node_list: str = ""  # comma-separated list of nodes, e.g., "node1,node2"
    slurm_qos: str = ""
    slurm_log_base_path: HPCFilePath = HPCFilePath(remote_path=Path(""))
    slurm_base_path: HPCFilePath = HPCFilePath(remote_path=Path(""))

    # Apptainer/Singularity temp directory for container builds
    # Use local SSD/NVMe (/tmp) for builds with many small files (faster metadata ops)
    # FSx Lustre has high latency for small file operations and can cause build timeouts
    apptainer_tmpdir: str = "/tmp/apptainer"  # noqa: S108 Intentional use of /tmp for fast metadata ops

    hpc_image_base_path: HPCFilePath = HPCFilePath(remote_path=Path(""))
    hpc_parca_base_path: HPCFilePath = HPCFilePath(remote_path=Path(""))
    hpc_repo_base_path: HPCFilePath = HPCFilePath(remote_path=Path(""))
    hpc_sim_base_path: HPCFilePath = HPCFilePath(remote_path=Path(""))
    hpc_sim_config_file: str = "default_with_publish.json"

    redis_internal_host: str = ""
    redis_internal_port: int = -1
    redis_external_host: str = ""
    redis_external_port: int = -1
    redis_channel: str = "worker.events"
    redis_emitter_magic_word: str = "emitter-magic-word"

    app_dir: str = f"{REPO_ROOT}/app"
    assets_dir: str = f"{REPO_ROOT}/assets"
    marimo_api_server: str = ""

    # data (outputs) retrieval
    hpc_user: str = ""
    hpc_group: str = ""
    deployment: str = "prod"
    namespace: Namespace = Namespace.TEST

    # external services
    biocyc_email: str = ""
    biocyc_password: str = ""

    # GitHub credentials for cloning private repos (PAT with repo scope)
    # Can be set directly or loaded from dockerconfigjson file (e.g., from K8s ghcr-secret)
    github_dockerconfig_path: str = ""  # Path to .dockerconfigjson file
    github_username: str = ""
    github_token: str = ""

    def model_post_init(self, __context: object) -> None:
        """Load GitHub credentials from dockerconfigjson if not set directly."""
        if (not self.github_username or not self.github_token) and self.github_dockerconfig_path:
            username, token = _parse_docker_config_json(self.github_dockerconfig_path)
            if username and token:
                object.__setattr__(self, "github_username", username)
                object.__setattr__(self, "github_token", token)

    simulation_outdir: HPCFilePath = HPCFilePath(remote_path=Path(""))
    analysis_outdir: HPCFilePath = HPCFilePath(remote_path=Path(""))
    vecoli_config_dir: HPCFilePath = HPCFilePath(remote_path=Path(""))
    cache_dir: str = f"{REPO_ROOT}/.results_cache"

    # Path prefix mapping for local vs remote (HPC) filesystem access
    # Example: path_local_prefix=/Volumes/SMS, path_remote_prefix=/projects/SMS
    path_local_prefix: str = ""
    path_remote_prefix: str = ""

    # valid namespaces correspond 1:1 with namespaces in kustomize/ config
    deployment_namespace: str = ""

    # Compute backend: "slurm" (SLURM via SSH) or "batch" (AWS Batch via Nextflow).
    # Must be set explicitly — no default.
    compute_backend: str = ""

    # Public mode exposes the CCAM fork repo and public simulation configs.
    # Private mode uses the Stanford private repo and private configs.
    # Must be set explicitly — no default.
    public_mode: str = ""

    # slurm constraint for arch mismatches
    slurm_constraint: str = ""

    # --- AWS Batch backend settings ---
    # Used when job_backend is "batch" (Stanford deployments)

    # K8s Job settings
    k8s_job_namespace: str = ""  # Namespace for Nextflow head Jobs (e.g. "sms-api-stanford")

    # AWS Batch settings (Nextflow submits tasks here)
    batch_task_arch: str = "amd64"  # Architecture for Batch task images: "amd64" or "arm64"
    batch_amd64_queue: str = ""  # AMD64 simulation task queue
    batch_arm64_queue: str = ""  # ARM64 simulation task queue (Graviton)
    batch_region: str = "us-gov-west-1"  # AWS region for Batch

    # S3 settings for workflow data
    s3_work_bucket: str = ""  # S3 bucket for Nextflow work dir and outputs
    s3_work_prefix: str = "nextflow/work"  # Prefix for Nextflow work directory
    s3_output_prefix: str = "vecoli-output"  # Prefix for workflow output data

    # ECR settings
    ecr_account_id: str = ""  # AWS account ID for ECR registry (e.g. "476270107793")
    ecr_repository: str = "vecoli"  # ECR repository name for vEcoli images

    # Docker image build settings (DooD via AWS Batch)
    build_arm64_queue: str = ""  # Batch queue for ARM64 builds (Graviton)
    build_amd64_queue: str = ""  # Batch queue for AMD64 builds
    build_job_definition: str = ""  # Batch job definition for DooD builds
    build_git_secret_arn: str = ""  # Secrets Manager ARN for GitHub PAT (private repo clone)

    # Optional: bake an `ecoli-sources`-shaped data repo into the simulator
    # image at build time (see vEcoli/runscripts/container/Dockerfile and
    # build-and-push-ecr.sh). Empty URL = skip the bake; the workflow then
    # relies on a runtime ECOLI_SOURCES env var (e.g. an s3:// URI).
    ecoli_sources_repo_url: str = ""
    ecoli_sources_ref: str = "main"

    # EC2 build machine (legacy, replaced by Batch DooD builds)
    build_node_host: str = ""
    build_node_user: str = ""
    build_node_key_path: str = ""


class ComputeBackend(StrEnum):
    """Compute backend for simulation workloads."""

    SLURM = "slurm"  # SLURM via SSH to a login node (UCONN CCAM)
    BATCH = "batch"  # AWS Batch via Nextflow (Stanford)


def get_job_backend() -> ComputeBackend:
    """Return the compute backend for the current deployment.

    Raises ValueError if COMPUTE_BACKEND is not set or invalid.
    """
    value = get_settings().compute_backend
    if not value:
        raise ValueError("COMPUTE_BACKEND must be set explicitly to 'slurm' or 'batch'")
    return ComputeBackend(value)


def get_public_mode() -> bool:
    """Return whether the deployment runs in public mode.

    Defaults to ``False`` when PUBLIC_MODE is not set so that the CLI and
    other local tooling can import ``simulator_defaults`` without requiring
    every server-side env var to be present.
    """
    value = get_settings().public_mode
    if not value:
        return False
    return value.lower() == "true"


@lru_cache
def get_settings(env_file: Path | None = None) -> Settings:
    if env_file is not None:
        DEV_ENV_PATH = str(env_file)
        load_dotenv(DEV_ENV_PATH)
    return Settings()


def get_local_cache_dir() -> Path:
    settings = get_settings()
    local_cache_dir = Path(settings.storage_local_cache_dir)
    local_cache_dir.mkdir(parents=True, exist_ok=True)
    return local_cache_dir
