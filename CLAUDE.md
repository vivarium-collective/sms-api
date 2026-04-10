# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

SMS API (Simulating Microbial Systems API, also known as Atlantis API) is a FastAPI-based REST API for designing, running, and analyzing whole-cell simulations of E. coli using the vEcoli model. The API supports two compute backends: **SLURM** (on-prem HPC at UCONN CCAM) and **K8s + AWS Batch** (GovCloud, Stanford deployment). Backend selection is automatic based on `deployment_namespace` in config.

## Architecture

### Core Components

- **FastAPI Server**: REST API hosted at `https://sms.cam.uchc.edu/`
- **SLURM Integration**: Submits and monitors jobs on HPC clusters via SSH
- **Singularity/Apptainer**: Containerized vEcoli simulator execution
- **PostgreSQL**: Stores simulation metadata, job records, and parca datasets
- **Marimo UI**: Web-based client interfaces

### Directory Structure

```
sms_api/
├── api/           # FastAPI routes and generated OpenAPI client
│   ├── routers/   # Route handlers: gateway, core, antibiotics, biofactory, inference, variants
│   ├── client/    # Auto-generated OpenAPI client (do NOT edit manually)
│   └── spec/      # Generated OpenAPI spec
├── analysis/      # Analysis job orchestration (post-simulation)
├── common/        # Shared utilities
│   ├── hpc/       # SLURM service, job models
│   ├── ssh/       # SSH session management (asyncssh)
│   ├── storage/   # File path abstractions (HPCFilePath), FileService (GCS, S3, Qumulo)
│   ├── gateway/   # Gateway I/O and models
│   └── messaging/ # MessagingService (Redis-backed)
├── data/          # Data services and BioCyc integration
├── simulation/    # Simulation service, database service, job scheduler, models, ORM tables
├── config.py      # Settings via pydantic-settings
└── dependencies.py # Dependency injection (SSH, DB, file, messaging, simulation services)

tests/
├── integration/   # HPC workflow tests (require SSH access)
├── fixtures/      # Pytest fixtures (centralized, imported via conftest.py)
│   └── configs/   # Sample JSON config files for testing
├── api/           # Route/handler tests
├── common/        # Service-level tests
├── data/          # Data service tests
└── simulation/    # Simulation logic tests

artifacts/         # Debug output directory (gitignored)
                   # Contains captured sbatch scripts and config snapshots
```

### Request Flow

API requests hit FastAPI routers (`sms_api/api/routers/`) which depend on services injected via `sms_api/dependencies.py`. The dependency module manages global singletons for SSH sessions, database connections, file storage, messaging, and the simulation service.

### Key Services

- **SimulationService** (`simulation/simulation_service.py`): Orchestrates the full HPC workflow (build, parca, simulate). Uses SlurmService + SSHSessionService.
- **AnalysisService** (`analysis/analysis_service.py`): Post-simulation analysis job orchestration.
- **DatabaseService** (`simulation/database_service.py`): SQLAlchemy async ORM for simulation metadata. Tables in `tables_orm.py`.
- **SlurmService** (`common/hpc/slurm_service.py`): SLURM job submission/monitoring. All methods take `ssh: SSHSession` as first arg.
- **SSHSessionService** (`common/ssh/ssh_service.py`): asyncssh connection pooling. Session reuse is critical for polling loops.
- **FileService** (`common/storage/`): Abstraction over GCS, S3, and Qumulo S3 storage backends.
- **JobScheduler** (`simulation/job_scheduler.py`): Coordinates multi-step HPC workflows.

### Compute Backend Dispatch

Backend selection is determined by `deployment_namespace` in `sms_api/config.py`:
- **SLURM** (default): `sms-api-rke`, `sms-api-rke-dev` — UCONN CCAM on-prem HPC
- **K8s + AWS Batch**: `sms-api-stanford`, `sms-api-stanford-test` — GovCloud

The dispatch happens in `dependencies.py` at startup: `SimulationServiceHpc` for SLURM, `SimulationServiceK8s` for K8s.

Config filenames are also namespace-aware via `sms_api/common/simulator_defaults.py`:
- `SimulationConfigPublic` (CCAM/RKE deployments)
- `SimulationConfigPrivate` (Stanford deployments)
- `SimulationConfigFilename` is dynamically set based on `PUBLIC_MODE`

### Three Client Interfaces

The API has three client entrypoints that implement the same EUTE workflow:
- **CLI** (`app.cli`): `uv run atlantis <command>` — Typer + Rich, Memphis theme
- **TUI** (`app.tui`): `uv run atlantis tui` — Textual app, animated logo banner
- **GUI** (`app.gui`): `uv run atlantis gui` — Marimo notebook, Memphis CSS theme

