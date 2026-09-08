# Nextflow dispatch, act 2: closing gate 4 and the shortcomings behind it

**Status (2026-09-08): gate 4 is still open. Five blockers have been found and
cleared in sequence; the fifth is fixed locally and not yet merged.** Everything
else here is inventory — every known shortcoming of the Nextflow dispatch path,
with what is measured, what is assumed, and who owns it.

> Companion to [`plan-nextflow-dispatch.md`](plan-nextflow-dispatch.md) ("act 1"),
> which carries the design and the go/no-go gate table. This document is the
> **execution** half: what is broken, in what order it gets fixed, and how far it
> has got. Act 1 stays the reference for *why the path is shaped this way*.
>
> Same house style as act 1: **status first, reasoning preserved with corrections
> inline** rather than rewritten in hindsight. Where I got something wrong, the
> wrong version stays visible with the correction attached — the mistakes have
> been the most useful part of this record.

---

## Where this stands

The path **works on real CD2 payloads**. On 2026-09-07 the Run 2 J3 probe
(simulator 160, simulation 511) succeeded on GovCloud:

- 85 minutes, `returncode 0`
- **100 objects / 1,147,657,136 bytes** published, under `variant=0` and `variant=1`
- **zero `v2ecoli-parca` invocations** — it fetched @cplong90's staged per-seed
  founder caches instead of rebuilding
- two genuinely different founder cells (`initial_state.json` 9,705,522 vs
  9,537,718 bytes)

