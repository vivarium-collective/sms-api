Choosing a Client Application
=============================

Atlantis provides three client applications. Each one exposes the same
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
   * - **Web GUI**
     - ``uv run atlantis gui``
     - Point-and-click in the browser, collaborative demos
     - Marimo reactive notebook with Tensorboard-style cards.

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

Web GUI (Marimo)
----------------

The web GUI is a `Marimo <https://marimo.io/>`_ reactive notebook that
opens in your browser:

.. code-block:: bash

   uv run atlantis gui

Features:

- Tensorboard-style card layout with rounded edges and coloured headers
- Interactive forms with live reactivity
- CSS-animated Memphis banner
- Iconify icons throughout the interface
- Status badges with colour-coded states
- Grid layout for compact, dashboard-like arrangement

Workflow Mapping
----------------

All three clients map to the same six workflow steps:

.. list-table::
   :header-rows: 1
   :widths: 10 30 20 20 20

   * - Step
     - Action
     - CLI
     - TUI
     - Web GUI
   * - 1--3
     - Build simulator
     - ``simulator latest``
     - Build Latest button
     - Simulator card
   * - 4
     - Submit simulation
     - ``simulation run``
     - Run New button / form
     - Simulation card
   * - 5
     - Check status
     - ``simulation status``
     - Status button / Poll
     - Status check card
   * - 6
     - Download results
     - ``simulation outputs``
     - Download Outputs
     - Outputs card
