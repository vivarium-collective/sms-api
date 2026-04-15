# Atlantis CLI Tutorial

Atlantis is the command-line interface for running whole-cell E. coli simulations via the SMS API. This guide walks you through the complete workflow: building a simulator, running a simulation, and downloading your results.

## Prerequisites

- Python 3.12+ with [uv](https://docs.astral.sh/uv/) installed
- Access to a running SMS API server (local or remote)
- Repository cloned and dependencies installed:

```bash
git clone https://github.com/vivarium-collective/sms-api.git
cd sms-api
uv sync
```

## Quick Start

Run a complete simulation in three commands:

```bash
# 1. Build the latest simulator
uv run atlantis simulator latest

# 2. Run a simulation (replace <SIMULATOR_ID> with the ID from step 1)
uv run atlantis simulation run my_experiment <SIMULATOR_ID> --run-parca --poll

# 3. Download results (replace <SIM_ID> with the ID from step 2)
uv run atlantis simulation outputs <SIM_ID> --dest ./results
```

## Connecting to an API Server

By default, Atlantis connects to `http://localhost:8080`. Override this with `--base-url` on any command, or set the `API_BASE_URL` environment variable:

```bash
# Use a specific server
uv run atlantis simulator latest --base-url https://sms.cam.uchc.edu

# Or set it once for your session
export API_BASE_URL=https://sms.cam.uchc.edu
```

Available servers:

| Server | URL |
|--------|-----|
| Production | `https://sms.cam.uchc.edu` |
| Development | `https://sms-dev.cam.uchc.edu` |
| Local (default) | `http://localhost:8080` |

## Step-by-Step Workflow

### Step 1: Build a Simulator

A **simulator** is a containerized build of the [vEcoli](https://github.com/CovertLabEcoli/vEcoli-private) whole-cell model. Before running simulations, you need a built simulator image.

**Fetch and build the latest version:**

```bash
uv run atlantis simulator latest \
  --repo-url https://github.com/CovertLabEcoli/vEcoli-private \
  --branch master
```

This command:
1. Fetches the latest commit from the specified repo and branch
2. Uploads the simulator metadata to the API
3. Polls the container build until it completes

The output will show a **Simulator ID** (e.g., `Simulator ID: 11`) -- save this for the next step.

**Force a rebuild** (even if the same commit was already built):

```bash
uv run atlantis simulator latest --force
```

**Check build status** for an existing simulator:

```bash
uv run atlantis simulator status <SIMULATOR_ID>
```

**List all simulators:**

```bash
uv run atlantis simulator list
```

### Step 2: Run a Simulation

Submit a simulation workflow using the simulator ID from step 1:

```bash
uv run atlantis simulation run my_experiment 11 \
  --generations 1 \
  --seeds 1 \
  --run-parca \
  --poll
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `EXPERIMENT_ID` | A name you choose for this experiment (e.g., `my_experiment`) |
| `SIMULATOR_ID` | The database ID of the simulator to use |

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--generations` | 1 | Number of cell generations to simulate per seed |
| `--seeds` | 3 | Number of independent lineages (seeds) to run |
| `--run-parca` | off | Run the parameter calculator before simulation |
| `--poll` | off | Wait and display status updates until completion |
| `--config-filename` | `api_simulation_default.json` | Simulation config file on HPC |
| `--description` | auto-generated | Custom description for the run |
| `--sources` | none | Local data-source directory to sync to S3 before the run. Repeatable. |
| `--sources-prefix` | `sources` | S3 key prefix under the configured bucket. |
| `--sources-delete` | off | Pass `--delete` to `aws s3 sync`. |

**What happens under the hood:**

The `--run-parca` flag triggers the full pipeline: **parca** (parameter calculator) -> **simulation** -> **analysis**. Without it, the simulation uses a pre-existing parca dataset.

With `--poll`, the CLI prints status updates every 30 seconds:

```
Simulation submitted!  ID: 35

Polling simulation status...
  [30s] status: running
  [60s] status: running
  ...
  [1110s] status: completed
+------------------------------ Simulation 35 ------------------------------+
| COMPLETED                                                                 |
+--------------------------------------------------------------------------+

Download data:  atlantis simulation outputs 35 --dest ./results
```

**Submit without polling** (fire and forget):

```bash
uv run atlantis simulation run my_experiment 11 --generations 2 --seeds 3
```

Then check status later:

```bash
uv run atlantis simulation status 35
```

Or poll an already-running simulation:

```bash
uv run atlantis simulation status 35 --poll
```

#### Syncing custom data sources with `--sources`

vEcoli's parca can consume RNA-seq datasets (and other curated inputs) from
sibling data repos like `ecoli-sources` and private overlays like
`ecoli-sources-vegas`. The `--sources` flag uploads local directories to S3
and wires the resulting URIs into the simulation container as
`ECOLI_SOURCES` / `ECOLI_SOURCES_OVERLAYS` environment variables — no manual
config editing required.

```bash
uv run atlantis simulation run my_experiment 11 \
  --config-filename configs/campaigns/pilot_expression_noise.json \
  --sources ../ecoli-sources \
  --sources ../ecoli-sources-vegas \
  --run-parca --poll
```

What this does:

1. For each `--sources <dir>`, runs `aws s3 sync <dir>
   s3://{STORAGE_S3_BUCKET}/sources/<basename>/` (excluding `.venv`,
   `__pycache__`, `.git`, `*.pyc`).
2. The first source backs `ECOLI_SOURCES`; subsequent ones become `;`-joined
   overlay manifest URIs in `ECOLI_SOURCES_OVERLAYS`.
3. Both env vars are set on the Batch container, so configs that reference
   `$ECOLI_SOURCES/data/manifest.tsv` resolve automatically.

Requires the AWS CLI on `PATH` with credentials configured and
`STORAGE_S3_BUCKET` set (e.g. in `assets/dev/config/.dev_env`).

The broader sensitivity-campaign workflow (campaign specs, perturbation
operators, cross-variant analyses) is documented in vEcoli's
[`doc/sensitivity_campaigns.rst`](https://github.com/CovertLab/vEcoli/blob/multi-parca-aws/doc/sensitivity_campaigns.rst).

### Step 3: Download Results

Once a simulation completes, download the output data:

```bash
uv run atlantis simulation outputs 35 --dest ./results
```

This downloads a `.tar.gz` archive containing analysis outputs (TSV data files, metadata JSON) and extracts it to the specified directory.

**Output structure:**

```
results/
  <experiment_id>/
    analyses/
      variant=0/
        plots/
          analysis=cd1_fluxomics/
            cd1_fluxomics_detailed.tsv
            metadata.json
          analysis=cd1_proteomics/
            proteomics.tsv
            metadata.json
          analysis=ptools_proteins/
            ptools_proteins.tsv
            metadata.json
          ...
    nextflow/
      workflow_config.json
  <experiment_id>.tar.gz
```

## Additional Commands

### Simulation Management

```bash
# List all simulations
uv run atlantis simulation list

# Get details for a specific simulation
uv run atlantis simulation get <SIM_ID>

# Cancel a running simulation
uv run atlantis simulation cancel <SIM_ID>
```

### Parca (Parameter Calculator)

```bash
# List all parca datasets
uv run atlantis parca list

# Check status of a parca run
uv run atlantis parca status <PARCA_ID>
```

### Analysis

```bash
# Get analysis details
uv run atlantis analysis get <ANALYSIS_ID>

# Check analysis status
uv run atlantis analysis status <ANALYSIS_ID>

# View analysis log
uv run atlantis analysis log <ANALYSIS_ID>

# List analysis plot outputs
uv run atlantis analysis plots <ANALYSIS_ID>
```

### Interactive TUI

Launch a full terminal UI with sidebar navigation and forms:

```bash
uv run atlantis tui tui
```

## Typical Run Times

| Pipeline Stage | Approximate Duration |
|---------------|---------------------|
| Simulator build (fresh) | 5-10 minutes |
| Simulator build (cached) | seconds |
| Parca (parameter calculator) | 5-8 minutes |
| Simulation (1 gen, 1 seed) | 5-7 minutes |
| Analysis (8 analyses) | 3-5 minutes |
| **Full pipeline (build + parca + sim + analysis)** | **~20-30 minutes** |

## Getting Help

```bash
# Top-level help
uv run atlantis --help

# Subcommand help
uv run atlantis simulator --help
uv run atlantis simulation run --help

# Contextual help for any command group
uv run atlantis help simulator
uv run atlantis help simulation
```
