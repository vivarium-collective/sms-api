# REST_PROCESS.md — Process-Bigraph Runtime Integration Report

**Branch:** `feat/rest-process-integration`
**Version:** `0.9.3`
**Target namespace:** `sms-api-rke` (SLURM/HPC, academic API)
**Audience:** Process-bigraph team — creators/maintainers of `process-bigraph`, `bigraph-schema`, `v2ecoli`, `rest-process`, `vivarium`, and `compose-api`

> **Interactive HTML report:** `./REST_PROCESS_REPORT.html` — open in any browser for a full visual overview with live registry explorer.

---

## What This PR Delivers

This PR (`feat/rest-process-integration`) completes the full integration of the process-bigraph ecosystem into the Atlantis platform (`sms-api` + `atlantis` CLI). It does three things:

1. **Mirrors the `rest-process` server paradigm** as a first-class REST API surface inside `sms-api`, giving any caller a stateful process lifecycle (initialize → inputs/outputs → update → end) over HTTP — without taking `rest-process` as a dependency.
2. **Documents and contextualizes** the BioModels integration (`v0.9.2`) and `v2ecoli` compose integration (`v0.9.0`) so the team can see concretely how PBG documents, type schemas, and simulator step classes are used inside the production SLURM pipeline.
3. **Proves correct usage** of `process_bigraph.allocate_core()`, `bigraph_schema` type strings, `pbsim_common` step classes, and the PBG document format — with runnable code at every step.

---

## Contribution 1 — Stateful Process Runtime (rest-process mirror)

### Purpose

`../rest-process` was sketched as a reference for what a PBG-native REST server should look like: every registered `Process`/`Step` class becomes a REST resource, instances are created on-demand, driven step-by-step, and terminated explicitly. This PR reimplements that exact paradigm inside `sms-api`'s `/compose/v1/` router — additive, no existing functionality touched.

### Commits

- `feat: mirror rest-process stateful runtime into compose subsystem (todo:50)`
- `chore: bump version to 0.9.3 — rest-process runtime (rke only)`

### What Changed

| File | Change |
|---|---|
| `sms_api/compose/process_runtime.py` | **New.** Core singleton (`allocate_core()`), UUID-keyed instance store, 8 functions mirroring `rest-process/server.py` |
| `sms_api/compose/models.py` | **Extended.** `ProcessInitializeRequest`, `ProcessInstance`, `ProcessUpdateRequest` |
| `sms_api/api/routers/compose.py` | **Extended.** 7 new endpoints, tag `Compose Runtime` |
| `app/app_data_service.py` | **Extended.** 7 new `E2EDataService` methods |
| `app/cli.py` | **Extended.** 7 new `atlantis compose` commands |
| `tests/compose/test_process_runtime.py` | **New.** 18 tests |
| `pyproject.toml` | **Extended.** `process_bigraph.*`, `bigraph_schema.*` added to mypy ignore list |
| `sms_api/api/spec/openapi_3_1_0_generated.yaml` | **Regenerated** |
| `sms_api/api/client/` | **Regenerated** |

### API Surface

```
GET  /compose/v1/types
GET  /compose/v1/process/{process_name}/config-schema
POST /compose/v1/process/{process_name}/initialize          body: {"config": {...}}
GET  /compose/v1/process/{process_name}/inputs/{process_id}
GET  /compose/v1/process/{process_name}/outputs/{process_id}
POST /compose/v1/process/{process_name}/update/{process_id} body: {"state": {...}, "interval": 1.0}
POST /compose/v1/process/{process_name}/end/{process_id}
```

### How process-bigraph is used correctly

**Core allocation** — `allocate_core()` is called exactly once (lazy singleton), which triggers auto-discovery of all installed `Process`/`Step` subclasses via entry-point scanning:

```python
# sms_api/compose/process_runtime.py
from process_bigraph import allocate_core

_core = None

def get_core():
    global _core
    if _core is None:
        _core = allocate_core()
    return _core
```

On the API pod (which has `pbsim_common` installed), this discovers **75 registered names**:

