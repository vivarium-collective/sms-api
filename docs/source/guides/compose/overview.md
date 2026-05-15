# Compose Subsystem Overview

*Available since v0.9.0 · Latest additions: process runtime, BioModels, v2ecoli, wrapper generation (v0.9.3)*

The **compose** subsystem brings the [process-bigraph](https://github.com/vivarium-collective/process-bigraph)
ecosystem into Atlantis as a production-grade, HPC-backed simulation platform.
It runs alongside the vEcoli batch subsystem — both share the same PostgreSQL
database, SLURM cluster, and Singularity container infrastructure.

## What you can do

| Capability | CLI entry point | Guide |
|---|---|---|
| Whole-cell *E. coli* simulation | `atlantis compose ecoli` | [v2ecoli](v2ecoli.md) |
| Colony simulations (multi-seed) | `atlantis compose ecoli` × N | [v2ecoli → Colony](v2ecoli.md#colony-simulations) |
| BioModels database (EBI) | `atlantis compose biomodels-*` | [BioModels](biomodels.md) |
| COPASI / Tellurium (SBML) | `atlantis compose copasi/tellurium` | below |
| Stateful process runtime | `atlantis compose init/update/end` | [REST-Process](rest-process.md) |
| Interactive live sandbox | `atlantis compose sandbox` | [Sandbox](sandbox.md) |
| PBG wrapper generation | `atlantis compose wrapper-create` | [Wrappers](wrappers.md) |
| Package registry | `atlantis compose packages/package-get/package-audit/package-register` | [Registry](registry.md) |

## Architecture

Compose simulations differ from the vEcoli batch workflow in one key way:
**containers are generated automatically** from the simulation's Python dependencies
rather than built from a fixed git commit.

```text
User request (CLI / REST)
        │
        ▼
FastAPI  /compose/v1/...
        │
        ▼  parse PBG document
        │  auto-generate Singularity .def (pbest)
        │  hash definition → check container cache
        │
        ├─── container not cached ──▶ SLURM: build image (~15 min)
        │
        ▼  container cached
SCP experiment files to HPC
        │
        ▼
SLURM: singularity exec <container> python runner.py
        │
        ▼
results.zip ◀── SCP ◀── /experiment/output/
```

### Comparison with vEcoli batch

| Aspect | vEcoli Batch | Compose |
|---|---|---|
| Input | Config JSON + git repo | OMEX/PBG/SBML file or curated template |
| Engine | Nextflow + vEcoli | process-bigraph + Singularity |
| Container | Built once from git hash | Auto-generated from PBG dependencies |
| Base endpoints | `/api/v1/simulations` | `/compose/v1/` |
| CLI prefix | `atlantis simulation` | `atlantis compose` |

## Quick Start

### v2ecoli whole-cell simulation

```bash
uv run atlantis compose ecoli \
    --duration 60 \
    --seed 0 \
    --poll \
    --base-url https://sms.cam.uchc.edu
```

### COPASI ODE from SBML

```bash
uv run atlantis compose copasi my_model.sbml \
    --duration 100 \
    --num-data-points 200 \
    --poll \
    --base-url https://sms.cam.uchc.edu
```

### Tellurium from SBML

```bash
uv run atlantis compose tellurium my_model.sbml \
    --end-time 100 \
    --num-data-points 200 \
    --poll \
    --base-url https://sms.cam.uchc.edu
```

### Generic PBG / OMEX upload

```bash
uv run atlantis compose run mymodel.omex \
    --interval-time 1.0 \
    --poll \
    --base-url https://sms.cam.uchc.edu
```

### Fetch status and results

```bash
uv run atlantis compose status <SIM_ID> --base-url https://sms.cam.uchc.edu
uv run atlantis compose results <SIM_ID> --dest ./output --base-url https://sms.cam.uchc.edu
uv run atlantis compose doc <SIM_ID> --base-url https://sms.cam.uchc.edu
```

## Database

Compose uses the same PostgreSQL instance as the vEcoli subsystem, with
separate `compose_`-prefixed tables:

| Table | Contents |
|---|---|
| `compose_simulators` | Container definition registry (content-hashed) |
| `compose_simulations` | Simulation metadata and input PBG documents |
| `compose_hpcruns` | SLURM job tracking |
| `compose_packages` | Registered process-bigraph packages |
| `compose_bigraph_compute` | Registered processes and steps |
| `compose_process_instance` | Live process runtime instances (UUID-keyed) |
| `compose_process_update` | Audit trail of every `update` call |
| `compose_pbg_wrapper` | PBG wrapper generation jobs |

## Process-Bigraph Document Format

`.pbg` files are JSON documents describing a composable simulation:

```json
{
    "state": {
        "my_process": {
            "_type": "process",
            "address": "local:my_module.MyProcess",
            "config": { "rate": 0.1 },
            "interval": 1.0,
            "inputs": { "substrate": ["stores", "substrate"] },
            "outputs": { "product":  ["stores", "product"] }
        }
    }
}
```

Key concepts:

- **`address`** — Python resolution path for the compute class (`local:` = same environment)
- **`config`** — passed to the class constructor
- **`inputs`/`outputs`** — port names mapped to paths in the shared store tree
- **`interval`** — timestep for continuous processes

`.pbg` files can be submitted standalone or bundled inside an OMEX archive (ZIP).

## Notes

- Compose endpoints are independent of vEcoli batch endpoints — both run simultaneously.
- Container builds run on SLURM; first build with a new definition takes ~15 minutes.
  Subsequent simulations reuse the cached image instantly.
- Compose is available on SLURM deployments only (`sms-api-rke`, `sms-api-rke-dev`).
  It is not deployed on the Stanford/AWS Batch path.
