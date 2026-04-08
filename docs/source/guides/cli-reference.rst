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
   * - ``--poll / --no-poll``
     - off
     - Poll until completion

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

Get the status and log for a simulation.

.. code-block:: bash

   uv run atlantis simulation status SIMULATION_ID [--poll]

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
