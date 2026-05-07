# Tutorial: Compositional Simulations with Process-Bigraph

This tutorial walks through Atlantis's **compose** subsystem end-to-end ---
from the process-bigraph concepts it builds on, to running a whole-cell
*E. coli* simulation composed of 55 biological processes, to downloading
the results.

If you're familiar with [process-bigraph](https://github.com/vivarium-collective/process-bigraph)
and [bigraph-schema](https://github.com/vivarium-collective/bigraph-schema),
this will show you how Atlantis uses those tools to orchestrate
containerized, HPC-scale biological simulations through a REST API and CLI.

## Background: Process-Bigraph in 60 Seconds

Process-bigraph is a framework for composing modular biological simulations.
The core abstractions:

- **Processes** are continuous, stateful compute units (e.g., an ODE solver
  for metabolism, a stochastic replication fork). Each Process declares typed
  input/output **ports** that wire to a shared **store** (state tree).
- **Steps** are discrete, stateless compute units (e.g., a single COPASI
  time-course evaluation).
- **Composites** are nested bigraphs of Processes and Steps wired together
  through the store. A Composite is itself runnable --- call `.run(interval)`
  to advance the simulation.
- **Documents** (`.pbg` files) are JSON descriptions of a bigraph's
  structure: what processes to instantiate, how to configure them, and how
  their ports connect to shared state.

A `.pbg` document looks like this:

```json
{
    "state": {
        "my_process": {
            "_type": "process",
            "address": "local:my_module.MyProcess",
            "config": { "rate": 0.1 },
            "interval": 1.0,
            "inputs": { "substrate": ["stores", "substrate"] },
            "outputs": { "product": ["stores", "product"] }
        }
    }
}
```

The `address` field tells process-bigraph where to find the Python class.
The `config` dict is passed to its constructor. The `inputs`/`outputs` map
port names to paths in the shared store tree.

## How Atlantis Uses Process-Bigraph

Atlantis wraps the process-bigraph workflow into a production pipeline:

```text
User (CLI/API)                    Atlantis Server                 HPC Cluster
      |                                |                              |
      |  POST /compose/v1/...         |                              |
      |------------------------------->|                              |
      |                                |  1. Parse PBG document       |
      |                                |  2. Auto-generate            |
      |                                |     Singularity def from     |
      |                                |     PBG dependencies         |
      |                                |  3. Hash def; check cache    |
      |                                |----- SCP + sbatch ---------->|
      |                                |                              | 4. Build container
      |                                |                              |    (if new hash)
      |                                |                              | 5. Run simulation
      |                                |                              |    inside container
      |                                |<---- SLURM status -----------|
      |  GET .../status               |                              |
      |<-------------------------------|                              |
      |                                |                              |
      |  GET .../results              |                              |
      |------------------------------->|<---- SCP results.zip --------|
      |<-------------------------------|                              |
```

Key design decisions:

1. **Container auto-generation**: The
   [pbest](https://github.com/biosimulations/pbest) library inspects the PBG
   document's dependency tree and generates a Singularity definition that
   includes exactly the Python packages needed. Container definitions are
   content-hashed --- identical compositions reuse cached containers.

2. **Curated templates**: For well-known simulators (v2ecoli, COPASI,
   Tellurium), Atlantis ships pre-authored PBG templates. Users don't need
   to write JSON --- they just call `atlantis compose ecoli --duration 60`.

3. **HPC execution**: Simulations run on SLURM-managed HPC nodes inside
   Singularity containers. The API handles job submission, status polling,
   and result retrieval over SSH.

## Tutorial: Three Simulation Engines

### 1. COPASI --- ODE Time-Course from SBML

COPASI solves ordinary differential equation (ODE) models defined in SBML.
The compose subsystem wraps it as a process-bigraph **Step**:

```json
{
    "state": {
        "time_course": {
            "_type": "step",
            "address": "local:pbsim_common.simulators.copasi_process.CopasiUTCStep",
            "config": {
                "model_source": "interesting.sbml",
                "sim_start_time": 0,
                "time": 100,
                "n_points": 200,
                "output_dir": "/output"
            },
            "interval": 1.0,
            "inputs": {},
            "outputs": {}
        }
    }
}
```

**Run it:**

```bash
# Upload an SBML model and simulate with COPASI
uv run atlantis compose copasi my_model.sbml \
    --duration 100 \
    --num-data-points 200 \
    --poll \
    --base-url https://sms.cam.uchc.edu
```

The `CopasiUTCStep` class from `pbsim-common` is resolved at runtime via
process-bigraph's `local:` protocol, which looks up registered Steps by
their module path.

### 2. Tellurium --- Stochastic/Deterministic from SBML

Tellurium provides both deterministic and stochastic simulation engines
for SBML models. It's also wrapped as a process-bigraph Step:

```json
{
    "state": {
        "time_course": {
            "_type": "step",
            "address": "local:pbsim_common.simulators.tellurium_process.TelluriumUTCStep",
            "config": {
                "model_source": "interesting.sbml",
                "sim_start_time": 0,
                "time": 100,
                "n_points": 200,
                "output_dir": "/output"
            },
            "interval": 1.0,
            "inputs": {},
            "outputs": {}
        }
    }
}
```

**Run it:**

```bash
uv run atlantis compose tellurium my_model.sbml \
    --end-time 100 \
    --num-data-points 200 \
    --poll \
    --base-url https://sms.cam.uchc.edu
```

### 3. v2ecoli --- Whole-Cell *E. coli* via Process-Bigraph

This is the flagship use case. [v2ecoli](https://github.com/vivarium-collective/v2ecoli)
is a whole-cell model of *Escherichia coli* that composes biological
processes --- metabolism, transcription, translation, replication,
chromosome structure, cell division, and more --- into a single
process-bigraph `Composite`.

Unlike COPASI and Tellurium (which are single Steps wrapping an SBML model),
v2ecoli assembles a **multi-layer execution graph** of `Process` and `Step`
instances wired to a shared store tree. Every process reads from and writes
to typed ports, and an allocator mediates resource contention between
processes that compete for shared molecules.

#### The biological processes

v2ecoli decomposes whole-cell behavior into individual process-bigraph
`Step` and `Process` classes, each responsible for one biological subsystem:

| Process | Class | Type | Biology |
|---------|-------|------|---------|
| Equilibrium | `Equilibrium` | Step | Macromolecular complexation equilibrium |
| Two-component system | `TwoComponentSystem` | Step | Histidine kinase signal transduction |
| RNA maturation | `RnaMaturation` | Step | rRNA/tRNA processing and modification |
| TF binding | `TfBinding` | Step | Transcription factor--promoter binding |
| TF unbinding | `TfUnbinding` | Step | Transcription factor release |
| Complexation | `Complexation` | Step | Protein complex formation |
| Protein degradation | `ProteinDegradation` | Step | Targeted proteolysis (Lon, ClpXP, etc.) |
| Transcript initiation | `TranscriptInitiation` | Step | RNAP--promoter open complex formation |
| Transcript elongation | `TranscriptElongation` | PartitionedProcess | Polymerization of RNA chains |
| Polypeptide initiation | `PolypeptideInitiation` | Step | Ribosome--mRNA binding (30S + 50S) |
| Polypeptide elongation | `PolypeptideElongation` | PartitionedProcess | Translation elongation (amino acid polymerization) |
| Chromosome replication | `ChromosomeReplication` | Step | DNA replication fork progression |
| Chromosome structure | `ChromosomeStructure` | Step | Topological domain management |
| RNA degradation | `RnaDegradation` | PartitionedProcess | Endonuclease/exonuclease mRNA decay |
| Metabolism | `Metabolism` | Step | Flux-balance analysis (FBA) for central + peripheral metabolism |
| Division | `Division` | Step | Cell division trigger and state partitioning |

In addition, **listener Steps** observe the simulation state and record
derived quantities each timestep:

| Listener | What it records |
|----------|----------------|
| `MassListener` | Dry mass, water mass, cell density, growth rate |
| `RNACounts` | Per-gene RNA copy numbers |
| `MonomerCounts` | Per-gene protein monomer counts |
| `RnaSynthProb` | Transcription initiation probabilities |
| `RnapData` | RNA polymerase counts and elongation rates |
| `RibosomeData` | Active ribosome counts and stalling events |
| `ReplicationData` | Fork positions, origin firing, termination |
| `UniqueMoleculeCounts` | Unique molecule census (ribosomes, RNAPs, forks) |

#### Execution layers and the partitioned architecture

The processes don't all run simultaneously. v2ecoli organizes them into
**execution layers** --- ordered groups that respect causal dependencies
and resource competition:

```text
Layer 0:  post-division-mass-listener
Layer 1:  media_update → tf-unbinding → exchange_data
Layer 2:  equilibrium, two-component-system, rna-maturation  (parallel)
Layer 3:  tf-binding
Layer 4:  protein-degradation
Layer 4b: complexation, chromosome-replication, polypeptide-initiation,
          transcript-initiation  (parallel)
          rna-degradation  (partitioned: requester → allocator → evolver)
Layer 5:  polypeptide-elongation, transcript-elongation
          (both partitioned: requesters → allocator → evolvers, parallel)
Layer 6:  chromosome-structure → metabolism  (sequential)
Layer 7:  all listeners  (parallel)
Layer 8:  mark-d-period → division
```

**Partitioned processes** (transcript elongation, polypeptide elongation,
RNA degradation) are processes that compete for shared resources (NTPs,
amino acids, water). They use a three-phase protocol:

1. **Requester** --- each process declares how many molecules it needs
2. **Allocator** --- a mediator distributes available molecules fairly
3. **Evolver** --- each process advances using its allocated share

This is implemented with process-bigraph's `Step` class for the requester
and evolver phases, with a shared allocator step that reads all requests
and writes allocations back to the store.

Between layers, **unique-molecule flush steps** drain a buffered update
queue for structured arrays (active ribosomes, replication forks, etc.)
to ensure consistency across process boundaries.

#### Feature modules

Optional biological features can be toggled on:

| Feature | What it adds |
|---------|-------------|
| `ppgpp_regulation` | ppGpp-mediated transcription initiation control (default: **on**) |
| `supercoiling` | DNA supercoiling dynamics affecting transcription |
| `trna_attenuation` | tRNA attenuation of amino acid biosynthesis operons |

```bash
# Enable supercoiling
uv run atlantis compose ecoli --features '["ppgpp_regulation", "supercoiling"]' ...
```

Features are injected into the execution layer graph at specific positions
(e.g., `supercoiling` inserts after `chromosome-structure`).

#### The `make_composite` factory

Unlike COPASI/Tellurium (which are standalone Step classes resolved by
process-bigraph's `local:` address protocol), v2ecoli uses a **factory
function** that builds the entire Composite programmatically:

```python
from v2ecoli.composite import make_composite

composite = make_composite(
    cache_dir='/out/cache',  # pre-computed ParCa cache
    seed=0,                  # random seed for stochastic processes
    features=[],             # optional feature modules
)

# The composite now contains ~55 wired process-bigraph Steps/Processes
# sharing a store with ~4,000 bulk molecule species, structured arrays
# for unique molecules, chromosome topology, and environment state.

composite.run(60.0)  # advance 60 seconds of simulated cell growth
```

The factory loads a **ParCa cache**, instantiates every process class with
its kinetic parameters, wires all ports to the shared store, builds the
execution layer schedule, and returns a `process_bigraph.Composite` ready
for `.run()`.

#### The pipeline: ParCa → cache → document → Composite

```text
┌──────────────────────────────────────────────────────────────────┐
│  ParCa (Parameter Calculator)                                    │
│                                                                  │
│  KnowledgeBaseEcoli (reconstruction data)                        │
│       ↓                                                          │
│  9-step pipeline (fitting kinetics, expression, regulation)      │
│       ↓                                                          │
│  SimulationDataEcoli (the "sim_data" object)                     │
│       ↓                                                          │
│  ┌──────────────────────────────────────────┐                    │
│  │ ParCa Cache (on disk)                     │                    │
│  │  initial_state.json  (~10 MB)             │                    │
│  │  sim_data_cache.dill (~165 MB)            │                    │
│  │  cache_version.json  (<1 KB)              │                    │
│  └──────────────────────────────────────────┘                    │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│  make_composite(cache_dir, seed, features)                       │
│                                                                  │
│  1. Load initial_state.json → bulk counts, unique molecules,     │
│     chromosome state, environment conditions                     │
│  2. Load sim_data_cache.dill → process configs (kinetics,        │
│     stoichiometry matrices, regulatory logic for all processes)  │
│  3. Instantiate ~16 biological Steps/Processes + ~8 listeners    │
│     + partition machinery (requesters, allocators, evolvers)     │
│  4. Wire all ports to the shared store tree                      │
│  5. Build execution layer schedule with FLUSH barriers           │
│  6. Return process_bigraph.Composite(document, core=core)        │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│  composite.run(60.0)                                             │
│                                                                  │
│  Each timestep (default 1.0s):                                   │
│    For each execution layer:                                     │
│      For each step/process in layer (parallel if multiple):      │
│        step.update(state) → writes to shared store ports         │
│      Flush unique-molecule buffer if FLUSH barrier               │
│    Advance global clock                                          │
│    Check division criteria (D-period complete + mass threshold)  │
└──────────────────────────────────────────────────────────────────┘
```

The ParCa cache is a one-time computation (~30 min for fast mode, several
hours for full). It is built from the
[ParCa fixture](https://github.com/vivarium-collective/v2ecoli/blob/main/models/parca/parca_state.pkl.gz)
shipped with v2ecoli using `python scripts/build_cache.py`. The cache
contains:

| File | Size | Contents |
|------|------|----------|
| `initial_state.json` | ~10 MB | ~4,000 bulk molecule counts, structured arrays for unique molecules (active ribosomes, RNA polymerases, replication forks), chromosome topology, media composition |
| `sim_data_cache.dill` | ~165 MB | Serialized dict with keys `configs` (per-process kinetic parameters, stoichiometry matrices, regulatory tables), `unique_names`, `dry_mass_inc_dict` |
| `cache_version.json` | <1 KB | SHA-256 hash of source files that affect the cache (composite.py, sim_data.py, initial_conditions.py, unit_bridge.py, quantity.py, and the ParCa fixture). Checked at load time --- a mismatch raises `StaleCacheError` with a clear rebuild message |

On the HPC, the cache is stored at a fixed filesystem path and **bind-mounted**
into the Singularity container at `/out/cache` at runtime.

```{note}
The cache must be built **inside the same container** that will run the
simulation, because `cache_version.json` hashes the installed v2ecoli
source files. A cache built with a different v2ecoli version will fail
the staleness check.
```

#### Full E2E walkthrough

**Step 1: Submit the simulation**

```bash
uv run atlantis compose ecoli \
    --duration 60 \
    --seed 0 \
    --base-url https://sms.cam.uchc.edu
```

Output:
```
Simulation ID: 18
Simulator ID: 3
{
  "simulation_database_id": 18,
  "simulator_database_id": 3,
  "last_updated": "2026-05-07 15:23:33.603842",
  "metadata": {}
}
```

**What happens on the server:**

1. The v2ecoli Jinja template is rendered with your parameters (`seed`,
   `features`, `cache_dir`, `interval`) into a PBG document
2. An OMEX archive is created containing `v2ecoli.pbg`
3. A Singularity container definition is auto-generated by pbest from the
   PBG's dependency tree, with an extra line injected:
   ```
   micromamba run -p /micromamba_env/runtime_env pip install \
       --ignore-requires-python \
       'git+https://github.com/vivarium-collective/v2ecoli.git'
   ```
   This installs v2ecoli and its transitive dependency vEcoli (the upstream
   *E. coli* model) into the container
4. The definition is content-hashed. If a container with that hash already
   exists on the HPC, the build is skipped (~15 min saved)
5. A Python runner script (`v2ecoli_run.py`) is generated and uploaded:
   ```python
   import os, json
   from v2ecoli.composite import make_composite
   from v2ecoli.cache import save_json
   composite = make_composite(cache_dir='/out/cache', seed=0, features=[])
   composite.run(60.0)
   outdir = '/experiment/output'
   os.makedirs(outdir, exist_ok=True)
   save_json(dict(composite.state), os.path.join(outdir, 'final_state.json'))
   print('v2ecoli simulation complete')
   ```
6. The OMEX, runner script, and sbatch file are uploaded to the HPC via SCP
7. A SLURM batch job executes the runner inside the Singularity container:
   ```bash
   CONDA_PREFIX=/micromamba_env/runtime_env singularity exec \
       --compat \
       --env CONDA_PREFIX=/micromamba_env/runtime_env \
       --bind /projects/.../experiment-<hash>:/experiment \
       --bind /projects/.../compose/cache:/out/cache \
       <container>.sif \
       /micromamba_env/runtime_env/bin/python3.12 /experiment/v2ecoli_run.py
   ```
8. On completion, the output is zipped: `final_state.json` → `results.zip`

**Step 2: Check status**

```bash
uv run atlantis compose status 18 --base-url https://sms.cam.uchc.edu
```

Output:
```
╭──────────────── Compose simulation 18 ─────────────────╮
│ RUNNING                                                 │
╰─────────────────────────────────────────────────────────╯
{
  "slurmjobid": 2050321,
  "status": "running",
  ...
}
```

**Step 3: Download results**

Once the simulation completes (~1--2 minutes for a 60-second run):

```bash
uv run atlantis compose results 18 \
    --dest ./my_results \
    --base-url https://sms.cam.uchc.edu
```

Output:
```
Results saved to: ./my_results/compose_results_18.zip
```

The ZIP contains `final_state.json` (~14 MB) --- a JSON serialization of
the full cell state after 60 seconds of simulated growth, serialized using
v2ecoli's `save_json` (which handles numpy arrays, pint Quantities,
structured dtypes, and sets). The state includes:

- **Bulk molecules**: ~4,000 species (ATP, amino acids, NTPs, metabolites, ...)
- **Unique molecules**: structured arrays for active ribosomes (mRNA index,
  peptide length, elongation state), RNA polymerases (promoter, transcript
  position), replication forks (coordinates, strand)
- **Chromosome**: origin firing state, fork positions, supercoiling density
- **Environment**: external metabolite concentrations, media composition
- **Derived quantities**: cell mass, volume, growth rate, ppGpp concentration

**Step 4: Retrieve the PBG document (provenance)**

```bash
uv run atlantis compose doc 18 --base-url https://sms.cam.uchc.edu
```

Returns the exact PBG document that was used, enabling full reproducibility.

#### CLI options reference

| Option | Default | Description |
|--------|---------|-------------|
| `--duration` | `60.0` | Simulation duration in seconds of biological time |
| `--seed` | `0` | Random seed (affects stochastic processes: transcription, translation, division timing) |
| `--interval` | `1.0` | Execution timestep in seconds (each tick advances all layers once) |
| `--features` | `[]` | JSON list of feature modules: `"ppgpp_regulation"`, `"supercoiling"`, `"trna_attenuation"` |
| `--cache-dir` | `/out/cache` | Absolute path to ParCa cache inside the container |
| `--poll` | off | Block and poll every 10s until the SLURM job completes or fails |

## Custom Compositions

You can submit your own process-bigraph documents. Create a `.pbg` file
that references any processes available in the container's Python
environment, bundle it in an OMEX archive (ZIP) with any needed SBML files,
and upload:

```bash
uv run atlantis compose run my_custom_model.omex \
    --interval-time 10.0 \
    --poll \
    --base-url https://sms.cam.uchc.edu
```

The container will be auto-generated from the document's dependency tree.
If your processes require packages not in the default set, the container
build will install them automatically via pbest's dependency resolver.

## Inspecting the Compute Registry

Atlantis tracks which process-bigraph processes and steps are available:

```bash
# List all registered simulator containers
uv run atlantis compose simulators --base-url https://sms.cam.uchc.edu

# List registered processes
uv run atlantis compose processes --base-url https://sms.cam.uchc.edu

# List registered steps
uv run atlantis compose steps --base-url https://sms.cam.uchc.edu

# Check a container build status
uv run atlantis compose build-status 3 --base-url https://sms.cam.uchc.edu
```

## Architecture Summary

```text
┌─────────────────────────────────────────────────────────┐
│                    Atlantis Server                       │
│                                                         │
│  /compose/v1/curated/ecoli ──┐                          │
│  /compose/v1/curated/copasi ─┤  PBG Template            │
│  /compose/v1/curated/tellurium┘  (Jinja → JSON)         │
│            │                                            │
│            ▼                                            │
│  ┌──────────────────┐   ┌─────────────────────────┐     │
│  │ pbest             │   │ Singularity Def          │     │
│  │ (container gen)   │──>│ (auto-generated,         │     │
│  └──────────────────┘   │  content-hashed, cached) │     │
│                          └───────────┬─────────────┘     │
│                                      │                   │
│  ┌──────────────────┐                │ SCP + sbatch      │
│  │ Compose DB        │                │                   │
│  │ (Postgres)        │                ▼                   │
│  │ - simulators      │   ┌─────────────────────────┐     │
│  │ - simulations     │   │ HPC / SLURM              │     │
│  │ - hpc_runs        │   │                           │     │
│  │ - documents       │   │  singularity exec         │     │
│  └──────────────────┘   │    --bind /experiment     │     │
│                          │    --bind /out/cache      │     │
│                          │    container.sif          │     │
│                          │    python v2ecoli_run.py  │     │
│                          │                           │     │
│                          │  → final_state.json       │     │
│                          │  → results.zip            │     │
│                          └─────────────────────────┘     │
└─────────────────────────────────────────────────────────┘
```

### Process-Bigraph integration points

| Layer | How process-bigraph is used |
|-------|---------------------------|
| **Document format** | `.pbg` files are process-bigraph JSON documents describing the bigraph topology |
| **Type system** | `bigraph-schema` Core with registered ecoli types (custom units, structured arrays) |
| **Composition** | `process_bigraph.Composite` realizes the document into a live simulation |
| **Execution** | `composite.run(interval)` advances all wired processes |
| **Process registry** | `local:` addresses resolve process classes from installed packages |
| **Dependency resolution** | pbest inspects PBG documents to determine which packages the container needs |

### Key packages in the ecosystem

| Package | Role |
|---------|------|
| [process-bigraph](https://github.com/vivarium-collective/process-bigraph) | Core composition engine (Composite, Process, Step) |
| [bigraph-schema](https://github.com/vivarium-collective/bigraph-schema) | Type system, serialization, document realization |
| [v2ecoli](https://github.com/vivarium-collective/v2ecoli) | Whole-cell *E. coli* model (55 processes, ParCa pipeline) |
| [pbest](https://github.com/biosimulations/pbest) | Container generation, PBG execution runtime |
| [pbsim-common](https://github.com/biosimulations/pbsim-common) | COPASI and Tellurium process-bigraph wrappers |
| [vivarium-core](https://github.com/vivarium-collective/vivarium-core) | Legacy vivarium engine (used by some v2ecoli internals) |
