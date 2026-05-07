# Compose (Process-Bigraph) Simulations

*Available since v0.9.0*

The **compose** subsystem enables running reproducible biological simulations
using the [process-bigraph](https://github.com/vivarium-collective/process-bigraph)
framework. It supports multiple simulation engines — including **v2ecoli**
(whole-cell *E. coli*), **COPASI**, and **Tellurium** — through a unified API
and CLI.

## Overview

Compose simulations work differently from the vEcoli batch workflow:

| Aspect | vEcoli (Batch) | Compose |
|--------|----------------|---------|
| **Input** | Config JSON + git repo | OMEX/PBG/SBML file upload or curated templates |
| **Engine** | Nextflow + vEcoli | process-bigraph + Singularity |
| **Container** | Pre-built from git hash | Auto-generated from PBG dependencies |
| **Endpoints** | `/api/v1/simulations` | `/compose/v1/simulation/*` |
| **CLI** | `atlantis simulation` | `atlantis compose` |

## REST API Endpoints

All compose endpoints are mounted at `/compose/v1/`.

### Simulation Lifecycle

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/simulation/run` | Upload OMEX/PBG/SBML and run simulation |
| `GET` | `/simulation/{id}/status` | Get SLURM job status |
| `GET` | `/simulation/{id}/results` | Download results as zip |
| `GET` | `/simulation/{id}/document` | Retrieve the PBG document used |
| `GET` | `/simulations/status/batch` | Batch status lookup (multiple IDs) |

### Compute Registry

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/simulators` | List registered compose simulators |
| `GET` | `/processes` | List registered BigGraph processes |
| `GET` | `/steps` | List registered BigGraph steps |
| `GET` | `/simulator/{id}/build/status` | Container build status |

### Curated Simulators

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/curated/ecoli` | Run v2ecoli whole-cell simulation |
| `POST` | `/curated/copasi` | Run COPASI simulation from SBML |
| `POST` | `/curated/tellurium` | Run Tellurium simulation from SBML |

## CLI Commands

All compose commands are under `atlantis compose`:

```bash
uv run atlantis compose help
```

### Run a generic simulation

Upload an OMEX, PBG, or SBML file:

```bash
uv run atlantis compose run mymodel.omex --poll --base-url https://sms.cam.uchc.edu
```

Options:
- `--interval-time` — simulation interval/duration (default: 1.0)
- `--batch / --no-batch` — batch submission mode
- `--poll / --no-poll` — wait for completion

### Run v2ecoli (whole-cell E. coli)

No file upload needed — the biological model is pre-computed in the ParCa cache:

```bash
uv run atlantis compose ecoli \
    --duration 60 \
    --seed 0 \
    --interval 1.0 \
    --base-url https://sms.cam.uchc.edu \
    --poll
```

Options:
- `--duration` — simulation duration in seconds (default: 60)
- `--seed` — random seed for stochastic processes (default: 0)
- `--interval` — execution timestep in seconds (default: 1.0)
- `--features` — JSON list of feature modules (default: `[]`)
- `--cache-dir` — ParCa cache path inside container (default: `out/cache`)

### Run COPASI

```bash
uv run atlantis compose copasi model.sbml \
    --start-time 0 \
    --duration 100 \
    --num-data-points 200 \
    --base-url https://sms.cam.uchc.edu
```

### Run Tellurium

```bash
uv run atlantis compose tellurium model.sbml \
    --start-time 0 \
    --end-time 100 \
    --num-data-points 200 \
    --base-url https://sms.cam.uchc.edu
```

### Check status and results

```bash
# Status
uv run atlantis compose status <SIMULATION_ID> --base-url https://sms.cam.uchc.edu

# Download results
uv run atlantis compose results <SIMULATION_ID> --dest ./compose_output

# Retrieve the PBG document
uv run atlantis compose doc <SIMULATION_ID>
```

### Registry queries

```bash
# List all compose simulators (container definitions)
uv run atlantis compose simulators

# List registered processes and steps
uv run atlantis compose processes
uv run atlantis compose steps

# Check container build status
uv run atlantis compose build-status <SIMULATOR_ID>
```

## Process-Bigraph Document Format

Compose simulations use `.pbg` files — JSON documents describing composable
simulation models:

```json
{
    "state": {
        "my_process": {
            "_type": "process",
            "address": "local:module.ClassName",
            "config": { "param": 42 },
            "interval": 1.0,
            "inputs": { "substrate": ["stores", "substrate"] },
            "outputs": { "product": ["stores", "product"] }
        }
    }
}
```

Key concepts:
- **Processes** — continuous compute units (ODE solvers, etc.)
- **Steps** — discrete one-shot compute units
- **Ports** — named I/O connections (`inputs`/`outputs`)
- **Stores** — shared state tree; ports wire to store paths
- **Address** — Python module path for the compute class

`.pbg` files can be submitted standalone or bundled inside an OMEX archive
(ZIP containing `.pbg` + `.sbml` + metadata).

## Document Persistence

When a simulation is submitted, the uploaded document content is stored in the
database. For OMEX archives, the contained `.pbg` file is extracted. You can
retrieve the document later:

```bash
uv run atlantis compose doc <SIMULATION_ID>
```

This returns the original PBG JSON or SBML XML that was used.

## Notes

- Compose endpoints are independent of the existing vEcoli simulation endpoints.
  Both can run simultaneously.
- Compose uses the same PostgreSQL database (separate `compose_`-prefixed tables).
- Container builds and simulation jobs run on HPC via SLURM.
- Optional NATS messaging for real-time worker event streaming.
