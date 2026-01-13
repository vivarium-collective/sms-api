import logging
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from sms_api.common.messaging.messaging_service import MessagingService
from sms_api.common.messaging.messaging_service_redis import MessagingServiceRedis
from sms_api.common.ssh.ssh_service import SSHSessionService
from sms_api.common.storage.file_service import FileService
from sms_api.common.storage.file_service_gcs import FileServiceGCS
from sms_api.common.storage.file_service_qumulo_s3 import FileServiceQumuloS3
from sms_api.common.storage.file_service_s3 import FileServiceS3
from sms_api.config import REPO_ROOT, get_settings
from sms_api.log_config import setup_logging
from sms_api.simulation.database_service import DatabaseService, DatabaseServiceSQL
from sms_api.simulation.tables_orm import create_db

if TYPE_CHECKING:
    from sms_api.simulation.job_scheduler import JobScheduler
    from sms_api.simulation.nextflow_service import NextflowServiceSlurm
    from sms_api.simulation.simulation_service import SimulationService

logger = logging.getLogger(__name__)
setup_logging(logger)


def verify_service(service: "DatabaseService | SimulationService | None") -> None:
    if service is None:
        logger.error(f"{service.__module__} is not initialized")
        raise HTTPException(status_code=500, detail=f"{service.__module__} is not initialized")


# ------ file service (standalone or pytest) ------

global_file_service: FileService | None = None


def set_file_service(file_service: FileService | None) -> None:
    global global_file_service
    global_file_service = file_service


def get_file_service() -> FileService | None:
    global global_file_service
    return global_file_service


# ------- sqlalchemy database service (standalone or pytest) ------

global_postgres_engine: AsyncEngine | None = None


def set_postgres_engine(engine: AsyncEngine | None) -> None:
    global global_postgres_engine
    global_postgres_engine = engine


def get_postgres_engine() -> AsyncEngine | None:
    global global_postgres_engine
    return global_postgres_engine


# ------- simulation database service (standalone or pytest) ------

global_database_service: DatabaseService | None = None


def set_database_service(database_service: DatabaseService | None) -> None:
    global global_database_service
    global_database_service = database_service


def get_database_service() -> DatabaseService | None:
    global global_database_service
    return global_database_service


# ------- simulation service (standalone or pytest) ------

global_simulation_service: "SimulationService | None" = None


def set_simulation_service(simulation_service: "SimulationService | None") -> None:
    global global_simulation_service
    global_simulation_service = simulation_service


def get_simulation_service() -> "SimulationService | None":
    global global_simulation_service
    return global_simulation_service


# ------ job scheduler (standalone) -----------------------------

global_job_scheduler: "JobScheduler | None" = None


def set_job_scheduler(job_scheduler: "JobScheduler | None") -> None:
    global global_job_scheduler
    global_job_scheduler = job_scheduler


def get_job_scheduler() -> "JobScheduler | None":
    global global_job_scheduler
    return global_job_scheduler


# ------ messaging/cache service (modular standalone: new/arbitrary channels ----

global_messaging_service: MessagingService | None = None


def set_messaging_service(service: MessagingService | None) -> None:
    global global_messaging_service
    global_job_scheduler = service  # noqa: F841


def get_messaging_service() -> MessagingService | None:
    global global_messaging_service
    return global_messaging_service


# ------ SSH session service (singleton) ------

global_ssh_session_service: SSHSessionService | None = None


def set_ssh_session_service(service: SSHSessionService | None) -> None:
    global global_ssh_session_service
    global_ssh_session_service = service


def get_ssh_session_service_or_none() -> SSHSessionService | None:
    """Get the SSHSessionService singleton, or None if not initialized."""
    global global_ssh_session_service
    return global_ssh_session_service


def get_ssh_session_service() -> SSHSessionService:
    """Get the SSHSessionService singleton. Raises RuntimeError if not initialized."""
    global global_ssh_session_service
    if global_ssh_session_service is None:
        raise RuntimeError("SSHSessionService singleton not initialized")
    return global_ssh_session_service


# ------ nextflow service (standalone or pytest) ------

global_nextflow_service: "NextflowServiceSlurm | None" = None


def set_nextflow_service(service: "NextflowServiceSlurm | None") -> None:
    global global_nextflow_service
    global_nextflow_service = service


def get_nextflow_service() -> "NextflowServiceSlurm | None":
    global global_nextflow_service
    return global_nextflow_service


# ------ initialized standalone application (standalone) ------


def get_async_engine(url: str, enable_ssl: bool = True, **engine_params: Any) -> AsyncEngine:
    if not enable_ssl:
        engine_params["connect_args"] = {"ssl": "disable"}
    return create_async_engine(url, **engine_params)