```
pbsim_common.simulators.copasi_process.CopasiUTCStep   → aliased as CopasiUTCStep
pbsim_common.simulators.copasi_process.CopasiUTCProcess → aliased as CopasiUTCProcess
pbsim_common.simulators.copasi_process.CopasiSteadyStateStep
pbsim_common.simulators.tellurium_process.TelluriumUTCStep → aliased as TelluriumUTCStep
pbsim_common.simulators.tellurium_process.TelluriumStep
pbsim_common.simulators.tellurium_process.TelluriumSteadyStateStep
pbsim_common.comparison.ComparisonTool → aliased as ComparisonTool
pbsim_common.comparison.MSEComparison  → aliased as MSEComparison
pbsim_common.stats.StatsTool
pbsim_common.stats.SumOfSquaresTool
process_bigraph.composite.Composite   → aliased as Composite
process_bigraph.composite.Step        → aliased as Step
process_bigraph.composite.Process     → aliased as Process
process_bigraph.protocols.rest.RestProcess → aliased as RestProcess
process_bigraph.processes.growth_division.Grow → aliased as Grow
process_bigraph.processes.growth_division.Divide
process_bigraph.experiments.minimal_gillespie.GillespieEvent
... (75 total)
```

**Type registry** — `bigraph_schema` exposes **42 types** accessible via `core.registry`:

```
composite, step, process, interface, bridge, ode_config, parallel, rest,
local, schema, link, interval, float, float64, integer, string, boolean,
list, map, tree, array, dataframe, maybe, union, enum, path, wires, ...
```

**Link registry dispatch** — exactly mirrors `rest-process/server.py`:

```python
# rest-process (reference)
def find_process_class(self, process):
    return self.core.link_registry.get(process, Edge)

# sms-api (this PR)
def get_config_schema(process_name: str) -> dict:
    core = get_core()
    process_class = core.link_registry.get(process_name, Edge)
    schema = getattr(process_class, 'config_schema', {})
    return schema
```

**Instance lifecycle** — mirrors rest-process `initialize → update → end`:

```python
def initialize_process(process_name: str, config: dict) -> str:
    core = get_core()
    process_class = core.link_registry.get(process_name)
    if process_class is None:
        raise KeyError(f"Process '{process_name}' not found in registry")
    process_id = str(uuid.uuid4())
    instance = process_class(config, core=core)   # standard PBG instantiation
    _instances[process_id] = instance
    return process_id

def update_process(process_id: str, state: dict, interval: float):
    instance = _instances[process_id]
    return instance.update(state, interval)        # standard PBG update call
```

### Verified & Reproducible Tests

**Unit tests** (`tests/compose/test_process_runtime.py`):

```bash
# Run from repo root
uv run pytest tests/compose/test_process_runtime.py -v
# 18 passed in ~1.3s
```

**HTTP roundtrip — quickstart:**

```python
# pip install httpx (or use the atlantis CLI below)
import httpx

BASE = "https://sms.cam.uchc.edu"  # live RKE API

# 1. List all 42 registered types
r = httpx.get(f"{BASE}/compose/v1/types")
print(r.json()[:5])  # ['node', 'atom', 'empty', 'union', 'tuple', ...]

# 2. Query config schema for the Grow process
r = httpx.get(f"{BASE}/compose/v1/process/Grow/config-schema")
print(r.json())  # {'rate': 'float'}

# 3. Instantiate Grow, run an update, terminate
r = httpx.post(f"{BASE}/compose/v1/process/Grow/initialize", json={"config": {"rate": 0.1}})
pid = r.json()["process_id"]

r = httpx.get(f"{BASE}/compose/v1/process/Grow/inputs/{pid}")
print(r.json())   # {'mass': 'float'}

r = httpx.post(f"{BASE}/compose/v1/process/Grow/update/{pid}",
               json={"state": {"mass": 1.0}, "interval": 1.0})
print(r.json())   # {'mass_delta': 0.1}

httpx.post(f"{BASE}/compose/v1/process/Grow/end/{pid}")
```

**CLI equivalent:**

