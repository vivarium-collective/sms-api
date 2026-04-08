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

When submitting a simulation, you choose a configuration preset via
``--config-filename`` (CLI) or the config dropdown (GUI/TUI):

.. list-table::
   :header-rows: 1

   * - Preset
     - Description
   * - ``api_simulation_default.json``
     - Standard configuration (default)
   * - ``api_simulation_default_ccam.json``
     - CCAM configuration
   * - ``api_simulation_default_aws_cdk.json``
     - AWS CDK / Batch configuration
   * - ``api_simulation_ptools_ccam.json``
     - PTools CCAM configuration

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
