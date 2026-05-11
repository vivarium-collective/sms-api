# PBG Live Sandbox

*Available since v0.9.3*

The **PBG Live Sandbox** is a self-contained Marimo app that lets you
explore and operate every part of the Atlantis compose subsystem live
from your browser — no local process-bigraph installation required.

## Launch

```bash
# Install Atlantis (if not already)
pip install sms-api

# Launch sandbox in app mode (recommended for demos)
uv run atlantis compose sandbox

# Notebook/edit mode — see and modify source cells
uv run atlantis compose sandbox --mode edit
```

Your browser opens automatically at `http://localhost:2718`.
All five tabs call the live Atlantis API at `https://sms.cam.uchc.edu`.

## The Five Tabs

### ⚗️ Process Runtime

Demonstrates the full stateful instance lifecycle from the
[Process Runtime](rest-process.md) endpoints.

**Walkthrough (no SBML needed):**

1. Select `MSEComparison` from the process dropdown
2. The config editor pre-fills with the live schema from the API:
   `{"ignore_nans": false, "columns_of_interest": []}`
3. Click **Initialize →** → API calls `POST /compose/v1/process/MSEComparison/initialize`,
   returns a UUID
4. Live `inputs` and `outputs` schemas appear automatically:
   - inputs: `{"results": "numeric_results"}`
   - outputs: `{"comparison_result": "map[map[map[float]]]"}`
5. Click **End Process** → instance released from memory and marked `ended` in DB

| Button | REST call | rest-process equivalent |
|---|---|---|
| Initialize → | `POST /process/{name}/initialize` | `POST /process/{name}` |
| *(auto)* | `GET /process/{name}/inputs/{id}` | `GET /process/{name}/inputs/{id}` |
| *(auto)* | `GET /process/{name}/outputs/{id}` | `GET /process/{name}/outputs/{id}` |
| End Process | `POST /process/{name}/end/{id}` | `DELETE /process/{name}/{id}` |

### 🧬 BioModels

Full EBI BioModels → SLURM simulation pipeline:

1. Click **Fetch IDs from EBI** → retrieves `BIOMD0000000001`–`005` etc.
2. Enter a model ID → **Get Metadata** → shows SBML files, authors, format
3. Select a simulator (`copasi` or `tellurium`) → **Submit Run → SLURM**
   - API fetches SBML from EBI
   - Extracts `UniformTimeCourse` from SED-ML
   - Builds a process-bigraph document (`CopasiUTCStep` or `TelluriumUTCStep`)
   - Dispatches SLURM job on UCONN CCAM HPC
   - Returns a simulation ID

See [BioModels](biomodels.md) for the full integration guide.

### 🦠 v2ecoli

Submit a whole-cell *E. coli* simulation directly from the browser:

1. Set **Duration** (seconds of biological time), **Seed**, **Interval**
2. Click **Submit v2ecoli → SLURM** → calls
   `POST /compose/v1/curated/ecoli?duration=10&seed=0&interval=1.0`
3. Returns a simulation ID — poll with
   `atlantis compose status <id> --base-url https://sms.cam.uchc.edu`

See [v2ecoli](v2ecoli.md) for full simulation options.

### 📋 Registry

Live table of all 11 link_registry entries with package origin, SBML
requirement, and config field names. This is the ground-truth view of what
`allocate_core()` discovers on the deployed API pod.

### 🔷 Types

Fetches all 42 bigraph-schema primitive types live from
`GET /compose/v1/types` — the same types used in all `config_schema`,
`inputs`, and `outputs` definitions across the compose system.

## Prerequisites

Only the Atlantis CLI is needed:

```bash
pip install sms-api
```

No local process-bigraph, pbsim-common, or v2ecoli installation required.
All computation runs on the Atlantis server and UCONN CCAM HPC.
