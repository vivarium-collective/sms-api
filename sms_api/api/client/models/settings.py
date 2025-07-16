from collections.abc import Mapping
from typing import Any, TypeVar, Optional, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.settings_storage_tensorstore_driver import SettingsStorageTensorstoreDriver
from ..models.settings_storage_tensorstore_kvstore_driver import SettingsStorageTensorstoreKvstoreDriver
from ..types import UNSET, Unset
from typing import Union






T = TypeVar("T", bound="Settings")



@_attrs_define
class Settings:
    """
        Attributes:
            storage_bucket (Union[Unset, str]):  Default: 'files.biosimulations.dev'.
            storage_endpoint_url (Union[Unset, str]):  Default: 'https://storage.googleapis.com'.
            storage_region (Union[Unset, str]):  Default: 'us-east4'.
            storage_tensorstore_driver (Union[Unset, SettingsStorageTensorstoreDriver]):  Default:
                SettingsStorageTensorstoreDriver.ZARR3.
            storage_tensorstore_kvstore_driver (Union[Unset, SettingsStorageTensorstoreKvstoreDriver]):  Default:
                SettingsStorageTensorstoreKvstoreDriver.GCS.
            temporal_service_url (Union[Unset, str]):  Default: 'localhost:7233'.
            storage_local_cache_dir (Union[Unset, str]):  Default: './local_cache'.
            storage_gcs_credentials_file (Union[Unset, str]):  Default: ''.
            mongodb_uri (Union[Unset, str]):  Default: 'mongodb://localhost:27017'.
            mongodb_database (Union[Unset, str]):  Default: 'biosimulations'.
            mongodb_collection_omex (Union[Unset, str]):  Default: 'BiosimOmex'.
            mongodb_collection_sims (Union[Unset, str]):  Default: 'BiosimSims'.
            mongodb_collection_compare (Union[Unset, str]):  Default: 'BiosimCompare'.
            postgres_user (Union[Unset, str]):  Default: '<USER>'.
            postgres_password (Union[Unset, str]):  Default: '<PASSWORD>'.
            postgres_database (Union[Unset, str]):  Default: 'sms'.
            postgres_host (Union[Unset, str]):  Default: 'localhost'.
            postgres_port (Union[Unset, int]):  Default: 5432.
            postgres_pool_size (Union[Unset, int]):  Default: 10.
            postgres_max_overflow (Union[Unset, int]):  Default: 5.
            postgres_pool_timeout (Union[Unset, int]):  Default: 30.
            postgres_pool_recycle (Union[Unset, int]):  Default: 1800.
            slurm_submit_host (Union[Unset, str]):  Default: ''.
            slurm_submit_user (Union[Unset, str]):  Default: ''.
            slurm_submit_key_path (Union[Unset, str]):  Default: ''.
            slurm_partition (Union[Unset, str]):  Default: ''.
            slurm_node_list (Union[Unset, str]):  Default: ''.
            slurm_qos (Union[Unset, str]):  Default: ''.
            slurm_log_base_path (Union[Unset, str]):  Default: ''.
            slurm_base_path (Union[Unset, str]):  Default: ''.
            hpc_image_base_path (Union[Unset, str]):  Default: ''.
            hpc_parca_base_path (Union[Unset, str]):  Default: ''.
            hpc_repo_base_path (Union[Unset, str]):  Default: ''.
            hpc_sim_base_path (Union[Unset, str]):  Default: ''.
            hpc_sim_config_file (Union[Unset, str]):  Default: 'publish.json'.
            nats_url (Union[Unset, str]):  Default: ''.
            nats_worker_event_subject (Union[Unset, str]):  Default: 'worker.events'.
            nats_emitter_url (Union[Unset, str]):  Default: ''.
            nats_emitter_magic_word (Union[Unset, str]):  Default: 'emitter-magic-word'.
            dev_mode (Union[Unset, str]):  Default: '0'.
            app_dir (Union[Unset, str]):  Default: '/Users/alexanderpatrie/Desktop/repos/ecoli/sms-api/app'.
            assets_dir (Union[Unset, str]):  Default: '/Users/alexanderpatrie/Desktop/repos/ecoli/sms-api/assets'.
            marimo_api_server (Union[Unset, str]):  Default: ''.
     """

    storage_bucket: Union[Unset, str] = 'files.biosimulations.dev'
    storage_endpoint_url: Union[Unset, str] = 'https://storage.googleapis.com'
    storage_region: Union[Unset, str] = 'us-east4'
    storage_tensorstore_driver: Union[Unset, SettingsStorageTensorstoreDriver] = SettingsStorageTensorstoreDriver.ZARR3
    storage_tensorstore_kvstore_driver: Union[Unset, SettingsStorageTensorstoreKvstoreDriver] = SettingsStorageTensorstoreKvstoreDriver.GCS
    temporal_service_url: Union[Unset, str] = 'localhost:7233'
    storage_local_cache_dir: Union[Unset, str] = './local_cache'
    storage_gcs_credentials_file: Union[Unset, str] = ''
    mongodb_uri: Union[Unset, str] = 'mongodb://localhost:27017'
    mongodb_database: Union[Unset, str] = 'biosimulations'
    mongodb_collection_omex: Union[Unset, str] = 'BiosimOmex'
    mongodb_collection_sims: Union[Unset, str] = 'BiosimSims'
    mongodb_collection_compare: Union[Unset, str] = 'BiosimCompare'
    postgres_user: Union[Unset, str] = '<USER>'
    postgres_password: Union[Unset, str] = '<PASSWORD>'
    postgres_database: Union[Unset, str] = 'sms'
    postgres_host: Union[Unset, str] = 'localhost'
    postgres_port: Union[Unset, int] = 5432
    postgres_pool_size: Union[Unset, int] = 10
    postgres_max_overflow: Union[Unset, int] = 5
    postgres_pool_timeout: Union[Unset, int] = 30
    postgres_pool_recycle: Union[Unset, int] = 1800
    slurm_submit_host: Union[Unset, str] = ''
    slurm_submit_user: Union[Unset, str] = ''
    slurm_submit_key_path: Union[Unset, str] = ''
    slurm_partition: Union[Unset, str] = ''
    slurm_node_list: Union[Unset, str] = ''
    slurm_qos: Union[Unset, str] = ''
    slurm_log_base_path: Union[Unset, str] = ''
    slurm_base_path: Union[Unset, str] = ''
    hpc_image_base_path: Union[Unset, str] = ''
    hpc_parca_base_path: Union[Unset, str] = ''
    hpc_repo_base_path: Union[Unset, str] = ''
    hpc_sim_base_path: Union[Unset, str] = ''
    hpc_sim_config_file: Union[Unset, str] = 'publish.json'
    nats_url: Union[Unset, str] = ''
    nats_worker_event_subject: Union[Unset, str] = 'worker.events'
    nats_emitter_url: Union[Unset, str] = ''
    nats_emitter_magic_word: Union[Unset, str] = 'emitter-magic-word'
    dev_mode: Union[Unset, str] = '0'
    app_dir: Union[Unset, str] = '/Users/alexanderpatrie/Desktop/repos/ecoli/sms-api/app'
    assets_dir: Union[Unset, str] = '/Users/alexanderpatrie/Desktop/repos/ecoli/sms-api/assets'
    marimo_api_server: Union[Unset, str] = ''





    def to_dict(self) -> dict[str, Any]:
        storage_bucket = self.storage_bucket

        storage_endpoint_url = self.storage_endpoint_url

        storage_region = self.storage_region

        storage_tensorstore_driver: Union[Unset, str] = UNSET
        if not isinstance(self.storage_tensorstore_driver, Unset):
            storage_tensorstore_driver = self.storage_tensorstore_driver.value


        storage_tensorstore_kvstore_driver: Union[Unset, str] = UNSET
        if not isinstance(self.storage_tensorstore_kvstore_driver, Unset):
            storage_tensorstore_kvstore_driver = self.storage_tensorstore_kvstore_driver.value


        temporal_service_url = self.temporal_service_url

        storage_local_cache_dir = self.storage_local_cache_dir

        storage_gcs_credentials_file = self.storage_gcs_credentials_file

        mongodb_uri = self.mongodb_uri

        mongodb_database = self.mongodb_database

        mongodb_collection_omex = self.mongodb_collection_omex

        mongodb_collection_sims = self.mongodb_collection_sims

        mongodb_collection_compare = self.mongodb_collection_compare

        postgres_user = self.postgres_user

        postgres_password = self.postgres_password

        postgres_database = self.postgres_database

        postgres_host = self.postgres_host

        postgres_port = self.postgres_port

        postgres_pool_size = self.postgres_pool_size

        postgres_max_overflow = self.postgres_max_overflow

        postgres_pool_timeout = self.postgres_pool_timeout

        postgres_pool_recycle = self.postgres_pool_recycle

        slurm_submit_host = self.slurm_submit_host

        slurm_submit_user = self.slurm_submit_user

        slurm_submit_key_path = self.slurm_submit_key_path

        slurm_partition = self.slurm_partition

        slurm_node_list = self.slurm_node_list

        slurm_qos = self.slurm_qos

        slurm_log_base_path = self.slurm_log_base_path

        slurm_base_path = self.slurm_base_path

        hpc_image_base_path = self.hpc_image_base_path

        hpc_parca_base_path = self.hpc_parca_base_path

        hpc_repo_base_path = self.hpc_repo_base_path

        hpc_sim_base_path = self.hpc_sim_base_path

        hpc_sim_config_file = self.hpc_sim_config_file

        nats_url = self.nats_url

        nats_worker_event_subject = self.nats_worker_event_subject

        nats_emitter_url = self.nats_emitter_url

        nats_emitter_magic_word = self.nats_emitter_magic_word

        dev_mode = self.dev_mode

        app_dir = self.app_dir

        assets_dir = self.assets_dir

        marimo_api_server = self.marimo_api_server


        field_dict: dict[str, Any] = {}

        field_dict.update({
        })
        if storage_bucket is not UNSET:
            field_dict["storage_bucket"] = storage_bucket
        if storage_endpoint_url is not UNSET:
            field_dict["storage_endpoint_url"] = storage_endpoint_url
        if storage_region is not UNSET:
            field_dict["storage_region"] = storage_region
        if storage_tensorstore_driver is not UNSET:
            field_dict["storage_tensorstore_driver"] = storage_tensorstore_driver
        if storage_tensorstore_kvstore_driver is not UNSET:
            field_dict["storage_tensorstore_kvstore_driver"] = storage_tensorstore_kvstore_driver
        if temporal_service_url is not UNSET:
            field_dict["temporal_service_url"] = temporal_service_url
        if storage_local_cache_dir is not UNSET:
            field_dict["storage_local_cache_dir"] = storage_local_cache_dir
        if storage_gcs_credentials_file is not UNSET:
            field_dict["storage_gcs_credentials_file"] = storage_gcs_credentials_file
        if mongodb_uri is not UNSET:
            field_dict["mongodb_uri"] = mongodb_uri
        if mongodb_database is not UNSET:
            field_dict["mongodb_database"] = mongodb_database
        if mongodb_collection_omex is not UNSET:
            field_dict["mongodb_collection_omex"] = mongodb_collection_omex
        if mongodb_collection_sims is not UNSET:
            field_dict["mongodb_collection_sims"] = mongodb_collection_sims
        if mongodb_collection_compare is not UNSET:
            field_dict["mongodb_collection_compare"] = mongodb_collection_compare
        if postgres_user is not UNSET:
            field_dict["postgres_user"] = postgres_user
        if postgres_password is not UNSET:
            field_dict["postgres_password"] = postgres_password
        if postgres_database is not UNSET:
            field_dict["postgres_database"] = postgres_database
        if postgres_host is not UNSET:
            field_dict["postgres_host"] = postgres_host
        if postgres_port is not UNSET:
            field_dict["postgres_port"] = postgres_port
        if postgres_pool_size is not UNSET:
            field_dict["postgres_pool_size"] = postgres_pool_size
        if postgres_max_overflow is not UNSET:
            field_dict["postgres_max_overflow"] = postgres_max_overflow
        if postgres_pool_timeout is not UNSET:
            field_dict["postgres_pool_timeout"] = postgres_pool_timeout
        if postgres_pool_recycle is not UNSET:
            field_dict["postgres_pool_recycle"] = postgres_pool_recycle
        if slurm_submit_host is not UNSET:
            field_dict["slurm_submit_host"] = slurm_submit_host
        if slurm_submit_user is not UNSET:
            field_dict["slurm_submit_user"] = slurm_submit_user
        if slurm_submit_key_path is not UNSET:
            field_dict["slurm_submit_key_path"] = slurm_submit_key_path
        if slurm_partition is not UNSET:
            field_dict["slurm_partition"] = slurm_partition
        if slurm_node_list is not UNSET:
            field_dict["slurm_node_list"] = slurm_node_list
        if slurm_qos is not UNSET:
            field_dict["slurm_qos"] = slurm_qos
        if slurm_log_base_path is not UNSET:
            field_dict["slurm_log_base_path"] = slurm_log_base_path
        if slurm_base_path is not UNSET:
            field_dict["slurm_base_path"] = slurm_base_path
        if hpc_image_base_path is not UNSET:
            field_dict["hpc_image_base_path"] = hpc_image_base_path
        if hpc_parca_base_path is not UNSET:
            field_dict["hpc_parca_base_path"] = hpc_parca_base_path
        if hpc_repo_base_path is not UNSET:
            field_dict["hpc_repo_base_path"] = hpc_repo_base_path
        if hpc_sim_base_path is not UNSET:
            field_dict["hpc_sim_base_path"] = hpc_sim_base_path
        if hpc_sim_config_file is not UNSET:
            field_dict["hpc_sim_config_file"] = hpc_sim_config_file
        if nats_url is not UNSET:
            field_dict["nats_url"] = nats_url
        if nats_worker_event_subject is not UNSET:
            field_dict["nats_worker_event_subject"] = nats_worker_event_subject
        if nats_emitter_url is not UNSET:
            field_dict["nats_emitter_url"] = nats_emitter_url
        if nats_emitter_magic_word is not UNSET:
            field_dict["nats_emitter_magic_word"] = nats_emitter_magic_word
        if dev_mode is not UNSET:
            field_dict["dev_mode"] = dev_mode
        if app_dir is not UNSET:
            field_dict["app_dir"] = app_dir
        if assets_dir is not UNSET:
            field_dict["assets_dir"] = assets_dir
        if marimo_api_server is not UNSET:
            field_dict["marimo_api_server"] = marimo_api_server

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        storage_bucket = d.pop("storage_bucket", UNSET)

        storage_endpoint_url = d.pop("storage_endpoint_url", UNSET)

        storage_region = d.pop("storage_region", UNSET)

        _storage_tensorstore_driver = d.pop("storage_tensorstore_driver", UNSET)
        storage_tensorstore_driver: Union[Unset, SettingsStorageTensorstoreDriver]
        if isinstance(_storage_tensorstore_driver,  Unset):
            storage_tensorstore_driver = UNSET
        else:
            storage_tensorstore_driver = SettingsStorageTensorstoreDriver(_storage_tensorstore_driver)




        _storage_tensorstore_kvstore_driver = d.pop("storage_tensorstore_kvstore_driver", UNSET)
        storage_tensorstore_kvstore_driver: Union[Unset, SettingsStorageTensorstoreKvstoreDriver]
        if isinstance(_storage_tensorstore_kvstore_driver,  Unset):
            storage_tensorstore_kvstore_driver = UNSET
        else:
            storage_tensorstore_kvstore_driver = SettingsStorageTensorstoreKvstoreDriver(_storage_tensorstore_kvstore_driver)




        temporal_service_url = d.pop("temporal_service_url", UNSET)

        storage_local_cache_dir = d.pop("storage_local_cache_dir", UNSET)

        storage_gcs_credentials_file = d.pop("storage_gcs_credentials_file", UNSET)

        mongodb_uri = d.pop("mongodb_uri", UNSET)

        mongodb_database = d.pop("mongodb_database", UNSET)

        mongodb_collection_omex = d.pop("mongodb_collection_omex", UNSET)

        mongodb_collection_sims = d.pop("mongodb_collection_sims", UNSET)

        mongodb_collection_compare = d.pop("mongodb_collection_compare", UNSET)

        postgres_user = d.pop("postgres_user", UNSET)

        postgres_password = d.pop("postgres_password", UNSET)

        postgres_database = d.pop("postgres_database", UNSET)

        postgres_host = d.pop("postgres_host", UNSET)

        postgres_port = d.pop("postgres_port", UNSET)

        postgres_pool_size = d.pop("postgres_pool_size", UNSET)

        postgres_max_overflow = d.pop("postgres_max_overflow", UNSET)

        postgres_pool_timeout = d.pop("postgres_pool_timeout", UNSET)

        postgres_pool_recycle = d.pop("postgres_pool_recycle", UNSET)

        slurm_submit_host = d.pop("slurm_submit_host", UNSET)

        slurm_submit_user = d.pop("slurm_submit_user", UNSET)

        slurm_submit_key_path = d.pop("slurm_submit_key_path", UNSET)

        slurm_partition = d.pop("slurm_partition", UNSET)

        slurm_node_list = d.pop("slurm_node_list", UNSET)

        slurm_qos = d.pop("slurm_qos", UNSET)

        slurm_log_base_path = d.pop("slurm_log_base_path", UNSET)

        slurm_base_path = d.pop("slurm_base_path", UNSET)

        hpc_image_base_path = d.pop("hpc_image_base_path", UNSET)

        hpc_parca_base_path = d.pop("hpc_parca_base_path", UNSET)

        hpc_repo_base_path = d.pop("hpc_repo_base_path", UNSET)

        hpc_sim_base_path = d.pop("hpc_sim_base_path", UNSET)

        hpc_sim_config_file = d.pop("hpc_sim_config_file", UNSET)

        nats_url = d.pop("nats_url", UNSET)

        nats_worker_event_subject = d.pop("nats_worker_event_subject", UNSET)

        nats_emitter_url = d.pop("nats_emitter_url", UNSET)

        nats_emitter_magic_word = d.pop("nats_emitter_magic_word", UNSET)

        dev_mode = d.pop("dev_mode", UNSET)

        app_dir = d.pop("app_dir", UNSET)

        assets_dir = d.pop("assets_dir", UNSET)

        marimo_api_server = d.pop("marimo_api_server", UNSET)

        settings = cls(
            storage_bucket=storage_bucket,
            storage_endpoint_url=storage_endpoint_url,
            storage_region=storage_region,
            storage_tensorstore_driver=storage_tensorstore_driver,
            storage_tensorstore_kvstore_driver=storage_tensorstore_kvstore_driver,
            temporal_service_url=temporal_service_url,
            storage_local_cache_dir=storage_local_cache_dir,
            storage_gcs_credentials_file=storage_gcs_credentials_file,
            mongodb_uri=mongodb_uri,
            mongodb_database=mongodb_database,
            mongodb_collection_omex=mongodb_collection_omex,
            mongodb_collection_sims=mongodb_collection_sims,
            mongodb_collection_compare=mongodb_collection_compare,
            postgres_user=postgres_user,
            postgres_password=postgres_password,
            postgres_database=postgres_database,
            postgres_host=postgres_host,
            postgres_port=postgres_port,
            postgres_pool_size=postgres_pool_size,
            postgres_max_overflow=postgres_max_overflow,
            postgres_pool_timeout=postgres_pool_timeout,
            postgres_pool_recycle=postgres_pool_recycle,
            slurm_submit_host=slurm_submit_host,
            slurm_submit_user=slurm_submit_user,
            slurm_submit_key_path=slurm_submit_key_path,
            slurm_partition=slurm_partition,
            slurm_node_list=slurm_node_list,
            slurm_qos=slurm_qos,
            slurm_log_base_path=slurm_log_base_path,
            slurm_base_path=slurm_base_path,
            hpc_image_base_path=hpc_image_base_path,
            hpc_parca_base_path=hpc_parca_base_path,
            hpc_repo_base_path=hpc_repo_base_path,
            hpc_sim_base_path=hpc_sim_base_path,
            hpc_sim_config_file=hpc_sim_config_file,
            nats_url=nats_url,
            nats_worker_event_subject=nats_worker_event_subject,
            nats_emitter_url=nats_emitter_url,
            nats_emitter_magic_word=nats_emitter_magic_word,
            dev_mode=dev_mode,
            app_dir=app_dir,
            assets_dir=assets_dir,
            marimo_api_server=marimo_api_server,
        )

        return settings
