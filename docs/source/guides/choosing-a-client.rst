Choosing a Client Application
=============================

Atlantis provides four client applications. Each one exposes the same
end-to-end workflow --- the difference is the interface.

.. contents:: On this page
   :local:
   :depth: 2

Quick Comparison
----------------

.. list-table::
   :header-rows: 1
   :widths: 15 20 20 45

   * - Client
     - Launch Command
     - Best For
     - Notes
   * - **CLI**
     - ``uv run atlantis``
     - Scripting, automation, quick one-off commands
     - Fastest for experienced users. Supports ``--poll`` for blocking runs.
   * - **TUI**
     - ``uv run atlantis tui``
     - Interactive terminal sessions, SSH environments
     - Sidebar navigation, tabbed results, file browser. No browser needed.
   * - **Desktop GUI**
     - ``uv run atlantis tkapp``
     - Visual workflow on desktop, DAW-style layout
     - Animated Memphis theme, resizable panels, JSON viewer. Requires Tcl/Tk.
   * - **Web GUI**
     - ``uv run atlantis gui``
     - Point-and-click in the browser, collaborative demos
     - Marimo reactive notebook. Opens in your default browser.

CLI
---

The ``atlantis`` command-line interface is the primary tool for working with
the platform. It supports all workflow steps as subcommands:

.. code-block:: bash

   uv run atlantis simulator latest       # Build
   uv run atlantis simulation run ...     # Run
   uv run atlantis simulation outputs ... # Download

Use ``--help`` on any command or subcommand for details:

.. code-block:: bash

   uv run atlantis help
   uv run atlantis help simulation
   uv run atlantis simulation help

See :doc:`cli-reference` for the full command reference.

TUI (Terminal User Interface)
-----------------------------

The TUI is a full-screen terminal application built with
`Textual <https://textual.textualize.io/>`_. It presents the same workflow
steps as buttons in a sidebar:

.. code-block:: bash

   uv run atlantis tui

Features:

- Sidebar with grouped navigation (Simulators, Simulations, Parca, Analyses)
- Tabbed results view (rich text log + data table)
- Modal forms for simulation submission
- Built-in file browser for exploring downloaded outputs
- Server selector at the bottom

The TUI uses ANSI 256-color mode for compatibility with all terminals.

Desktop GUI (Tkinter)
---------------------

The desktop GUI is a native Tkinter application with a Memphis-inspired
visual theme:

.. code-block:: bash

   uv run atlantis tkapp

Features:

- Four-tab notebook: Simulator, Simulation, Data, Parca/Analysis
- Animated DNA helix banner and geometric Memphis decorations
- Treeview tables for listing simulators and simulations
- JSON syntax-highlighted output panel
- Pulsing status indicator
- Resizable split panels (DAW-style layout)

All API calls run in background threads --- the UI stays responsive during
long-running operations.

Web GUI (Marimo)
----------------

The web GUI is a `Marimo <https://marimo.io/>`_ reactive notebook that
opens in your browser:

.. code-block:: bash

   uv run atlantis gui

Features:

- Interactive forms with live reactivity
- CSS-animated Memphis banner
- Iconify icons throughout the interface
- Status badges with colour-coded states
- In-browser file listing after download

Workflow Mapping
----------------

All four clients map to the same six workflow steps:

.. list-table::
   :header-rows: 1
   :widths: 10 30 20 20 20

   * - Step
     - Action
     - CLI
     - TUI / Desktop GUI
     - Web GUI
   * - 1--3
     - Build simulator
     - ``simulator latest``
     - Build Latest button
     - Section 1 form
   * - 4
     - Submit simulation
     - ``simulation run``
     - Run New button / form
     - Section 2 form
   * - 5
     - Check status
     - ``simulation status``
     - Status button / Poll
     - Section 2 poll
   * - 6
     - Download results
     - ``simulation outputs``
     - Download Outputs
     - Section 3 form