```bash
BASE=https://sms.cam.uchc.edu

atlantis compose list-types --base-url $BASE
atlantis compose config-schema Grow --base-url $BASE
# returns: {"rate": "float"}

PID=$(atlantis compose init Grow --config '{"rate": 0.1}' --base-url $BASE | grep process_id | awk '{print $2}' | tr -d '"')
atlantis compose inputs Grow $PID --base-url $BASE
atlantis compose update Grow $PID --state '{"mass": 1.0}' --interval 1.0 --base-url $BASE
atlantis compose end Grow $PID --base-url $BASE
```

> **Note on simulator steps (CopasiUTCStep, TelluriumUTCStep):** These require `model_source` (a valid SBML file path) in their config. They are not suitable for the arbitrary REST update loop — their intended invocation path is through the BioModels pipeline (Contribution 2) which handles SBML fetch, PBG document construction, and SLURM dispatch. The REST runtime is most useful for lightweight processes (`Grow`, `Divide`, `GillespieEvent`, `MSEComparison`, custom process classes).

---

## Contribution 2 — BioModels Integration (`v0.9.2`)

### Purpose

Port the full `../biomodels-regression` pipeline into `sms-api`: fetch SBML from the EBI BioModels database, extract UTC parameters from SED-ML, construct a process-bigraph document, and submit it as a SLURM job via `pbsim_common` simulator steps. Exposes 6 dedicated endpoints and 6 CLI commands targeting BioModels database owners as the primary user.

### Commits