The Atlantis logo (E. coli capsule + flagella squigglies) is defined in:
- `app/cli_theme.py` — CLI Rich markup
- `app/tui.py` — TUI with animated green↔purple gradient (`_animated_banner()`)
- `app/gui.py` — GUI with HTML/CSS + SVG flagella

### HPC Workflow Pipeline

1. **Build Image**: Clone vEcoli repo, build Singularity container
2. **Run Parca**: Parameter calculator creates simulation dataset
3. **Run Simulation**: Execute vEcoli simulation via SLURM
4. **Run Analysis**: Post-process simulation outputs

### File Paths

- `HPCFilePath`: Abstraction for remote HPC paths with `.remote_path` and `.local_path()` methods
- Key settings paths: `hpc_image_base_path`, `hpc_parca_base_path`, `hpc_repo_base_path`, `simulation_outdir`, `analysis_outdir`

### Generated Code

`sms_api/api/client/` is auto-generated from the OpenAPI spec. Regenerate with `make api_client`.

## Development

### Setup

```bash
uv sync                    # Install dependencies (includes dev + docs groups)
uv run pre-commit install  # Set up pre-commit hooks (ruff lint + format, JSON formatting)
```

### Configuration

Environment variables loaded from `assets/dev/config/.dev_env`:
- `SLURM_SUBMIT_HOST`, `SLURM_SUBMIT_USER`, `SLURM_SUBMIT_KEY_PATH`: SSH access
- `POSTGRES_*`: Database connection
- `HPC_*`: HPC filesystem paths

### Key Commands

```bash
make check                 # Full quality check: lock consistency, pre-commit, mypy, deptry
make test                  # Run all tests with coverage
make gateway               # Start local dev server (port 8888, auto-reload)
make spec                  # Regenerate OpenAPI spec
make api_client            # Regenerate spec + OpenAPI client library
make e2e                   # Run full simulation end-to-end test

uv run pytest              # Run all tests
uv run pytest -x           # Stop on first failure
uv run pytest tests/path/test_file.py::TestClass::test_method -v -s  # Single test
uv run pytest tests/integration/test_hpc_workflow.py -v              # Integration tests (need SSH)
```

### After Making Significant Changes

After making significant code changes, run these steps in order:

1. `make spec` - regenerate OpenAPI spec (if API routes/models changed)
2. `make api_client` - regenerate client library (if spec changed)
3. `make check` - lint and type check
4. `uv run pytest` - run all unit tests
5. `uv run pytest tests/integration/test_hpc_workflow.py -v` - integration tests (requires SSH)

## Testing

### Integration Tests

`tests/integration/test_hpc_workflow.py` tests the full HPC workflow:
- Requires SSH access (skipped if `SLURM_SUBMIT_KEY_PATH` not set)
- Tests are idempotent - check for existing HPC artifacts before running
- Uses `TEST_EXPERIMENT_ID = "test_integration"`

### Fixtures

Key fixtures centralized in `tests/fixtures/` and imported via `tests/conftest.py`:
- `database_service`: SQLite test database
- `simulation_service_slurm`: HPC simulation service
- `slurm_service`, `ssh_session_service`: SLURM and SSH fixtures
- `file_service_gcs`, `file_service_s3`, `file_service_qumulo`: Storage backend fixtures
- `simulator_repo_info`: Default vEcoli repo config
- `configs/`: Sample JSON config files for deserialization tests
- Uses testcontainers for Postgres, Redis, MongoDB
- pytest-asyncio for async test support

## Common Patterns

### SSH Session Reuse (for polling loops)

```python
async with get_ssh_session_service().session() as ssh:
    while not done:
        status = await service.get_status(job_id, ssh=ssh)
        await asyncio.sleep(10)
```

### Database Operations

```python
async with database_service.session() as session:
    result = await session.execute(query)
```

### SLURM Job Submission

```python
slurm_service = SlurmService()
async with get_ssh_session_service().session() as ssh:
    job_id = await slurm_service.submit_job(
        ssh,  # Required first argument
        local_sbatch_file=local_path,
        remote_sbatch_file=remote_hpc_path,
    )
    # Reuse session for polling
    status = await slurm_service.get_job_status_squeue(ssh, job_ids=[job_id])
```

## Tooling

