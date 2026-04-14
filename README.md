# sms-api: Simulating Microbial Systems

[![Homepage](https://img.shields.io/badge/Homepage-Visit-blue)](https://sms.cam.uchc.edu/home)
[![API Documentation](https://img.shields.io/badge/docs-REST%20API-blue)](https://sms.cam.uchc.edu/documentation)
[![Swagger UI](https://img.shields.io/badge/swagger_docs-Swagger_UI-green?logo=swagger)](https://sms.cam.uchc.edu/docs)
[![Build status](https://img.shields.io/github/actions/workflow/status/vivarium-collective/sms-api/main.yml?branch=main)](https://github.com/vivarium-collective/sms-api/actions/workflows/main.yml?query=branch%3Amain)
[![codecov](https://codecov.io/gh/vivarium-collective/sms-api/branch/main/graph/badge.svg)](https://codecov.io/gh/vivarium-collective/sms-api)
[![Commit activity](https://img.shields.io/github/commit-activity/m/vivarium-collective/sms-api)](https://img.shields.io/github/commit-activity/m/vivarium-collective/sms-api)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](./LICENSE)
[![Documentation](https://img.shields.io/badge/documentation-online-blue.svg)](https://sms-api.readthedocs.io/en/latest/)

<p align="center">
  <img src="https://github.com/vivarium-collective/sms-api/blob/main/docs/source/_static/wholecellecoli.png?raw=true" width="400" />
</p>

- **Github repository**: <https://github.com/vivarium-collective/sms-api/>
- **REST API Documentation**: [View Docs](https://sms.cam.uchc.edu/documentation)
- **Documentation(In progress, not complete)** <https://sms-api.readthedocs.io/en/latest/>

#### SMS API (otherwise known as _Atlantis API_):

Design, run, and analyze reproducible simulations of dynamic cellular processes in Escherichia coli. SMS API uses the vEcoli model. Please refer to [the vEcoli documentation](https://covertlab.github.io/vEcoli/) for more details.
The vEcoli documentation is very well written and we highly recommend that users become familiar with it.

## Quick Start (Atlantis CLI)

```bash
# Install
uv sync

# Build a simulator (public vEcoli repo)
uv run atlantis simulator latest --repo-url https://github.com/CovertLab/vEcoli --branch master

# Discover available configs and analysis modules for your simulator
uv run atlantis simulation configs 16
uv run atlantis simulation analyses 16

# Run a simulation (1 generation, 1 seed)
uv run atlantis simulation run my-experiment 16 --generations 1 --seeds 1 --poll

# Check status (fast — shows log tail + status)
uv run atlantis simulation status 37

# Download outputs
uv run atlantis simulation outputs 37 --dest ./results

# Help works at any nesting level
uv run atlantis simulation run help
```

## Three Client Interfaces

All three clients expose the same end-to-end workflow:

| Client | Launch | Best For |
|--------|--------|----------|
| **CLI** | `uv run atlantis <command>` | Scripting, automation, quick commands |
| **TUI** | `uv run atlantis tui` | Interactive terminal sessions, SSH |
| **GUI** | `uv run atlantis gui` | Browser-based point-and-click |

## Architecture

### Server

A Kubernetes cluster running a FastAPI application, hosted at [https://sms.cam.uchc.edu/](https://sms.cam.uchc.edu/). Supports two compute backends:

- **SLURM** (UCONN CCAM on-prem HPC) — `sms-api-rke` namespace
- **K8s + AWS Batch** (GovCloud) — `sms-api-stanford-test` namespace

**Routers:**
- `core`: Administrative — simulator builds, parca management
- `api`: User-facing — simulation workflows, status, data download

### Client

Three client applications connect to the server:

- **CLI** (`app/cli.py`): Typer + Rich, Memphis design theme
- **TUI** (`app/tui.py`): Textual terminal app with animated banner, auto-listing with status, file explorer
- **GUI** (`app/gui.py`): Marimo reactive notebook with Memphis-styled cards

---

```
    ╭────────────────────────────────────────────╮
    │    ▄▀▄ ▀█▀ █   ▄▀▄ █▄ █ ▀█▀ █ ▄▀▀          │∿~∿~~∿~∿~
    │    █▀█  █  █▄▄ █▀█ █ ▀█  █  █ ▄██           │~∿~∿~~∿~∿
    │     ∿ whole-cell simulation platform ∿     │∿~~∿~∿~~∿
    ╰────────────────────────────────────────────╯
```

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 200" width="100" height="200">
  <style>
    .sk { fill: none; stroke: #006600; stroke-width: 7; stroke-linecap: round; }
  </style>
  <path class="sk"
    d="M 50 10
       C 10 10, 10 100, 50 100
       C 90 100, 90 190, 50 190"
  />
  <line class="sk" x1="50" y1="10" x2="50" y2="190" />
</svg>
