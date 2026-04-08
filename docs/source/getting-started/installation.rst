Installation
============

Prerequisites
-------------

- **Python 3.12** (pinned to 3.12.9)
- `uv <https://docs.astral.sh/uv/>`_ package manager
- **Git**

You also need access to a running Atlantis API server --- either a deployed
instance (production or development) or a local development server.

Install from Source
-------------------

.. code-block:: bash

   git clone https://github.com/vivarium-collective/sms-api.git
   cd sms-api
   uv sync

This installs the ``atlantis`` command and all four client applications
(CLI, TUI, Desktop GUI, Web GUI).

Verify the Installation
-----------------------

.. code-block:: bash

   uv run atlantis help

You should see the Atlantis banner and a list of available commands.

Tkinter Note (macOS)
~~~~~~~~~~~~~~~~~~~~

The Desktop GUI (``atlantis tkapp``) uses Tkinter, which requires Tcl/Tk.
If you see a ``TclError`` about ``init.tcl``, set the Tcl library path:

.. code-block:: bash

   # Find your Tcl 8.6 library (common locations)
   find ~/.local/share/mamba -name "init.tcl" -path "*/tcl8.6*" 2>/dev/null

   # Add to your shell profile (~/.zshrc or ~/.bashrc)
   export TCL_LIBRARY="/path/to/tcl8.6"

Connecting to an API Server
---------------------------

By default, Atlantis connects to ``http://localhost:8080``. Override this
with ``--base-url`` on any command, or set the ``API_BASE_URL`` environment
variable:

.. code-block:: bash

   # Use a specific server for one command
   uv run atlantis simulator latest --base-url https://sms.cam.uchc.edu

   # Or set it for your entire session
   export API_BASE_URL=https://sms.cam.uchc.edu

.. list-table:: Available Servers
   :header-rows: 1

   * - Server
     - URL
   * - Production
     - ``https://sms.cam.uchc.edu``
   * - Development
     - ``https://sms-dev.cam.uchc.edu``
   * - Local (default)
     - ``http://localhost:8080``
