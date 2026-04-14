Configuration
=============

Server Connection
-----------------

All client applications connect to an Atlantis API server. The default is
``http://localhost:8080``.

Override per-command (CLI):

.. code-block:: bash

   uv run atlantis simulator latest --base-url https://sms.cam.uchc.edu

Override for your session:

.. code-block:: bash

   export API_BASE_URL=https://sms.cam.uchc.edu

In the TUI, Desktop GUI, and Web GUI, use the server selector dropdown
to switch servers at any time.

.. list-table:: Available Servers
   :header-rows: 1

   * - Server
     - URL
     - Notes
   * - Production
     - ``https://sms.cam.uchc.edu``
     - Main deployment
   * - Development
     - ``https://sms-dev.cam.uchc.edu``
     - Staging / test
   * - Local
     - ``http://localhost:8080``
     - Default; typically a port-forward to a remote cluster

Simulation Configuration Presets
--------------------------------

Available config filenames are **discovered dynamically** from the simulator's
vEcoli repository. Different simulators (different commits, repos, branches)
may have different configs available. Use the discovery command to see what's
available for a given simulator:

.. code-block:: bash

   uv run atlantis simulation configs SIMULATOR_ID

The default is ``api_simulation_default.json``. If the config file doesn't
exist in the repo, the server falls back to an embedded default template.

Analysis Module Discovery
-------------------------

Analysis modules available for ``--analysis-options`` depend on what exists in
the simulator's vEcoli repo under ``ecoli/analysis/{category}/``. Discover
available modules before submitting:

.. code-block:: bash

   uv run atlantis simulation analyses SIMULATOR_ID

Or via the REST API:

.. code-block:: bash

   curl http://localhost:8080/api/v1/simulations/discovery?simulator_id=16

Analysis defaults are **repo-aware**: private vEcoli repo simulators get cd1_*
modules by default; public repo simulators get no default analyses. User-specified
``--analysis-options`` always overrides the defaults.

Environment Variables
---------------------

These environment variables affect client behavior:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Variable
     - Description
   * - ``API_BASE_URL``
     - Default API server URL (overrides ``http://localhost:8080``)