- **Linting/Formatting**: ruff (line length 120). Pre-commit runs ruff lint + ruff format.
- **Type checking**: mypy with strict mode. Excludes: `sms_api/api/client/`, `app/ui/`, `notes/`, `scratchpads/`.
- **Python**: 3.12.9 (pinned exact).
- **Package manager**: uv with hatchling build backend.


## Notes

### Full end-user E2E workflow (E.U.T.E: End User Tooling Experience)

#### We consider the "full end-user end-to-end workflow (a.k.a: E.U.T.E: End User Tooling Experience) to be: *(build -> get build status -> workflow(parca --> simulation --> analyses)) -> get workflow status -> get simulation data (download)*
We seek to have the Atlantis CLI (`app.cli`) to do this workflow, which again should be:

```
1. <GET> /core/v1/simulator/latest
2. -> <POST> /core/v1/simulator/upload
3. -> <GET> /core/v1/simulator/status (perhaps poll?, whatever is in the atlantis cli)
4. (once done) -> <POST> /api/v1/simulations
5. -> <GET> /api/v1/simulations/{id}/status (again, perhaps poll? Whatever is sleek and a good ux)
6. -> (once done) <POST> /api/v1/simulations/{id}/data (saved to a specified outdir, which for our testing/debugging can be a dir at ./debug)
7. -> (optional) <POST> /api/v1/simulations/{id}/analysis (re-run specific analysis modules on existing output)
```


#### Development Flow State for EUTE

*WHEN TESTING THE SMS_API's EUTE, MAKE SURE to use the atlantis cli (app.cli).* IN FACT, this is the iterative dev loop i want to get in: we use the cli to test end-user-facing e2e workflows (that is, the
"product" itself, one that stakeholders and clients alike will use: must be sleek, easy to use, yet robust and informative, and most importantly useful/novel enough to where it would be perferred to use the cli over any other
arbitrary external client that may call the api...I will then want to ensure that the same working functionality is exposed/present in the tui (basically, the entrypoint to the rest api defined in sms_api has 3
entrypoints/clients (other than direct http requests to the endpoints themselves): a. the marimo notebooks found in app/ui/..., b. the cli (atlantis) found in app.cli, c. the tui found at app.tui. With that said, it is
imperative that the aforementioned a, b, and c are implementations of the same thing (the full e2e end-user workflow calling the restapi endpoonts as mentioned), but within different media...ie: cli app, marimo gui (app mode in
marimo), and tui (textual-based tui) all expose/provide the same functionality, just in those different formats. Let's fully make this happen! If youre in, say "I dig ya broski: let's cook!", then make it happen babbbby!

### Stanford-Test Deploy Loop (K8s + AWS Batch)

The iterative fix → deploy → test cycle for the `sms-api-stanford-test` namespace:

```bash
# 1. Fix code, then commit and push
git add <files> && git commit -m "fix: ..." && git push

# 2. Build and push Docker image via GitHub Action
gh workflow run build-and-push.yml --ref atlantis-cli -f version=<VERSION>
gh run watch $(gh run list --workflow=build-and-push.yml --limit 1 --json databaseId -q '.[0].databaseId')
# NOTE: The action builds sms-api and sms-ptools. sms-api is the important one.
# The ptools step may fail (Dockerfile-nextflow issue) — that's fine as long as sms-api succeeds.

# 3. Deploy to K8s (rollout restart forces new image pull even if tag unchanged)
kubectl rollout restart deployment/api -n sms-api-stanford-test
kubectl rollout status deployment/api -n sms-api-stanford-test

# 4. Start proxy for local access
AWS_PROFILE=stanford-sso AWS_DEFAULT_REGION=us-gov-west-1 ../sms-cdk/scripts/ptools-proxy.sh -s smsvpctest

# 5. Verify version
curl -s http://localhost:8080/health

# 6. Test E2E via Atlantis CLI (NOT curl)
uv run atlantis simulator latest --repo-url https://github.com/CovertLabEcoli/vEcoli-private --branch master
uv run atlantis simulation run test1 <SIMULATOR_ID> --generations 1 --seeds 1 --poll
uv run atlantis simulation outputs <SIM_ID> --dest ./debug
```

**Version sync:** When bumping version, update `sms_api/version.py` AND `kustomize/overlays/sms-api-stanford-test/kustomization.yaml` (both `newTag` fields). Same tag is fine for iterative fixes — `rollout restart` forces a new pull regardless.

**Alternative: Local build** (faster, no GH Action wait):
```bash
./kustomize/scripts/build_and_push.sh   # reads version from sms_api/version.py
```

# PRIORITY

Implement that which is laid out in ./PLAN.md, if not already done.
