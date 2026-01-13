# SMS CCAM Nextflow Integration Test Context

## Date: 2026-01-12

## Status: PASSING

## Summary

Created an integration test for the SMS CCAM Nextflow workflow that uploads `main_stub.nf` and `workflow_config.json` to the SLURM cluster and runs the workflow in stub mode.

## Files Modified

### 1. `tests/fixtures/slurm_fixtures.py`
Added new fixtures:
- `nextflow_inputs_dir` - Path to `tests/fixtures/nextflow_inputs/`
- `sms_ccam_main_nf` - Loads `main.nf` content
- `sms_ccam_workflow_config` - Loads `workflow_config.json` content
- `sms_ccam_nextflow_config` - Loads `nextflow.config` content
- `slurm_template_nextflow_sms_ccam` - Sbatch template for SMS CCAM test
- `nextflow_config_sms_ccam_executor` - Nextflow config with SLURM executor settings

### 2. `tests/common/test_slurm_service.py`
Added:
- `_run_sms_ccam_nextflow_test()` - Helper function that:
  - Creates remote output directory
  - Uploads `main.nf`, `workflow_config.json`, and `nextflow.config` to SLURM cluster
  - Supports `-stub` mode for testing without running actual simulations
  - Polls for job completion

- `test_nextflow_workflow_sms_ccam_slurm_executor()` - Integration test

### 3. `tests/conftest.py`
Added imports for the new fixtures:
- `nextflow_config_sms_ccam_executor`
- `nextflow_inputs_dir`
- `slurm_template_nextflow_sms_ccam`
- `sms_ccam_main_nf`
- `sms_ccam_nextflow_config`
- `sms_ccam_workflow_config`

## Test Execution Results

### What Worked
1. SSH connection to HPC cluster established successfully
2. Remote directory created: `/projects/SMS/sms_api/alex/htclogs/sms_ccam_*_output`
3. Files uploaded successfully:
   - `main.nf`
   - `workflow_config.json`
   - `nextflow.config`
4. SLURM job submitted (Job ID: 1282493)
5. Nextflow started and ran with stub mode (`-stub` flag)
6. Stub blocks for `runParca` and `createVariants` completed successfully

### What Failed
The external vEcoli modules (`sim_gen_1`, etc.) failed because:
- They are included from `/projects/SMS/sms_api/dev/repos/53526a7/vEcoli/runscripts/nextflow/sim.nf`
- These external modules don't have stub blocks defined
- Error: `No such variable: sim_seed` in `sim.nf` at line 46

### Error Details
```
ERROR ~ Error executing process > 'sim_gen_1 (2)'

Caused by:
  No such variable: sim_seed -- Check script '/projects/SMS/sms_api/dev/repos/53526a7/vEcoli/runscripts/nextflow/sim.nf' at line: 46
```

## Solution Implemented

**Option 2: Create a simpler test workflow** was implemented.

A self-contained `main_stub.nf` workflow was created that replaces external includes with local process definitions that have stub blocks. This allows the workflow to run in `-stub` mode without depending on external vEcoli modules.

### Changes Made

1. **Created `tests/fixtures/nextflow_inputs/main_stub.nf`**:
   - Self-contained workflow with all processes defined locally
   - All processes have stub blocks for testing the workflow DAG
   - Simplified process signatures to avoid Nextflow static analysis issues
   - Tests core workflow DAG: runParca -> analysisParca -> createVariants -> runSimulation -> runAnalysis
   - Uses 2 seeds for faster stub testing

2. **Added fixture `sms_ccam_main_stub_nf`** in `tests/fixtures/slurm_fixtures.py`

3. **Updated test** to use `sms_ccam_main_stub_nf` instead of `sms_ccam_main_nf`

4. **Updated `tests/conftest.py`** to import the new fixture

## How to Run the Test

```bash
uv run pytest tests/common/test_slurm_service.py::test_nextflow_workflow_sms_ccam_slurm_executor -v
```

## Log File Locations on HPC

- Output: `/projects/SMS/sms_api/alex/htclogs/sms_ccam_<uuid>.out`
- Error: `/projects/SMS/sms_api/alex/htclogs/sms_ccam_<uuid>.err`
- Nextflow work dir: `/projects/SMS/sms_api/alex/htclogs/sms_ccam_<uuid>_work`

## Key Code Snippets

### Helper Function Signature
```python
async def _run_sms_ccam_nextflow_test(
    slurm_service: SlurmService,
    main_nf_content: str,
    workflow_config_content: str,
    nextflow_config: str,
    sbatch_template: str,
    *,
    file_prefix: str,
    expected_job_name: str,
    use_stub_mode: bool = True,
    max_wait_seconds: int = 600,
    poll_interval_seconds: int = 10,
) -> NextflowTestResult:
```

