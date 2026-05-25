# BioModels Integration

*Available since v0.9.1*

The **BioModels integration** enables running, auditing, and regression-testing
[EBI BioModels](https://www.ebi.ac.uk/biomodels/) directly through the Atlantis
API and CLI. It provides a complete pipeline from EBI model discovery to HPC
simulation dispatch --- without writing any custom scripts.

## Overview

[BioModels](https://www.ebi.ac.uk/biomodels/) is the world's largest curated
database of published mathematical models of biological systems. Atlantis
integrates with the EBI REST API to fetch models on demand, parses their SED-ML
descriptions to extract simulation parameters, constructs
[process-bigraph](https://github.com/vivarium-collective/process-bigraph)
documents, and dispatches them to HPC via SLURM.

### Three use cases

| Use Case | Description | CLI command |
|----------|-------------|-------------|
| **Run** | Simulate a single BioModel (SBML/ODE) with COPASI or Tellurium | `biomodels-run` |
| **Audit** | Run the same model through two simulators side-by-side, compare | `biomodels-audit` |
| **Regression** | Screen up to 1,000 models as a validation suite | `biomodels-regression` |

### How it fits in the compose subsystem

```text
EBI BioModels REST API
        |
        | OMEX download (SBML + SED-ML)
        v
biomodels_service.py
  - load_biomodel()         ← fetch OMEX from EBI
  - _read_sedml_doc()       ← parse SED-ML
  - _extract_first_utc()    ← extract time-course params (start, end, n_points)
        |
        v
biomodel_documents.py
  - make_biomodel_document()       ← single-simulator PBG document
  - make_multi_biomodel_document() ← multi-model document
        |
        v
handlers.py → run_compose_curated()
        |
        v
SLURM job (Singularity container + pbsim-common)
        |
        v
results.zip (species concentrations, counts)
```

---

## Quick Start

### List available BioModel identifiers

```bash
uv run atlantis compose biomodels-ids \
    --base-url https://sms.cam.uchc.edu
```

Returns a list of BioModels IDs from the EBI registry (e.g.
`BIOMD0000000001`, `BIOMD0000000012`, ...).

### Get metadata for a specific model

```bash
uv run atlantis compose biomodels-meta BIOMD0000000001 \
    --base-url https://sms.cam.uchc.edu
```

Returns the model's name, description, authors, and supported simulators.

### Run a single model

```bash
uv run atlantis compose biomodels-run BIOMD0000000001 \
    --simulator copasi \
    --poll \
    --base-url https://sms.cam.uchc.edu
```

This command:
1. Fetches the OMEX from EBI
2. Parses the SED-ML to determine simulation parameters
3. Generates a process-bigraph document with a `CopasiUTCStep`
4. Submits an OMEX to HPC via SLURM
5. Polls until complete (with `--poll`)

---

## REST API Reference

All biomodels endpoints are mounted under `/compose/v1/biomodels/`.

### List BioModel identifiers

```
GET /compose/v1/biomodels/identifiers
```

Returns the list of curated BioModel IDs available from EBI.

**Response** (`200 OK`):
```json
{
  "ids": ["BIOMD0000000001", "BIOMD0000000012", ...]
}
```

---

### Get model metadata

```
GET /compose/v1/biomodels/{biomodel_id}/metadata
```

**Path parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `biomodel_id` | string | EBI BioModels ID (e.g. `BIOMD0000000001`) |

**Response** (`200 OK`) — `BiomodelInfo`:
```json
{
  "biomodel_id": "BIOMD0000000001",
  "name": "Goldbeter1991_MinMitOscil",
  "description": "Minimal model for mitotic oscillator...",
  "url": "https://www.ebi.ac.uk/biomodels/BIOMD0000000001",
  "simulators": ["copasi", "tellurium"]
}
```

---

### Run a single model

```
POST /compose/v1/biomodels/{biomodel_id}/run
```

**Path parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `biomodel_id` | string | EBI BioModels ID |

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `simulator` | string | `copasi` | Simulator to use: `copasi` or `tellurium` |

**Response** (`200 OK`) — `BiomodelsRunResult`:
```json
{
  "experiment": {
    "simulation_database_id": 42,
    "simulator_database_id": 3,
    "last_updated": "2026-05-08T12:00:00Z",
    "metadata": {}
  },
  "biomodel_id": "BIOMD0000000001",
  "simulator": "copasi"
}
```

---

### Run a batch of models

```
POST /compose/v1/biomodels/batch
```

Runs multiple models with the same simulator. Each model becomes its own
compose simulation (its own OMEX, its own SLURM job).

**Request body** — `BiomodelsRunRequest`:
```json
{
  "biomodel_ids": ["BIOMD0000000001", "BIOMD0000000012"],
  "simulator": "copasi"
}
```

**Response** (`200 OK`) — list of `BiomodelsRunResult`:
```json
[
  { "experiment": {...}, "biomodel_id": "BIOMD0000000001", "simulator": "copasi" },
  { "experiment": {...}, "biomodel_id": "BIOMD0000000012", "simulator": "copasi" }
]
```

---

### Audit a model with dual-simulator comparison

```
POST /compose/v1/biomodels/{biomodel_id}/audit
```

Runs the same model through two simulators in a single compose job. Both
simulators are wired to the same shared stores, so their outputs are
directly comparable.

**Path parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `biomodel_id` | string | EBI BioModels ID |

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `simulators` | string | `copasi,tellurium` | Comma-separated list of simulators |

**Response** (`200 OK`) — `BiomodelsAuditResult`:
```json
{
  "experiment": {
    "simulation_database_id": 43,
    "simulator_database_id": 3,
    "last_updated": "2026-05-08T12:00:00Z",
    "metadata": {}
  },
  "biomodel_id": "BIOMD0000000001",
  "simulators_used": ["copasi", "tellurium"]
}
```

---

### Run a regression suite

```
POST /compose/v1/biomodels/regression
```

Runs up to 1,000 BioModels as a validation pass. Each model is submitted
as a separate compose simulation. Use this to screen new simulators or
validate a batch of model submissions.

**Request body** — `BiomodelsRegressionRequest`:
```json
{
  "n_models": 100,
  "model_ids": null,
  "simulators": ["copasi", "tellurium"]
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `n_models` | integer | `10` | How many models to run (1–1000). Ignored if `model_ids` provided. |
| `model_ids` | list[string] \| null | `null` | Explicit list of IDs. Overrides `n_models`. |
| `simulators` | list[string] | `["copasi", "tellurium"]` | Simulators to use for each model |

**Response** (`200 OK`) — `BiomodelsRegressionResult`:
```json
{
  "submitted": [
    { "simulation_database_id": 44, "simulator_database_id": 3, ... },
    ...
  ],
  "failed": ["BIOMD0000000099"],
  "total_requested": 100
}
```

---

## CLI Reference

All biomodels commands live under `atlantis compose biomodels-*`.

### `biomodels-ids` — list available IDs

```bash
uv run atlantis compose biomodels-ids [--base-url URL]
```

Fetches and prints the list of curated BioModels IDs from EBI.

---

### `biomodels-meta` — model metadata

```bash
uv run atlantis compose biomodels-meta BIOMD0000000001 [--base-url URL]
```

| Argument | Description |
|----------|-------------|
| `BIOMD0000000001` | BioModels ID (positional) |

Prints the model name, description, URL, and supported simulators.

---

### `biomodels-run` — run a single model

```bash
uv run atlantis compose biomodels-run BIOMD0000000001 \
    --simulator copasi \
    [--poll] \
    [--base-url URL]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--simulator` | `copasi` | Simulator: `copasi` or `tellurium` |
| `--poll / --no-poll` | `--no-poll` | Block and poll until the job completes |

---

### `biomodels-batch` — batch submission

```bash
uv run atlantis compose biomodels-batch BIOMD0000000001 BIOMD0000000012 \
    --simulator tellurium \
    [--base-url URL]
```

| Argument | Description |
|----------|-------------|
| `IDS...` | One or more BioModels IDs (positional, variadic) |

| Option | Default | Description |
|--------|---------|-------------|
| `--simulator` | `copasi` | Simulator to use for all models |

---

### `biomodels-audit` — dual-simulator audit

```bash
uv run atlantis compose biomodels-audit BIOMD0000000001 \
    --simulators copasi,tellurium \
    [--poll] \
    [--base-url URL]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--simulators` | `copasi,tellurium` | Comma-separated list of simulators |
| `--poll / --no-poll` | `--no-poll` | Block and poll until complete |

---

### `biomodels-regression` — regression suite

```bash
uv run atlantis compose biomodels-regression \
    --n 100 \
    [--ids BIOMD0000000001,BIOMD0000000012] \
    [--simulators copasi,tellurium] \
    [--base-url URL]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--n` | `10` | Number of models to fetch from EBI and run |
| `--ids` | (none) | Explicit comma-separated IDs, overrides `--n` |
| `--simulators` | `copasi,tellurium` | Simulators to use for each model |

---

## Walkthrough Tutorial

This walkthrough goes from model discovery through audit to a 100-model
regression run.

### Step 1 — Discover available models

```bash
uv run atlantis compose biomodels-ids --base-url https://sms.cam.uchc.edu
```

You'll see output like:

```
BIOMD0000000001
BIOMD0000000012
BIOMD0000000023
...
```

### Step 2 — Inspect a model

```bash
uv run atlantis compose biomodels-meta BIOMD0000000001 \
    --base-url https://sms.cam.uchc.edu
```

```json
{
  "biomodel_id": "BIOMD0000000001",
  "name": "Goldbeter1991_MinMitOscil",
  "description": "Minimal model for mitotic oscillations...",
  "url": "https://www.ebi.ac.uk/biomodels/BIOMD0000000001",
  "simulators": ["copasi", "tellurium"]
}
```

### Step 3 — Run a single model

```bash
uv run atlantis compose biomodels-run BIOMD0000000001 \
    --simulator copasi \
    --poll \
    --base-url https://sms.cam.uchc.edu
```

The server will:
1. Fetch the OMEX archive from EBI (`BIOMD0000000001.omex`)
2. Parse `sedml/BIOMD0000000001_sim.xml` to extract time-course parameters
3. Generate a process-bigraph document:
   ```json
   {
     "state": {
       "BIOMD0000000001_copasi": {
         "_type": "step",
         "address": "local:pbsim_common.simulators.copasi_process.CopasiUTCStep",
         "config": {
           "model_source": "interesting.sbml",
           "sim_start_time": 0,
           "time": 100,
           "n_points": 100,
           "output_dir": "/output"
         }
       }
     }
   }
   ```
4. Package the PBG document + SBML into an OMEX archive
5. Submit to HPC via SLURM

Once `--poll` returns, you'll see:

```
Simulation ID: 42
{
  "simulation_database_id": 42,
  "simulator_database_id": 3,
  ...
}
```

### Step 4 — Audit with dual simulators

```bash
uv run atlantis compose biomodels-audit BIOMD0000000001 \
    --simulators copasi,tellurium \
    --poll \
    --base-url https://sms.cam.uchc.edu
```

This runs both COPASI and Tellurium in a **single compose job**. The PBG
document contains both steps wired to the same shared stores:

```json
{
  "state": {
    "BIOMD0000000001_copasi": {
      "_type": "step",
      "address": "local:pbsim_common.simulators.copasi_process.CopasiUTCStep",
      ...
    },
    "BIOMD0000000001_tellurium": {
      "_type": "step",
      "address": "local:pbsim_common.simulators.tellurium_process.TelluriumUTCStep",
      ...
    }
  }
}
```

The results (`species_concentrations`, `species_counts`) are keyed by
`{biomodel_id}_{simulator}`, enabling direct comparison.

### Step 5 — Run a 100-model regression suite

```bash
uv run atlantis compose biomodels-regression \
    --n 100 \
    --simulators copasi,tellurium \
    --base-url https://sms.cam.uchc.edu
```

This submits 100 compose simulations (one per model). The response reports
which models were successfully submitted and which failed (e.g. due to
unsupported SED-ML features):

```json
{
  "submitted": [ ... ],
  "failed": ["BIOMD0000000099"],
  "total_requested": 100
}
```

Use `atlantis compose status <SIM_ID>` to check individual results, or
`atlantis compose results <SIM_ID> --dest ./output` to download them.

---

## Architecture Notes

### EBI fetch and SED-ML parsing

The `biomodels_service.py` module handles all EBI interaction:

- `get_identifiers()` — calls the EBI BioModels search API to retrieve
  curated ODE model IDs
- `get_biomodel_info()` — fetches metadata for a single model
- `load_biomodel()` — downloads the OMEX from EBI and returns a
  `BiomodelLoadResult` containing the SBML path, SED-ML document, and
  extracted UTC parameters (`start_time`, `end_time`, `num_data_points`)

The SED-ML parser (`_extract_first_utc`) handles both `uniformTimeCourse`
and `steadyState` simulation types. Models with unsupported types are
reported as failures.

### Process-bigraph document generation

`biomodel_documents.py` generates PBG documents programmatically (not via
Jinja templates). Two factory functions:

- `make_biomodel_document(biomodel_id, sbml_path, utc, simulators)` ---
  one or two simulator steps wired to shared stores
- `make_multi_biomodel_document(biomodel_load_results, simulators)` ---
  multiple models, each with their own simulator steps

The shared stores use the `numeric_result`, `result`, `species_concentrations`,
and `species_counts` types from `bigraph-schema`'s registered type system.

### Deployment scope

BioModels integration targets the **`sms-api-rke` namespace** (UCONN CCAM
on-prem SLURM cluster). It is not deployed to GovCloud (`sms-api-stanford*`).

---

## Notes

- Models that cannot be loaded (unsupported SED-ML, missing SBML) are
  reported in the `failed` list without interrupting the batch.
- Each compose simulation has its own SLURM job, container, and output
  directory --- results are isolated per model.
- The EBI BioModels API is called live at request time. An EBI outage will
  cause endpoint failures; retry or specify explicit `model_ids` to bypass
  the live lookup.
- For the regression suite, the `--n 1000` maximum matches the number of
  curated ODE models in the EBI BioModels database.
