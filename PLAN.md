# PLAN: EUTE Status — Current State

## The Full EUTE Pipeline

```
1. GET  /core/v1/simulator/latest
2. POST /core/v1/simulator/upload
3. GET  /core/v1/simulator/status (poll)
4. POST /api/v1/simulations
5. GET  /api/v1/simulations/{id}/status (poll)
6. POST /api/v1/simulations/{id}/data (download)
```

## Code Status: COMPLETE

All 6 EUTE steps are fully implemented in the API, CLI, and TUI.

Full EUTE verified end-to-end via Swagger (manual, 2026-04-06). Infrastructure is operational — IRSA permissions, Batch, S3, ECR all working.

| # | Step | CLI Command | Code Status | Infra Status |
|---|------|-------------|-------------|--------------|
| 1 | Get latest simulator | `atlantis simulator latest --repo-url ... --branch master` | DONE | PASS |
| 2 | Upload + build image | (included in step 1) | DONE | PASS |
| 3 | Poll build status | (included in step 1, `--poll` default) | DONE | PASS |
| 4 | Submit simulation | `atlantis simulation run <exp> <sim_id> --run-parca --poll` | DONE | PASS |
| 5 | Simulation execution + status poll | `atlantis simulation status <id> --poll` | DONE | PASS |
| 6 | Download outputs | `atlantis simulation outputs <id> --dest ./debug` | DONE | PASS |

## Three-Client Parity

| Feature | CLI | TUI | Marimo |
|---------|-----|-----|--------|
| Simulator latest/build | DONE | DONE | NOT IMPLEMENTED |
| Simulation run | DONE | DONE | NOT IMPLEMENTED |
| Simulation status + error_message | DONE | DONE | NOT IMPLEMENTED |
| Simulation outputs download | DONE | DONE | NOT IMPLEMENTED |

**CLI** (`app/cli_app.py`): Full coverage — `simulator latest`, `simulation run`, `simulation status --poll`, `simulation outputs`, plus list/cancel/get/log commands.

**TUI** (`app/tui.py`): Full coverage — sidebar buttons for all 6 steps, RunSimulationScreen form, FileBrowserScreen for downloaded outputs, server selector dropdown.

**Marimo** (`app/ui/`): No EUTE workflow notebook exists. The current notebooks (`configure.py`, `explore.py`, `biofactory.py`, `antibiotic.py`) are post-simulation analysis tools — none expose steps 1-6.

## Remaining Work

### 1. CLI E2E Verification

The full EUTE has been verified via Swagger. The CLI and TUI call the same endpoints through `E2EDataService`, so they should work identically. Run the following to confirm:

```bash
# Steps 1-3
uv run atlantis simulator latest --repo-url https://github.com/CovertLabEcoli/vEcoli-private --branch master
# Steps 4-5
uv run atlantis simulation run test_cli <SIMULATOR_ID> --generations 1 --seeds 1 --run-parca --poll
# Step 6
uv run atlantis simulation outputs <SIM_ID> --dest ./debug
```

### 2. Marimo EUTE Notebook (three-client parity)

Create `app/ui/eute.py` — a Marimo notebook exposing the full EUTE workflow using `E2EDataService` from `app/app_data_service.py`. Should cover:
- Simulator build (steps 1-3) with status display
- Simulation run form + status polling (steps 4-5)
- Output download + file browser (step 6)

## Resolved Items

- **IRSA permissions**: Working — full EUTE verified via Swagger (2026-04-06). CDK deploy section removed.
- **All pre-existing test failures**: Fixed. Test suite: 66 passed, 9 skipped, 0 failed.
- **Workflow log retrieval**: `_get_k8s_log` falls back to `_get_s3_nextflow_log` when pod logs are unavailable.
- **Build pipeline**: Migrated from DinD to DooD, multi-arch support via Batch (ARM64) + K8s (AMD64).
- **Error message display**: `SimulationRun.error_message` shown in both CLI and TUI.