That was the first exercise of `cache_uri` (v2ecoli#732) and multi-variant
rendering (v2ecoli#723), and the first campaign whose seeds are not copies of one
founder.

**The history is real data, not a false positive.** Re-checked against viva-api#475's
new criterion: 47.6 MB and 48.8 MB parquet chunks (`1200.pq`, `1600.pq`) per
generation — nothing like the `global_time`-only files that made three other
campaigns report success having written nothing (see **D**).

**But gate 4 — "do 336 lineages render, and does the gather receive all of them?" —
has still never executed.** Five blockers, each visible only once the one before it
was cleared:

| # | blocker | status |
|---|---|---|
| 1 | `analysis_options` not declared on the generator | fixed, v2ecoli#730 |
| 2 | founders shared across seeds | expressible, v2ecoli#731 / #732 |
| 3 | pre-built cache not reachable | fixed, v2ecoli#732 |
| 4 | nested-composite path (PBG#207) | worked around, v2ecoli#723 |
| 5 | **every lineage emits a directory named `sweep`** | **fixed locally, unmerged** — see A |

---

## The inventory

### A. Blocking gate 4 — the lineage output name collides

Every lineage emits a directory named literally `sweep`: `lineage_step.py` declares
`nextflow_port_decls = {"sweep_dir": 'path "sweep"'}` and each node's config sets
`out_dir: "sweep"`. Unique *within* a task, identical *across* tasks. Measured on
the 3×2 (simulation 513, `sim160-gate4-3x2-f07a`):

```
Process `analysis` input file name collision --
There are multiple input files for each of the following file names: sweep

Failed to publish file: .../work/14/27c67.../sweep; to: .../vecoli-output/.../sweep [copy]
```

Two failures, one cause. The gather cannot stage three inputs of the same name, and
concurrent `publishDir` copies into the same destination name collide. Result:
**89 objects / 1,050,163,871 bytes published under `lineage_seed=1` and `=2` only** —
seed 0's data never left the work directory.

> ⚠ **I asserted the opposite**, in v2ecoli#718 ("copies interleave rather than
> collide") and again in the #725 gather. Both times I was reasoning about directory
> *contents* while Nextflow reasons about the directory *name*. Every earlier run
> passed because no two tasks ever shared a destination: 1×1, then 2 variants × **1
> seed**. Same class as #721 — a name unique within one scope but not across it.

**The fix** keeps the declaration class-level and uniform (it must be: see the
constraint below) and moves the variation into ordinary per-node config:

- `lineage_step.py` — `'path "sweep"'` becomes the glob `'path "sweep_*"'`
- `workflow_nf.py` — the lineage node's `out_dir` becomes `sweep_v{vi}_s{seed}`

The gather needs no change: eagmon's #724 runs `v2ecoli-analyze .` over the task
work dir, and `history_files` globs the hive tree recursively, so it never names
`sweep`. `publishDir` needs no change either — with distinct names the copies simply
stop colliding.

**The constraint that shapes this:** `nextflow_port_decls` is read via
`_class_annotation` → `getattr(type(instance), key)`, i.e. **off the class**. It
cannot vary per instance — a property would return the descriptor, not a value.
`AnalysisTaskStep`'s own comment already records this.

**Blast radius: two coupled lines, and it was checked rather than assumed.** Having
been wrong twice on exactly this reasoning, the consumers were verified directly:

- every reader funnels through the recursive glob in `v2ecoli/library/sweep_io.py`
  (`<sweep_dir>/**/history/experiment_id=*/**/*.pq`)
- sms-ecoli's readers — `run_standalone_analysis.py`, `run_multi_node_analysis.py`,
  `s3_compare_report.py` — all take `--history-uri s3://…/vecoli-output/<experiment_id>`,
  i.e. the **experiment root**, never `<exp>/sweep/`
- no consumer in any of the three repos hard-codes a `/sweep/` path segment
  (sms-ecoli's other `"sweep"` hits are provenance labels and dict keys)
- `data_layout.py` has no `sweep` segment at all — sms-api supplies only the
  `publish_dir` prefix and Nextflow appends the rest

> ⚠ **The published shape changes, and people read these paths by hand.** Today N
> lineages merge into one hive dataset at
> `<exp>/sweep/<exp>/history/experiment_id=…/variant=…/lineage_seed=…/`. After this
> they become N sibling trees: `<exp>/sweep_v0_s0/…`, `<exp>/sweep_v0_s1/…`.
> Anyone pointing at `<exp>/` is unaffected. Anyone who bookmarked `<exp>/sweep/`
> needs to move up one level. **@cplong90 / @AlexPatrie — this is the one thing here
> that can surprise you.**

**Verified locally:** 4 new contract tests pass, and `nextflow -preview` on the
3-seed single-variant shape compiles clean (DAG: `parca_v0`, three
`runs_v0:lineage_v0_s*`, `analysis`).

### B. Cancel does not reliably stop the work

- **#472** filed, closed by **#473** (grace period 30→120 s, plus a reap) and
  **#474** (reap only a campaign the run owns outright). Both deployed in **0.9.112**.
- **#478** (open) sequences the reap *after* the head dies — reaping into a live head
  makes Nextflow treat terminations as task failures and **resubmit** them. Measured
  by hand: terminating 10 tasks produced 9 fresh jobs.

**On review the whole approach is weak, and should be replaced rather than merged:**

| defect | consequence |
|---|---|
| `_reap_campaign_batch_tasks` does not paginate (`list_jobs` caps at 100) | a 336-lineage Run 4 campaign silently misses most of its tasks |
| scans one queue (`batch_amd64_queue`) only | tasks on other queues survive |
| synchronous inside the cancel request | a pod restart mid-cancel — i.e. any deploy — loses the intent entirely |
| — | cancel latency up to ~150 s |
| a **resumed** campaign reaps nothing, by design of #474 | orphans |

Real cost already paid: cancelling simulation 441 left **8 orphan Batch tasks**
running ~100 minutes, which later caused `No space left on device` in an unrelated
campaign.

### C. The gather

- **Gate 4 unexecuted** (blocked by A).
- **#449** — analysis defaults OFF. Flipping it alone makes *every* campaign fail its
  last node, because empty `analysis_options` produces no `analysis/` for Nextflow to
  collect. Needs a default source or a dispatch-time rejection.
- **#448** — the analysis leg loads *stock* simData for candidate strains.
- **#447** — the acceptance gate is not wired into the analysis DAG.
- **#727** (sim_data for standalone sweeps) is in simulator 160 but has never been
  reached, since the gather has never run.

### D. Output integrity — fixed by eagmon, and my analysis of it was wrong

viva-api **#475** (merged 2026-09-07 21:05Z) root-caused the CD2 empty-emit failures
and closed both holes: parquet now requires **>1 column and >0 rows** (footer read
via a lazily-imported pyarrow); zarr requires a real **chunk**, not a marker.

> ⚠ **I recorded #467 as "not exposed"** — in act 1's gate table and again in its
> gate-6 section — on the grounds that lineages emit `.pq` and the parquet branch is
> checked first and requires `st_size > 0`. That was wrong. eagmon found the second
> hole I had not considered: **a `global_time`-only parquet is >0 bytes**, so the
> very check I cited as protective passed it. Three GovCloud dispatches (Run 2 10×10,
> Run 3 mecillinam, Run 4) reported success having written no usable history.
>
> The error was one of method, not detail: I traced the branch order, found the
> guard, and stopped — never asking what a *passing* file could actually contain.

**The Nextflow lineage path was nonetheless never afflicted** — measured, not argued:
J3's published history is 47.6 MB / 48.8 MB multi-column chunks. So the J3 evidence
above stands.

- **#467 is still open although #475 fixes it** — close it citing the PR.
- #475 deliberately does **not** fix *why* emits were empty (undeclared `emit_paths`;
  Run 4's zarr emitter selection). That is dispatch-side, tracked on sms-ecoli#166.

### E. Science correctness

- **Gate 1b / v2ecoli#693** — seeds sharing a `cache_dir` share a founder object. Now
  expressible two ways, **#731** (re-draw per seed) and **#732** (per-seed pre-built
  cache), but only #732 is verified on infrastructure. The J3 probe got distinct
  founders from the *caches*, not from #731's re-draw. **#731 remains unverified.**
- ParCa caches are keyed **commit + variant** and are a deliberately *shared*
  resource. Any dispatch-identity token must **not** enter cache paths, or reuse
  breaks and @cplong90's staged caches are stranded. (This is why F resolves to
  attribution rather than path derivation.)
- **v2ecoli#735** (open, eagmon) moves `compute_cache_version` to **schema 3**,
  folding chassis provenance into `inputs_hash`. This **rekeys every shared
  commit+variant cache** — a one-time rebuild. Worth saying out loud so nobody reads
  the resulting cache miss as a regression. The explicit `cache_uri` path (#732) is
  **immune**, since it fetches a URI rather than deriving a key — an argument for
  preferring it for staged caches. viva-api **#479** (open, @AlexPatrie) carries the
  matching `_parca_command` passthroughs.

### F. Identity and observability

- **No monotonic dispatch identity in the artifacts.** `unique_experiment_id` is
  `sim{simulator_id}-{label}-{4hex}` — unique, but a *nonce*, so two dispatches
  cannot be ordered. `simulation.database_id` **is** monotonic and appears in none of
  the identities we compare on. Consequence: ownership and reap decisions are lexical
  string matches (#474) rather than ordinal comparisons.
- **No task↔run correlation.** nf-amazon 3.4.2 exposes no Batch job tags — verified
  by inspecting the plugin classes, not inferred from docs. Nextflow's own trace
  carries `native_id` = the Batch job id, and `nf-weblog` streams the same live, but
  that plugin's last release is **Nov 2023** with an open "bump for 25.10", and a core
  weblog bug was closed `wontfix`. Usable, not dependable.
- **process-bigraph#207** — `render_composite` descends into a nested composite with
  the inner-only path; worked around in v2ecoli#723, still open upstream.

### G. `emit_paths` cannot be set per campaign — the fourth of one bug class

`emit_paths` is forwarded by `LineageStep._FORWARDED`, declared in both
`lineage_step.py` and `lineage.py`, and honoured by `LineageProcess` — but it is
**absent from `workflow_nf`'s generator `parameters` block**, so a dispatch cannot
actually set it. The value dies at the one hop nobody declared it at.

This is the **fourth** instance of an identical bug already fixed three times: #730
(`analysis_options`), #731 (`independent_founders`), #732 (`cache_uri`). Not a gate-4
blocker — the default `[]` means "all listener paths", which is why J3 wrote 47 MB
chunks — but it bites the moment anyone wants to *trim* emissions on a large campaign.

**The recurrence is the real finding.** Four identical escapes says the rule —
*a value must be declared at every hop it crosses* — needs a structural check rather
than vigilance: one test asserting every `_FORWARDED` key is reachable from the
generator's `parameters` would have caught all four at once.

### H. ~~Active science-side unknown~~ — root-caused and fixed (v2ecoli#737)

**Run 3's one-tick collapse** — dispatch 439 collapsing after `global_time ≈ 1.0` —
is fixed by @eagmon's v2ecoli#737 (merged 2026-09-08 01:15Z), which root-caused it
from the live CloudWatch tracebacks rather than from the #733 instrumentation:

- **It was never silent.** The injected/swap runs *crashed before emitting*
  (`non-advancing interval: 0.0` → `composite CRASHED at 1s in generation 1`), and
  `PBG_REQUIRE_OUTPUT` correctly refused success. The output gate did its job.
- Cause: `_should_inject_as_step` recognised a Step only via
  `issubclass(vivarium.Step)`, which is False for a **v2ecoli-native deriver** like
  the native `ecoli-metabolism-redux`.
- #737 also fixes `metabolism.py:841`, where `boundary.external[aa] > threshold`
  compared a pint `Quantity` against a float — which is why only the
  amino-acid-supplemented (`_with_trp`) arm crashed and plain `minimal` never did.

**Why this still matters to gate 4:** the general caution stands — a campaign can
pass gate 4 *structurally* (analysis runs, partitions publish) while carrying
degenerate data — so the gate-4 criterion keeps its "history must satisfy #475's
>1-column, >0-row test" clause. What is no longer true is that we have an unexplained
collapse in flight.

### I. Operational

- `GET /simulations/discovery` lists only **top-level** `configs/*.json`; a nested
  path (`experiments/foo.json`) dispatches fine but is invisible.
- The K4 cell-only configs live on `study/cd2-pnnl-02-strain-sims`, so an image built
  from `main` cannot see them.
- `tests/api/app/test_cli_e2e.py` runs against the **live** deployment whenever
  `localhost:8080` is reachable — 5 phantom failures with a tunnel open.

---

## The plan

### Phase 1 — Unblock gate 4: give each lineage a distinct output name

The only change needed to answer the gate; everything else can follow.

1. Rebase `fix/lineage-output-name-collision` (1 behind `origin/main`: #734, ptools
   windowing, touches none of these files), commit, PR, merge.
2. Add the structural test from **G** — every `_FORWARDED` key reachable from the
   generator's `parameters`.
3. Re-pin sms-ecoli. ⚠ The pin keeps moving — verify it rather than trusting any
   note, this one included. As of 2026-09-08 both `pyproject.toml` and `uv.lock` on
   sms-ecoli `main` read **`5f6a7d54`** (#734, ptools windowing), which succeeded
   `32ca56da` (#733) and `5836ff2f` (#263). **Pin forward from `5f6a7d54`.**
4. Rebuild the simulator image; re-run the 3×2.

**Gate 4 closes only if** the `analysis` process actually executes, `analysis.json`
publishes, **three** distinct `lineage_seed=` partitions appear, and the history
satisfies #475's criterion (>1 column, >0 rows). Compare against the recorded
failure: `sim160-gate4-3x2-f07a`, 89 objects, `lineage_seed=1` and `=2` only.

### Phase 2 — Replace the cancel reap with scheduler reconciliation

**Decided: close #478 unmerged** and do this properly. Until it lands, 0.9.112 keeps
#473's grace period and #474's ownership guard, so **the resubmission race is live** —
worth knowing if anyone cancels a campaign meanwhile.

Reuse the existing orphan-reconciliation idiom in
`viva_api/simulation/job_scheduler.py`: `_polling_loop` already runs every 30 s and
calls `reconcile_local_tasks()` alongside `_reconcile_orphaned_build` /
`_reconcile_orphaned_simulation_placeholder` / `_finish_orphan`.

- Add `reconcile_cancelled_nextflow_campaigns()` to that family: find runs already
  marked `CANCELLED` that still have live Batch tasks, and terminate them.
- **Restart-safe** (intent lives in the DB row that cancel already writes),
  **idempotent**, retried every 30 s, and it removes ~150 s of latency from a
  user-facing call.
- Fix both defects while moving it: **paginate** `list_jobs` via `nextToken`, and scan
  **every** task queue.
- Keep #478's sequencing insight — never reap while a head is alive.

### Phase 3 — Make the gather trustworthy

- **#449**: default `analysis_options` from the simulation config's own block, *and*
  reject `include_analysis` with empty options at the API boundary. The boundary check
  is the cheap half and needs no science decision (same shape as #456).
- Confirm **#727** actually satisfies the molecular analyses (`cd1_transcriptomics`,
  `cd1_proteomics`) once the gather runs — if not, that is a gap in the fix, not a
  missing dependency.

### Phase 4 — Ordinal identity instead of string matching

`simulation.database_id` is already monotonic. Use it for **attribution**, not path
derivation — paths are constrained by **E** and by resume sharing a work dir:

- ownership asks "is a live run with a higher `database_id` sharing this campaign?"
  rather than comparing sanitised strings
- cache paths and the shared results layout stay untouched, so **no cross-dispatcher
  agreement is required** — chain-dispatch and Ray need not adopt anything

### Phase 5 — Hygiene

- ~~#467~~ — fixed by eagmon in #475; close the issue citing the PR.
- Close **#478** unmerged, recording *why* on the thread so its sequencing insight
  survives the closure.
- Declare `emit_paths` in `workflow_nf`'s generator parameters (**G**).
- `discovery` should list nested configs, or document that nested paths are accepted.
- Guard `test_cli_e2e.py` behind an explicit opt-in env var so an open tunnel cannot
  turn it into 5 phantom failures.

### Coordination

Phases 3–5 are substantially other people's work: #467 is already eagmon's (#475),
#447/#448/#449 are his issues, #735/#479 are his and @AlexPatrie's. **Comment on the
issue before touching it** — I duplicated eagmon on #721/#722 this week by not doing
that.

---

## Progress log

Newest last. Updated as each phase lands — the point of this document is that it
stays current.

| date | what happened |
|---|---|
| 2026-09-07 | Run 2 J3 probe (sim 160 / simulation 511) **SUCCEEDED**: 85 min, 100 objects / 1.15 GB, two real founders, zero ParCa invocations. `cache_uri` and multi-variant rendering exercised for the first time |
| 2026-09-07 | 3×2 attempt (simulation 513) **FAILED** on the `sweep` name collision — blocker 5. 89 objects published, seed 0 lost |
| 2026-09-07 | eagmon's #475 closes the empty-emit holes; corrects my "not exposed" reading of #467 (**D**) |
| 2026-09-08 | Blocker 5 fixed locally: `path "sweep_*"` + `out_dir = sweep_v{vi}_s{seed}`. 4 contract tests pass, `nextflow -preview` clean. **Unmerged** |
| 2026-09-08 | This document written; act 1 cross-linked |
| 2026-09-08 | v2ecoli#736 opened (blocker 5 + the structural test). Classifying `_FORWARDED` found the gap is **7 keys**, not just `emit_paths` — `media` among them, so a `workflow_nf` campaign cannot select media. Flagged on sms-ecoli#166 |
| 2026-09-08 | viva-api#467 closed (fixed by #475); #478 already closed unmerged |
| 2026-09-08 | v2ecoli#735 merged — `cache_version` schema 3 is now live, so shared commit+variant caches are **rekeyed**. `cache_uri` campaigns are unaffected |
| 2026-09-08 | Pin correction: @AlexPatrie's review of #480 flagged my `32ca56da` note as stale — correct, but the SHA he gave (`3132543e`) is #691 from 09-04, **53 commits behind**. Verified against sms-ecoli's `pyproject.toml` + `uv.lock`: the real pin is `5f6a7d54` (#734) |
| 2026-09-08 | v2ecoli#737 (@eagmon) **closes item H** — the one-tick collapse was a pre-emit crash (native derivers not recognised as Steps), not a silent empty emit; `PBG_REQUIRE_OUTPUT` had refused it correctly. Also fixes the pint `Quantity > float` crash on AA media |
