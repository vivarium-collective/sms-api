import logging
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
from sms_api.config import Settings, get_job_backend, get_settings
from sms_api.log_config import setup_logging
from sms_api.simulation.database_service import DatabaseService, DatabaseServiceSQL
from sms_api.simulation.tables_orm import create_db

if TYPE_CHECKING:
    from sms_api.simulation.job_scheduler import JobScheduler
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


# ------ initialized standalone application (standalone) ------


def get_async_engine(url: str, enable_ssl: bool = True, **engine_params: Any) -> AsyncEngine:
    if not enable_ssl:
        engine_params["connect_args"] = {"ssl": "disable"}
    return create_async_engine(url, **engine_params)


def _init_simulation_service(job_backend: str, settings: Settings) -> None:
    """Initialize the simulation service based on the job backend."""
    from sms_api.simulation.simulation_service import SimulationServiceHpc

    if job_backend == "k8s":
        from sms_api.common.hpc.k8s_job_service import K8sJobService
        from sms_api.simulation.simulation_service_k8s import SimulationServiceK8s

        logger.info("Initializing simulation service (K8s + AWS Batch)...")
        k8s_job_service = K8sJobService(namespace=settings.k8s_job_namespace)
        set_simulation_service(SimulationServiceK8s(k8s_job_service=k8s_job_service))
        logger.info("✓ Simulation service initialized (K8s)")
    else:
        logger.info("Initializing simulation service (HPC/SLURM)...")
        set_simulation_service(SimulationServiceHpc())
        logger.info("✓ Simulation service initialized (SLURM)")


def _init_ssh_service(job_backend: str, settings: Settings) -> None:
    """Initialize SSH session service based on the job backend.

    SLURM backend: SSH to HPC login node for all operations.
    K8s backend: SSH to EC2 submit node for ARM64 Docker image builds only.
    """
    if job_backend == "k8s" and settings.submit_node_host:
        logger.info("Initializing SSH session service (EC2 submit node for image builds)...")
        ssh_session_service = SSHSessionService(
            hostname=settings.submit_node_host,
            username=settings.submit_node_user,
            key_path=Path(settings.submit_node_key_path),
        )
        set_ssh_session_service(ssh_session_service)
        logger.info(f"✓ SSHSessionService initialized for {settings.submit_node_user}@{settings.submit_node_host}")
    elif job_backend == "slurm":
        logger.info("Initializing SSH session service (SLURM login node)...")
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


async def init_standalone(enable_ssl: bool = True) -> None:
    from sms_api.common.hpc.slurm_service import SlurmService
    from sms_api.simulation.job_scheduler import JobScheduler

    _settings = get_settings()
    job_backend = get_job_backend()

    try:
        # Initialize file service based on configured backend
        logger.info(f"Initializing file service with backend: {_settings.storage_backend}")
        if _settings.storage_backend == "s3":
            set_file_service(FileServiceS3())
        elif _settings.storage_backend == "qumulo":
            set_file_service(FileServiceQumuloS3())
        elif _settings.storage_backend == "gcs":
            set_file_service(FileServiceGCS())
        else:
            logger.error(f"Unsupported storage backend: {_settings.storage_backend}")

        _init_simulation_service(job_backend, _settings)

        # Validate and initialize Postgres connection
        logger.info("Validating Postgres configuration...")
        pg = _settings
        if not (
            pg.postgres_user and pg.postgres_password and pg.postgres_database and pg.postgres_host and pg.postgres_port
        ):
            logger.error("Postgres connection settings are not properly configured.")
        postgres_url = (
            f"postgresql+asyncpg://{pg.postgres_user}:{pg.postgres_password}"
            f"@{pg.postgres_host}:{pg.postgres_port}/{pg.postgres_database}"
        )

        # Check if database service is already set (e.g., by test fixtures)
        db_service: DatabaseService | None = get_database_service()
        if db_service is not None:
            logger.info("✓ Using existing database service (test mode)")
        else:
            logger.info("Initializing postgres connection...")
            engine = get_async_engine(
                url=postgres_url,
                enable_ssl=enable_ssl,
                echo=False,
                pool_size=pg.postgres_pool_size,
                max_overflow=pg.postgres_max_overflow,
                pool_timeout=pg.postgres_pool_timeout,
                pool_recycle=pg.postgres_pool_recycle,
            )
            logger.info("Initializing database tables...")
            await create_db(engine)
            set_postgres_engine(engine)
            logger.info("✓ Postgres connection established and tables initialized")
            db_service = DatabaseServiceSQL(engine)
            set_database_service(db_service)

        _init_ssh_service(job_backend, _settings)

        # Initialize Slurm service (SLURM backend only)
        slurm_service: SlurmService | None = None
        if job_backend == "slurm":
            slurm_service = SlurmService()
            logger.info("✓ SlurmService initialized")

        # Initialize messaging service
        redis_addr = f"{_settings.redis_internal_host}:{_settings.redis_internal_port}"
        logger.info(f"Initializing Redis messaging service at {redis_addr}...")
        messaging_service: MessagingService = MessagingServiceRedis()
        await messaging_service.connect(host=_settings.redis_internal_host, port=_settings.redis_internal_port)
        logger.info("✓ Messaging service connected")
        set_messaging_service(messaging_service)

        # Initialize JobScheduler
        logger.info("Initializing JobScheduler...")
        job_scheduler = JobScheduler(
            messaging_service=messaging_service,
            database_service=db_service,
            slurm_service=slurm_service,
        )
        set_job_scheduler(job_scheduler)
        logger.info("✓ JobScheduler initialized")

    except Exception as e:
        logger.error(f"Failed to initialize standalone services: {e}", exc_info=True)
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
    # for dirpath in [p for p in Path(f"{REPO_ROOT}/.results_cache").rglob("*") if p.is_dir()]:
    #     shutil.rmtree(dirpath)
