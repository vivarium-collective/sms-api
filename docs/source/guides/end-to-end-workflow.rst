End-to-End Workflow
===================

This guide walks through the complete simulation workflow in detail,
with examples for the CLI. The same steps apply in the TUI, Desktop GUI,
and Web GUI --- see :doc:`choosing-a-client` for how each client maps to
these steps.

.. contents:: On this page
   :local:
   :depth: 2

Overview
--------

The workflow has three phases:

.. code-block:: text

   Build Simulator  -->  Run Simulation  -->  Download Results
        (1-3)               (4-5)               (6)

Broken down into six steps:

1. Fetch the latest simulator source from Git
2. Upload and trigger a container build
3. Poll the build until it completes
4. Submit a simulation workflow
5. Poll the simulation until it completes
6. Download the output data

Step 1--3: Build a Simulator
-----------------------------

A **simulator** is a containerized build of the vEcoli whole-cell model.
You need a completed simulator before running any simulations.

.. code-block:: bash

   uv run atlantis simulator latest \
     --repo-url https://github.com/CovertLabEcoli/vEcoli-private \
     --branch master

This single command handles all three sub-steps: fetching the latest
commit, uploading it, and polling the container build to completion.

The output shows a **Simulator ID** --- save this for the next step:

.. code-block:: text

   Commit: a1b2c3d  (https://github.com/CovertLabEcoli/vEcoli-private @ master)
   Simulator ID: 11
   Waiting for build...
     [15s] status: running
     [30s] status: running
     ...
     [120s] status: completed
   +----- Build --- simulator 11 -----+
   | COMPLETED                        |
   +----------------------------------+

Managing simulators
~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # List all registered simulators
   uv run atlantis simulator list

   # Check the build status of a specific simulator
   uv run atlantis simulator status 11

   # Force a rebuild (e.g. after a code change on the same commit)
   uv run atlantis simulator latest --force

Step 4--5: Run a Simulation
----------------------------

Submit a simulation workflow using your simulator ID:

.. code-block:: bash

   uv run atlantis simulation run my_experiment 11 \
     --generations 1 \
     --seeds 1 \
     --run-parca \
     --poll

.. list-table:: Required Arguments
   :header-rows: 1

   * - Argument
     - Description
   * - ``EXPERIMENT_ID``
     - A name you choose for this experiment (e.g. ``my_experiment``)
   * - ``SIMULATOR_ID``
     - The database ID from Step 1--3

.. list-table:: Options
   :header-rows: 1
   :widths: 25 15 60

   * - Option
     - Default
     - Description
   * - ``--generations``
     - 1
     - Number of cell generations to simulate per seed
   * - ``--seeds``
     - 3
     - Number of independent lineages (seeds) to run
   * - ``--run-parca``
     - off
     - Run the parameter calculator before simulation
   * - ``--poll``
     - off
     - Wait and display status updates until completion
   * - ``--config-filename``
     - ``api_simulation_default.json``
     - Simulation configuration preset
   * - ``--observables``
     - baseline (55 paths)
     - Comma-separated dot-path observables to record.
       Limits output to specified vEcoli state paths.
       If omitted, the default baseline set is used (covers all analysis modules).
   * - ``--description``
     - auto-generated
     - Custom description for the run

The pipeline
~~~~~~~~~~~~

With ``--run-parca``, the server runs: **parca** --> **simulation** --> **analysis**.
Without it, a pre-existing parca dataset is reused, saving ~5--8 minutes.

With ``--poll``, the CLI prints status updates every 30 seconds:

.. code-block:: text

   Simulation submitted!  ID: 35

   Polling simulation status...
     [30s] status: running
     [60s] status: running
     ...
     [1110s] status: completed
   +---- Simulation 35 ----+
   | COMPLETED              |
   +------------------------+

   Download data:  atlantis simulation outputs 35 --dest ./results

Fire-and-forget mode
~~~~~~~~~~~~~~~~~~~~

Submit without polling, then check later:

.. code-block:: bash

   # Submit and return immediately
   uv run atlantis simulation run my_experiment 11 --generations 2 --seeds 3

   # Check status at any time
   uv run atlantis simulation status 35

   # Or start polling a running simulation
   uv run atlantis simulation status 35 --poll

Managing simulations
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # List all simulations
   uv run atlantis simulation list

   # Get details for a specific simulation
   uv run atlantis simulation get 35

   # Cancel a running simulation
   uv run atlantis simulation cancel 35

   # View the full Nextflow workflow log
   uv run atlantis simulation log 35

Step 6: Download Results
-------------------------

Once the simulation completes, download the output data:

.. code-block:: bash

   uv run atlantis simulation outputs 35 --dest ./results

This downloads a ``.tar.gz`` archive and extracts it. The output structure:

.. code-block:: text

   results/
     <experiment_id>/
       analyses/
         variant=0/
           plots/
             analysis=cd1_fluxomics/
               cd1_fluxomics_detailed.tsv
               metadata.json
             analysis=cd1_proteomics/
               proteomics.tsv
               metadata.json
             analysis=ptools_proteins/
               ptools_proteins.tsv
               metadata.json
             ...
       nextflow/
         workflow_config.json

Inspecting Parca Datasets
--------------------------

The parameter calculator (parca) runs as part of the simulation pipeline.
You can inspect parca datasets independently:

.. code-block:: bash

   # List all parca datasets
   uv run atlantis parca list

   # Check the status of a specific parca run
   uv run atlantis parca status <PARCA_ID>

Running Standalone Analysis
----------------------------

You can re-run specific analysis modules on a completed simulation without
re-running the entire workflow. This is useful when the original workflow
included unwanted modules or you want to try different parameters:

.. code-block:: bash

   # Default ptools analysis on a completed simulation
   uv run atlantis simulation analysis 44

   # Only specific modules
   uv run atlantis simulation analysis 44 \
     --modules '{"multiseed": {"ptools_rna": {"n_tp": 10}, "ptools_rxns": {"n_tp": 10}}}'

Inspecting Analysis Results
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Each simulation produces analysis outputs. You can inspect them individually:

.. code-block:: bash

   # Get the analysis spec
   uv run atlantis analysis get <ANALYSIS_ID>

   # Check analysis run status
   uv run atlantis analysis status <ANALYSIS_ID>

   # View the analysis log
   uv run atlantis analysis log <ANALYSIS_ID>

   # List analysis plot outputs
   uv run atlantis analysis plots <ANALYSIS_ID>