async def init_standalone(enable_ssl: bool = True) -> None:
    # Lazy imports to avoid circular dependencies
    from sms_api.common.hpc.slurm_service import SlurmService
    from sms_api.simulation.job_scheduler import JobScheduler
    from sms_api.simulation.simulation_service import SimulationServiceHpc

    _settings = get_settings()

    try:
        # Initialize file service based on configured backend
        logger.info(f"Initializing file service with backend: {_settings.storage_backend}")
        if _settings.storage_backend == "s3":
            set_file_service(FileServiceS3())
        elif _settings.storage_backend == "qumulo":
            set_file_service(FileServiceQumuloS3())
        elif _settings.storage_backend == "gcs":  # default to gcs
            set_file_service(FileServiceGCS())
        else:
            logger.error(f"Unsupported storage backend: {_settings.storage_backend}")

        # set services that don't require params (currently using hpc)
        logger.info("Initializing simulation service (HPC)...")
        set_simulation_service(SimulationServiceHpc())
        logger.info("✓ Simulation service initialized")

        # Validate and initialize Postgres connection
        logger.info("Validating Postgres configuration...")
        PG_USER = _settings.postgres_user
        PG_PSWD = _settings.postgres_password
        PG_DATABASE = _settings.postgres_database
        PG_HOST = _settings.postgres_host
        PG_PORT = _settings.postgres_port
        PG_POOL_SIZE = _settings.postgres_pool_size
        PG_MAX_OVERFLOW = _settings.postgres_max_overflow
        PG_POOL_TIMEOUT = _settings.postgres_pool_timeout
        PG_POOL_RECYCLE = _settings.postgres_pool_recycle
        if not PG_USER or not PG_PSWD or not PG_DATABASE or not PG_HOST or not PG_PORT:
            logger.error("Postgres connection settings are not properly configured.")
        postgres_url = f"postgresql+asyncpg://{PG_USER}:{PG_PSWD}@{PG_HOST}:{PG_PORT}/{PG_DATABASE}"

        logger.info("Initializing postgres connection...")
        engine = get_async_engine(
            url=postgres_url,
            enable_ssl=enable_ssl,
            echo=False,  # Disable verbose SQL logging (set to True for debugging)
            pool_size=PG_POOL_SIZE,
            max_overflow=PG_MAX_OVERFLOW,
            pool_timeout=PG_POOL_TIMEOUT,
            pool_recycle=PG_POOL_RECYCLE,
        )
        logger.info("Initializing database tables...")
        await create_db(engine)
        set_postgres_engine(engine)
        logger.info("✓ Postgres connection established and tables initialized")

        database = DatabaseServiceSQL(engine)
        set_database_service(database)

        # Initialize SSHSessionService singleton
        logger.info("Initializing SSH session service...")
        settings = get_settings()
        ssh_key_path = Path(settings.slurm_submit_key_path)
        if not ssh_key_path.exists():
            logger.warning(f"SSH key file not found: {ssh_key_path}")
        else:
            logger.info(f"SSH key found at: {ssh_key_path}")

        ssh_session_service = SSHSessionService(
            hostname=settings.slurm_submit_host,
            username=settings.slurm_submit_user,
            key_path=ssh_key_path,
            known_hosts=Path(settings.slurm_submit_known_hosts) if settings.slurm_submit_known_hosts else None,
        )
        set_ssh_session_service(ssh_session_service)
        logger.info(f"✓ SSHSessionService initialized for {settings.slurm_submit_user}@{settings.slurm_submit_host}")

        # Initialize Slurm service (uses SSHSessionService singleton)
        slurm_service = SlurmService()
        logger.info("✓ SlurmService initialized")

        # Initialize messaging service
        redis_host = _settings.redis_internal_host
        redis_port = _settings.redis_internal_port
        logger.info(f"Initializing Redis messaging service at host:port {redis_host}:{redis_port}...")
        messaging_service: MessagingService = MessagingServiceRedis()

        await messaging_service.connect(host=redis_host, port=redis_port)
        logger.info("✓ Messaging service connected")
        set_messaging_service(messaging_service)

        # Initialize JobScheduler
        logger.info("Initializing JobScheduler...")
        job_scheduler = JobScheduler(
            messaging_service=messaging_service, database_service=database, slurm_service=slurm_service
        )
        set_job_scheduler(job_scheduler)
        logger.info("✓ JobScheduler initialized")

    except Exception as e:
        logger.error(f"Failed to initialize JobScheduler: {e}", exc_info=True)
        raise


async def shutdown_standalone() -> None:
    mongodb_service = get_database_service()
    if mongodb_service:
        await mongodb_service.close()

    engine = get_postgres_engine()
    if engine:
        await engine.dispose()

    file_service = get_file_service()
    if file_service:
        await file_service.close()

    set_simulation_service(None)
    set_database_service(None)
    set_file_service(None)
    set_ssh_session_service(None)

    job_scheduler = get_job_scheduler()
    if job_scheduler:
        await job_scheduler.close()
        set_job_scheduler(None)
    for dirpath in [p for p in Path(f"{REPO_ROOT}/.results_cache").rglob("*") if p.is_dir()]:
        shutil.rmtree(dirpath)
