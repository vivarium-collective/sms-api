# Ptools Latency / Blocking-Call Mitigation Report

**Status:** Design exploration — no code changes yet.
**Author:** Atlantis API team
**Date:** 2026-05-29
**Stakeholder:** Pathway Tools (ptools) frontend developer (SRI)
**Scope:** `POST /api/v1/analyses` on the `sms-api-rke` namespace.

---

## 1. Problem statement

The ptools frontend issues a single HTTP call to the SMS API and expects it
to block until ptools analysis output is ready, then return the TSVs in the
HTTP response body. The reason this call is "blocking" today is that the
analysis is computed by a fresh SLURM submission — there is *no* way to short-
circuit it, because the only knob the frontend cares about — `n_tp` (number
of timepoints / columns in each TSV) — is currently propagated into the
analysis module config, which causes vEcoli to produce a different TSV per
value. Re-parameterizing `n_tp` therefore triggers a re-run of the analysis
module.

The current request path is:

```
ptools-frontend (browser)
   │  HTTPS, single request, must remain open for the entire duration
   ▼
[Internet]
   │
   ▼
RKE ingress (nginx) ── idle-timeout, connection budget
   │
   ▼
api pod (FastAPI, `handle_run_analysis_slurm`)  sms_api/common/handlers/analyses.py:55
   │  open asyncssh session
   ▼
HPC submit host (vivarium / vcell-services)
   │  sbatch submit + sacct poll loop (3-second cadence)
   ▼
SLURM scheduler → compute node (singularity container) → vEcoli analysis.py
   │
   ▼  (job completes)
api pod scp_download from HPC → local cache → assemble Sequence[TsvOutputFile]
   │
   ▼
HTTPS response (potentially many MB of TSV bytes)
```

Every hop in that chain adds a chance of failure for a long-lived single
request:

| Hop | Failure mode | Observed in this project |
|-----|--------------|--------------------------|
| Client → ingress | TLS keepalive / idle timeout, 504 from ingress | yes (see `incident_v093_compose_broken`, ptools 504 from stakeholder) |
| Ingress → api pod | nginx upstream timeout, pod eviction | yes (Pitfall 5 in CLAUDE.md) |
| api pod ↔ HPC SSH | asyncssh disconnect on idle, `vcell` partition queueing latency | yes (`incident_slurm_queue_2026_05_11`) |
| SLURM queue | job may wait minutes-to-hours behind other jobs | structural |
| Compute node | vEcoli analysis runtime variance (DuckDB scan + matplotlib) | structural |
| Response body | multi-MB TSVs over a single sync HTTP body | bandwidth-bound |

So the stakeholder's ask — *one synchronous HTTP call, no polling* — is
asking the system to keep an end-to-end TCP path alive across all of the
above for the wall-clock duration of a SLURM job. That is not a workload
HTTP was designed for, and it is the root cause of the friction. The
mitigation strategies below address the problem from different angles.

---

## 2. Root-cause framing

There are two **independent** sources of latency that get conflated:

1. **Scheduling latency** — time between "request received" and "the
   analysis process is running". Driven by SLURM queue depth, image cache,
   SSH session setup, parca data availability. **Bounded by infrastructure
   we don't fully control.**
2. **Compute latency** — time the analysis itself takes to read sim history
   and emit a TSV. For ptools modules (`ptools_rxns`, `ptools_rna`,
   `ptools_proteins`) this is small to moderate (DuckDB query over partition
   parquet + downsample to `n_tp` columns).

The frontend's mental model is "I want compute latency only." Every mitigation
below is some combination of:

- **Avoid scheduling latency** (run the analysis somewhere other than fresh
  SLURM jobs).
