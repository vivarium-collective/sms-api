# Compose Results P0 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or superpowers:executing-plans. Steps use `- [ ]`.

**Goal:** Make GovCloud composite runs auto-run their declared analyses on completion (fix the vwb#1022 no-op), by chaining an analysis job onto the compose sim that writes the standard analysis manifest, which the workbench lands.

**Architecture:** Reuse the study Batch analysis-DAG-node (`viva_api/simulation/simulation_service_ray.py` `_submit_analysis_job`/`_analysis_command`) for the compose Batch backend; carry `analysis_options` on the compose request; land the manifest in the workbench via the existing `land_remote_run`/`_fold_analyses`. Analyses only (viz/tests = P1).

**Tech Stack:** Python; viva-api (FastAPI + AWS Batch / SLURM HPC dispatch, pkg `viva_api/`); vivarium-workbench (`lib/`). pytest.

**Spec:** `docs/superpowers/specs/2026-09-07-compose-results-p0-design.md`
**Worktrees:** viva-api `~/code/sms-api--compose-results` (branch `compose-results-p0`, off origin/main dbe82876); workbench `~/code/vivarium-workbench--compose-results` (branch `compose-results-land-p0`, off origin/main 1916195f).

## Global Constraints
- No AI attribution on commits (no `Co-Authored-By: Claude` / `Claude-Session:`). Subject-only.
- Analysis CLI argv contract (help-team v2ecoli#722): the analysis invocation MUST be **positional `sweep_dir` + `--config`**, never `--experiment-id`/`--out-dir`.
- sim_data points at the compose run's OWN cache, never a stock per-commit one (viva-api#448 trap).
- Scope is ANALYSES only. Do NOT touch viz/tests/report-cards, do not build the general ResultsRunner (P1), do not delete `run_declared_results`/the duplicate flush (P1).
- Two repos: viva-api tasks in the sms-api worktree, workbench tasks in the workbench worktree; run each repo's own suite.
- GovCloud can't run in CI: HPC-submit tasks are unit-tested by asserting the submitted job spec (mock the Batch/SLURM client), not by a live run. The one live end-to-end check is manual (Task 7).

---

### Task 0 (GATING — verify-first; do before any code): pin the unknowns
**Files:** none (investigation → write findings to `docs/superpowers/plans/compose-results-p0-findings.md`).

Answer, with file:line, in the findings file — the rest of the plan is parameterized by these:
1. **Which compose backend does GovCloud CD2 use — Batch (`viva_api/compose/simulation_service_ray.py`) or SLURM (`viva_api/compose/simulation_service.py`)?** Check how the compose subsystem selects a backend (dependencies.py `_init_compose_subsystem`) and what the GovCloud deployment namespace resolves to. Scope Tasks 2-3 to that backend.
2. **The compose output store contract:** what `run_pbg.py` writes and where (the S3/HPC prefix, parquet/zarr partitioning) — confirm an analysis reader can be pointed at it via `emitter_arg.out_dir`/an S3 uri. Cite `run_pbg.py` (the emitter redirect + flush).
3. **The reusable analysis submitter:** read `viva_api/simulation/simulation_service_ray.py` `_submit_analysis_job` (~L2073) + `_analysis_command` (~L2010) — its exact signature, the argv it builds (confirm/fix to positional sweep_dir + --config per #722), how it points at the sim output + sim_data, and how it records in the `analyses` table. Note what must be extracted to be callable from compose.
4. **The workbench land seam:** read `vivarium-workbench lib/remote_run_landing.py` `land_remote_run` + `_fold_analyses`, and `lib/run_runner.py` `_execute_remote` — confirm `land_remote_run` folds the manifest the analysis node writes, and what `_execute_remote` must call to land instead of parking the zip.
5. **Analysis image:** confirm the analysis container image has sms-ecoli installed and that `run_analyses`/`_register_builtin_analyses` fires the entry-point discovery (v2ecoli#709/sms-ecoli#239) so `ptools_metabolites` registers.

- [ ] Investigate the 5 items; write `compose-results-p0-findings.md` with file:line evidence and the backend decision.
- [ ] Commit the findings file.

If item 1 says SLURM (not Batch), Task 2/3 target `viva_api/compose/simulation_service.py` (append the analysis runner to the sbatch) instead — same intent, different host; the findings file records the concrete anchor.

---

### Task 1 (viva-api): carry `analysis_options` on the compose request
**Files:**
- Modify: `viva_api/compose/models.py` (`ComposeSimulationRequest`, `ComposeDocumentSubmission`)
- Modify: `viva_api/api/routers/compose.py` (`/simulation/run`, `/run-document` handlers)
- Modify: `viva_api/compose/handlers.py` (`run_compose_simulation`/`_v2ecoli`/`_curated` construction sites) + the DB insert (persist on the `ComposeSimulation` row)
- Test: `tests/compose/test_compose_request_analysis_options.py` (new)

**Interfaces:** Produces `analysis_options: dict | None` on the compose request + persisted on the row; consumed by Task 3.

- [ ] **Step 1: failing test** — POST the compose run/run-document with an `analysis_options` form field (JSON string) and assert it round-trips onto the constructed `ComposeSimulationRequest` and the persisted `ComposeSimulation` row. Mirror the existing compose request test (find `tests/compose/test_*` that posts to `/simulation/run`).
- [ ] **Step 2: run it — fails** (`analysis_options` unknown / dropped).
- [ ] **Step 3: implement** — add `analysis_options: dict | None = None` to the request model(s); accept it as a multipart Form field carrying a JSON string on both endpoints (parse with `json.loads`, default `None`); thread it through the 3 construction sites and the DB insert. Follow the endpoints' existing Form-field pattern.
- [ ] **Step 4: run tests — pass.**
- [ ] **Step 5: commit** — `feat(compose): accept analysis_options on the compose run request`.

---

### Task 2 (viva-api): make the analysis-node submitter reusable
**Files:**
- Modify: `viva_api/simulation/simulation_service_ray.py` (extract `_submit_analysis_job`/`_analysis_command` into a shared, backend-callable helper — or a small `viva_api/common/analysis_dag.py`) — per the Task-0 findings.
- Test: `tests/.../test_analysis_dag_reuse.py` (new)

**Interfaces:** Produces a function that, given (output store prefix, analysis_options, sim_data ref, a dependsOn parent job id), submits the analysis Batch job and returns its id + records it in the `analyses` table — callable from BOTH the study and compose backends. The argv it emits is positional `sweep_dir` + `--config` (#722).

- [ ] **Step 1: failing test** — call the extracted helper with a mocked Batch client; assert the submitted job's command is the positional-`sweep_dir` + `--config` form (NOT `--experiment-id`/`--out-dir`), that it `dependsOn` the given parent, and that the config points sim_data at the given cache (not a stock path).
- [ ] **Step 2: run it — fails.**
- [ ] **Step 3: implement** — extract the study path's analysis-node submit into the shared helper with no behavior change for the study caller; if `_analysis_command` currently emits `--experiment-id`/`--out-dir`, fix it to the positional+`--config` contract (coordinate with help-team #722 so the fix lands once).
- [ ] **Step 4: run tests — pass** (incl. the existing study-path Batch tests — no regression).
- [ ] **Step 5: commit** — `refactor(analysis): share the Batch analysis-node submitter; honor positional sweep_dir+--config`.

---

### Task 3 (viva-api): chain the analysis node onto the compose sim
**Files:**
- Modify: the compose backend from Task-0 findings — Batch: `viva_api/compose/simulation_service_ray.py` (`submit_simulation_job`); SLURM: `viva_api/compose/simulation_service.py` (append to the sbatch).
- Test: `tests/compose/test_compose_chains_analysis.py` (new)

**Interfaces:** Consumes Task 1's `analysis_options` + Task 2's shared submitter.

- [ ] **Step 1: failing test** — with a mocked backend client, submit a compose run whose row carries `analysis_options`; assert an analysis job is submitted that `dependsOn` the compose sim job, pointed at the compose run's output prefix + its cache; and that with `analysis_options` absent NO analysis job is submitted.
- [ ] **Step 2: run it — fails.**
- [ ] **Step 3: implement** — after the compose sim job is submitted (Batch: reuse the `dependsOn` chaining already used for ParСa→sim; SLURM: append the runner between `composite.run` and `zip`), call the Task-2 helper when `analysis_options` is present; record the analysis job so `GET /analyses/{id}/status` (S3-manifest probe) works for compose.
- [ ] **Step 4: run tests — pass.**
- [ ] **Step 5: commit** — `feat(compose): chain the analysis DAG node onto compose sims when analysis_options is declared`.

---

### Task 4 (workbench): send `analysis_options` in the request body/form
**Files:**
- Modify: `vivarium-workbench lib/sms_api_client.py` (`compose_submit` — stop encoding `analysis_options` as a query param; send it in the multipart body/form where Task 1 reads it)
- Modify: `lib/remote_run.py` (`run_remote` passthrough, if it drops it)
- Test: `tests/test_C3_sms_client.py` (extend — urlopen-patched)

- [ ] **Step 1: failing test** — assert `compose_submit(..., analysis_options={...})` sends it in the request body/form (not the query string), and omits it when `None`. (This is the fix for the exact bug that made #1022 a no-op.)
- [ ] **Step 2: run it — fails** (currently a dropped query param).
- [ ] **Step 3: implement** — move `analysis_options` from the query string into the multipart form field Task 1 expects.
- [ ] **Step 4: run tests — pass.**
- [ ] **Step 5: commit** — `fix(remote): send compose analysis_options in the request body, not a dropped query param`.

---

### Task 5 (workbench): land the compose results manifest
**Files:**
- Modify: `lib/run_runner.py` (`_execute_remote` — land via `remote_run_landing.land_remote_run` instead of parking the raw `results.zip`)
- Modify: `lib/remote_run.py` (drop/adjust the raw-zip return contract as needed)
- Test: `tests/test_remote_composite_land.py` (new; mock the client + a fixture results tar/manifest)

- [ ] **Step 1: failing test** — a completed compose remote run whose landed artifact contains a manifest → `_execute_remote` calls `land_remote_run`, `_fold_analyses` writes `analyses.json`, and the per-run status reports `has_analyses`. (Mirror the existing study land test.)
- [ ] **Step 2: run it — fails** (`_execute_remote` parks the zip, never lands).
- [ ] **Step 3: implement** — route `_execute_remote` through `land_remote_run` (it already detects zarr/parquet + folds manifests); ensure the composite run dir gets `analyses.json`.
- [ ] **Step 4: run tests — pass.**
- [ ] **Step 5: commit** — `feat(remote): land compose run results (fold the analysis manifest) instead of parking the zip`.

---

### Task 6: end-to-end acceptance (manual, GovCloud)
**Files:** none (a documented manual verification; CI can't run GovCloud).

- [ ] Dispatch one CD2 composite (e.g. K4) to GovCloud with a declared ptools analysis; confirm the analysis job runs server-side, the manifest lands, and `analyses.json` + the analyses appear on the workbench per-run view — matching a local composite run. Record the run id + result in the findings file. Coordinate with Alex (@AlexPatrie) / help-team (#166) for the GovCloud run.

## Self-Review
- Spec coverage: request field (T1), reuse+argv (T2), compose chain (T3), workbench send+land (T4/T5), acceptance (T6), backend/registration/store unknowns (T0). ✓
- No-op fix: T4 (dropped query param) + T5 (never-lands) are the two exact causes Fable found. ✓
- Placeholder scan: HPC-submit tasks intentionally say "mirror `_submit_analysis_job` per Task-0 findings" with exact anchors rather than inlining code not yet read against live HPC — legitimate given Task 0 gates the specifics and GovCloud isn't in CI. Test intent is concrete per task.
- Type consistency: `analysis_options: dict | None` flows T1→T3; the shared submitter signature is fixed in T2 and consumed in T3.
- Ordering: T0 gates all; T2 before T3; T1 before T3; T4/T5 (workbench) independent of viva-api and can proceed in parallel once T0's land-seam item is confirmed.
