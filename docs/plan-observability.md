# Observability plan for whole-cell campaigns (viva-api · v2ecoli · process-bigraph)

> **Status (2026-09-10 05:50Z): APPROVED by Jim; implementation started.** PR-A (viva-api `feat/nextflow-head-poller`) and PR-B (process-bigraph `feat/events`) are in progress; PR-C/PR-D follow. Progress rows go in `docs/plan-nextflow-act3.md`; this file is the design of record. Companion to `plan-nextflow-dispatch.md`, `plan-nextflow-act2.md`, `plan-nextflow-act3.md`.


## Context — why now

On 2026-09-10 a one-line omission in v2ecoli's lineage carry policy (#765 carried the
per-tick `request`/`allocate` partition roots across division) killed every
multi-generation run built from `main` for five hours. Finding it needed:

- reading two CloudWatch log groups reachable only after `describe-jobs` for the stream
  name (the chain path logs to `smsvpctest-ray-batch-…`, Nextflow tasks to
  `/aws/batch/job`);
- reconstructing simulation id → Batch job id → log stream by hand, every time;
- a bisect image (simulator 192) to prove which of three co-shipped PRs was at fault;
- noticing by accident that 943's Nextflow head was silently re-running a
  deterministic crash (retry 3 of 10, API status "running"), and that 749 said
  "running" for hours after its head had finished with four failed tasks.

The same session showed the pattern is general, not one bug: the wrong chassis on
the 42 Run 4 inductions (silent overwrite of a shared S3 slot), the `6.07` vs
`10^6.07` induction (never checked before compute burned), the MNP swap drop
(classic FBA ran where redux was declared), the zarr `_check_group` race on the
MNP path. Each was invisible until a downstream process threw or a human compared
numbers. The API layer answered "running" or "failed: backoff limit" throughout.

The engineering principle Jim set: **we fix pipeline/dispatch/communication bugs and
measure; we do not decide model questions.** Observability is the tool that lets us
do the first without a bisect and lets Chris and Eran see the second.

## Broad goals

1. **A run explains itself.** From `atlantis simulation status <id>` (and the
   workbench) a person can tell, without AWS credentials: what stage it is in, whether
   it is progressing, what it decided at every seam (chassis, cache key, carried
   state, seed, retry), and — on failure — which process, at which simulated time, in
   which generation, with what state summary.
2. **Instrumentation is automatic.** Process and step authors (Chris, Alex, Eran,
   the CD2 contributors) do not add log lines. The engine (process-bigraph) and the
   runners (v2ecoli lineage runner, viva-api dispatchers) emit the events, so any new
   composite, injected process, or fork inherits the same visibility.
3. **One identity, end to end, with nested context.** A simulation id is stamped into
   every artifact: Batch job names, log stream prefixes, the S3 output prefix, the
   event stream. One query finds everything about a run. Identity is modelled
   OpenTelemetry-style (Jim, 05:40Z): a `trace_id` per campaign (viva-api's existing
   `HpcRun.correlation_id`), `span_id`/`parent_span_id` for the nested contexts
   campaign → ParCa / lineage(variant, seed) / analysis → generation → (opt-in)
   process invoke, propagated to tasks in W3C `traceparent` style through an
   environment variable. No OTel SDK in the engine; the schema is OTel-compatible so
   an OTLP exporter can be added later as one more sink.
4. **Failures fail once, and say why.** Deterministic crashes do not retry ten times;
   the first traceback reaches the API's `error_message`; the run flips to FAILED when
   its head or any required task fails, not when someone notices.
5. **Cheap enough to be always on.** Heartbeat and seam events cost nothing
   measurable against a 30-minute generation; per-tick detail is opt-in.

## Desirable characteristics

