Architecture Overview
=====================

.. note::

   This section covers internal architecture and is primarily useful for
   developers working on Atlantis itself. End users should start with
   :doc:`/getting-started/quickstart`.

Atlantis is a FastAPI-based REST API for orchestrating whole-cell
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

HPC Workflow Pipeline
---------------------

1. **Build Image** -- Clone vEcoli repo, build container image (Singularity or Docker)
2. **Run Parca** -- Parameter calculator creates simulation dataset
3. **Run Simulation** -- Execute vEcoli simulation via SLURM or Nextflow + Batch
4. **Run Analysis** -- Post-process simulation outputs (8 analysis types)

Three Client Interfaces
-----------------------

The API has three client interfaces that all expose the same workflow:

1. **CLI** (``atlantis``) -- Typer-based command-line interface (``app/cli.py``)
2. **TUI** -- Textual-based terminal UI with sidebar navigation (``app/tui.py``)
3. **Web GUI** -- Marimo notebook with Tensorboard-style card layout (``app/gui.py``)

All three use ``E2EDataService`` (``app/app_data_service.py``) as the shared
data layer, which calls the REST API endpoints via ``httpx``.

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
