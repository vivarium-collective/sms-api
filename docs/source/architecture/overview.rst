Architecture Overview
====================

Atlantis API (SMS API) is a FastAPI-based REST API for orchestrating whole-cell
simulations of *E. coli* using the vEcoli model.

.. contents:: On this page
   :local:
   :depth: 2

System Components
-----------------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Component
     - Description
   * - FastAPI Server
     - REST API hosted at ``https://sms.cam.uchc.edu/``
   * - SLURM / AWS Batch
     - HPC job submission and monitoring
   * - Singularity + Docker
     - Containerized vEcoli simulator execution
   * - PostgreSQL
     - Simulation metadata, job records, parca datasets
   * - Nextflow
     - Workflow orchestration (parca -> simulation -> analysis)
   * - S3
     - Simulation output storage

Directory Structure
-------------------

.. code-block:: text

   sms_api/
   +-- api/           # FastAPI routes and generated OpenAPI client
   |   +-- routers/   # Route handlers
   |   +-- client/    # Auto-generated OpenAPI client (do NOT edit)
   |   +-- spec/      # Generated OpenAPI spec
   +-- analysis/      # Analysis job orchestration
   +-- common/        # Shared utilities
   |   +-- hpc/       # SLURM service, K8s job service, job models
   |   +-- ssh/       # SSH session management (asyncssh)
   |   +-- storage/   # FileService (S3, Qumulo)
   |   +-- gateway/   # Gateway I/O and models
   |   +-- messaging/ # MessagingService (Redis-backed)
   +-- data/          # Data services and BioCyc integration
   +-- simulation/    # SimulationService, DatabaseService, ORM tables
   +-- config.py      # Settings via pydantic-settings
   +-- dependencies.py # Dependency injection

Request Flow
------------

API requests hit FastAPI routers (``sms_api/api/routers/``) which depend on
services injected via ``sms_api/dependencies.py``. The dependency module manages
global singletons for SSH sessions, database connections, file storage,
messaging, and the simulation service.

Key Services
------------

**SimulationService** (``simulation/simulation_service.py``)
   Orchestrates the full HPC workflow (build, parca, simulate). Two
   implementations: ``SimulationServiceHpc`` (SLURM) and
   ``SimulationServiceK8s`` (K8s + AWS Batch).

**DatabaseService** (``simulation/database_service.py``)
   SQLAlchemy async ORM for simulation metadata.

**SlurmService** (``common/hpc/slurm_service.py``)
   SLURM job submission and monitoring via SSH.

**K8sJobService** (``common/hpc/k8s_job_service.py``)
   Kubernetes Job CRUD operations for Nextflow workflow heads.

**FileService** (``common/storage/``)
   Abstraction over S3 and Qumulo S3 storage backends.

HPC Workflow Pipeline
---------------------

1. **Build Image** -- Clone vEcoli repo, build container image (Singularity or Docker)
2. **Run Parca** -- Parameter calculator creates simulation dataset
3. **Run Simulation** -- Execute vEcoli simulation via SLURM or Nextflow + Batch
4. **Run Analysis** -- Post-process simulation outputs (8 analysis types)

Three Client Interfaces
-----------------------

The API has three client interfaces that all expose the same workflow:

1. **CLI** (``atlantis``) -- Typer-based command-line interface (``app/cli_app.py``)
2. **TUI** -- Textual-based terminal UI with sidebar navigation (``app/tui.py``)
3. **Marimo** -- Web-based notebook interfaces (``app/ui/``)

All three use ``E2EDataService`` (``app/app_data_service.py``) as the shared
data layer, which calls the REST API endpoints via ``httpx``.