| characteristic | meaning here |
|---|---|
| **Layered, not centralised** | engine events (tick, process timing, exception context) · runner events (generation, carry, checkpoint) · dispatcher events (submit, stage cache, retry, reap) · API view (aggregate). Each layer works alone; together they compose. |
| **Structured** | one JSON object per event with `sim_id`, `experiment_id`, `variant`, `lineage_seed`, `generation`, `global_time`, `wall_time`, `event`, `level`, `payload`. Text logs keep working (stdout mirror), but the JSON is the contract. |
| **Push, not pull** | a task writes its events as it goes (stdout → CloudWatch, plus a per-run JSON-lines object flushed on a timer), so a stalled task is visible *before* it exits. Today S3 sees nothing until the task ends. |
| **State-aware, not just log-aware** | the engine can summarise a store cheaply (counts, sizes, min/max, NaN/negative flags) at a seam or at the moment of an exception. That is what turns "negative count in polypeptide elongation" into "daughter's `request` root carried 14 stale process entries totalling N counts". |
| **Zero-config default, knobs for depth** | always: heartbeat every N seconds of sim time, seam decisions, run start/end summary, exception context. Opt-in: per-process timing, per-tick store deltas (the #733 `LINEAGE_DEBUG_DIVISION` class), full state dumps. |
| **Backend-agnostic** | the same events on Nextflow tasks, chain container jobs, MNP Ray actors, local `vwb` runs. The transport differs (CloudWatch group, Ray driver log, local file), the schema does not. |
| **Reachable from the tools people already use** | `atlantis simulation status/events/log`, the workbench run page, the act docs. Not a new dashboard first. |
| **Tested like code** | log-line/event tests with `capsys`/`caplog` next to the behaviour they observe; a static test that every runtime root store is classified (the check that would have caught #765). |
| **Pluggable and optional, infrastructure-agnostic** (Jim, 05:35Z) | the engine defines an event-sink interface and ships only stdout and local-file sinks; it never imports boto3, kubernetes or redis. Sinks are registered by the caller (`PBG_EVENT_SINKS="stdout,file:/path"` or a registry call), so the S3 events object, CloudWatch enrichment and the API ingester are viva-api/v2ecoli adapters, each independently switchable off. A laptop `vwb` run gets identical events with the file sink alone. The core event schema carries no AWS identifiers; job ids and log streams are payload fields the dispatcher adapter adds. Off, or stdout-only, needs zero configuration. |

## Where instrumentation lives (the question this plan must settle)

Three candidate homes, from most general to most specific:

- **process-bigraph engine** (`Composite._run_inner` → `run_steps`/`run_process` →
  `process_update` → `invoke`): tick heartbeat, per-process wall time, exception
  context (process path, `global_time`, store summary), run start/end. Reaches every
  composite in the ecosystem; needs an upstream PR (eagmon's repo; contribution
  boundary applies to Alex, not to us — check).
- **v2ecoli runners** (`LineageProcess`, `LineageStep`, `run.py`, emitters):
  generation/carry/checkpoint/seed events, chunk-flush heartbeat, structured failure
  record at the top-level except.
- **viva-api dispatchers + scheduler**: submit/stage/retry/reap events, Batch job id
  ↔ sim id correlation, failure reason capture into `error_message`, head-exit → run
  status mapping, `/simulations/{id}/events`.

The plan (next section, after exploration) picks concrete hook points and a rollout
order that gives value at each step without waiting for the engine PR.

## What exists today (verified 2026-09-10; the plan reuses these rather than adding code)

| primitive | where | state |
|---|---|---|
| `PROCESS_BIGRAPH_TRACE_FILE` JSONL sink + `_trace_invoke` | process-bigraph `composite.py:43-110`, fired at `:3049` | built, referenced nowhere, records only *successful* invokes |
| `_summarize_value` (scalars, numpy → shape/dtype/sum/head, dict depth 3) | `composite.py:59-87` | reusable as the state summariser; lacks NaN/negative flags |
| `TimingSummary` / `Composite.timing_summary()` | `composite.py:150-192`, `:2724` | computed on every run, printed by nothing |
| `ReconcileSummary` (touched leaf paths + structural flag per tick) | `composite.py:3211-3220` | used for scheduling, then discarded |
| `PROCESS_BIGRAPH_PROFILE_PROCESSES` per-process timing | `composite.py:55`, `:1508` | env-flippable, undocumented |
| Nextflow `trace.csv` (per-task status + Batch `native_id`) | staged out by `_render_nf_command` (viva-api `simulation_service_ray.py:1585`) | never read |
| Nextflow weblog receiver + typed models | viva-api `common/hpc/nextflow_weblog.py` | wired only into the legacy SLURM path |
| `K8sJobService.get_pod_termination` (reason + exit code) | `common/hpc/k8s_job_service.py:116-146` | unused on the simulation path |
| Batch `exit_code` on `JobStatusInfo` | `simulation_service_ray.py:513-527`, `:4389` | computed, dropped by `update_hpcrun_status` |
| `HpcRun.correlation_id` (indexed) | `simulation/tables_orm.py:110` | joins worker events; becomes the trace id |
| chain Batch tags (`ExperimentId`, `Seed`, …) | `simulation_service_ray.py:3567-3579` | set, never queried back |
| `scripts/diagnose_sim.py` (NF log → per-task records, `.command.err` tails) | viva-api | client-side only |
| chain wrapper periodic out-dir sync (`CONTAINER_OUT_SYNC_INTERVAL`, 30 s) | sms-ecoli `docker/batch-container-entrypoint.sh:33` | free upload path for a file sink |

And the gaps they leave: no exception wrapping anywhere on the tick path (`process_update`
`composite.py:3039` invokes unguarded); the lineage runner is silent for a whole generation
(`lineage.py:901` is one blocking `run(interval)` of 3,600 s); no structured failure record
(`LineageStep.update` has no try/except); the scheduler never polls a Nextflow head (only a
user's `GET /status` does, mapping the K8s condition to FAILED with "backoff limit"); Nextflow
retries any non-zero exit three times (`nextflow_deploy.py:200-201`), each attempt invisible;
`.nextflow.log` is never uploaded on the v2ecoli path; no CloudWatch client; no events endpoint.

## Design

### D1. Event schema (one JSON object per line; the contract every layer shares)

```
{ "v":1, "ts":"2026-09-10T05:34:12.123Z", "seq":17, "layer":"engine|runner|dispatcher|api",
  "event":"tick", "level":"debug|info|warning|error",
  "trace_id":"<HpcRun.correlation_id>", "span_id":"…", "parent_span_id":"…",
  "sim_id":"946", "experiment_id":"…", "variant":0, "lineage_seed":3, "generation":2,
  "global_time":1734.0, "wall_time":812.4, "source":"<host-pid or task id>",
  "tags":{…opaque, dispatcher-added…}, "payload":{…} }
```

- **Identity block** is all-optional (`null` when unknown). No AWS/K8s identifiers in the core
  schema: Batch job ids, K8s job names, log streams, attempt numbers live in `tags`/`payload`,
  added by the dispatcher adapter or at ingestion.
- **Nested contexts, OpenTelemetry-style, no SDK**: `trace_id` = the campaign (viva-api's
  `correlation_id`); spans nest campaign → ParCa / lineage(variant, seed) / analysis →
  generation → (opt-in) process invoke. `run_start`/`run_end`, `generation_start`/`_end`,
  `task_start`/`_end` are the span boundaries (each carries `span_id`, `parent_span_id`,
  and `span_end` repeats `start_ts` so a consumer that missed the start can still place it).
  `trace_id` = first 32 hex of `sha256(correlation_id)` — deterministic, because
  `correlation_id` is `{sim_id}_{commit}_{random}` (`compose/hpc_utils.py:44`), not W3C hex;
  the ingester can recompute it from the existing column. Context propagates in full W3C
  form, `PBG_TRACEPARENT="00-<trace_id>-<parent_span_id>-01"`, plus `PBG_TRACE_BAGGAGE`
  (JSON: `sim_id`, `experiment_id`, `variant`, `lineage_seed`; all optional — the runner
  binds what only it knows). The task entrypoint opens the task span and re-exports the
  new `traceparent` into `os.environ` so subprocesses and Ray `runtime_env` inherit it. A
  laptop run with no traceparent mints its own `trace_id`. Ids are a `contextvars.ContextVar`
  copied into the parallel process layer. Cost: three short ids per event, two events per
  span. An OTLP exporter is a later sink; nothing in the engine changes for it.
- **Events by layer** (payload in brackets):
  - engine: `run_start` [interval, n_processes, n_steps, detail]; `tick` heartbeat,
    wall-clock throttled, default 30 s [ticks, process_time, framework_time,
    leaf_paths_touched, structural_changes since last]; `structural_change` [n_paths,
    sample_paths] (this is the division signal); `exception` [path, cls, address, is_step,
    interval, exc_type, exc_msg, state_summary]; `run_end` [status, total, process_time,
    framework_time, top5]; opt-in `process_timing`, `invoke`; `sink_error`;
    entrypoint `task_start`/`task_end` [exit_code, traceback_tail].
  - runner: `generation_start` [gen_seed, lineage_offset, emitter{kind,target,batch_size},
    carry report of the previous division]; `division` [signal structural|flag|exception,
    t_division, dry_mass, carried_roots, dropped_roots{non_carried, edges, unclassified}];
    `generation_end`; `checkpoint`; `chunk_flushed` [num_emits, file, seconds];
    `warning` (one per occurrence, next to each `warnings.warn`); `failure_record`.
  - dispatcher (written straight to the DB, never through the engine): `submitted`,
    `cache_staged`, `retry_observed`, `head_exit`, `task_outcome`, `reaped`.

### D2. Engine (process-bigraph PR, we author, eagmon reviews → release 1.9.0)

New module `process_bigraph/events.py`:
- `EventSink` (`emit/flush/close`); built-ins `StdoutSink`, `FileSink`, `MultiSink`,
  `NullSink` only. **Never imports boto3/kubernetes/redis/requests.**
- Registry + resolution: `PBG_EVENT_SINKS="stdout,file:/path,s3://bucket/prefix/"`;
  unknown schemes resolve via `register_sink_factory(scheme, fn)`, the entry-point group
  `process_bigraph.event_sinks`, or a `module:attr` spec. Unresolvable → one warning, dropped.
- `EventEmitter`: sinks, identity (from `PBG_EVENT_IDENTITY`/`PBG_TRACEPARENT`), lock-guarded
  `seq`, heartbeat throttle (`PBG_EVENT_HEARTBEAT_S`), detail flags (`PBG_EVENT_DETAIL=
  timing,invoke`), `bind(**identity)`, `span(name)` contextmanager, `event()`, `heartbeat()`,
  `exception()`. A sink that raises is disabled after one `sink_error`; **the sink can never
  raise into the simulation** (same wrapper as today's `_trace_invoke`).
- Defaults: library **off** (`NullSink`); the CLI entrypoints `run_composite.py`/`run_step.py`
  default to **stdout**, so a container gets events with zero configuration.
- Move `_summarize_value` here (re-export from `composite`), add `min/max/nan_count/neg_count`
  to the ndarray branch, add `summarize_state(state, max_roots=64)` (one level of root
  stores). Retire `PROCESS_BIGRAPH_TRACE_FILE`/`PROCESS_BIGRAPH_PROFILE_PROCESSES` as aliases.

Hooks in `process_bigraph/composite.py` (all data already in scope):
- **H3 `run` `:2618-2629`**: `run_start` before the contextvar set; `run_end` in the
  `finally` with `timing_summary()` fields and `status=error` when an exception propagates.
- **H1 `_run_inner` loop top `:2640`**: `heartbeat(global_time=…)` — one monotonic read per
  tick when idle.
- **H4 `apply_updates` `:3211-3220`**: fold `len(summary.paths)` into the heartbeat counters;
  emit `structural_change` when `summary.has_structural`.
- **H2 `process_update` `:3038-3041`**: `try/except BaseException` around `invoke` → emit
  `exception` with `'/'.join(path)`, `type(instance).__name__`, `process['address']`,
  `interval == -1.0` (Step), `global_time`, `summarize_state(clean_state)`; attach
  `exc.pbg_context = {...}` (+ `add_note` on 3.11+) and **bare `raise`** — v2ecoli's
  `is_division_exception` needs the original type. Replace the `_TRACE_FH` block with
  `if detail_invoke: emitter.invoke(...)`.
- **H5**: `_flush_protocol_runtimes` `:1548-1551` try/except → `exception`
  [runtime class], re-raise; `protocols/ray.py` `_RayBatchActor.batch_update` `:478-488`
  per-`proc_id` try/except re-raising `RuntimeError("batch_update failed for proc_id=… class=…")
  from exc`; `flush_pending` `:651` try/except → `exception` [shard_idx, proc_ids], re-raise;
  `enqueue` `:617` times `init_cell` → `process_init` (cold starts visible).

Entrypoints: `run_composite.py` (`:66` configure default stdout; wrap `composite.run` `:116`
→ `task_end`, write `failure.json` via `_write_json` `:57`, re-raise; optional `--summary-out`),
`run_step.py` same around `invoke` `:146`. Exit codes unchanged.

Nextflow template `nextflow_deploy.py`: `AWSBATCH_DEFAULTS` gains
`retry_exit_codes=[137,143,104,134,139]` (OOM/SIGKILL/SIGTERM/the nf-core set) and
`_awsbatch_profile` `:200-201` renders
`errorStrategy = { (task.exitStatus in <list>) && task.attempt <= task.maxRetries ? 'retry' : 'finish' }`
— a Python exception (exit 1) is never retried. `_resource_lines` `:42-58` accepts
`maxRetries`/`errorStrategy` per label. Optional `params.sim_tag` → `tag` directive so Batch
job names carry the sim id (verify on the pilot).

Tests (`process_bigraph/tests/test_events.py`, extend `tests.py:3144-3162`): off-by-default
emits nothing; run_start/run_end with identity; heartbeat throttle; exception event names the
path and re-raises the original type; a raising sink never breaks the sim; entry-point and
`module:attr` sink resolution; `run_composite` writes `failure.json` and exits non-zero;
Ray `batch_update` error names the proc_id; **instrumentation on/off yields identical state**
(the existing invariant test, extended). `test_nextflow_deploy.py`: retry only on the exit set,
per-label override, tag directive.

### D3. Runner (v2ecoli PR; pins `process-bigraph>=1.9.0`)

- `v2ecoli/workflow/events.py`: `get_emitter()` with a no-op fallback when the engine predates
  1.9 (so the pin can lag one image); `bind_generation(lp)`; `_ObservedEmitter` wrapper that
  delegates to the viva_emitters ParquetEmitter and emits `chunk_flushed` when
  `num_emits // batch_size` advances (viva_emitters is not ours; wrap from outside).
- `v2ecoli/workflow/event_sinks.py`: `S3JsonlSink(uri)` — buffered, a daemon timer rewrites
  `<uri>/<source>.jsonl` every `PBG_EVENT_FLUSH_S` (60 s) with `fsspec` (v2ecoli already
  depends on `s3fs`); `flush()` on `run_end`/`atexit`. Registered as the `s3` entry point.
  `source` = `AWS_BATCH_JOB_ID` if set else `host-pid` (the only AWS-aware line, and only for
  uniqueness). `LineageStep` also always adds `file:{out_dir}/events.jsonl` — on the chain path
  the wrapper's 30 s out-dir sync uploads it for free.
- **Heartbeat needs no slicing**: `self._composite.run(interval)` (`lineage.py:901`) enters the
  inner composite's `_run_inner`, so the engine heartbeat fires every 30 s wall with the right
  `global_time`; `_elapsed_after_run` and division detection stay untouched. (Slicing at `:901`
  is the fallback only if the engine pin cannot advance.)
- `_build_generation` (`:416-548`): `bind_generation` after `gen_seed` (`:424`); open the
  generation span; emit `generation_start` [gen_seed, `_lineage_offset`, emitter target,
  previous carry report]. Forward `time_step` (`_bio_kwargs` `:462-482` drops it; the inner
  composite reads `config.get('time_step', 1)` at `ecoli_baseline.py:910/931`) — call it out in
  the PR since it changes results for any campaign that set `time_step ≠ 1`.
- Carry report at the `select_carry_daughter` call in `_run_until_division` (after `:960`):
  `dropped = set(mother_snapshot) − set(carry) − {'_carried_listeners'}` partitioned into
  `non_carried` (`NON_CARRIED_ROOT_KEYS`), `edges` (`is_edge_node`), `unclassified` (→ level
  warning). Emit `division` [signal, t_division, dry_mass, report]; keep on
  `self._last_carry_report`.
- Replace the `print`s at `:997-1003`/`:1022-1103` with `generation_end`/`checkpoint` events
  (the stdout sink still shows them); add an event next to each of the 8 `warnings.warn` sites;
  emit `[lineage-debug]` as a `debug` event too.
- `LineageStep.update` (`lineage_step.py:275`): `configure(default='stdout')` + file sink; wrap
  `_run_lineage` in try/except → `failure_record` {exc_type, exc_msg, traceback_tail(40),
  `exc.pbg_context` (path, global_time, interval, state_summary), generation, wall_time} →
  `out_dir/failure.json` + event + `flush()` → re-raise.
- **Static classification test** `tests/test_root_store_classification.py` (`fast`): every
  single-element root port declared across `v2ecoli/steps`, `processes`, `composites` (the set
  enumerated tonight: request, allocate, central_fluxes, pinned_flux_targets, periplasm,
  imposed_flux_bounds, …) must be in `CORE_DIVISIBLE_KEYS ∪ NON_CARRIED_ROOT_KEYS ∪ registered
  dividers ∪ an explicit COPIED allow-list`; fails naming any unclassified root. A `slow` twin
  regenerates the set from a rendered `baseline()` agent document.
- Tests: `tests/test_workflow_lineage.py` (`_make` fixture `:5-46` + capsys: one
  `generation_start`/`generation_end` per generation, `gen_seed == _derive_generation_seed`);
  `tests/test_lineage_chain_seam.py` (`_FakeComposite`: `division` reports the three buckets);
  `tests/test_lineage_step.py` (failure record written and re-raised);
  `tests/test_lineage_checkpoint_observability.py` (checkpoint event); wrapper chunk test;
  `tests/test_lineage_time_offset.py` (`time_step` reaches the inner baseline).

### D4. Dispatcher, scheduler, API (viva-api; each piece behind a setting, each optional)

**(a) Identity + transport** — `Settings`: `events_enabled`, `events_s3_prefix` (default
`s3://{s3_work_bucket}/{s3_work_prefix}/{experiment_id}/events/`), `events_flush_seconds`,
`events_heartbeat_seconds`, `events_ingest_enabled`, `events_ingest_max_objects_per_tick`,
`cloudwatch_enrichment_enabled`, `cloudwatch_log_group_nf_tasks`, `cloudwatch_log_group_chain`.
`_awsbatch_nf_params` `container_env` (`simulation_service_ray.py:1440`), `_submit_container`
env (`:1030`), MNP `shared_env` (+ Ray `runtime_env.env_vars`) all get `PBG_EVENT_IDENTITY`,
`PBG_TRACEPARENT`, `PBG_EVENT_SINKS="stdout,s3://…/events/"`, `PBG_EVENT_FLUSH_S`,
`PBG_EVENT_HEARTBEAT_S`, `PBG_EVENT_TAGS` ({backend, seed, generation, …}); whitelist `PBG_*`
in the task-env validator. The dispatcher opens the campaign span (`span_id` stored on the row).

**(b) Storage + ingester** — `ORMHpcRunEvent` (`hpcrun_event`: hpcrun_id, source, seq, ts,
layer, event, level, generation, global_time, wall_time, span_id, parent_span_id, payload,
tags; unique `(hpcrun_id, source, seq)` for idempotent re-ingest). `ORMHpcRun` gains
`exit_code`, `attempt`, `events_s3_prefix`, `events_cursor` (JSONB `{key: bytes_read}`),
`stage`, `generation`, `last_event_at`, `error_source`, `trace_id` (indexed),
`campaign_span_id`; a materialised `hpcrun_span` table (`trace_id, span_id, parent_span_id,
name, attrs, start_ts, end_ts, status, error`) upserted from `span_start`/`span_end`, with
open spans closed as `status=unknown` when the row goes terminal; `stage` is derived as the
list of open span names (e.g. `["lineage[seed=3]", "generation[2]"]`), not free text.
`JobStatus`/`JobStatusDB` gain `PARTIAL`. One Alembic migration + one `LEGACY_FINGERPRINTS` marker (`db_reconcile.py`),
`ALTER TYPE … ADD VALUE IF NOT EXISTS`. `viva_api/simulation/event_ingest.py`: per active run,
list the prefix, Range-GET from the cursor, bulk-insert non-`tick` events (`ON CONFLICT DO
NOTHING`), fold `tick`/`generation_*` into `stage/generation/last_event_at`; capped per tick,
idle rows skipped. `JobScheduler._polling_loop` (`job_scheduler.py:143-167`) gains
`ingest_run_events()`.

**(c) Nextflow head poller + failure capture** (first PR; no upstream dependency) —
`list_active_nextflow_hpcruns()`; `JobScheduler.update_nextflow_heads()` mirrors
`update_multi_node_jobs`: on head terminal → `get_pod_termination` for exit/reason, read
`{results}/trace.csv` (new `common/hpc/nextflow_trace.py::parse_trace_csv`), status =
COMPLETED (all rows COMPLETED/CACHED) / PARTIAL (head 0, some FAILED) / FAILED (head ≠ 0 or no
rows); `error_message` precedence: latest `failure_record` → failed row's `.command.err`
tail (lift `diagnose_sim.py::_fetch_s3_text`) → CloudWatch (e) → K8s condition; persist
`exit_code`, `attempt`, `error_source`. `_render_nf_command` `:1560-1568` also uploads
`.nextflow.log` (mirror `simulation_service_k8s.py:274`); `_get_s3_nextflow_log` tries the
v2ecoli key; `_get_k8s_log` `:2002-2008` uses `get_simulation_service_for_job` (latent
TypeError). `update_hpcrun_status` (`database_service.py:1156`): replace the write-once
`if update.error_message:` with precedence by `error_source`. Chain `_finalize_campaign`
(`job_scheduler.py:740-787`) reports PARTIAL and the failed seeds' `failure_record`/status
reason instead of bare job ids.

**(d) API + CLI** — `GET /simulations/{id}/events` (filters `level, event, generation,
after_seq, limit≤1000`, `?tree=1` returns the span tree), `GET /simulations/{id}/tasks`
(trace rows for NF; chain job ids via `get_batch_job_statuses` `:4393`), richer `/status`
(`stage, generation, last_event_at, attempt, exit_code, error_source`; additive). `make spec`
+ `make api_client` with `SIMULATION_OUTDIR`/`HPC_SIM_BASE_PATH` overridden. CLI (`app/cli.py`
after `:1726`): `atlantis simulation events <id> [--follow] [--level] [--generation] [--tree]`,
`simulation tasks <id>`, `simulation status` shows stage / generation / last heartbeat /
attempt / exit code; the poll loop's terminal set gains `partial`.

**(e) CloudWatch enrichment** (optional, last, off by default) —
`common/hpc/cloudwatch_logs.py::tail_log_stream(group, stream, n)`; stream from
`describe_jobs` `container.logStreamName`; log groups from settings, never prose.

## Validation before any merge: a hash-pinned branch chain (Jim, 05:47Z)

Nothing here needs an upstream release to be tested end to end. v2ecoli already pins
process-bigraph by git rev (`pyproject.toml:191`, `rev = "78d14883…"`) and sms-ecoli pins
v2ecoli by rev (`:258`); simulator images build from a branch with `uv sync --locked`. That is
exactly how simulators 192/193 were built tonight. So:

```
process-bigraph  feat/events        (sha P)
v2ecoli          feat/events        pins process-bigraph @ P     (sha V)
sms-ecoli        feat/events        pins v2ecoli @ V             (sha S)  → simulator image "instrumented"
sms-ecoli        main (or 193's c233c7a)                                  → simulator image "control"
```

Same seed, same config, same chassis on both images; the control run proves the invariance
("instrumentation does not change results") on the real model, and the instrumented run
proves the events, `/status`, `/events`, and the failure path — all before Eran reviews a line.
The three branches ride the same review order afterwards (PR-B → PR-C → sms-ecoli pin), and
the pins move from branch hashes to the merge commits.

## Rollout order (value at every step; parallel where independent)

1. **viva-api PR-A** — head poller, `trace.csv`, `.nextflow.log` upload, `exit_code`,
   PARTIAL, error precedence, `_get_k8s_log` fix, identity env vars, the migration. No
   upstream dependency. Immediate effect: a Nextflow run flips to FAILED/PARTIAL with the first
   `.command.err` traceback within one scheduler tick of head exit; 749's and 943's cases
   become legible from `atlantis simulation status`.
2. **process-bigraph PR-B** — `events.py`, hooks H1–H5, entrypoints, retry template. Release
   1.9.0. Parallel with A.
3. **v2ecoli PR-C** — events wrapper, S3 sink plugin, generation/division/failure events,
   `time_step`, classification test. Developed against a git pin of B; merges once 1.9.0 is on
   PyPI. Then one sms-ecoli pin + one simulator image (`_ensure_container_job_def` copies the
   base job def, so no CDK change).
4. **viva-api PR-D** — events table ingester, `/events`, `/tasks`, richer `/status`, CLI.
   Parallel with B/C; tolerates an empty prefix until the new image runs.
5. **viva-api PR-E** — CloudWatch enrichment. Optional.

## Verification

- Unit: D2/D3 tests above; viva-api `tests/simulation/test_scheduler.py::TestUpdateNextflowHeads`
  (mirror `TestUpdateMultiNodeJobs:886` incl. the disjointness test `:987` and the loop-order
  test `:1358`), `tests/common/hpc/test_nextflow_trace.py` (all-completed / one-failed / cached
  / reclaimed fixtures), `tests/simulation/test_event_ingest.py` (cursor, idempotence,
  heartbeat folding), handler tests for `/events`, `/tasks`, `/status`, `_get_k8s_log` routing,
  `tests/simulation/test_nextflow_dispatch_axis.py` (identity env, log upload, exit-code retry
  list), a CLI test for `simulation events`.
- Integration on `smsvpctest`, reference shape = sims **946** (Nextflow) and **947** (chain),
  both COMPLETED 5 generations on #769 tonight: a 1×2 Nextflow pilot and a 1×2 chain pilot on
  the bare `6299ba5/` chassis with the new image. Expected per generation in
  `atlantis simulation events --tree`: `generation_start` (with `gen_seed`,
  `dropped_roots.unclassified == []`), ~`wall/30` ticks, `chunk_flushed ≈ ⌈emits/400⌉`, one
  `structural_change` + one `division`, `generation_end`, `checkpoint`; per task one
  `task_start`/`task_end`; `/status` shows `stage=running, generation=N, last_event_at` within
  60 s of real time; `/tasks` lists 1 ParCa + 2 lineage rows.
- Deliberate failure: inject a process that raises `ValueError("boom")` at `global_time ≥ 100`
  in generation 1. Expect one `exception` event with the process path, `generation=1`,
  `global_time=100`, a state summary; one `failure_record`; exactly one Batch attempt (exit 1
  not in the retry set); status FAILED with `error_message` ending `ValueError: boom` and
  `error_source=failure_record`.
- Invariance: same seed and config with sinks off vs `stdout,file,s3` + `detail=timing,invoke`;
  history parquet series (`dry_mass`, per-emit bulk sums) byte-identical; `run_end.total`
  overhead < 2 %.
- Laptop: `PBG_EVENT_SINKS=file:./events.jsonl vwb run-study …` produces the same event stream
  with no AWS configuration.

## Risks and open questions

- **Spot reclaim visibility**: Batch retries reclaim internally (`maxSpotAttempts`), so
  Nextflow's `errorStrategy` only sees the exhausted case; its exit status may be absent. Read
  one reclaimed task's `trace.csv` `exit` on the pilot before widening `retry_exit_codes`.
- **Volume/cost**: heartbeat 30 s + seam events ≈ 150 lines/hour/task on CloudWatch; `invoke`
  detail stays opt-in; `tick` is never stored in the DB.
- **S3 flush at 1,000 lineages**: whole-object rewrite every 60 s ≈ 17 PUT/s campaign-wide;
  cursor-based ingest capped per tick; idle rows skipped.
- **Threads**: emitter and `seq` under a lock (parallel process layers, the emitter's thread
  pool); the S3 sink's timer thread daemonised and flushed at exit.
- **viva_emitters boundary**: wrapped from outside only; a stalled parquet write still surfaces
  at the next `.result()`, now bracketed by heartbeats.
- **Exception type preservation**: bare re-raise is mandatory (division detection); `add_note`
  needs Python ≥ 3.11, else the attribute only.
- **Ray identity**: `_stable_proc_id = id(shadow)` carries no path; H5 names class + shard until
  the runtime records the path at enqueue. MNP actors need `PBG_*` through `runtime_env`.
- **Engine default off vs stdout**: a judgement call Eran may reverse; one line in `configure()`.
- **Alembic**: one migration, one fingerprint marker; PARTIAL must be accepted by CLI/TUI/GUI and
  the workbench's terminal-status buckets (`remote_run_views.py:43-44`) — flag to Alex.
- **`time_step` forwarding** changes results for any campaign that set it ≠ 1; called out in
  the PR, not silently fixed.