- **Make re-parameterization free** (decouple `n_tp` from "do I need to
  re-run the analysis at all").
- **Keep the HTTP connection alive credibly** (heartbeats / chunked
  responses / SSE) so a long blocking call doesn't get killed at any hop.

The *most leveraged* lever, by far, is #2 — because `n_tp` is **purely a
downsampling parameter on the time axis**. There is nothing about
re-parameterizing it that requires new simulation data or a new SLURM job.

---

## 3. Mitigation paths

Each option below is presented standalone. Options can be combined
(recommendation: a layered strategy with **Path B as the primary fix** is
covered in §4).

---

### Path A — Pre-compute a fixed matrix of `n_tp` at simulation time *(the option you proposed)*

**What it is:** When the parent simulation completes, automatically run each
ptools analysis module across a small, **fixed** menu of `n_tp` values —
e.g. `{4, 8, 16, 32, 64, 128}` — and persist all of those TSVs to the file
store. The ptools frontend gets a dropdown populated from a manifest
endpoint and can only pick from that menu.

**Where it plugs in:**
- Extend the simulation completion hook (or analysis post-step in the
  workflow) to fan out N ptools jobs, one per `n_tp`.
- Persist outputs under a deterministic key:
  `<experiment_id>/analyses/ptools/<module>/n_tp=<k>.tsv`.
- New endpoint: `GET /api/v1/analyses/{experiment_id}/manifest` →
  `{module: [n_tp_values…]}` so the frontend knows what's available.
- Existing `POST /analyses` becomes a fast lookup: read TSV from cache /
  object store, return immediately.

**Pros:**
- Zero SLURM latency on the request path; response is bounded by file read
  + network upload.
- The blocking call the frontend wants is now **legitimately fast**, so
  it's safe to ship as-is.
- Storage cost is modest: a `ptools_rna.tsv` at n_tp=128 is small (KB to
  low MB).

**Cons:**
- **Restricts the UX** — the frontend can no longer pick arbitrary `n_tp`.
  You're trading expressiveness for reliability. The stakeholder explicitly
  asked for full re-parameterization, so this is a partial concession.
- Doubles the work the simulation workflow performs at completion (N×
  ptools jobs instead of 1).
- If we later want to add `time_unit` or any other knob, the matrix
  explodes.

**Verdict:** Acceptable as a *fallback* if Path B (below) can't be done
quickly, but it's strictly weaker than Path B because Path B yields the
same UX with continuous-valued `n_tp` for free.

---

### Path B — Decouple `n_tp` from the SLURM run; re-aggregate at read time *(strongest single fix, with caveats)*

> **2026-05-29 correction — vEcoli investigation result.** Path B's
> original premise ("downsample by picking `n_tp` columns out of a
> higher-resolution TSV") was wrong. Verified by reading
> `~/sms/vecoli_fork/ecoli/analysis/single/ptools_{rxns,rna,proteins}.py`
> (`api-support` branch) and `~/sms/vEcoli/.../ptools_*.py`
> (`ptools_viz` branch):
>
> - In `api-support`, `n_tp` controls a DuckDB time-window aggregation:
>   `[min_t, max_t]` is split into `n_tp` uniform bins and each output
>   column is the **AVG** of the underlying values whose `time` falls
>   in that bin. Output column labels are bin-start times.
> - In `ptools_viz`, `n_tp` controls a row-index `np.linspace`
>   partition; each output column is a **SUM** (or normalized mean) of
>   the rows in that block, prepended with the initial state.
>
> **Implication:** "Run vEcoli with `n_tp=8`" and "run vEcoli with
> `n_tp=128` then pick 8 columns" do **not** produce the same numbers —
> the underlying bin contents differ. Path B is still viable but must
> be re-aggregation (sum-of-sums / weighted-mean-of-means), not
> column-picking, and exact equivalence is only achievable under
> specific divisor + row-uniformity conditions. See "Corrected Path B"
> below.

**Corrected Path B (re-aggregation, two sub-variants):**

**B1 — Cache canonical TSV at `n_tp_max`; re-aggregate to divisors at
read time.**
Run SLURM at a fixed `n_tp_max` (e.g. 120 — many divisors:
`{1,2,3,4,5,6,8,10,12,15,20,24,30,40,60,120}`). Cache the TSV. At read
time, if the requested `n_tp` divides `n_tp_max`, group adjacent columns
and take their mean (api-support semantic) or sum (ptools_viz semantic).
- Approximate equivalence — exact only if row counts per fine bin are
  uniform. Sim time *is* uniform in vEcoli, so this is "close enough"
  in practice but not bit-identical.
- UX: continuous-feeling dropdown of divisors. Reject `n_tp` values
  that don't divide `n_tp_max` (or snap to the nearest divisor +
  document the snap).

**B2 — Cache the *pre-aggregation* artifact; run vEcoli's
`build_query` SQL (or `consolidate_timepoints` numpy) at read time
inside the api pod.**
- Modify the ptools modules (vEcoli-side PR) to *also* emit the raw
  pre-aggregation data — either a parquet slice of the relevant
  columns + `time` (api-support), or the `state_mtx` numpy array
  (ptools_viz). Cache that.
- API pod runs DuckDB (api-support) or numpy `consolidate_timepoints`
  (ptools_viz) at request time with the requested `n_tp`.
- **Bit-identical** to running vEcoli with that `n_tp`, because we are
  literally running the same code on the same input.
- Requires a vEcoli-side change. Compatible with Path C (running the
  whole analysis in-tree).

**What it is (B1, no vEcoli changes):**
1. Run each ptools analysis **once per experiment**, at a fixed
   `n_tp_max` (recommend `n_tp_max=120`). Cache that TSV by
   `(experiment_id, module, simulator_hash, filters)` — **n_tp NOT in
   the cache key**.
2. The `POST /api/v1/analyses` endpoint becomes:
   - Cache hit + `requested_n_tp == n_tp_max` → return TSV as-is.
   - Cache hit + `requested_n_tp` divides `n_tp_max` → load TSV,
     group `n_tp_max / requested_n_tp` adjacent columns, take mean
     (or sum, depending on module semantic), return.
   - Cache hit + `requested_n_tp` does not divide → snap to the
     nearest divisor and document, or 400.
   - Cache miss → submit SLURM at `n_tp_max`, cache result, then
     re-aggregate as above. *Slow only on first request per
     `(experiment_id, filters)`.*

**Where it plugs in (B1):**
- `sms_api/analysis/analysis_service.py` — add a
  `_reaggregate_columns(df, source_n_tp, target_n_tp, mode="mean")`
  helper that group-aggregates contiguous time columns. Mode is
  per-module (mean for api-support, sum for the ptools_viz rna
  variant).
- `sms_api/common/handlers/analyses.py` — change `RequestPayload`
  hashing so it strips `n_tp` from every `PtoolsAnalysisConfig` before
  hashing (cache key independent of `n_tp`). Keep `n_tp` in the
  request for the re-aggregation step at response time.
- `sms_api/analysis/analysis_service.py` — `complete_config_template`
  must always submit SLURM with the canonical `n_tp_max`, ignoring
  what the request asked for.

**Pros:**
- **Frontend gets exactly the UX it asked for** — continuous `n_tp`, fast
  blocking response — for every request *after* the first per
  `(experiment_id, filters)`.
- No matrix explosion (Path A's issue); adding `n_tp` values is free.
- Eliminates 99% of SLURM dispatches from the ptools workflow.
- Compatible with Path C — the canonical compute can run inside the api
  pod instead of on SLURM if we want to go further.
- Backwards compatible: the request schema doesn't have to change.

**Cons (B1):**
- **Approximate, not bit-identical** to running vEcoli at the requested
  `n_tp` — see correction box above. In practice, divergence is small
  (rows per fine bin are nearly uniform), but it is observable. If the
  stakeholder needs exact reproduction of vEcoli output, use B2.
- UX restricted to divisors of `n_tp_max` (with `n_tp_max=120`, that's
  16 supported values; if the request is e.g. `n_tp=7`, we either 400
  it or snap to a divisor and document).
- First request for a brand-new experiment is still slow. (Path D
  mitigates this by warming the cache at simulation-completion time;
  Path B + Path D = canonical artifact materialized eagerly,
  re-aggregated on read.)
- Cache invalidation: if vEcoli ptools logic changes, the canonical
  TSV becomes stale. Embed simulator git hash in the cache key (we
  already thread `simulator_hash` through `dispatch_analysis`).

**B2 trade-offs:**
- Bit-identical results, continuous `n_tp` — no divisor constraint.
- Requires an upstream vEcoli PR (one extra emission step inside the
  ptools `plot()` functions) and we ship behind a simulator version
  bump.
- The api pod gains a DuckDB dependency (likely already present
  transitively via vEcoli imports) and needs read access to the
  cached parquet.

**Important Note:**
For reference on the exact inner workings of the vEcoli ptools analyses, please use
~/sms/vecoli_fork on the "api-support" branch.

**Verdict:** **Recommended primary fix.** It directly addresses why the
re-runs were happening in the first place, without restricting the
frontend's UX.

---

### Path C — Eliminate SLURM from the ptools request path entirely

**What it is:** Stand up a long-lived ptools analysis worker (a Python
process inside the api pod, or a sidecar container, or its own deployment)
that already has read access to simulation history files. The api handler
calls into this worker directly — no SSH, no sbatch, no queue.

Two flavors:

**C1 — In-process module.** Import vEcoli's ptools analysis modules into
the api pod. They are largely DuckDB + pandas; the heavy lifting is
already a `SELECT FROM parquet`. No singularity, no SLURM.

**C2 — Dedicated worker pod.** Same code, but in its own pod, talking to
the api over an internal queue (Redis already in the stack — see
`sms_api/common/messaging/`). The worker preloads recently-touched
experiments' DuckDB connections.

**Where it plugs in:**
- Sim history files: needs to be readable from the api pod. Today the api
  pod reads from HPC via SSH because outputs live on the SLURM filesystem.
  This requires either:
  - Mounting the Qumulo S3 bucket where simulation outputs land
    (already exists for K8s deployments — see `FileService` in
    `sms_api/common/storage/`).
  - Or copying outputs to a shared store at simulation-completion time.
- API handler: replace `analysis_service.dispatch_analysis` with a direct
  function call.

**Pros:**
- **True synchronous response in single-digit-second territory** for every
  request, not just cache hits. The only latency is DuckDB scan + render.
- Frontend's API contract doesn't change.
- Eliminates the SLURM queue as a bottleneck and the SSH session as a
  failure mode.

**Cons:**
- Significant engineering work: bring ptools analysis code in-tree, manage
  its dependencies, ensure vEcoli upstream changes don't drift.
- The api pod becomes responsible for CPU and memory previously isolated
  on compute nodes. ptools_rna at high n_tp on a multi-generation run can
  be a couple of GB of pandas. Sizing matters.
- Requires the sim history Parquet to be reachable from the api pod, which
  is true today on Stanford (S3) but **not** on `sms-api-rke` (HPC
  filesystem only). Either we copy completed sim outputs to S3 on RKE too,
  or we mount the HPC filesystem into the api pod (complex).

**Verdict:** Best long-term answer, but a much bigger lift than Path B.
Recommend as the second wave once Path B is in production.

---

### Path D — Materialize the canonical artifact eagerly as part of the simulation workflow

**What it is:** Don't wait for the frontend's first `POST /analyses` to
trigger the canonical SLURM job (Path B). Instead, run it automatically as
the last step of every simulation workflow, so the cache is **already
populated** the first time any frontend asks for it.

This is essentially Path A, but with a *single* high-resolution artifact
per `(experiment_id, module)` instead of one per `n_tp` value. Combined
with Path B's read-time downsampling, the frontend gets continuous `n_tp`
**with no first-request slowdown**.

**Where it plugs in:**
- `sms_api/simulation/job_scheduler.py` — add a final stage after the
  simulation completes that submits a ptools analysis job per module at
  canonical resolution.
- The frontend never has to trigger compute. The `POST /analyses` endpoint
  becomes read-only from the api's perspective.

**Pros:**
- Eliminates the only remaining slow case from Path B (cold cache).
- Predictable cost: one extra short SLURM job per ptools module per
  simulation, run by us at workflow time, not by the user at request time.
- Lets us move ptools out of the user-facing critical path entirely.

**Cons:**
- Wastes compute for simulations the frontend never inspects.
- Couples the simulation pipeline to a downstream concern (ptools-specific
  analyses). Need to gate it ("only for simulations the user opts into" or
  "only for the public simulator versions ptools targets").

**Verdict:** A natural extension of Path B; ship Path B first, layer Path
D on once the canonical artifact format has stabilized.

---

### Path E — Honest async: 202 + status URL + cache-by-hash (no polling, server pushes via SSE)

**What it is:** Don't pretend the call is synchronous. Have
`POST /api/v1/analyses` return immediately with `202 Accepted` + a
`Location: /api/v1/analyses/{job_id}/events` SSE endpoint. The frontend
opens that SSE stream and receives:

```
event: status
data: {"phase": "queued"}

event: status
data: {"phase": "running", "progress": 0.3}

event: result
data: <json with signed download URL>

event: end
```

From the frontend's perspective, this is *almost* what they want — a
single connection that delivers the result without manual polling. The
SSE protocol is a single GET with chunked response; heartbeats every few
seconds keep it alive through every proxy/idle-timeout in the chain.

**Where it plugs in:**
- New SSE endpoint in `sms_api/api/routers/sms.py`.
- Reuse existing job polling logic (`AnalysisServiceSlurm.poll_status`),
  but emit events to a per-job Redis pub/sub channel instead of just
  awaiting.
- Final `result` event carries a signed URL to the TSV in object store —
  the frontend issues a normal GET to fetch the actual data, so the
  response body never has to flow through the SSE stream.

**Pros:**
- The frontend writes "one call, no polling" code (an `EventSource` in JS
  is one line). Their stated requirement is *behaviorally* satisfied.
- Heartbeats eliminate idle-timeout failures across all hops.
- Decoupled compute means we can scale and retry without the frontend
  caring.

**Cons:**
- **The stakeholder explicitly said they don't want anything other than
  one blocking call.** SSE is technically not polling, but it is a
  different code path on their side. Need a conversation.
- Doesn't help with the underlying compute latency, only with the
  *connection management* of the long wait.

**Verdict:** Defensible fallback if the stakeholder is willing to accept
"one open connection, server-pushed result." It is the standard
industry answer to "I want a blocking call across an unreliable
roundtrip." Path B is still better because it removes the wait entirely.

---

### Path F — Heartbeat the existing blocking call (chunked transfer with whitespace pings)

**What it is:** Keep the existing `POST /analyses` synchronous from the
frontend's point of view, but have the api pod write a single space
character (or a comment line in NDJSON) to the response body every few
seconds while the SLURM job is running. Most proxies, ingresses, and
ALB conntracks treat any byte on the wire as activity, so the connection
won't be killed.

**Where it plugs in:**
- FastAPI: switch the handler to `StreamingResponse` and yield bytes from
  an async generator.
- Yield a heartbeat (`b" "` or a structured `{"hb": true}\n`) every
  ~5 seconds; yield the final JSON-encoded result body at the end.

**Pros:**
- Minimal code change. No new endpoints. No frontend contract changes
  beyond "tolerate leading whitespace in the response body."
- Defeats idle-timeout / conntrack staleness across every hop in §1.
- Buys time until Path B / D ship.

**Cons:**
- Doesn't reduce wait time; the frontend's UI still hangs for the same
  duration.
- Some HTTP clients buffer the entire response before exposing it; need
  to confirm the frontend's HTTP layer streams.
- The total wall-clock blocking time is bounded by browser limits
  (Chrome/Firefox are generous, but corporate proxies vary).

**Verdict:** A duct-tape mitigation, valuable as a *day-1* shipped fix
while the real work (Path B) is in flight.

---

### Path G — Pre-signed object-store URLs + direct frontend download

**What it is:** Once the analysis has produced a TSV (in either the cache
or the canonical-artifact store), the api returns a pre-signed URL to
object storage (S3/GCS/Qumulo). The frontend downloads directly from the
object store, bypassing the api pod's bandwidth.

**Where it plugs in:**
- Add a TSV-to-S3 mirror to the cache write path.
- `TsvOutputFile` model gets an optional `download_url` field; populated
  when the file has been uploaded.
- Frontend opts into "give me URLs, not bytes" with a query param.

**Pros:**
- Removes the api pod from the *bandwidth* critical path — only relevant
  if response sizes get large, which they currently don't for ptools.
- Plays nicely with Path B and Path D (the canonical artifact lives in S3
  as a natural side-effect).
- Mitigates Pitfall 4 (ALB target group flake on sustained traffic).

**Cons:**
- Two-step download adds frontend complexity (and a CORS conversation).
- Object store needs to be reachable from the frontend's network. RKE
  ingress already brokers this for static content; new policy needed for
  pre-signed S3 URLs.

**Verdict:** Optional, helpful at scale; not the bottleneck today.

---

### Path H — Persistent SLURM "ptools service" job

**What it is:** Submit one *long-running* SLURM job (e.g. 7 days
allocation) on the HPC that hosts a small HTTP server inside a Singularity
container. The api pod tunnels analysis requests to it via SSH port-
forward. Re-parameterization is cheap because the worker is already warm
and has the sim data on-disk.

**Where it plugs in:**
- Submit a `srun --pty`-style long job that runs a flask/uvicorn worker.
- api pod opens an SSH tunnel on startup and proxies analysis requests
  over it.

**Pros:**
- Eliminates SLURM queueing latency for ptools.
- Keeps the analysis on the HPC filesystem (no need to mirror data to S3
  for Path C).
- Lower engineering cost than Path C.

**Cons:**
- The HPC partition policy (vcell-services QoS, see
  `project_slurm_config_change_2026_05_15`) may not love a 7-day pinning
  job. Need an ops conversation with CCAM.
- A worker death means a multi-minute restart from sbatch; need
  supervision.
- Not portable to the Stanford deployment (different compute backend).

**Verdict:** Worth pricing if Path C is judged too expensive. Behaviorally
identical to Path C from the frontend's perspective.

---

## 4. Recommended phased plan

### Phase 1 — Stop the bleeding (1–2 days, ship today)
- **Path F (heartbeat the existing blocking call).** Switch `run_analysis`
  to `StreamingResponse` with whitespace heartbeats. Eliminates idle-
  timeout failures across the ingress / HPC-SSH / ALB chain without
  changing the API contract.
- Communicate the change to the stakeholder: "no client change required;
  fewer 504s."

### Phase 2 — The real fix (1–2 weeks)
- **Path B (decouple `n_tp` from the SLURM run; downsample at read time).**
  - Verify vEcoli ptools `n_tp` semantics — confirm uniform time-axis
    downsampling.
  - Add `_downsample_columns(df, n_tp)` to `AnalysisServiceSlurm`.
  - Strip `n_tp` from the `RequestPayload.hash()` cache key in
    `sms_api/analysis/analysis_service.py:44`.
  - Submit SLURM with a canonical `n_tp` (max of supported menu).
  - All subsequent same-experiment, same-filter requests are
    sub-second.
- **Path D (eagerly materialize canonical artifact at simulation
  completion).** Layered on top of Path B; removes the only remaining
  slow case (cold cache for first frontend request).

### Phase 3 — Defense in depth (optional, weeks-to-months)
- **Path C (eliminate SLURM from the request path).** Once Phase 2 is
  stable and we've decided ptools is a permanent product surface, port
  the analysis modules in-tree and run them inside the api pod
  (or a worker pod). Requires sim history to be readable from the api
  pod on RKE — either S3 mirroring or HPC mount.
- **Path G (pre-signed URLs).** Only if response sizes start hurting api
  pod bandwidth.

### What about the stakeholder's "one blocking call" demand?
- Phase 1 makes the existing blocking call **reliable** (heartbeats).
- Phase 2 makes the existing blocking call **fast** (cached canonical
  artifact + read-time downsample).
- The combination delivers exactly what they asked for, with no protocol
  change on their side. **They never have to know we changed anything
  internally.** The dropdown restriction from Path A is avoided entirely.

If after Phase 1+2 they still hit specific failure modes, Path E (SSE) is
the proper standards-compliant escape hatch and is worth a separate
conversation at that point.

---

## 5. Risks and open questions

1. **Does vEcoli's ptools analysis actually downsample uniformly over
   the time axis?** Path B's correctness depends on this. Investigation
   needed in `vEcoli/ecoli/analysis/ptools_{rxns,rna,proteins}.py`. If
   the answer is "it picks division-aligned timepoints" or any other
   semantic operation, Path B would silently change result semantics and
   we'd need to fall back to Path A or D for the cases where it matters.
2. **Is the canonical resolution (`n_tp`) a configurable max, or unbounded
   raw history?** If we go with raw history, file size grows linearly
   with sim length × generations × seeds. For the largest sims (1000
   seeds × 10 generations, see `project_large_scale_sim`) this matters.
3. **Cache invalidation:** key must include `(experiment_id,
   simulator_git_hash, generation_range, lineage_seed)` — everything
   *except* `n_tp`. Already mostly true; just need to drop `n_tp` from the
   hashed payload.
4. **vEcoli multigeneration filter bug** (documented in
   `project_ptools_filtering`): aggregated analyses ignore
   `generation_range`. Path B doesn't fix this — orthogonal issue, file
   upstream as planned.
5. **Storage budget for Path D.** Eagerly materializing per simulation
   means O(experiments × modules) artifacts. Small per artifact, but
   verify Qumulo / GCS budget if we have thousands of experiments.
6. **Stakeholder conversation.** Path A vs. Path B yields the same final
   UX from the stakeholder's perspective (continuous `n_tp`, fast
   responses), but Path A requires us to tell them "you can only pick
   from this dropdown." If Path B's investigation (item 1) reveals a
   blocker, we'll need that conversation. Better to do the investigation
   *first* before committing to Path A's UX restriction.

---

## 6. Appendix — Why the current design ended up here

For context, the current `POST /analyses` blocking-then-polling flow is in
`sms_api/common/handlers/analyses.py:55–124`:

```python
async with get_ssh_session_service(SSHTarget.SLURM).session() as ssh:
    jobname, jobid, config = await analysis_service.dispatch_analysis(...)
    dto = await db_service.insert_analysis(...)
    _run = await analysis_service.poll_status(dto=dto, ssh=ssh)  # ← blocks
# ...then downloads files and returns
```

The cache check immediately above it (`analysis_request_cache.exists()`)
hashes the entire request body, **including `n_tp`**:
```python
payload_hash = RequestPayload(data=request.model_dump()).hash()
```
which is precisely why bumping `n_tp` re-triggers compute even though the
underlying simulation data is identical. Path B fixes exactly this — the
single most leveraged line in the codebase for this problem.

The reason it was built this way originally is that the API treats vEcoli
analysis modules as opaque — whatever the frontend asks for, we forward to
vEcoli and let it decide what `n_tp` means. That was the right call when
analyses had varied per-module semantics. Now that we've learned `n_tp` is
universally "time axis downsample count" for the ptools modules, we can
specialize the path for those modules and reap the win.