- `feat: add BioModels integration to compose subsystem (todo:40)` (branch: `feat/biomodels-integration`, merged in PR #125 → v0.9.2)

### What Changed

| File | Change |
|---|---|
| `sms_api/compose/biomodels_service.py` | **New.** EBI REST fetch, SED-ML UTC extraction, `BiomodelsService.load_biomodel()` |
| `sms_api/compose/biomodel_documents.py` | **New.** PBG document factory: `make_biomodel_document`, `make_utc_step_state`, `TYPES_DICT` |
| `sms_api/compose/models.py` | **Extended.** `BiomodelSimulator`, `BiomodelInfo`, `BiomodelsRunRequest/Result`, `BiomodelsAuditResult`, `BiomodelsRegressionRequest/Result` |
| `sms_api/api/routers/compose.py` | **Extended.** 6 new endpoints, tag `Compose BioModels` |
| `app/cli.py` | **Extended.** 6 new commands: `biomodels-ids`, `biomodels-meta`, `biomodels-run`, `biomodels-batch`, `biomodels-audit`, `biomodels-regression` |
| `tests/compose/test_biomodel_documents.py` | **New.** 11 tests |
| `tests/compose/test_biomodels_service.py` | **New.** 14 tests |
| `tests/compose/test_biomodels_routes.py` | **New.** 9 tests |
| `tests/compose/test_biomodels_cli.py` | **New.** 8 tests |
| `docs/source/guides/biomodels.md` | **New.** ReadTheDocs guide |

### How process-bigraph is used correctly

The critical path is: EBI REST → SBML file → `UniformTimeCourseSpec` (from SED-ML) → PBG document → OMEX archive → SLURM.

**PBG Document Structure (produced by `make_biomodel_document`):**

```python
# sms_api/compose/biomodel_documents.py

COPASI_STEP_ADDRESS  = "local:pbsim_common.simulators.copasi_process.CopasiUTCStep"
TELLURIUM_STEP_ADDRESS = "local:pbsim_common.simulators.tellurium_process.TelluriumUTCStep"

TYPES_DICT = {
    "numeric_result": {
        "time": "list[float]",
        "columns": "list[string]",
        "values": "list[list[float]]",
    },
    "numeric_results": "map[numeric_result]",
    "result": {
        "time": "list[float]",
        "species_concentrations": "map[list[float]]",
    },
    "results": "map[result]",
}
```

Concrete document for `BIOMD0000000001` with COPASI:

```json
{
  "schema": {
    "species_concentrations": "map[float]",
    "species_counts": "map[float]",
    "results": "map[numeric_result]"
  },
  "state": {
    "species_concentrations": {},
    "species_counts": {},
    "results": {},
    "BIOMD0000000001_copasi_step": {
      "_type": "step",
      "address": "local:pbsim_common.simulators.copasi_process.CopasiUTCStep",
      "config": {
        "model_source": "/tmp/biomodel_BIOMD0000000001_.../BIOMD0000000001_url.xml",
        "time": 1.0,
        "n_points": 100
      },
      "inputs": {
        "species_concentrations": ["species_concentrations"],
        "species_counts": ["species_counts"]
      },
      "outputs": {
        "result": ["results", "BIOMD0000000001_copasi"]
      }
    }
  }
}
```

**Dual-simulator audit document** (both COPASI + Tellurium wired into one PBG state):

```python
steps = {
    "copasi":    "local:pbsim_common.simulators.copasi_process.CopasiUTCStep",
    "tellurium": "local:pbsim_common.simulators.tellurium_process.TelluriumUTCStep",
}
pb_doc = make_biomodel_document(biomodel_id, sbml_path, utc, steps)
# → state contains both BIOMD..._copasi_step and BIOMD..._tellurium_step
# → outputs wired to separate results["BIOMD..._copasi"] and results["BIOMD..._tellurium"]
# → a single SLURM job runs both simulators and produces comparable outputs
```

### Verified on Live RKE Infrastructure

```bash
BASE=https://sms.cam.uchc.edu

# Fetch identifiers from EBI (live)
uv run atlantis compose biomodels-ids --base-url $BASE
# Returns: ['BIOMD0000000001', 'BIOMD0000000002', ...]  (confirmed 2026-05-08)

# Fetch metadata (live EBI call)
uv run atlantis compose biomodels-meta BIOMD0000000001 --base-url $BASE
# Returns: {biomodel_id: "BIOMD0000000001", metadata: {files: [{name: "BIOMD0000000001_url.xml", ...}]}}

# Submit single-simulator run (SLURM job)
uv run atlantis compose biomodels-run BIOMD0000000001 --simulator copasi \
  --base-url $BASE --poll
# SLURM job submitted: simulation_database_id=20 (confirmed running 2026-05-08)

# Audit: dual-simulator cross-validation
uv run atlantis compose biomodels-audit BIOMD0000000001 --base-url $BASE

# Regression suite: first 10 models
uv run atlantis compose biomodels-regression --n 10 --base-url $BASE
```

**Reproducible unit test:**

```bash
uv run pytest tests/compose/test_biomodel_documents.py \
              tests/compose/test_biomodels_service.py \
              tests/compose/test_biomodels_routes.py \
              tests/compose/test_biomodels_cli.py -v
# 42 tests, all passed
```

---

## Contribution 3 — v2ecoli Compose Integration (`v0.9.0`, context)

### Purpose

Run a full E. coli whole-cell simulation using `v2ecoli` inside a Singularity container on SLURM, orchestrated by the `sms-api` compose subsystem. The `v2ecoli` model uses `process_bigraph.Composite` to wire ~55 biological processes (metabolism, transcription, translation, replication, division, etc.) into a single runnable composite document. This was merged in v0.9.0 and forms the foundation on which BioModels and rest-process runtime are layered.

### How process-bigraph is used correctly

The v2ecoli model is constructed with `make_composite` (a factory, not a `Process` subclass) inside a Singularity container. The API submits a Python runner script (`v2ecoli_run.py`) to HPC via SLURM:

```python
# Internal v2ecoli runner (uploaded to HPC, executed inside Singularity)
from v2ecoli.library.compose import make_composite
from process_bigraph import Composite

sim_config = {
    "seed": seed,
    "total_time": duration,
    "initial_state": initial_state,
}
composite = make_composite(sim_config)  # wires ~55 Process/Step instances
sim = Composite({"state": composite}, core=core)
sim.run(duration)
```

The `Composite` document has `"_type": "process"` nodes for each of the 55 biological processes, all wired through the bigraph-schema store topology. `allocate_core()` is called with v2ecoli's `register_types()` to add biological type specializations.

### CLI

```bash
BASE=https://sms.cam.uchc.edu

# Run a 60-second E. coli whole-cell simulation
uv run atlantis compose ecoli \
  --duration 60 \
  --seed 0 \
  --interval 1.0 \
  --base-url $BASE \
  --poll

# Check status
uv run atlantis compose status <simulation_id> --base-url $BASE

# Download results
uv run atlantis compose results <simulation_id> --dest ./ecoli_out --base-url $BASE
```

### E2E Verification (production RKE, confirmed)

```
Container:   sha256:32637c9f1987791ddf2ebc197bb0754c (2.36 GB, v2ecoli + vEcoli baked in)
ParCa cache: /projects/SMS/sms_api/prod/compose/cache/ (175 MB)
Result:      final_state.json (14 MB), results.zip (917 KB)
Duration:    60 s biological time
```

---

## Registry Explorer — Live Introspection

The following shows the actual state of the PBG registry on the API pod (run at any time with `atlantis compose list-types` and `atlantis compose processes`):

### Type Registry (42 types via bigraph-schema)

```
node  atom  empty  union  tuple  boolean  or  and  xor
number  integer  float  float64  delta  nonnegative  random_state
string  enum  wrap  maybe  overwrite  list  map  tree  array
dataframe  path  wires  protocol  local  schema  link  interval
default 1  ode_config  parallel  rest  step  process  interface  bridge  composite
```

### Process/Step Registry (75 entries via allocate_core)

**pbsim_common** (ODE simulator steps — key for BioModels):

| Short name | Full address | config_schema |
|---|---|---|
| `CopasiUTCStep` | `pbsim_common.simulators.copasi_process.CopasiUTCStep` | `{model_source: string, time: float, n_points: integer, output_dir: string}` |
| `TelluriumUTCStep` | `pbsim_common.simulators.tellurium_process.TelluriumUTCStep` | `{model_source: string, time: float, n_points: integer, output_dir: string}` |
| `CopasiUTCProcess` | `pbsim_common.simulators.copasi_process.CopasiUTCProcess` | `{model_source: string, time: float, n_points: integer}` |
| `MSEComparison` | `pbsim_common.comparison.MSEComparison` | `{ignore_nans: boolean, columns_of_interest: list[string]}` |
| `ComparisonTool` | `pbsim_common.comparison.ComparisonTool` | `{}` |
| `StatsTool` | `pbsim_common.stats.StatsTool` | `{}` |

**process-bigraph built-ins**:

| Short name | config_schema |
|---|---|
| `Composite` | `{composition: schema, state: tree[any], interface: {...}, bridge: {...}}` |
| `Grow` | `{rate: float}` |
| `Divide` | `{}` |
| `GillespieEvent` | `{kdeg: float, ktsc: float, ...}` |
| `ParameterScan` | `{parameters: list, ...}` |
| `RestProcess` | `{}` (native PBG REST process) |
| `RAMEmitter` | `{}` |
| `JSONEmitter` | `{path: string}` |

---

## Verification Summary

| Check | Status | Command |
|---|---|---|
| `make check` (ruff + mypy + deptry) | PASS | `make check` |
| Unit tests — process_runtime | 18/18 PASS | `uv run pytest tests/compose/test_process_runtime.py -v` |
| Unit tests — BioModels | 42/42 PASS | `uv run pytest tests/compose/test_biomodel_documents.py tests/compose/test_biomodels_service.py tests/compose/test_biomodels_routes.py tests/compose/test_biomodels_cli.py -v` |
| Live: `biomodels-ids` on RKE v0.9.2 | PASS | `atlantis compose biomodels-ids --base-url https://sms.cam.uchc.edu` |
| Live: `biomodels-meta` on RKE v0.9.2 | PASS | `atlantis compose biomodels-meta BIOMD0000000001 ...` |
| Live: SLURM job submission (sim_id=20) | PASS (submitted, running) | `atlantis compose biomodels-run BIOMD0000000001 --simulator copasi --poll ...` |
| Live: v2ecoli E2E on RKE | PASS (v0.9.0) | `atlantis compose ecoli --duration 60 --seed 0 --poll ...` |

**Run all tests at once:**

```bash
uv run pytest tests/compose/ -v
# Expected: 60+ passed
```

---

## Known Gaps / What Remains

### 1. Process Runtime — Simulator Steps Require SBML

`CopasiUTCStep` and `TelluriumUTCStep` require a `model_source` (SBML file path) to instantiate. The REST update loop (`init → update → end`) works for lightweight processes like `Grow`, `GillespieEvent`, `MSEComparison`. For BioSim simulators, the correct path is always through `biomodels-run` / `curated/copasi` / `curated/tellurium` (which handle SBML fetch + SLURM dispatch).

**Planned:** A future endpoint `POST /compose/v1/process/{name}/initialize-with-file` that accepts multipart SBML upload + config, enabling full REST lifecycle for simulator steps.

### 2. Instance Persistence

Process instances live in the API pod's memory. A pod restart or new replica silently loses all active instances. Callers receive `404` on stale process IDs.

**Planned:** Redis-backed instance store (process config + UUID → Redis key with TTL) using the existing `MessagingService` infrastructure in `sms_api/dependencies.py`.

### 3. BioModels-run Result Poll — Awaiting SLURM Completion

The live test `atlantis compose biomodels-run BIOMD0000000001 --simulator copasi --poll` was submitted (sim_id=20, confirmed status=`running`) at time of writing. SLURM job duration depends on COPASI runtime for the Edelstein1996 model. Full verification (confirmed `completed` status + results download) pending SLURM completion.

**To verify when complete:**

```bash
uv run atlantis compose status 20 --base-url https://sms.cam.uchc.edu
uv run atlantis compose results 20 --dest ./biomodels_out --base-url https://sms.cam.uchc.edu
```

### 4. Hosted Documentation

Docs live at `docs/source/guides/biomodels.md` and `docs/source/guides/compose.md`. ReadTheDocs build is triggered on merge to `main`. The public URL will be available after the `check-docs` CI job completes for v0.9.3.

**To build locally:**

```bash
make docs  # or: cd docs && make html
```

### 5. Registry Endpoints for Custom Process Registration (todo:43)

`POST /compose/v1/process/register` — dynamically register a new process class from a pip package or module path, making it immediately available in `/list-processes`, `/initialize`, etc. This is the next logical step after this PR and will complete the registry loop.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Atlantis CLI                              │
│  atlantis compose list-types / config-schema / init / update    │
│  atlantis compose biomodels-ids / biomodels-run / biomodels-audit│
│  atlantis compose ecoli                                          │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTPS
                    ┌──────────▼──────────┐
                    │   sms-api (FastAPI)  │
                    │   /compose/v1/       │
                    │                     │
                    │  ┌───────────────┐  │
                    │  │ process_runtime│  │  ← this PR
                    │  │  allocate_core │  │    (rest-process mirror)
                    │  │  _instances{}  │  │
                    │  └───────────────┘  │
                    │                     │
                    │  ┌───────────────┐  │
                    │  │biomodels_svc  │  │  ← v0.9.2
                    │  │ EBI REST fetch │  │    (BioModels)
                    │  │ SED-ML parse  │  │
                    │  │ PBG doc factory│  │
                    │  └──────┬────────┘  │
                    └─────────┼───────────┘
                              │ SLURM sbatch (SSH)
                    ┌─────────▼───────────┐
                    │   UCONN CCAM HPC     │
                    │                     │
                    │  ┌───────────────┐  │
                    │  │  Singularity  │  │
                    │  │  container    │  │
                    │  │  pbsim_common │  │
                    │  │  CopasiUTCStep│  │
                    │  │  TelluriumUTC │  │
                    │  │  v2ecoli      │  │
                    │  │  process_bigraph  │
                    │  └───────────────┘  │
                    └─────────────────────┘
```

---

*Generated 2026-05-08 — `feat/rest-process-integration` — sms-api v0.9.3*
*Interactive report: `./REST_PROCESS_REPORT.html`*
