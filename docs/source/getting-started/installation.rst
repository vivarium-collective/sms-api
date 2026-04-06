Installation
============

Prerequisites
-------------

- **Python 3.12+** (pinned to 3.12.9 in this project)
- `uv <https://docs.astral.sh/uv/>`_ package manager
- **Git**

For running simulations, you also need access to a running SMS API server
(local development server, or a deployed instance).

Install from Source
-------------------

Clone the repository and install dependencies:

.. code-block:: bash

   git clone https://github.com/vivarium-collective/sms-api.git
   cd sms-api
   uv sync
   uv run pre-commit install

This installs the ``atlantis`` CLI, the full ``sms_api`` library, and all
development tools (linting, testing, type checking).

Verify the Installation
-----------------------

.. code-block:: bash

   # Check CLI is available
   uv run atlantis --help

   # Run the test suite
   uv run pytest

   # Run quality checks
   make check

Starting a Local Dev Server
---------------------------

To run the API locally for development:

.. code-block:: bash

   make gateway

This starts a FastAPI server on ``http://localhost:8888`` with auto-reload.

Configuration
-------------

Environment variables are loaded from ``assets/dev/config/.dev_env``. Key settings:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Variable
     - Description
   * - ``SLURM_SUBMIT_HOST``
     - SSH hostname for the HPC cluster
   * - ``SLURM_SUBMIT_USER``
     - SSH username for job submission
   * - ``SLURM_SUBMIT_KEY_PATH``
     - Path to SSH private key
   * - ``POSTGRES_*``
     - Database connection settings
   * - ``STORAGE_S3_BUCKET``
     - S3 bucket for simulation outputs
   * - ``STORAGE_S3_REGION``
     - AWS region for S3 bucket

See ``sms_api/config.py`` for the full list of configuration options.
