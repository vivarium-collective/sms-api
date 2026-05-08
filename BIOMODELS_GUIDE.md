# BioModels User Guide — Atlantis CLI

*For the EBI BioModels database team. Applies to the academic API deployment only (`sms-api-rke`, base URL `https://sms.cam.uchc.edu`).*

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Command Reference](#command-reference)
   - [`biomodels-ids` — list available models](#biomodels-ids--list-available-models)
   - [`biomodels-meta` — inspect a model](#biomodels-meta--inspect-a-model)
   - [`biomodels-run` — run a single model](#biomodels-run--run-a-single-model)
   - [`biomodels-batch` — run multiple models](#biomodels-batch--run-multiple-models)
   - [`biomodels-audit` — dual-simulator cross-validation](#biomodels-audit--dual-simulator-cross-validation)
   - [`biomodels-regression` — full regression suite](#biomodels-regression--full-regression-suite)
4. [Use Case Walkthroughs](#use-case-walkthroughs)
   - [A. Audit: compare COPASI vs Tellurium on the same model](#a-audit-compare-copasi-vs-tellurium-on-the-same-model)
   - [B. Validate/Onboard: screen new models before accepting to BioModels DB](#b-validateonboard-screen-new-models-before-accepting-to-biomodels-db)
   - [C. Author modifications: re-run a modified publication model](#c-author-modifications-re-run-a-modified-publication-model)
5. [Retrieving Results](#retrieving-results)
6. [What Happens Behind the Scenes](#what-happens-behind-the-scenes)
7. [Troubleshooting & Notes](#troubleshooting--notes)

---

## Overview

The Atlantis CLI gives you the ability to run any SBML/ODE model from the
[EBI BioModels database](https://www.ebi.ac.uk/biomodels/) on the UCONN CCAM
HPC cluster (SLURM) using two simulators:

| Simulator | Description |
|-----------|-------------|
| **COPASI** | COmplex PAthway SImulator — mature, widely-used ODE solver |
| **Tellurium** | Python-based ODE solver (libroadrunner backend) |

You interact through a single CLI command (`uv run atlantis compose biomodels-*`)
which talks to the Atlantis REST API at `https://sms.cam.uchc.edu`. The API
fetches the model from EBI, parses its SED-ML to extract simulation parameters,
builds a process-bigraph document, and dispatches it as a SLURM job on HPC.

**Three use cases are supported:**

- **Audit** — Run the same model on both COPASI and Tellurium side-by-side for
  cross-validation
- **Validate/Onboard** — Screen new models before accepting them into the
  BioModels database
- **Author modifications** — Re-run a modified publication model to verify the
  changes

---

## Quick Start

All commands use the base URL `https://sms.cam.uchc.edu`. To avoid typing it
every time, set the environment variable:

```bash
export API_BASE_URL="https://sms.cam.uchc.edu"
```

Then any `--base-url` argument can be omitted (the CLI reads `API_BASE_URL`).

### 1. List available models

```bash
uv run atlantis compose biomodels-ids
```

Returns curated ODE model IDs from EBI (`BIOMD0000000001`, `BIOMD0000000012`, ...).

### 2. Inspect a model

```bash
uv run atlantis compose biomodels-meta BIOMD0000000001
```

Shows name, description, URL, and supported simulators.

### 3. Run a model

```bash
uv run atlantis compose biomodels-run BIOMD0000000001 --poll
```

The `--poll` flag blocks until the HPC job completes and prints the final
status. Without it, the command returns immediately with a
`simulation_database_id` you can use to check status later.

### 4. Check status later

```bash
uv run atlantis compose status <SIMULATION_ID>
```

### 5. Download results

```bash
uv run atlantis compose results <SIMULATION_ID> --dest ./my_results
```

---

## Command Reference

### `biomodels-ids` — list available models

```bash
uv run atlantis compose biomodels-ids [--n N]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--n` | `20` | Max identifiers to return (1–500) |

**Example:**

```bash
$ uv run atlantis compose biomodels-ids --n 5
['BIOMD0000000001', 'BIOMD0000000012', 'BIOMD0000000023', 'BIOMD0000000034', 'BIOMD0000000045']
```

---

### `biomodels-meta` — inspect a model

```bash
uv run atlantis compose biomodels-meta <BIOMODEL_ID>
```

**Example — check a model before running it:**

```bash
$ uv run atlantis compose biomodels-meta BIOMD0000000001
{
  "biomodel_id": "BIOMD0000000001",
  "metadata": {
    "name": "Goldbeter1991_MinMitOscil",
    "description": "Minimal model for mitotic oscillations...",
    "url": "https://www.ebi.ac.uk/biomodels/BIOMD0000000001",
    "simulators": ["copasi", "tellurium"]
  }
}
```

**What to look for:** If `simulators` includes both `copasi` and `tellurium`,
the model is a good candidate for audit runs. If only one is listed, dual-sim
comparison won't be available for that model.

---

### `biomodels-run` — run a single model

```bash
uv run atlantis compose biomodels-run <BIOMODEL_ID> [--simulator copasi|tellurium] [--poll]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--simulator` | `copasi` | Which simulator to use |
| `--poll` | off | Wait for the HPC job to complete before returning |

**Example 1 — submit and get an ID back immediately:**

```bash
$ uv run atlantis compose biomodels-run BIOMD0000000001
{
  "experiment": {
    "simulation_database_id": 42,
    "simulator_database_id": 3,
    "last_updated": "2026-05-08T12:00:00",
    "metadata": {}
  },
  "biomodel_id": "BIOMD0000000001",
  "simulator": "copasi"
}
```

**Example 2 — submit with Tellurium and wait for completion:**

```bash
$ uv run atlantis compose biomodels-run BIOMD0000000001 --simulator tellurium --poll
[status updates every 5s...]
{
  "experiment": {
    "simulation_database_id": 43,
    "simulator_database_id": 3,
    "last_updated": "2026-05-08T12:01:30",
    "metadata": {}
  },
  "biomodel_id": "BIOMD0000000001",
  "simulator": "tellurium"
}
```

---

### `biomodels-batch` — run multiple models

```bash
uv run atlantis compose biomodels-batch [--n N] [--ids ID1,ID2,...] [--simulator copasi|tellurium]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--n` | `5` | How many models to auto-fetch from EBI (ignored if `--ids` given) |
| `--ids` | (none) | Comma-separated explicit list of model IDs |
| `--simulator` | `copasi` | Simulator for all models |

Each model becomes its own SLURM job. The response reports which submissions
succeeded and which failed:

**Example — run three specific models:**

```bash
$ uv run atlantis compose biomodels-batch \
    --ids BIOMD0000000001,BIOMD0000000012,BIOMD0000000023
{
  "submitted": [
    { "simulation_database_id": 44, "biomodel_id": "BIOMD0000000001", ... },
    { "simulation_database_id": 45, "biomodel_id": "BIOMD0000000012", ... },
    { "simulation_database_id": 46, "biomodel_id": "BIOMD0000000023", ... }
  ],
  "failed": []
}
```

**Example — run the first 10 models from EBI with Tellurium:**

```bash
uv run atlantis compose biomodels-batch --n 10 --simulator tellurium
```

---

### `biomodels-audit` — dual-simulator cross-validation

```bash
uv run atlantis compose biomodels-audit <BIOMODEL_ID> [--simulators copasi,tellurium] [--poll]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--simulators` | `copasi,tellurium` | Comma-separated list of simulators |
| `--poll` | off | Wait for the HPC job to complete |

This runs the same model through **both simulators in a single SLURM job**.
Both are wired to the same shared data stores, making outputs directly comparable.

**Example:**

```bash
$ uv run atlantis compose biomodels-audit BIOMD0000000001 --poll
{
  "experiment": {
    "simulation_database_id": 47,
    "status": "completed",
    ...
  },
  "simulators_used": ["copasi", "tellurium"]
}
```

After completion, download results to compare species concentrations:

```bash
uv run atlantis compose results 47 --dest ./audit_output
```

The results directory contains subdirectories keyed by both model ID and
simulator (e.g. `BIOMD0000000001_copasi/`, `BIOMD0000000001_tellurium/`)
so you can directly compare outputs.

---

### `biomodels-regression` — full regression suite

```bash
uv run atlantis compose biomodels-regression [--n N] [--ids ID1,ID2,...] [--simulators copasi,tellurium]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--n` | `10` | Number of models to auto-fetch and run (1–1000) |
| `--ids` | (none) | Explicit comma-separated IDs, overrides `--n` |
| `--simulators` | `copasi,tellurium` | Simulators to use per model |

This is the heavy-lifting command. It fetches N models from EBI and submits
**each as a separate SLURM job** (dual-simulator by default; single-simulator
if only one is passed via `--simulators`). Use this for:
- Screening new simulator versions
- Validating a batch of model submissions
- Running the full ~1000 model regression pass

**Example — run a full 1000-model regression:**

```bash
$ uv run atlantis compose biomodels-regression --n 1000
Regression complete: 992/1000 submitted, 8 failed
Failed IDs: BIOMD0000000099, BIOMD0000000150, ...
```

**Example — run specific models as a targeted regression:**

```bash
$ uv run atlantis compose biomodels-regression \
    --ids BIOMD0000000001,BIOMD0000000012,BIOMD0000000023 \
    --simulators copasi,tellurium
```

Failures (e.g. unsupported SED-ML, missing SBML) don't interrupt the suite.
Check the `failed` list in the response and investigate those individually.

---

## Use Case Walkthroughs

### A. Audit: compare COPASI vs Tellurium on the same model

**Scenario:** You want to verify that a new Tellurium release produces the same
results as COPASI for a specific model before declaring it production-ready.

```bash
# Step 1 — inspect the model to confirm both simulators are supported
uv run atlantis compose biomodels-meta BIOMD0000000001

# Step 2 — run the audit (both simulators, wait for completion)
uv run atlantis compose biomodels-audit BIOMD0000000001 --poll

# Step 3 — download the results
uv run atlantis compose results <SIM_ID> --dest ./audit_results

# Step 4 — compare species_concentrations between the two simulators
# (The output is organized by {biomodel_id}_{simulator})
ls ./audit_results/
# BIOMD0000000001_copasi/  BIOMD0000000001_tellurium/

# Use pandas to compare numerically — avoid diff -r on floating-point CSVs
uv run python3 - <<'EOF'
import pandas as pd
a = pd.read_csv("./audit_results/BIOMD0000000001_copasi/species_concentrations.csv")
b = pd.read_csv("./audit_results/BIOMD0000000001_tellurium/species_concentrations.csv")
print(abs(a - b).max())
EOF
```

**Expected outcome:** Both simulators produce the same species concentration
curves within numerical tolerance. Discrepancies should be investigated as
potential bugs.

---

### B. Validate/Onboard: screen new models before accepting to BioModels DB

**Scenario:** A submitter sends you a new model (OMEX archive) that you need
to validate before accepting into the BioModels database. You want to confirm
it runs cleanly on both simulators.

If the model is already published on EBI (has a `BIOMD...` ID):

```bash
# Run a full audit — both simulators, with polling
uv run atlantis compose biomodels-audit BIOMD0000000999 --poll

# If it fails, check which simulator caused the issue
# Try each simulator individually:
uv run atlantis compose biomodels-run BIOMD0000000999 --simulator copasi --poll
uv run atlantis compose biomodels-run BIOMD0000000999 --simulator tellurium --poll
```

**What to check:**
- Both simulators complete without error (`status: "completed"`)
- The model matches its metadata description
- Output species concentrations are physically plausible (no NaNs, no
  unreasonably large values)

**For pre-publication models** (not yet on EBI), you can still use the
standard `compose run` command with a simulation document pointing to your
local SBML — see the compose tutorial in `docs/source/guides/compose.md`.

---

### C. Author modifications: re-run a modified publication model

**Scenario:** An author has made revisions to their published model and wants
to verify the changes produce correct results before updating the BioModels
entry.

```bash
# Step 1 — get the baseline run with the current published model
uv run atlantis compose biomodels-run BIOMD0000000042 --simulator copasi --poll
uv run atlantis compose results <BASELINE_SIM_ID> --dest ./baseline

# Step 2 — inspect the model metadata to understand the version
uv run atlantis compose biomodels-meta BIOMD0000000042

# Step 3 — run an audit to get both-Copasi-and-Tellurium results
uv run atlantis compose biomodels-audit BIOMD0000000042 --poll
uv run atlantis compose results <AUDIT_SIM_ID> --dest ./audit_results

# Step 4 — compare baseline vs audit results numerically
uv run python3 - <<'EOF'
import pandas as pd
base = pd.read_csv("./baseline/species_concentrations.csv")
audit = pd.read_csv("./audit_results/BIOMD0000000042_copasi/species_concentrations.csv")
print(abs(base - audit).max())
EOF
```

**Expected outcome:** Baseline and audit results should match for the same
simulator. If the author's modification is already reflected in a new EBI
version, the audit will show both simulators agreeing on the new behavior.

---

## Retrieving Results

### Check job status

```bash
uv run atlantis compose status <SIMULATION_ID>
```

Returns `queued`, `running`, `completed`, `failed`, `cancelled`, or `timeout`.

### Download outputs

```bash
uv run atlantis compose results <SIMULATION_ID> --dest ./output_directory
```

Downloads and extracts the results archive. The exact filenames depend on
what the pbsim-common simulator runtime writes to `/output`, but expected
contents based on the process-bigraph output store names include:

| File | Description |
|------|-------------|
| `species_concentrations.csv` | Time-series of all species concentrations |
| `species_counts.csv` | Molecule counts per species |
| `metadata.json` | Simulation metadata, parameters, and timestamps |

For audit runs, results are organized per simulator:
```
output_directory/
  BIOMD0000000001_copasi/
    species_concentrations.csv
    species_counts.csv
  BIOMD0000000001_tellurium/
    species_concentrations.csv
    species_counts.csv
```

---

## What Happens Behind the Scenes

When you run `biomodels-run BIOMD0000000001`:

1. **Model fetch** — The API downloads the OMEX archive from
   `https://www.ebi.ac.uk/biomodels/BIOMD0000000001` and extracts its contents
2. **SED-ML parsing** — The SED-ML simulation description is read to extract
   time-course parameters: `start_time`, `end_time`, `num_points`
3. **PBG document construction** — A process-bigraph document is generated
   programmatically (not via templates) containing:
   - A simulator step (CopasiUTCStep or TelluriumUTCStep)
   - Shared data stores for inputs and results
   - Wiring from the SBML model source to the simulator
4. **SLURM dispatch** — The document, SBML, and simulator config are packaged
   into an OMEX archive and submitted as a SLURM batch job on the UCONN CCAM
   cluster
5. **Execution** — The job runs inside a Singularity container with the
   `pbsim-common` simulator runtime
6. **Results collection** — Outputs (species concentrations, counts) are
   collected into a ZIP archive and made available for download

---

## Troubleshooting & Notes

### Common issues

| Problem | Likely cause | What to do |
|---------|-------------|------------|
| `Failed to load BioModel` | EBI API unreachable, unsupported SED-ML, or missing SBML | Try `--ids` with explicit IDs to bypass the live lookup; check the model has a `uniformTimeCourse` simulation |
| Job stuck in `queued` | HPC cluster busy | Wait; check `atlantis compose status` periodically |
| Job status `failed` | Simulator crashed or model has unsupported features | Try the other simulator; run individually to isolate |
| Regression shows many failures | Some models use non-ODE SED-ML types | Check the `failed` list; those models may use `steadyState` or other unsupported SED-ML types |

### Important notes

- **EBI dependency** — The API fetches models live from EBI at request time.
  An EBI outage will cause endpoint failures. Use explicit `--ids` to bypass
  the live lookup if you already know which models to run.
- **Writes to EBI not supported** — This tool is read-only with respect to
  EBI. It cannot submit, update, or delete models in the BioModels database.
- **Results are isolated** — Each simulation gets its own SLURM job,
  container, and output directory. No interference between models.
- **Backend routing** — When you point the CLI at `https://sms.cam.uchc.edu`,
  the request lands on the `sms-api-rke` K8s namespace, which configures
  `COMPUTE_BACKEND=slurm`. The compose subsystem always submits to SLURM
  via SSH (there is no AWS Batch implementation for compose). You can verify
  this by checking the `SLURM_SUBMIT_HOST` and `SLURM_PARTITION` in the
  deployment config.
- **No GovCloud support** — BioModels integration runs only on the academic
  API (`sms-api-rke`). The GovCloud/Stanford deployment does not include
  these endpoints.
- **1000 model maximum** — The `--n 1000` cap matches the current number of
  curated ODE models in the BioModels database.
- **All times UTC** — Simulation timestamps and status times are in UTC.
