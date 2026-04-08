Quickstart
==========

This page takes you from zero to downloaded simulation results in three
commands. For a deeper walkthrough, see :doc:`/guides/end-to-end-workflow`.

.. contents:: On this page
   :local:
   :depth: 1

The End-to-End Workflow
-----------------------

Every simulation follows the same three-step pattern, regardless of which
client application you use:

1. **Build** a simulator container image from the vEcoli source code
2. **Run** a simulation workflow using that simulator
3. **Download** the results

CLI Quickstart
--------------

.. code-block:: bash

   # 1. Build the latest simulator (polls until the build finishes)
   uv run atlantis simulator latest

   # 2. Run a simulation (replace 11 with your Simulator ID from step 1)
   uv run atlantis simulation run my_experiment 11 \
     --generations 1 --seeds 1 --run-parca --poll

   # 3. Download results (replace 35 with your Simulation ID from step 2)
   uv run atlantis simulation outputs 35 --dest ./results

That's it. Your results are in ``./results/``.

TUI Quickstart
--------------

.. code-block:: bash

   uv run atlantis tui

The TUI opens an interactive terminal with a sidebar. Use the navigation
buttons to:

1. Click **Build Latest** under SIMULATORS
2. Click **Run New** under SIMULATIONS, fill in the form, and submit
3. Click **Download Outputs** and enter the simulation ID

Desktop GUI Quickstart
----------------------

.. code-block:: bash

   uv run atlantis tkapp

The Tkinter desktop app has a tabbed interface:

1. Go to the **Simulator** tab, click **Build Latest**
2. Go to the **Simulation** tab, fill in the form, click **Submit**
3. Go to the **Data** tab, enter the simulation ID, click **Download Outputs**

Web GUI Quickstart
------------------

.. code-block:: bash

   uv run atlantis gui

This opens a Marimo notebook in your browser with interactive sections for
each workflow step. Fill in the forms and click the run buttons in order.

What Happens During a Run
-------------------------

When you submit a simulation with ``--run-parca``, the platform runs a
multi-step pipeline on the HPC cluster:

1. **Parca** (parameter calculator) --- generates the simulation dataset
   from the vEcoli model (~5--8 min)
2. **Simulation** --- runs the whole-cell simulation for the specified
   number of generations and seeds (~5--7 min per gen per seed)
3. **Analysis** --- post-processes simulation outputs into TSV data files
   and plots (~3--5 min)

Without ``--run-parca``, step 1 is skipped and a pre-existing parca
dataset is used.

Next Steps
----------

- :doc:`/guides/end-to-end-workflow` --- detailed walkthrough of every step
- :doc:`/guides/choosing-a-client` --- which client app to use when
- :doc:`/guides/cli-reference` --- full command reference
