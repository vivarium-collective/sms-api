Atlantis API (SMS API)
=====================

.. image:: _static/wholecellecoli.png
   :width: 200px
   :align: right

**Atlantis API** is a REST API and CLI for designing, running, and analyzing
whole-cell simulations of *E. coli* using the `vEcoli <https://github.com/CovertLabEcoli/vEcoli-private>`_ model.

The platform orchestrates HPC jobs via SLURM on remote clusters or AWS Batch,
manages simulation metadata in PostgreSQL, and provides three client interfaces:
a **CLI** (``atlantis``), a **TUI**, and **Marimo** notebooks.

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   getting-started/installation
   getting-started/tutorial

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   guides/cli-reference
   guides/aws-s3-setup
   guides/qumulo-setup

.. toctree::
   :maxdepth: 2
   :caption: Architecture

   architecture/overview
   architecture/aws-batch
   architecture/build-pipeline

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/modules
