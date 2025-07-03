import os
import shutil
from functools import lru_cache
from pathlib import Path
from typing import Literal

import dotenv
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

KV_DRIVER = Literal["file", "s3", "gcs"]
TS_DRIVER = Literal["zarr", "n5", "zarr3"]

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

os.environ["SLURM_SUBMIT_HOST"] = "login.hpc.cam.uchc.edu"


class Settings(BaseSettings):
    storage_bucket: str = "files.biosimulations.dev"
    storage_endpoint_url: str = "https://storage.googleapis.com"
    storage_region: str = "us-east4"
    storage_tensorstore_driver: TS_DRIVER = "zarr3"
    storage_tensorstore_kvstore_driver: KV_DRIVER = "gcs"

    temporal_service_url: str = "localhost:7233"

    storage_local_cache_dir: str = "./local_cache"

    storage_gcs_credentials_file: str = ""

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "biosimulations"
    mongodb_collection_omex: str = "BiosimOmex"
    mongodb_collection_sims: str = "BiosimSims"
    mongodb_collection_compare: str = "BiosimCompare"

    postgres_user: str = os.getenv("POSTGRES_USER", "<USER>")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "<PASSWORD>")
    postgres_database: str = "sms"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_pool_size: int = 10  # number of connections in the pool
    postgres_max_overflow: int = 5  # maximum number of connections that can be created beyond the pool size
    postgres_pool_timeout: int = 30  # timeout for acquiring a connection from the pool in seconds
    postgres_pool_recycle: int = 1800  # recycle connections every seconds

    slurm_submit_host: str = "login.hpc.cam.uchc.edu"  # "mantis-sub-1.cam.uchc.edu"
    slurm_submit_user: str = os.getenv("SLURM_SUBMIT_USER", "svc_vivarium")
    slurm_submit_key_path: str = os.getenv(
        "SLURM_SUBMIT_KEY_PATH", "/Users/alexanderpatrie/.ssh/sms_id_rsa"
    )  # "/Users/jimschaff/.ssh/id_rsa"
    slurm_partition: str = "vivarium"
    slurm_node_list: str = "mantis-039"  # comma-separated list of nodes, e.g., "node1,node2"
    slurm_qos: str = "vivarium"
    slurm_log_base_path: str = "/home/FCAM/svc_vivarium/dev/htclogs"

    hpc_image_base_path: str = ""
    hpc_parca_base_path: str = ""
    hpc_repo_base_path: str = ""
    hpc_sim_base_path: str = ""

    slurm_base_path: str = "/home/FCAM/svc_vivarium"
    

@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_local_cache_dir() -> Path:
    settings = get_settings()
    local_cache_dir = Path(settings.storage_local_cache_dir)
    local_cache_dir.mkdir(parents=True, exist_ok=True)
    return local_cache_dir


def purge_local_cache_dir(local_cache_dir: Path) -> None:
    shutil.rmtree(local_cache_dir)
