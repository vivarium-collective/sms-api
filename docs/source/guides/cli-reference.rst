CLI Reference
=============

The ``atlantis`` CLI provides commands for the full simulation lifecycle.

.. contents:: Commands
   :local:
   :depth: 2

Top-Level
---------

.. code-block:: text

   atlantis [OPTIONS] COMMAND [ARGS]...

Commands: ``simulator``, ``simulation``, ``parca``, ``analysis``, ``demo``,
``tui``, ``gui``, ``help``.

Global option: ``--base-url`` selects the API server (default:
``http://localhost:8080``). Can also be set via the ``API_BASE_URL``
environment variable.

help
----

Show help for the top-level CLI or any command group:

.. code-block:: bash

   uv run atlantis help
   uv run atlantis help simulator
   uv run atlantis simulator help    # equivalent

simulator
---------

Manage simulator (vEcoli) container images.

simulator latest
~~~~~~~~~~~~~~~~

Fetch the latest commit, upload, and build a simulator image.

.. code-block:: bash

   uv run atlantis simulator latest [OPTIONS]

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Option
     - Description
   * - ``--repo-url TEXT``
     - Git repo URL. Defaults to the configured default.
   * - ``--branch TEXT``
     - Git branch. Defaults to ``master``.
   * - ``--force / --no-force``
     - Force rebuild even if a completed build exists.

simulator list
~~~~~~~~~~~~~~

List all registered simulator versions.

.. code-block:: bash

   uv run atlantis simulator list

simulator status
~~~~~~~~~~~~~~~~

Get the container build status for a simulator.

.. code-block:: bash

   uv run atlantis simulator status SIMULATOR_ID

simulation
----------

Run and inspect simulation workflows.

simulation run
~~~~~~~~~~~~~~

Submit a simulation workflow (parca -> simulation -> analysis).

.. code-block:: bash

   uv run atlantis simulation run EXPERIMENT_ID SIMULATOR_ID [OPTIONS]

.. list-table::
   :header-rows: 1
   :widths: 30 15 55

   * - Option
     - Default
     - Description
   * - ``--config-filename``
     - ``api_simulation_default.json``
     - Simulation config preset
   * - ``--generations``
     - 1
     - Generations per seed
   * - ``--seeds``
     - 3
     - Number of lineages
   * - ``--description``
     - auto
     - Custom run description
   * - ``--run-parca / --no-run-parca``
     - off
     - Run parameter calculator first
   * - ``--observables``
     - baseline (all analysis paths)
     - Comma-separated dot-path observables to record.
       Limits simulation output to the specified vEcoli state paths.
       If omitted, uses the default baseline set (55 paths covering
       all analysis modules).
   * - ``--analysis-options``
     - default ptools modules
     - JSON string overriding which analysis modules run as part of the
       workflow. E.g. ``'{"multiseed": {"ptools_rna": {"n_tp": 10}}}'``.
       If omitted, uses the default set.
   * - ``--poll / --no-poll``
     - off
     - Poll until completion

**Examples:**

.. code-block:: bash

   # Minimal: 1 generation, 1 seed, default observables
   uv run atlantis simulation run my-experiment 11

   # Large-scale: 10 generations, 1000 seeds, with parca
   uv run atlantis simulation run baseline-1k 11 --generations 10 --seeds 1000 --run-parca

   # Poll until completion
   uv run atlantis simulation run quick-test 11 --generations 1 --seeds 1 --poll

   # Custom observables (only mass and bulk)
   uv run atlantis simulation run mass-only 11 --observables "bulk,listeners.mass.cell_mass,listeners.mass.dry_mass"

   # Custom analysis modules
   uv run atlantis simulation run my-exp 11 \
     --analysis-options '{"multiseed": {"ptools_rna": {"n_tp": 10}, "ptools_rxns": {"n_tp": 10}}}'

   # Target a specific server
   uv run atlantis simulation run test1 11 --base-url https://sms.cam.uchc.edu

   # With a custom config preset and description
   uv run atlantis simulation run violacein-run 12 \
     --config-filename api_test_violacein_with_metabolism.json \
     --generations 5 --seeds 10 \
     --description "Violacein pathway test with metabolism" \
     --poll

simulation get
~~~~~~~~~~~~~~

Get a simulation by its database ID.

.. code-block:: bash

   uv run atlantis simulation get SIMULATION_ID

simulation list
~~~~~~~~~~~~~~~

List all simulations.

.. code-block:: bash

   uv run atlantis simulation list

simulation status
~~~~~~~~~~~~~~~~~

Show the workflow log tail and status for a simulation. Displays the Nextflow
executor summary block (last progress snapshot) followed by a status panel.
Fast even for large simulations — only the log tail is rendered.

.. code-block:: bash

   uv run atlantis simulation status SIMULATION_ID [--poll]

Use ``--poll`` to keep checking until the simulation reaches a terminal state.

simulation log
~~~~~~~~~~~~~~

Show the full Nextflow workflow log for a simulation (any state).

.. code-block:: bash

   uv run atlantis simulation log SIMULATION_ID

simulation cancel
~~~~~~~~~~~~~~~~~

Cancel a running simulation.

.. code-block:: bash

   uv run atlantis simulation cancel SIMULATION_ID

simulation outputs
~~~~~~~~~~~~~~~~~~

Download simulation output data as a tar.gz archive.

.. code-block:: bash

   uv run atlantis simulation outputs SIMULATION_ID [--dest DIR]

``--dest`` defaults to ``./simulation_id_<ID>``.

simulation analysis
~~~~~~~~~~~~~~~~~~~

Run standalone analysis on existing simulation output. Useful for re-running
specific analysis modules on a completed simulation without re-running the
entire workflow.

.. code-block:: bash

   uv run atlantis simulation analysis SIMULATION_ID [--modules JSON]

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Option
     - Description
   * - ``--modules``
     - JSON string of analysis modules keyed by domain.
       E.g. ``'{"multiseed": {"ptools_rna": {"n_tp": 10}}}'``.
       If omitted, runs default ptools modules (rna, rxns, proteins).

**Examples:**

.. code-block:: bash

   # Default ptools analysis on simulation 44
   uv run atlantis simulation analysis 44

   # Specific modules only
   uv run atlantis simulation analysis 44 \
     --modules '{"multiseed": {"ptools_rna": {"n_tp": 10}, "cd1_fluxomics": {"generation_lower_bound": 5}}}'

parca
-----

Inspect parca (parameter calculator) datasets and runs.

parca list
~~~~~~~~~~

.. code-block:: bash

   uv run atlantis parca list

parca status
~~~~~~~~~~~~

.. code-block:: bash

   uv run atlantis parca status PARCA_ID

analysis
--------

Inspect analysis jobs and outputs.

analysis get / status / log / plots
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   uv run atlantis analysis get ANALYSIS_ID
   uv run atlantis analysis status ANALYSIS_ID
   uv run atlantis analysis log ANALYSIS_ID
   uv run atlantis analysis plots ANALYSIS_ID

Application Launchers
---------------------

tui
~~~

Launch the interactive terminal UI.

.. code-block:: bash

   uv run atlantis tui [--base-url URL]

Three navigation buttons (Simulations, Simulators, Analyses) with auto-listing
and status enrichment. Double-click a completed simulation to browse its output
files interactively.

gui
~~~

Launch the Marimo web GUI (opens in browser).

.. code-block:: bash

   uv run atlantis gui [--base-url URL]

demo
----

demo get-data
~~~~~~~~~~~~~

Download S3 simulation outputs directly (no running API server needed).

.. code-block:: bash

   uv run atlantis demo get-data [--dest DIR]

Requires ``TEST_BUCKET_EXPERIMENT_OUTDIR`` and S3 credentials in environment.

Observables
-----------

The ``--observables`` flag controls which vEcoli state paths are recorded in
simulation output. Each observable is a dot-separated path that maps to a node
in the simulation state tree:

.. code-block:: text

   bulk                                   # all bulk molecule counts
   listeners.mass.cell_mass               # scalar cell mass
   listeners.fba_results.base_reaction_fluxes  # FBA fluxes
   listeners.monomer_counts               # protein counts

When omitted, the **baseline set** (55 paths) is used automatically. This set
covers every analysis module shipped with vEcoli (single, multigeneration,
multiseed, multivariant). The full list is defined in
``sms_api.common.simulator_defaults.DEFAULT_OBSERVABLES``.

To emit **all** simulation data (no filtering), pass an empty string:
``--observables ""``.

.. note::

   The baseline observables reference file is also available at
   ``assets/observables_baseline.json`` in the repository.