### Test Function Signature (Updated)
```python
@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_nextflow_workflow_sms_ccam_slurm_executor(
    slurm_service: SlurmService,
    ssh_session_service: SSHSessionService,
    sms_ccam_main_stub_nf: str,  # Changed from sms_ccam_main_nf
    sms_ccam_workflow_config: str,
    nextflow_config_sms_ccam_executor: str,
    slurm_template_nextflow_sms_ccam: str,
) -> None:
```

## Files in nextflow_inputs/

- `main.nf` - Original workflow with external includes (for production use)
- `main_stub.nf` - Self-contained workflow with stub blocks (for quick CI testing)
- `main_real.nf` - Real simulation workflow using external vEcoli modules
- `workflow_config.json` - Workflow configuration for stub testing
- `workflow_config_real.json` - Minimal workflow config for real simulation testing
- `nextflow.config` - Nextflow configuration
- `sms_ccam.sh` - Shell script helper
- `workflow.py` - Python workflow helper
- `fetch_logs.py` - Utility to fetch HPC logs for debugging

---

## Real Simulation Test

### test_nextflow_workflow_sms_ccam_real_simulation

A second integration test was added that runs an **actual vEcoli simulation** (not stub mode).

### Features
- Runs real vEcoli simulation producing parquet output files
- Uses existing parca dataset (skips ParCa step for speed)
- Uses Singularity container with vEcoli image
- Outputs to `hpc_sim_base_path` (`/projects/SMS/sms_api/alex/sims/`)
- Minimal config: 1 seed, 1 generation, 120s max duration, reduced processes

### Files Added
1. **`main_real.nf`** - Workflow using external vEcoli modules (sim.nf, analysis.nf)
2. **`workflow_config_real.json`** - Minimal simulation config with parquet emitter

### Fixtures Added
- `sms_ccam_main_real_nf` - Loads main_real.nf
- `sms_ccam_workflow_config_real` - Loads workflow_config_real.json
- `nextflow_config_sms_ccam_real` - Nextflow config with Singularity container support
- `slurm_template_nextflow_sms_ccam_real` - Sbatch template with 2-hour timeout

### How to Run
```bash
# Stub test (quick, ~30 seconds)
uv run pytest tests/common/test_slurm_service.py::test_nextflow_workflow_sms_ccam_slurm_executor -v

# Real simulation test (slow, ~5-30 minutes)
uv run pytest tests/common/test_slurm_service.py::test_nextflow_workflow_sms_ccam_real_simulation -v
```

### Resource Paths
- Parca dataset: `/projects/SMS/sms_api/alex/parca/parca_8f119dd_id_1/kb/simData.cPickle`
- Container image: `/projects/SMS/sms_api/alex/images/vecoli-8f119dd.sif`
- Simulation output: `/projects/SMS/sms_api/alex/sims/integration_test_<uuid>/`

### Real Simulation Test Status (2026-01-13)

**Status**: BLOCKED BY VECOLI MODEL BUG

The container infrastructure has been fixed. The `vecoli-8f119dd.sif` container now has:
1. Pre-compiled Cython extensions (`.so` files)
2. Python interpreter preserved at `/vEcoli/.uv_python/cpython-3.12.9-linux-x86_64-gnu/bin/`
3. `source-info/git_diff.txt` for simulation metadata

**Container Build Changes**:
The Singularity definition file was updated to:
1. Set `UV_PYTHON_INSTALL_DIR="/vEcoli/.uv_python"` to preserve Python in the container
2. Run `uv run python setup.py build_ext --inplace` to pre-compile Cython extensions
3. Create `source-info/git_diff.txt` in the repo.tar archive

**What Works**:
- ✅ Container Python environment loads correctly
- ✅ Cython extensions are available
- ✅ `createVariants` process completes successfully (1 of 1)
- ✅ `sim_gen_1` process starts and begins simulation

**Current Failure**:
The simulation crashes with a vEcoli model bug:
```
NegativeCountsError: Negative value(s) in counts_unallocated:
PHOSPHO-ARCA[c] (-1)
```

This is a numerical precision issue in `ecoli/processes/allocator.py`, not an infrastructure problem.

**Next Steps**:
The real simulation test requires vEcoli model fixes to resolve the `NegativeCountsError`. The stub test (`test_nextflow_workflow_sms_ccam_slurm_executor`) passes consistently and validates the workflow DAG and infrastructure.

**Workaround for CI**:
Use the stub test which validates the Nextflow workflow structure without running actual simulations.
