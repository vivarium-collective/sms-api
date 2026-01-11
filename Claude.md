# SMS API - Repository Context

## Overview

SMS API (Simulating Microbial Systems API, also known as Atlantis API) is a FastAPI-based REST API for designing, running, and analyzing whole-cell simulations of E. coli using the vEcoli model. The API orchestrates HPC (High Performance Computing) jobs via SLURM on remote clusters.

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
├── analysis/      # Analysis job orchestration (post-simulation)
├── common/        # Shared utilities
│   ├── hpc/       # SLURM service, job models
│   ├── ssh/       # SSH session management (asyncssh)
│   └── storage/   # File path abstractions (HPCFilePath)
├── data/          # Data services and BioCyc integration
├── simulation/    # Simulation service, database service, models
├── config.py      # Settings via pydantic-settings
└── dependencies.py # Dependency injection (SSH, DB services)

tests/
├── integration/   # HPC workflow tests (require SSH access)
├── fixtures/      # Pytest fixtures
│   └── configs/   # Sample JSON config files for testing
└── ...

artifacts/         # Debug output directory (gitignored)
                   # Contains captured sbatch scripts and config snapshots
```

## Key Concepts

### HPC Workflow

1. **Build Image**: Clone vEcoli repo, build Singularity container
2. **Run Parca**: Parameter calculator creates simulation dataset
3. **Run Simulation**: Execute vEcoli simulation
4. **Run Analysis**: Post-process simulation outputs

### File Paths

- `HPCFilePath`: Abstraction for remote HPC paths with `.remote_path` and `.local_path()` methods
- Key settings paths:
  - `hpc_image_base_path`: Singularity images
  - `hpc_parca_base_path`: Parca datasets
  - `hpc_repo_base_path`: Cloned vEcoli repos
  - `simulation_outdir`: Simulation output (uses `experiment_id` from config)
  - `analysis_outdir`: Analysis output

### SSH Session Management

- Uses `asyncssh` for SSH connections
- `SSHSessionService` provides connection pooling via `get_ssh_session_service()`
- Session reuse is critical for long-polling operations to avoid connection exhaustion
- Pattern: `async with get_ssh_session_service().session() as ssh:`

### SLURM Jobs

- `SlurmService` handles job submission and status queries
- All methods require `ssh: SSHSession` as the first parameter (mandatory)
- Status polling via `squeue` (active jobs) and `sacct` (completed jobs)

## Development

### Setup

```bash
uv sync                    # Install dependencies
uv run pytest             # Run tests
uv run pytest tests/integration/test_hpc_workflow.py -v  # Integration tests
```

### Configuration

Environment variables loaded from `assets/dev/config/.dev_env`:
- `SLURM_SUBMIT_HOST`, `SLURM_SUBMIT_USER`, `SLURM_SUBMIT_KEY_PATH`: SSH access
- `POSTGRES_*`: Database connection
- `HPC_*`: HPC filesystem paths

### Code Generation

```bash
./scripts/generate-api-client.sh  # Regenerate OpenAPI client
```

### Key Commands

```bash
make check                 # Run linting and type checks
uv run pytest -x          # Run tests, stop on first failure
```

### After Making Significant Changes

After making significant code changes, run these steps in order:

1. **Regenerate OpenAPI spec** (if API routes/models changed):
   ```bash
   uv run python sms_api/api/openapi_spec.py
   ```

2. **Regenerate API client library** (if OpenAPI spec changed):
   ```bash
   ./scripts/generate-api-client.sh
   ```

3. **Run linting and type checks**:
   ```bash
   make check
   ```

4. **Run all unit tests**:
   ```bash
   uv run pytest
   ```

5. **Run integration tests** (requires SSH access to HPC):
   ```bash
   uv run pytest tests/integration/test_hpc_workflow.py -v
   ```

## Testing

### Integration Tests

`tests/integration/test_hpc_workflow.py` tests the full HPC workflow:
- Requires SSH access (skipped if `SLURM_SUBMIT_KEY_PATH` not set)
- Tests are idempotent - check for existing HPC artifacts before running
- Uses `TEST_EXPERIMENT_ID = "test_integration"`

### Fixtures

Key fixtures in `tests/fixtures/`:
- `database_service`: SQLite test database
- `simulation_service_slurm`: HPC simulation service
- `simulator_repo_info`: Default vEcoli repo config
- `configs/`: Sample JSON config files for deserialization tests

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
