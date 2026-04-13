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

**CLI E2E verified** (2026-04-06): Full pipeline tested via `atlantis` CLI against deployed stanford-test API. All steps pass including output download with analysis data.

| # | Step | CLI Command | Status |
|---|------|-------------|--------|
| 1 | Get latest simulator | `atlantis simulator latest --repo-url ... --branch master` | PASS |
| 2 | Upload + build image | (included in step 1) | PASS |
| 3 | Poll build status | (included in step 1) | PASS |
| 4 | Submit simulation | `atlantis simulation run <exp> <sim_id> --run-parca --poll` | PASS |
| 5 | Simulation execution + status poll | `atlantis simulation status <id> --poll` | PASS |
| 6 | Download outputs | `atlantis simulation outputs <id> --dest ./debug` | PASS |

## Three-Client Parity

| Feature | CLI | TUI | Marimo |
|---------|-----|-----|--------|
| Simulator latest/build | DONE | DONE | NOT IMPLEMENTED |
| Simulation run | DONE | DONE | NOT IMPLEMENTED |
| Simulation status + error_message | DONE | DONE | NOT IMPLEMENTED |
| Simulation outputs download | DONE | DONE | NOT IMPLEMENTED |

## Documentation

- **ATLANTIS_TUTORIAL.md**: End-user CLI quick-reference at repo root
- **docs/**: Full Sphinx documentation (ReadTheDocs-compatible)
  - Getting Started: installation + tutorial
  - User Guide: CLI reference, S3 setup, Qumulo setup
  - Architecture: overview, AWS Batch, build pipeline
  - API Reference: auto-generated from source

## Remaining Work

### 1. Marimo EUTE Notebook (three-client parity)

Create `app/ui/eute.py` — a Marimo notebook exposing the full EUTE workflow using `E2EDataService` from `app/app_data_service.py`. Should cover:
- Simulator build (steps 1-3) with status display
- Simulation run form + status polling (steps 4-5)
- Output download + file browser (step 6)

## Resolved Items

- **CLI E2E verification**: All 6 EUTE steps pass via `atlantis` CLI (2026-04-06).
- **S3 output download**: Fixed double experiment_id nesting in S3 prefix path.
- **STORAGE_S3_BUCKET/REGION**: Added to stanford-test kustomize config.
- **Documentation**: Consolidated from MkDocs+Sphinx hybrid to Sphinx-only with myst-parser for markdown. ReadTheDocs config updated.
- **IRSA permissions**: Working — full EUTE verified via Swagger and CLI.
- **All pre-existing test failures**: Fixed. Test suite: 66 passed, 9 skipped, 0 failed.
- **Workflow log retrieval**: `_get_k8s_log` falls back to `_get_s3_nextflow_log` when pod logs are unavailable.
- **Build pipeline**: Migrated from DinD to DooD, multi-arch support via Batch (ARM64) + K8s (AMD64).
- **Error message display**: `SimulationRun.error_message` shown in both CLI and TUI.
- **mypy**: All checks pass — textual, boto3, kubernetes stubs excluded.
