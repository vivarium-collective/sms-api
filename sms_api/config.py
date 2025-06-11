import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

KV_DRIVER = Literal["file", "s3", "gcs"]
TS_DRIVER = Literal["zarr", "n5", "zarr3"]

load_dotenv()

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

    simdata_api_base_url: str = "https://simdata.api.biosimulations.org"
    biosimulators_api_base_url: str = "https://api.biosimulators.org"
    biosimulations_api_base_url: str = "https://api.biosimulations.org"

    slurm_submit_host: str = ""  # "mantis-sub-1.cam.uchc.edu"
    slurm_submit_user: str = ""  # "svc_vivarium"
    slurm_submit_key_path: str = ""  # "/Users/jimschaff/.ssh/id_rsa"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_local_cache_dir() -> Path:
    settings = get_settings()
    local_cache_dir = Path(settings.storage_local_cache_dir)
    local_cache_dir.mkdir(parents=True, exist_ok=True)
    return local_cache_dir
