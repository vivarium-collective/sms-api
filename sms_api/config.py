import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

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

    sqlite_dbfile: str = "./sms.db"  # SQLite database URL for local development

    slurm_submit_host: str = ""
    slurm_submit_user: str = ""  # "svc_vivarium"
    slurm_submit_key_path: str = ""  # "/Users/jimschaff/.ssh/id_rsa"
    slurm_submit_known_hosts: str | None = None
    slurm_partition: str = ""
    slurm_node_list: str = ""  # comma-separated list of nodes, e.g., "node1,node2"
    slurm_qos: str = ""
    slurm_log_base_path: str = ""
    slurm_base_path: str = ""

    hpc_image_base_path: str = ""
    hpc_parca_base_path: str = ""
    hpc_repo_base_path: str = ""
    hpc_sim_base_path: str = ""
    hpc_sim_config_file: str = "publish.json"

    nats_url: str = ""
    nats_worker_event_subject: str = "worker.events"

    nats_emitter_url: str = ""
    nats_emitter_magic_word: str = "emitter-magic-word"

    dev_mode: str = "0"
    app_dir: str = f"{REPO_ROOT}/app"
    assets_dir: str = f"{REPO_ROOT}/assets"
    marimo_api_server: str = ""
    hpc_user: str = ""
    hpc_group: str = ""
    deployment: str = "prod"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_local_cache_dir() -> Path:
    settings = get_settings()
    local_cache_dir = Path(settings.storage_local_cache_dir)
    local_cache_dir.mkdir(parents=True, exist_ok=True)
    return local_cache_dir
