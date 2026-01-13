# Plan: Placeholder Parca Dataset for run_workflow_simple()

## Problem

The `insert_simulation` database method requires a valid `parca_dataset_id`, but in the new `run_workflow_simple()` flow, parca is executed as part of the Nextflow workflow rather than as a separate pre-step.

Error observed:
```
Exception: Parca Dataset with not found in the database with reference to simulator: 1
```

## Current Architecture

### Database Flow (Legacy)
1. Create `ParcaDataset` entry → get `parca_dataset_id`
2. Submit parca SLURM job → wait for completion
3. Create `Simulation` entry with `parca_dataset_id`
4. Submit simulation SLURM job

### New Workflow Flow
1. Nextflow workflow handles parca + simulation together
2. No separate parca job submission
3. Still need database tracking for the simulation

## Proposed Solution: Placeholder Parca Dataset

Create a parca dataset entry **before** inserting the simulation, even though parca will be executed by the Nextflow workflow.

### Implementation Steps

1. **In `run_workflow_simple()`**, after reading the config template:
   - Extract `parca_options` from the parsed config
   - Create a `ParcaDatasetRequest` with the simulator and parca options
   - Call `insert_parca_dataset()` to create the database entry
   - Use the returned `parca_dataset_id` when creating the `SimulationRequest`

2. **Code changes** in `sms_api/common/handlers/simulations.py`:
   ```python
   # After step 4 (Override config values), add:

   # 5. Create placeholder parca dataset entry
   parca_ds = await database_service.insert_parca_dataset(
       parca_dataset_request=ParcaDatasetRequest(
           simulator_version=simulator,
           parca_config=config.parca_options
       )
   )

   # 6. Create SimulationRequest with parca_dataset_id
   request = SimulationRequest(
       config=config,
       simulator_id=simulator_id,
       parca_dataset_id=parca_ds.database_id,  # Now we have this!
   )
   ```

### Advantages

1. **No schema changes** - Uses existing database structure
2. **Maintains referential integrity** - Simulation still links to a valid parca dataset
3. **Consistent tracking** - All simulations have associated parca config recorded
4. **Reuse potential** - If parca output is cached on HPC, the config_hash can help identify it

### Considerations

1. **Parca dataset state** - The entry is created before parca actually runs. The `remote_archive_path` will be `None` initially.
2. **Config hash matching** - If a parca dataset with the same config already exists, `insert_parca_dataset` returns the existing one (deduplication built-in).
3. **HpcRun tracking** - We're NOT inserting an HpcRun for parca since it's part of the workflow job. Only the simulation HpcRun is created.

### Files to Modify

1. `sms_api/common/handlers/simulations.py` - Add parca dataset creation in `run_workflow_simple()`

### Testing

1. Update `tests/integration/test_run_workflow_simple.py` to verify:
   - Parca dataset is created
   - Simulation references the parca dataset
   - Workflow completes successfully

## Alternative Considered: Make parca_dataset_id Optional

Could modify `insert_simulation` to allow `parca_dataset_id=None`, but this:
- Breaks referential integrity
- Requires schema changes (nullable FK)
- Loses parca config tracking
- Creates inconsistency with legacy flow

**Rejected** in favor of placeholder approach.
