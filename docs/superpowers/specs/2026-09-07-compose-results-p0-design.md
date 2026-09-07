# P0: auto-run analyses for GovCloud composite runs (fix the #1022 no-op)

**Date:** 2026-09-07
**Status:** Design — spec for review, then implementation plan.
**Repos:** viva-api (`~/code/sms-api`, GitHub `vivarium-collective/viva-api`, pkg `viva_api/`) + vivarium-workbench.
**Basis:** origin/main — viva-api `dbe82876`, workbench `1916195f` (#1022). Local checkouts are stale; work in worktrees.
**Tracking issue:** viva-api#462. **Review that motivates this:** Fable integration review (P0 slice).

## Problem
vivarium-workbench #1022 was supposed to make composite runs auto-run their declared analyses on completion — locally AND on GovCloud. The **local** half works. The **GovCloud** half is a silent no-op:
- The workbench encodes `analysis_options` as a **query param** on the compose submit (`sms_api_client.compose_submit`); the `/compose/v1/simulation/run` endpoint doesn't accept it, so FastAPI drops it.
- `run_runner._execute_remote` returns after `remote_run.run_remote` lands a raw `results.zip` and **never flushes** — nothing unpacks or analyzes it.

Net: a bare composite on GovCloud gets no analyses, no viz, no report card. P0 fixes the ANALYSES half end-to-end. (Viz + tests are P1 — see Non-goals.)

## Goal
A GovCloud composite run whose config/composite declares analyses runs those analyses **server-side** as a job chained onto the compose sim, writes the **standard analysis manifest** (the same `_manifest.json` shape the study Batch path writes and the workbench already folds), and the workbench **lands** it — so composite GovCloud runs get analyses on the workbench, matching local composite behavior.

## Key reuse (do not reinvent)
The study Batch backend already does exactly this: `_submit_analysis_job` + `_analysis_command` (`viva_api/simulation/simulation_service_ray.py:2010-2163`) submit an analysis DAG node that runs the analyses over the sim's output store and writes a manifest to S3. The compose Batch backend (`viva_api/compose/simulation_service_ray.py:156 submit_simulation_job`) runs the generic `run_pbg.py` on the **same Batch MNP machinery** but chains no analysis node. P0 = give compose that same analysis node.

The compose sim output is already present and discoverable: `run_pbg.py` redirects every file-emitter's `out_dir`/`out_uri` into the results prefix and flushes parquet (`viva_api/compose/run_pbg.py`), so a parquet/zarr store lands alongside `final_state.json`. The analysis node reads that store.

## Design

### viva-api
1. **Carry `analysis_options` on the compose request.** Add `analysis_options: dict | None = None` to the compose request model (`viva_api/compose/models.py` `ComposeSimulationRequest` / `ComposeDocumentSubmission`), accept it on the `/compose/v1/simulation/run` (+ `run-document`) endpoints (a multipart Form field carrying a JSON string, since the endpoint is upload-based), and persist it on the `ComposeSimulation` row. Update the 3 in-process construction sites (`run_compose_simulation`/`_v2ecoli`/`_curated`).
2. **Chain the analysis node on the compose Batch backend.** In `viva_api/compose/simulation_service_ray.py submit_simulation_job`, when `analysis_options` is present, submit an analysis job that `dependsOn` the compose sim job, reusing `simulation/simulation_service_ray.py`'s `_submit_analysis_job`/`_analysis_command` (extract/share it rather than copy) pointed at the compose run's output store prefix + the compose run's sim_data cache. Record the analysis job in the same `analyses` table so `GET /analyses/{id}/status` (the S3-manifest probe) works for compose unchanged.
3. **sim_data / cache:** point the analysis node's sim_data at the compose run's OWN cache (`compose_cache_base_path`/the run's variant cache), never a stock per-commit one (issue-166 viva-api#448 trap). Compose has no `variant_sim_data` concept today — P0 uses the compose run's `cache_dir`; flag if that's insufficient for a variant strain.
4. **Registration:** ensure the analysis container registers sms_modules analyses — issue-166's v2ecoli#709/sms-ecoli#239 entry-point discovery fires in `run_analyses`; the analysis image must have sms-ecoli installed. Verify in the analysis node's image.
5. **SLURM backend (secondary):** if CD2 composite runs use the SLURM compose backend (`viva_api/compose/simulation_service.py`) rather than Batch, append the analysis runner to the sbatch between the composite run and the `zip`, OR chain a SLURM analysis job. VERIFY which backend GovCloud CD2 composite uses (Task 0) and scope P0 to that one.

### vivarium-workbench
6. **Send `analysis_options` in the request body/form, not a query param** — fix `lib/sms_api_client.compose_submit` (+ `remote_run.run_remote` passthrough) to carry it where viva-api now reads it.
7. **Land the results.** `run_runner._execute_remote` (`run_runner.py:858`) must land via `remote_run_landing.land_remote_run` (which already detects zarr/parquet and folds a manifest via `_fold_analyses`) instead of parking the raw `results.zip`. The folded `analyses.json` then surfaces through the existing `composite_run_views` per-run status.
8. Gate on `auto_results` (already wired at dispatch for the composite remote path — keep it gating the injection).

### The analysis CLI argv contract (from help-team #722)
The analysis invocation the compose chain builds MUST honor the real CLI: **positional `sweep_dir` + `--config`** — NOT `--experiment-id` / `--out-dir` (the gather node currently emits those and the real CLI rejects them; that's help-team's v2ecoli#722). Whatever `_analysis_command` is reused/shared must produce the positional-sweep_dir + `--config` form, or fix it to.

## Acceptance
A GovCloud composite run (CD2, e.g. K4) with a declared analysis: the analysis node runs server-side, writes the manifest, the workbench lands it, and `analyses.json` + the analyses appear on the workbench per-run view — matching what a LOCAL composite run produces. Verified end-to-end on GovCloud with one CD2 composite.

## Non-goals (P1+, tracked separately)
- The general `ResultsPlan → ResultsRunner → manifest` unification (P1).
- Visualizations + tests/report-cards for composite GovCloud runs (they render workbench-land-side today; server-side move is P1/P2).
- Deleting `run_declared_results`, the duplicate 8-stage flush, the 4 `build_analysis_options` sites (P1).
- Typed `ResultDecl` + `tests=` in process-bigraph (P2).
- Collapsing the two dispatch paths (P3).

## Risks / verify-first
- **Which compose backend does GovCloud CD2 use — Batch or SLURM?** Determines where the chain goes (Task 0, gating).
- The compose output store's exact prefix/partitioning vs what `_analysis_command` expects (`emitter_arg.out_dir`/S3 uri) — confirm the reader can point at the compose prefix.
- The analysis image having sms-ecoli + the entry-point registration (else ptools_metabolites won't register).
