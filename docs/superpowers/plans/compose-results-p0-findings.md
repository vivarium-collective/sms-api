# Compose Results P0 — Task 0 Findings

**Date:** 2026-09-07
**Scope:** verify-first investigation only (no code changes). Answers the 5 gating
items in `docs/superpowers/plans/2026-09-07-compose-results-p0.md` Task 0, plus
two additional blockers surfaced while tracing the actual code (not just the
plan's assumptions).

---

## 1. Which compose backend does GovCloud use?

**BACKEND DECISION: Batch/Ray (`ComposeSimulationServiceRay`,
`viva_api/compose/simulation_service_ray.py`).** Tasks 2–3 target that file, not
the SLURM path.

Trace:
- `viva_api/dependencies.py:436-501` `_init_compose_subsystem` builds a
  per-backend `compose_registry: dict[ComputeBackend, ComposeSimulationService]`:
  - `dependencies.py:475-479` registers `ComputeBackend.RAY →
    ComposeSimulationServiceRay()` **iff `settings.ray_mnp_queue` is truthy**.
  - `dependencies.py:480-482` registers `ComputeBackend.SLURM →
    ComposeSimulationServiceHpc()` **iff `default_backend == ComputeBackend.SLURM`**
    (`default_backend = get_job_backend()`, i.e. the `COMPUTE_BACKEND` env var —
    `viva_api/config.py:424-433`).
  - `dependencies.py:485-487`: `compose_sim = compose_registry.get(default_backend)
    or next(iter(compose_registry.values()), ComposeSimulationServiceHpc())`.
    **There is no branch that ever inserts a `ComputeBackend.BATCH` key into
    `compose_registry`** — only RAY and SLURM are ever registered. So when
    `default_backend == ComputeBackend.BATCH`, `compose_registry.get(BATCH)` is
    always `None`, and the `or` falls through to `next(iter(...))`.
  - This service becomes the default via `set_compose_services(sim=compose_sim,
    ...)` (`dependencies.py:496`), and `viva_api/api/routers/compose.py:83-102`
    `_require_sim(compute_backend=None)` returns exactly that default
    (`_compose_sim_service`) for the normal (no per-request override) case.
- Both Stanford overlays set `COMPUTE_BACKEND=batch`
  (`kustomize/config/sms-api-stanford/shared.env:2`,
  `kustomize/config/sms-api-stanford-test/shared.env:4`) — **not** `ray` and
  **not** `slurm`. `default_backend` is therefore `ComputeBackend.BATCH` on both
  GovCloud namespaces.
- Both Stanford overlays also set `RAY_MNP_QUEUE`
  (`sms-api-stanford/shared.env:26 RAY_MNP_QUEUE=smscdk-ray-mnp`,
  `sms-api-stanford-test/shared.env:29 RAY_MNP_QUEUE=smsvpctest-ray-mnp`), so
  `settings.ray_mnp_queue` is truthy → `compose_registry = {RAY:
  ComposeSimulationServiceRay()}` only (SLURM is never inserted, since
  `default_backend` is `BATCH`, not `SLURM`).
- Given `compose_registry.get(BATCH) is None`, the fallback
  `next(iter(compose_registry.values()))` returns the **only** entry —
  `ComposeSimulationServiceRay`. That is the default compose backend on both
  GovCloud namespaces today.
- Both Stanford overlays also set the Ray-Batch-specific compose settings
  (`COMPOSE_RAY_IMAGE_TAG`, `COMPOSE_PARCA_CACHE_DIR`,
  `COMPOSE_PBG_CORE_BUILDER=v2ecoli.core:build_core` —
  `sms-api-stanford/shared.env` and `sms-api-stanford-test/shared.env`, "Compose
  (Ray-on-Batch)" section), which only `ComposeSimulationServiceRay` reads
  (`viva_api/compose/simulation_service_ray.py:73-83,97,127-133`). Neither
  overlay sets any `HPC_*`/`SLURM_*` var the SLURM compose path
  (`ComposeSimulationServiceHpc`, `viva_api/compose/simulation_service.py`)
  needs. This is independent, corroborating evidence for the same conclusion.

**Note — stale comment in the code itself:** `dependencies.py:483-484` says
*"Stanford runs COMPUTE_BACKEND=ray; UCONN → SLURM"* — this is wrong as written
(Stanford actually runs `COMPUTE_BACKEND=batch` and reaches Ray only via the
`compose_registry` fallback described above, not because `default_backend` is
literally `ray`). The conclusion (Ray/Batch wins on Stanford) is still correct,
but a future reader trusting the comment's literal claim would misread *why*.
Worth a one-line comment fix, out of scope for this findings task.

---

## 2. Compose output store contract (`run_pbg.py`)

- **Where it writes, inside the container:** `RESULTS_DIR` /
  `PBG_RESULTS_DIR`, default `/experiment/output`
  (`viva_api/compose/run_pbg.py:38`). The Batch/Ray dispatch overrides it to
  `COMPOSE_OUT_DIR = "/tmp/pbg_out"`
  (`viva_api/compose/simulation_service_ray.py:38`, passed as
  `PBG_RESULTS_DIR={COMPOSE_OUT_DIR}` in the container command,
  `simulation_service_ray.py:100,107`).
- **The emitter redirect:** `_redirect_emitters(document, results_dir)`
  (`run_pbg.py:566-608`) recursively rewrites any file-backed emitter step's
  `out_dir`/`out_uri` config key (`_EMITTER_OUT_KEYS = ("out_dir", "out_uri")`,
  `run_pbg.py:193`) to `str(results_dir)` — line `run_pbg.py:600
  config[key] = str(results_dir)` — overriding whatever workspace-relative path
  the authoring document had. Called at `run_pbg.py:718` inside `run()`, before
  `Composite(document, core=core)` is constructed (`run_pbg.py:719`).
- **The flush:** `_flush_emitters(composite)` (`run_pbg.py:208-229`) calls
  `viva_emitters.ParquetEmitter.flush_all_in_composite(composite,
  success=True)` — the trailing partial batch. Called at `run_pbg.py:721`,
  right after `composite.run(steps)` (`run_pbg.py:720`) and before
  `final_state.json` is written (`run_pbg.py:731-732`).
- **v2ecoli-specific override** (`_v2ecoli_parquet_emitter_override`,
  `run_pbg.py:41-113`): for v2ecoli composites (`ecoli_baseline`/
  `batch_baseline`) whose default `ParquetEmitter` is built eagerly inside
  `to_document()` (so the generic redirect above has nothing to act on), this
  calls v2ecoli's `set_parquet_emitter_override` with a real
  `parquet_vecoli(out_dir=..., experiment_id=..., lineage_seed=..., generation=...)`
  preset — confirmed (per the docstring, `run_pbg.py:60-63`) to produce real
  hive-partition columns (`variant`/`lineage_seed`/`generation`/`agent_id`),
  not a bare `out_dir` that loses partitioning.
- **Where it lands in S3 / the URI shape:** the Batch container command
  (`_compose_command`, `simulation_service_ray.py:85-109`) writes to
  `COMPOSE_OUT_DIR` locally; the image's own Ray-on-Batch entrypoint
  (bundled in the image, not in this repo — `simulation_service_ray.py:36-37`
  comment) syncs `RAY_OUT_DIR → RAY_OUT_S3`. `submit_simulation_job` passes
  `out_s3=data_layout.RayLayout.results_uri(experiment_id)` and
  `out_dir=COMPOSE_OUT_DIR` into `self._ray._submit_mnp(...)`
  (`simulation_service_ray.py:199-208`, specifically lines 204-205).
  `RayLayout.results_uri` = `s3://{bucket}/{prefix}/{experiment_id}/`
  (`viva_api/common/storage/data_layout.py:76-78`, single-nested,
  trailing-slash = sync dir) — bucket-relative prefix built from
  `RayLayout.experiment_prefix` (`data_layout.py:71-73`).
- **Can an analysis reader point at it via S3 uri / `emitter_arg.out_dir`?
  YES, and the study Batch analysis path already does, at the exact same URI
  shape**: `SimulationServiceRay._results_s3_uri(experiment_id)` (used by
  `_analysis_command`, see item 3) is `data_layout.RayLayout.results_uri
  (experiment_id)` verbatim (`viva_api/simulation/simulation_service_ray.py:
  582-583`) — the identical helper compose's `submit_simulation_job` calls. So
  a compose experiment's S3 prefix and a study Ray simulation's S3 prefix are
  laid out through the same `RayLayout` class/convention; an analysis reader
  built against one is, by construction, pointed at the other correctly as
  long as `experiment_id` is threaded through unchanged.
- **sim_data cache**: `RayLayout.parca_cache_uri(commit)` (`data_layout.py:
  116-133`) is used both by compose's own ParCa staging (`_parca_staging`,
  `simulation_service_ray.py:111-133`, keyed by `commit or
  settings.compose_ray_image_tag`) and by the study analysis command's
  `sim_data_uri` (see item 3) — same helper, same key convention.

## 3. The reusable analysis submitter (`viva_api/simulation/simulation_service_ray.py`)

**Signatures** (as of this checkout):
- `_analysis_command(self, *, experiment_id: str, n_seeds: int, n_generations:
  int, modules: dict[str, dict[str, Any]] | str, analysis_name: str, commit:
  str) -> str` — `simulation_service_ray.py:2010-2071`.
- `_submit_analysis_job(self, *, simulation: Simulation, database_service:
  DatabaseService, job_definition: str, commit: str, sim_job_id: str | None,
  n_seeds: int, n_generations: int, depends_type: str | None, tags: dict[str,
  str]) -> str | None` — `simulation_service_ray.py:2073-2177`.

**The argv it builds TODAY — SURPRISE, matches neither form the plan
anticipated.** `_analysis_command` (`simulation_service_ray.py:2062-2071`)
builds:

```
cd /app/v2ecoli && V2ECOLI_SIM_DATA=<sim_data_uri> python scripts/run_standalone_analysis.py \
  --out-uri <out_uri> --n-seeds <n> [--n-generations <n>] --modules <json> --analysis-name <name>
```

This is neither `--experiment-id`/`--out-dir` (the plan's "wrong form") nor
positional `sweep_dir` + `--config` (the plan's "target form" from help-team
v2ecoli#722) — it is a **third, flag-based form** (`--out-uri`, `--n-seeds`,
`--n-generations`, `--modules`, `--analysis-name`), invoking a *different*
script (`scripts/run_standalone_analysis.py`) than the ones referenced
elsewhere in this repo under the `--config`/`--config-file` names:
- `viva_api/simulation/simulation_service_k8s.py:462` invokes the **same**
  `scripts/run_standalone_analysis.py` but with **`--config-file
  /config/params.json`** (a third-different invocation of the same script, for
  the K8s-native analysis path).
- `viva_api/analysis/analysis_service.py:369` and
  `viva_api/simulation/simulation_service.py:407,713` invoke a **different**
  script, `runscripts/analysis.py --config <path>` (the SLURM path).
- **`scripts/run_standalone_analysis.py` itself is not vendored in this repo**
  (it ships inside the v2ecoli/sms-ecoli image) — this repo cannot confirm from
  its own source whether that script's real argparse contract is positional
  `sweep_dir` + `--config`, `--config-file`, or the flags `_analysis_command`
  emits today. **This is a real gap Task 2 must resolve by reading the actual
  script in the v2ecoli/sms-ecoli repo (or coordinating with help-team #722)
  before "fixing to the positional+--config contract" — the plan's assumption
  about what's broken vs. correct does not match what's in viva-api.**

**How it points at the sim output store + sim_data cache**
(`simulation_service_ray.py:2052-2053`):
```python
out_uri = self._results_s3_uri(experiment_id).rstrip("/")   # RayLayout.results_uri(experiment_id)
sim_data_uri = f"{data_layout.RayLayout.parca_cache_uri(commit)}simData.cPickle"
```
Both derive from `experiment_id`/`commit` alone — no other simulation-specific
state — which is exactly what a compose caller has available (compose already
computes an `experiment_id` and, when a per-run image was resolved, a
`commit`; see item 2).

**How it records in the `analyses` table**
(`_submit_analysis_job`, `simulation_service_ray.py:2130-2176`): submits via
`self._submit_container(...)` then calls `database_service.record_analysis(
experiment_id=..., n_tp=None, status=..., config=params, name=analysis_name,
simulation_id=simulation.database_id, backend="ray", job_id_ext=...,
result_uri=f"{out_uri}/analyses/{analysis_name}")`. `record_analysis` is
declared on the **study** `DatabaseService` ABC
(`viva_api/simulation/database_service.py:64-79`) and implemented in
`DatabaseServiceSQL` (`database_service.py:439`). Its `simulation_id` param is
`int | None = None` — **not a hard FK requirement** — so a caller with no
study `Simulation` row (i.e. compose) can pass `simulation_id=None`.

**What must be EXTRACTED to call this from the compose backend** (concrete,
beyond the plan's one-line note):
1. **Type coupling.** `_submit_analysis_job` takes a `simulation: Simulation`
   (the *study* ORM/dataclass type) and reads `simulation.config.experiment_id`
   plus calls `analysis_modules_for(simulation.config)`
   (`simulation_service_ray.py:2110,2114`, helper at `:248-269`) and
   `simulation.database_id` (`:2160,2172`). Compose's own request type is
   `ComposeSimulation`/`ComposeSimulationRequest`
   (`viva_api/compose/models.py:285-296`), a *different* type with no
   `.config.analysis_options`/`.database_id` shape. The helper must be
   re-parameterized to take plain values (`experiment_id: str, modules: dict |
   str, database_id: int | None`) rather than a `Simulation` object — matches
   the plan's Task 2 intent exactly, just spelled out precisely here.
2. **Cross-subsystem DB access.** `record_analysis` lives on the *study*
   `DatabaseService`, obtained via `viva_api.dependencies.get_database_service()`
   — **not** on `ComposeDatabaseService`
   (`viva_api/compose/database_service.py` has no `analyses`-table concept at
   all — grepped, zero hits). The good news: `ComposeSimulationServiceRay`
   **already imports and calls this exact cross-subsystem accessor** today, for
   a different reason (`_resolve_commit`,
   `viva_api/compose/simulation_service_ray.py:135-153`, specifically
   `simulation_service_ray.py:145 from viva_api.dependencies import
   get_database_service`) — so the import path is proven to work from the
   compose module; Task 2/3 just needs to reuse it to fetch the study
   `DatabaseService` for `record_analysis(..., simulation_id=None, ...)`.
3. **`_ensure_container_job_def`/`self._image_uri(commit)`.**
   `ComposeSimulationServiceRay.__init__` already holds `self._ray =
   SimulationServiceRay()` (`simulation_service_ray.py` compose file, line 65),
   so `self._ray._ensure_container_job_def(image, commit_or_tag)` and
   `self._ray._analysis_command(...)`/`self._ray._submit_analysis_job(...)`
   (once re-parameterized per point 1) are directly reachable without new
   plumbing — see `submit_campaign_analysis`
   (`simulation_service_ray.py:3301-3339`) for the existing precedent pattern
   (a thin wrapper that resolves a container job def then calls
   `_submit_analysis_job`).
4. **`modules`/`analysis_options` shape.** `analysis_modules_for(config)`
   (`simulation_service_ray.py:248-269`) does `getattr(config,
   "analysis_options", None)` and handles both a pydantic `BaseModel` and a
   plain `dict` — so once Task 1 adds `analysis_options: dict | None` to the
   compose request model, this helper (or its post-extraction replacement)
   accepts it unchanged.

## 4. Workbench land seam

- **`_fold_analyses(extract_root, ws_root, run_id)`**
  (`vivarium_workbench/lib/remote_run_landing.py:54-82`): globs
  `extract_root.glob("**/analyses/*/_manifest.json")`
  (`remote_run_landing.py:67`) and, for each manifest found, reads
  `manifest.get("analysis_name")`, `manifest.get("written", [])`,
  `manifest.get("errors", [])` (`remote_run_landing.py:76-79`), writing
  `.pbg/runs/<run_id>/analyses.json` (`remote_run_landing.py:80-82`). This
  **is compatible with the manifest shape the study Batch analysis node
  produces**: `_submit_analysis_job` sets `result_uri =
  f"{out_uri}/analyses/{analysis_name}"`
  (`viva_api/simulation/simulation_service_ray.py:2113`) — i.e. an
  `analyses/<analysis_name>/` prefix under the sim's own output root, matching
  the glob exactly, assuming `run_standalone_analysis.py`/`run_analyses`
  writes a `_manifest.json` there (not independently verifiable from this
  repo — the script isn't vendored — but the shape `_fold_analyses` expects is
  the shape the reused submitter's `result_uri` targets).
- **`land_remote_run(...)`** (`remote_run_landing.py:162-335`): extracts
  `tar_path` via **`tarfile.open(tar_path, "r:gz")`**
  (`remote_run_landing.py:239-240`) — **a `.tar.gz`, not a `.zip`.** Detects
  zarr vs. parquet (`_detect_and_locate_all`, `:85-109`), lands the store under
  `study_dir`, and — only `if ws_root is not None` (`:271-272`) — calls
  `_fold_analyses(extract_root, ws_root, run_id)`.
- **`_execute_remote(req, run_dir)`**
  (`vivarium_workbench/lib/run_runner.py:858-905`) — confirmed to already
  build `analysis_options` (`_remote_analysis_options`, `run_runner.py:
  ~820-855`, reading `req.declared_results`/the composite's declared analyses
  via `study_run_post.build_analysis_options`) and thread it into
  `remote_run.run_remote(..., analysis_options=analysis_options)`
  (`run_runner.py:880-886`) when non-empty. **What it does NOT do**: after
  `remote_run.run_remote(...)` returns, it only calls
  `cr.complete_metadata(conn, run_id=req.run_id, n_steps=req.steps,
  status="completed")` (`run_runner.py:900-901`) — **it never calls
  `land_remote_run`, never unpacks the downloaded archive, and discards the
  `Path` `run_remote()` returns.** This confirms the plan's framing: the run
  is marked "completed" with the raw results artifact just parked on disk,
  never landed/folded.

### Additional blocker NOT anticipated by the plan: zip vs. tar.gz format mismatch

`remote_run.run_remote()` downloads results via
`client.download_compose_results(sim_id, dest)`
(`vivarium_workbench/lib/remote_run.py:239`), whose implementation
(`vivarium_workbench/lib/sms_api_client.py:601-624`) streams
`GET /compose/v1/simulation/{id}/results` to **`dest / "results.zip"`**
(`sms_api_client.py:611`, confirmed server-side:
`viva_api/api/routers/compose.py:289` returns
`FileResponse(..., filename=f"{experiment_id}_results.zip",
media_type="application/zip")`).

`land_remote_run` unconditionally opens its `tar_path` argument with
`tarfile.open(tar_path, "r:gz")` (`remote_run_landing.py:239-240`) — **it
cannot read a `.zip`.** The *existing, working* caller of `land_remote_run`
(`vivarium_workbench/lib/remote_run_views.py:536` in the study/non-compose
land route) gets a real `.tar.gz` from a **different** viva-api endpoint —
`client.download_data(sim_id, ...)` → `POST
/api/v1/simulations/{id}/data` → `sim_{id}.tar.gz`
(`sms_api_client.py:626-639`) — which has **no compose equivalent**. Grepped
`viva_api/api/routers/compose.py` for every route; the only download route is
`get_results` (zip, SLURM SCP — see below).

**Task 5 as currently scoped ("route `_execute_remote` through
`land_remote_run`") cannot work unmodified against the compose `results.zip`.**
Either (a) `remote_run_landing`/`_detect_and_locate_all` need a
`zipfile`-based extraction path in addition to `tarfile`, or (b) `_execute_remote`
must convert the zip to a tar-like structure before calling `land_remote_run`,
or (c) viva-api needs a tar.gz-serving compose download route. This needs a
decision before Task 5 is implemented — it is a real scope item, not a detail.

### Additional blocker NOT anticipated by the plan: the compose results-download route is SLURM-only and will fail on GovCloud/Ray

`GET /compose/v1/simulation/{id}/results` (`get_results`,
`viva_api/api/routers/compose.py:251-289`) is **hardcoded to SLURM SSH/SCP**
regardless of which backend actually ran the simulation:
```python
async with get_ssh_session_service(SSHTarget.SLURM).session() as ssh:
    await ssh.scp_download(local_file=local_path,
                            remote_path=HPCFilePath(remote_path=remote_path))
```
(`compose.py:280-281`), where `remote_path = get_compose_sim_results_path
(experiment_id)` (`compose.py:271`) resolves to a **local HPC filesystem
path** (`compose_sim_base_path / "experiment-{experiment_id}" /
"results.zip"`, `viva_api/compose/hpc_utils.py:26-34`) — meaningless for a
Batch/Ray run whose output lives in S3 under `RayLayout.results_uri` (item 2).

`ComposeSimulationService`'s ABC (`viva_api/compose/simulation_service.py:
39-62`) declares only `submit_simulation_job`, `build_container`,
`get_job_status` — **no `download_results`/results-retrieval method at all**,
so there is no backend-aware dispatch point this route could call into even in
principle; it always goes through the one hardcoded SSH branch.

`SSHTarget.SLURM` is only registered when `settings.slurm_submit_host` and
`settings.slurm_submit_key_path` are both set
(`viva_api/dependencies.py:293-311`); neither Stanford overlay's `shared.env`
sets either (grepped both files, zero hits), so
`get_ssh_session_service(SSHTarget.SLURM)` raises `RuntimeError
("SSHSessionService 'slurm' not initialized")` on both GovCloud namespaces —
this route returns a 500 for **every** compose run on GovCloud today,
independent of `analysis_options`.

**This means the "GovCloud half is a silent no-op" framing in the spec may
understate the current state**: if `get_results` genuinely 500s on
Stanford/Stanford-test, `client.download_compose_results()` raises
`SmsApiError`, `remote_run.run_remote()` propagates it, and `_execute_remote`
logs "REMOTE RUN FAILED" and marks the run `status="failed"` — i.e. a GovCloud
composite run may not even be completing/landing *anything* today, not just
missing analyses. **This should be verified against a real GovCloud dispatch
before Task 5 is scoped/started** (or confirmed as already known/tracked
elsewhere) — it is out of this investigation's scope to run that dispatch, but
it changes what "land the compose results manifest" (Task 5) actually needs to
fix: potentially a new Ray/S3-aware results-download route in viva-api
(`viva_api/api/routers/compose.py`), not only a workbench-side landing change.

## 5. Analysis image registration

- **Image identity**: the Ray/Batch backend (item 1) submits both the compose
  sim and — if Task 2/3 reuse `_submit_analysis_job`/`_analysis_command` as
  designed — the analysis node against the **same image family**:
  `ComposeSimulationServiceRay._image_uri(commit=None)`
  (`viva_api/compose/simulation_service_ray.py:67-83`) resolves
  `<ecr_account>.dkr.ecr.<region>.amazonaws.com/<ray_ecr_repository>:<compose_ray_image_tag>`
  — the same `ray_ecr_repository`/registry the study Ray path's
  `SimulationServiceRay._image_uri(commit)`
  (`simulation_service_ray.py:585-589`) uses. Both Stanford overlays'
  `COMPOSE_RAY_IMAGE_TAG` comments confirm this ECR repo (named `v2ecoli`) is
  actually built from **sms-ecoli** commits: `kustomize/config/sms-api-stanford
  /shared.env` "Compose (Ray-on-Batch)" section, the 2026-08-31 history —
  `COMPOSE_RAY_IMAGE_TAG=188da91`, "sms-ecoli `main` tip after #171 merged" —
  i.e. **sms-ecoli is installed in this image by construction** (it's built
  from that repo).
- **Not bespoke — goes through `run_analyses`**: `_analysis_command`'s own
  docstring (`simulation_service_ray.py:2040-2043`) states the node "reuses
  the model image's existing, S3-native entrypoint
  (`scripts/run_standalone_analysis.py` → `v2ecoli.workflow.analysis_runner.
  run_analyses`) — the SAME function the composite's inline flush calls."
  If Task 2/3 reuse this exact command (rather than hand-rolling a bespoke
  compose-side analysis invocation), the entry-point discovery path (v2ecoli
  #709/sms-ecoli#239) is exercised automatically — no separate
  `import v2ecoli.workflow.analysis_runner; _register_builtin_analyses()`
  call is needed in viva-api, since it is presumably already inside
  `run_analyses`'s own implementation.
- **Caveat**: `scripts/run_standalone_analysis.py` and
  `v2ecoli.workflow.analysis_runner.run_analyses` are **not vendored in this
  repo** (they ship inside the v2ecoli/sms-ecoli image) — this repo's source
  cannot directly confirm that `run_analyses` calls
  `_register_builtin_analyses()` internally. What IS confirmed from this repo:
  (a) this exact call path is the one the *study* Ray backend already runs in
  production today (same `_analysis_command`), so if `ptools_metabolites`
  registration were broken here, the study path's auto-triggered analyses
  (viva-api 0.9.41, `viva_api/version.py:240-268`) would already be failing to
  register it too — making this a pre-existing, already-live code path rather
  than new-and-unverified; and (b) this is contingent on Task 2/3 actually
  reusing `_analysis_command` verbatim (item 3's finding) rather than building
  a new bespoke compose-side analysis command — if scope drifts to a bespoke
  invocation, the registration import becomes necessary and should be added
  explicitly.

---

## Summary of surprises for the rest of the plan

1. **Item 1 confirmed**: Ray/Batch (`ComposeSimulationServiceRay`), reached via
   registry-fallback (not because `COMPUTE_BACKEND` is literally `ray` on
   Stanford — it's `batch`, and the code comment claiming otherwise is stale).
2. **Item 2 confirmed**: output store contract is S3, same `RayLayout`
   convention the study analysis path already reads via `_results_s3_uri`.
   Emitter redirect (`run_pbg.py:566-608`) + flush (`run_pbg.py:208-229,721`)
   both cited.
3. **Item 3 — real surprise**: today's `_analysis_command` argv is neither of
   the two forms the plan named (`--experiment-id`/`--out-dir` vs. positional
   `sweep_dir`+`--config`) — it's a third, flag-based form
   (`--out-uri`/`--n-seeds`/`--n-generations`/`--modules`/`--analysis-name`)
   against `scripts/run_standalone_analysis.py`, which is not vendored in this
   repo. Task 2 needs to read that script directly (in the v2ecoli/sms-ecoli
   checkout) before deciding what "fix to positional+--config" means in
   practice. The extraction shape (decouple from `Simulation`/study
   `DatabaseService` types, reuse the already-proven
   `get_database_service()` cross-import) is now concretely specified.
4. **Item 4 — two real blockers beyond the plan's framing**:
   - `land_remote_run` requires `.tar.gz`; compose's only download route
     serves `.zip`. Needs a decision (zip-reading support in landing, or a
     converted/alternate download path) before Task 5 can be implemented as
     written.
   - `GET /compose/v1/simulation/{id}/results` is hardcoded to SLURM SSH/SCP
     and has no S3/Ray branch — it will raise on both Stanford namespaces for
     ANY compose run today, independent of analyses. This should be verified
     against a real GovCloud run before Task 5 is scoped; it may mean Task 5
     needs a new viva-api download route, not just a workbench landing change.
5. **Item 5 confirmed, conditionally**: sms-ecoli is installed in the compose
   Ray image by construction, and reuse of `_analysis_command` (item 3) routes
   through `run_analyses`, which should fire entry-point discovery for free —
   contingent on Task 2/3 not going bespoke.
