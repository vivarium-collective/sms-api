# Nextflow dispatch, act 2: closing gate 4 and the shortcomings behind it

**Status (2026-09-08 15:30Z): GATES 4 AND 1b ARE CLOSED.** Simulation **574** (simulator 167,
sms-ecoli `1c66700` → v2ecoli `b9942d78`) completed end to end: ParCa → three lineages →
the gather, with the analyses receiving **all three sweeps** and their sim_data. Seven
blockers were found and cleared in sequence to get here. Phases 1 and 2 are done — the
cancel reconciler and the 32 GB gather default went live on `smsvpctest` in 0.9.122 and are
carried by every later roll (the cluster is on 0.9.125 as of #507).
**Gate 1b is also closed** (sim 577, 14:5xZ): independent founders verified on
infrastructure. What remains is content-level (Phase 3: #449, the `cd1_exchange_fluxes`
column pending verification on a ≥ #741 image), Phase 4 (ordinal identity), Phase 5 hygiene,
and one thing not yet demonstrated: the gather at 336-scale. Everything
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
| 5 | every lineage emits a directory named `sweep` | fixed, v2ecoli#736 — **confirmed**: all 3 lineages of sim 562 SUCCEEDED with distinct dirs |
| 6 | the fix for 5 also captures the port manifest `sweep_dir.json` | fixed, v2ecoli#739 — **confirmed**: sim 570 staged all three sweeps, 1.62 GB published, `lineage_seed=0/1/2` |
| 7 | the gather has no `simData.cPickle` — `resolve_sim_data` fails | fixed, v2ecoli#742 — **confirmed**: sim 574's gather resolved sim_data and completed |

#### Gate 4 — the evidence (sim 574, `sim167-gate4-3x2-b7-95aa`, completed 08:40:42Z)

| criterion | measured |
|---|---|
| three lineages render and run | `parca_v0` 4 m (cache hit); lineages **77 / 83 / 91 min**, all SUCCEEDED |
| three sweeps published | `sweep_v0_s0/s1/s2`, **`lineage_seed=0/1/2`** (30 objects each); **197 objects / 1,654,087,569 bytes** total |
| the gather executes | `analysis` SUCCEEDED (2 min on the retry — see below) |
| **the analyses receive all N sweeps** | `analysis/ptools/cd1_proteomics__variant=0.tsv` columns: `Cell: 0_0_0, 0_1_00, 1_0_0, 1_1_00, 2_0_0, 2_1_00` — **seeds 0, 1, 2 × generations 0, 1** |
| `analysis.json` publishes | 8,428,358 bytes; `analysis/` = **51 objects / 32.1 MB** incl. per-cell `ptools_*` TSVs for all six cells |
| history is real (#475) | smallest chunk: **244 columns × 127 rows** |

**Two findings on the way through, neither a blocker:**

- **`analysis.json` reports `PARTIAL`: 10 of 11 analyses `ok`.** `multiseed/cd1_exchange_fluxes`
  fails with `Binder Error: Referenced column "listeners__fba_results__external_exchange_fluxes"
  not found` — the `j3` variant swaps in `ecoli-metabolism-redux`, whose listeners emit
  `base_reaction_fluxes` / `solution_fluxes` / `estimated_fluxes` but not that column. An
  analysis-vs-redux listener mismatch, i.e. item **C** (#448 territory), not a dispatch defect.
  Handed to @eagmon on sms-ecoli#166.
- **The gather OOMs at 16 GB and needs the retry.** First attempt: exit **137**
  (`OutOfMemoryError: Container killed due to memory usage`) after 1 min; the awsbatch profile's
  `memory = { task.exitStatus == 137 ? 16.GB * task.attempt : 16.GB }` gave the retry 32 GB and it
  finished in 2 min. So the exit-status-keyed scaling act 1 flagged as missing **is in place and
  worked** — but a 3×2 already needs it, and Run 4 is 336 lineages. Raise the `analysis` label's
  base memory before a real campaign relies on the retry.

**What gate 4 does *not* say:** nothing about founders (gate 1b, #731 still unverified on
infrastructure), nothing about 336-scale (the 255-arity wall was measured at render time; the
gather has now run at N=3), and nothing about the science in the TSVs.

**FIRED 2026-09-08 21:42Z — simulation 683** (`sim172-run2-j3-10x8-founders-4626`), shape 1
below, after MNP's 666 died of the xarray bug: `mecillinam_wellmixed.json`, Alex's fresh J3
chassis via `cache_uri`, redux swap, `exchange_fluxes` + basis inside `injected_processes`,
10 seeds × 8 generations (mirroring 666's spec), `--independent-founders`, gather on.
Announced on #166. Expected terminal ~03:00–04:00Z.

**Next milestone on this path — a Run 2, and it is now a coordination decision.** Alex's
MNP Run 2 (Dispatch 666) is running, so a Nextflow Run 2 is no longer the only route to the
deliverable; its value would be (a) the gather running as part of the campaign — MNP needs a
manual flush — and (b) an independent replication. Two shapes, both exercised:
1. **`--independent-founders` on the fresh J3 chassis** (1 variant × 10 seeds, gate 1b's
   verified route): simplest, one cache for the gather, but not the same founders as 666's
   composed per-seed caches — a valid Run 2, not a replication.
2. **10 single-seed "variants", each with `--cache-uri` at one of Alex's 10 founder
   compositions** (the J3 probe's shape scaled up): same founders as 666 — a replication —
   at the cost of 10 caches staged into the gather (all named `cache`; first-hit sim_data is
   fine here because all 10 share one simData).
Either way `cd1_exchange_fluxes` comes back 10/11 until the redux binding lands, and either
way the variant must carry `exchange_fluxes` + `exchange_flux_basis` in `injected_processes`
(679 did not). ~8 h of lineage time on the same Spot queue as Alex's fan-outs. Not fired
without a decision.

**What gate 4 buys that the team's other path does not (recorded 2026-09-08 13:00Z):** CD2
Runs 1–4 are being dispatched on `lineage_ray_batch`/MNP, where — per @eagmon's readiness audit,
GATE 1 — *analyses do not auto-trigger*; every run needs a manual flush after it lands. On this
path the gather is a node in the DAG: sim 574's `analysis/` was published by the campaign itself.
That is the concrete operational difference, now measured on both sides.

---

## The inventory

### A. ~~Blocking gate 4 — the lineage output name collides~~ — resolved (blockers 5, 6, 7; gate 4 closed by sim 574)

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

#### A.6 — Blocker 6: the fix for 5 collides one file over (sim 562, 2026-09-08 03:33Z)

The re-run on simulator 161 got further than any campaign before it: `parca_v0`
hit the (schema-3) cache in 3 min, and **all three lineages SUCCEEDED** — 94 m, 94 m,
73 m, real 64–69 MB parquet chunks under `sweep_v0_s1/` and `sweep_v0_s2/`. Blocker 5
is genuinely fixed. Then the gather failed at staging:

```
Process `analysis` input file name collision --
There are multiple input files for each of the following file names: sweep_dir.json
```

`run_step` writes each output port's value manifest as `<port>.json` — for the port
`sweep_dir`, that is `sweep_dir.json` — into the *same* work dir, and my glob
`path "sweep_*"` matches it. So every lineage emitted two items into the channel:
its distinct directory **and** an identically named manifest. The gather collided on
the manifest exactly as 513 had collided on the directory. `publishDir` even copied
the manifest to the results prefix as if it were output, and the abort interrupted
seed 0's in-flight publish (`sleep interrupted`) — its 552 MB is intact in work dir
`e4/6166eb`.

> ⚠ Same lesson, third time: `-preview` compiles the DAG and cannot see staging
> collisions, which are a runtime property. And my blocker-5 contract test asserted
> the *directory* names were distinct — it never asked what *else* the glob matched.

**Fix (v2ecoli#739):** encode the invariant instead of another naming rule — the value
of this port *is a directory*: `path "sweep_*", type: "dir"`. No file can match. The
new test is structural: for every Step's declared output glob, `fnmatch("<port>.json",
glob)` must be false or the decl must be typed `dir`.

**Upstream (process-bigraph#208):** the renderer's own default decl is literally
`path "<port>.json"`, and the manifest is emitted regardless of override, so any
override glob that begins with the port name sweeps it up. A dotfile manifest
(`.<port>.json`) is invisible to Nextflow globs by default and removes the footgun
at the source.

#### A.7 — Blocker 7: the gather ran, and had no sim_data (sim 570, 2026-09-08 06:09Z)

The re-run on simulator 164 (v2ecoli#739 in) cleared blocker 6 completely: all three
sweeps staged, **143 objects / 1,621,594,959 bytes published**, `sweep_v0_s0/s1/s2`
with `lineage_seed=0/1/2`. Then — **for the first time in this path's history — the
`analysis` process was submitted and executed.** Four attempts (the retry policy),
each exiting 1 in under a minute:

```
FileNotFoundError: could not resolve sim_data for '.' (the Analysis steps need the
ParCa simData.cPickle). Checked, in order: a sweep-local sim_data*.cPickle;
$V2ECOLI_SIM_DATA; the sweep's run_identity.json 'sim_data' pointer; and
out/kb|workflow/simData.cPickle.
```

This is inventory item **C**'s "#727 has never been reached" — reached. None of the
four resolution routes can succeed in a Nextflow gather task: the sweeps carry only
`configuration/` and `history/` (no pickle, no `run_identity.json`, so #727's pointer
has nothing to read); `$V2ECOLI_SIM_DATA` is threaded on the **Ray** analysis path only
(viva-api#448); `out/kb` is not in a task work dir. The cache that *holds* the pickle
is staged into every lineage as `path cache` — and never into the gather.

**Fix (v2ecoli#742):** stage it there too. `AnalysisTaskStep` takes one `cache_v{i}`
input per variant, wired from `parca_v{i}`'s cache store, exactly as the lineages do;
`resolve_sim_data`'s *first* branch — the sweep-local glob, "the exact pairing,
preferred" — then finds `cache/simData.cPickle`. Verified against the real ParCa work
dir that the cache contains it (84,719,053 bytes). Single repo, no env plumbing, and
the analyses read the very cache the lineages ran from.

*Known limit, not new:* a multi-variant campaign stages N caches all named `cache`,
and `resolve_sim_data` takes the first hit — the same open question as #448.

**Also learned on this run — `-resume` needs a FOURTH thing aligned:** the same
container image. 570 was dispatched with `--resume-from sim161-gate4-3x2-6ff7`, and
every task re-ran (`parca_v0` hash `47/f9b132` → `96/7962d8`): the container is part of
Nextflow's task hash. A fix that needs a new image can never reuse the previous
campaign's lineages. Budget the full re-run.

### B. ~~Cancel does not reliably stop the work~~ — resolved by Phase 2 (viva-api#481, verified live 2026-09-08)

> Kept as written because the defect table below is the specification #481 was
> built against. Every row is now addressed: the reap runs from the scheduler off
> the CANCELLED row (restart-safe), paginates, scans every queue, defers while the
> head exists, and a resumed run still reaps nothing it does not own. The live
> test is under Phase 2.


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

- ~~**Gate 1b / v2ecoli#693**~~ — **CLOSED 2026-09-08 by simulation 577** (`sim167-gate1b-
  founders-3x1-fc4d`: 3 seeds × 1 gen, `--independent-founders`, same `j3` variant as 574).
  Both routes are now verified on infrastructure — #732 (pre-built per-seed caches) by the J3
  probe, and **#731 (re-draw per seed) by 577**. Measured as act 1 specified, pairwise
  `bulk__count` at `global_time == 0` over 16,321 species, against sim 574 as the
  shared-founder control:

  | | species differing | total-count difference |
  |---|---|---|
  | control, sim 574 (shared founder) | 221 / 255 / 249 — **1.4–1.6 %** | 68–183 molecules |
  | gate 1b, sim 577 (`--independent-founders`) | 4,941 / 4,997 / 5,005 — **30.3–30.7 %** | 4.2×10⁸ – 5.7×10⁹ molecules |

  Twenty-fold more species differ and the totals differ by billions of molecules: three
  different cells, not one cell with sub-timestep drift. The flag was confirmed to reach all
  three staged lineage configs (`independent_founders: true`, `founder_sim_data:
  cache/simData.cPickle`) before the run — read from the `stage-<session>/` work dir, since the
  output-prefix copies land only at stage-out. Cost: lineages 33–38 min for one generation
  (574's were 77–91 for two), so the re-draw is not visibly expensive at this scale.
- ParCa caches are keyed **commit + variant** and are a deliberately *shared*
  resource. Any dispatch-identity token must **not** enter cache paths, or reuse
  breaks and @cplong90's staged caches are stranded.
- **The staged J3 founder caches the J3 probe reused are pinned to an old v2ecoli
  commit** (Alex, Slack 2026-09-08 09:50/11:05). The probe ran on simulator 160, which
  predates #735; on any image at or past #735, `cache_version` schema 3 refuses
  cross-commit reuse, so the same `--cache-uri` dispatch would fail loudly today.
  **Superseded 18:39Z (Alex, #166):** the fresh J3 chassis is built and verified at
  `s3://…/ray-parca-cache/2fddfcb81655e5447f7ae9da4a0e5039ed73ec65/cd2-run2-j3-candidate-v1-lambda075/`
  with 10 per-seed founder compositions (`/parca/new-gene-cache` × 10), and **the real Run 2
  is dispatched on MNP as Dispatch 666** (10 seeds, `n_generations: 8` — @cplong90 notes the
  proven J3 baseline used 4; Alex confirmed 8 deliberately). Still no *completed* Run 2 proof
  on either path; MNP's is running.
- ~~**Run 2 on MNP (sim 666) is on the parquet emitter, not xarray — measured 20:02Z.**~~
  **Wrong, and corrected on #166 at 21:2xZ.** 666 FAILED at 21:08:02Z of exactly the 665
  bug: `lineage.py:586 _emit_xarray → zarr_writer.py:573 _check_group →
  FileNotFoundError … lineage_seed=6/emitstep_gen=4` inside seed 6's Ray actor, re-raised
  through `composite.run`, whole 10-node job exit 1. The MNP lineage runs **both** emitters;
  the xarray store is only *opened* at a generation boundary, so "no zarr objects yet" at
  20:02Z was not evidence of not being exposed — reading `_emit_xarray`'s call site would have
  been. Four 66-byte `zarr.json` files appeared at 21:07:40Z, no generation-4 success marker.
  The parquet half is intact: 10/10 seeds, generations 0–4, ~11 GB. Still true: 666's hive key
  is `experiment_id=lineage_ray_batch` (the #450/#457 class); and the Nextflow path is
  parquet-only by construction (`_emit_xarray` never runs — 574/577/679 completed), so it is
  genuinely outside this bug. Any MNP re-fire needs `emitter: parquet` until eagmon's fix.
  **Root cause found by Alex (22:16Z) — it was viva-api, not the emitter:** `run_pbg.py`'s
  `_redirect_emitters()` pointed the xarray store at the same local `PBG_RESULTS_DIR` that
  `ray-batch-entrypoint.sh` syncs to S3 best-effort every 30 s, so a node change lost the
  previous generation's zarr groups (parquet survives that because each chunk is an
  independent file). Fixed in **viva-api#520** (xarray gets a direct S3 `out_uri`), deployed
  as **0.9.127**. **Scope check for this path:** the Nextflow head reuses only `run_pbg`'s
  resolver; a lineage runs via `process_bigraph.run_step` and Nextflow uploads the task's
  outputs itself — `_redirect_emitters` is never on the lineage path, which is the measured
  form of "parquet-only by construction".
- **`inputs_hash` bound (@cplong90, #166 14:37Z):** the `cache_version` guard *can condemn a
  pin but cannot clear one* — the condemning half is trustworthy, the clearing half is not.
  A cache that passes the guard is not thereby proven to match the pin. (This is why F resolves to
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

### Phase 1 — Unblock gate 4: give each lineage a distinct output name — ✅ DONE (gate 4 closed by sim 574)

The only change needed to answer the gate; everything else can follow.

1. ~~Rebase, commit, PR, merge~~ — **done**, v2ecoli#736 (`2d20a158`).
2. ~~Structural test from **G**~~ — **done** in #736; it found **seven** unreachable
   keys, not one (see G).
3. ~~Re-pin sms-ecoli~~ — **done**, sms-ecoli#270 (`5fff5c79`), pinned forward from the
   *verified* `5f6a7d54`. ⚠ The pin keeps moving; verify it against `origin/main`'s
   `pyproject.toml` + `uv.lock` before every bump, never a recorded note.
4. ~~Rebuild; re-run the 3×2~~ — **done**: simulator 161, simulation 562 → **blocker 6**
   (A.6).
5. ~~merge v2ecoli#739 → re-pin → rebuild → re-run~~ — **done**: sms-ecoli#281,
   simulator 164, simulation 570 → blocker 6 cleared, gather RAN, **blocker 7** (A.7).
   The image change re-hashed every task, so nothing was cached (see A.7).
6. ~~merge v2ecoli#742 → re-pin → rebuild → re-run~~ — **done**: sms-ecoli#285 (`1c66700a`),
   simulator **167**, simulation **574 COMPLETED**. Gate 4 closed; evidence above.

**Gate 4 closes only if** the `analysis` process actually executes, `analysis.json`
publishes, **three** distinct `lineage_seed=` partitions appear, and the history
satisfies #475's criterion (>1 column, >0 rows). Compare against the recorded
failure: `sim160-gate4-3x2-f07a`, 89 objects, `lineage_seed=1` and `=2` only.

✅ **Closed 2026-09-08 08:40Z by simulation 574** — every criterion measured; see
"Gate 4 — the evidence" under §A.

### Phase 2 — Replace the cancel reap with scheduler reconciliation — ✅ DONE, VERIFIED LIVE

**viva-api#481** merged, deployed to `smsvpctest` as **0.9.115** (#483), and verified
against the case the old code could not survive (sim 567, 2026-09-08 02:29–02:32Z):

```
02:29:36Z  DELETE /simulations/567/cancel → 200 in 0.14 s      (inline reap: up to ~150 s)
02:29:38Z  api pod restarted → new ReplicaSet; the pod that took the cancel is gone
02:31:20Z  NEW pod: "head … still terminating; will re-check next tick"  ×4
02:31:41Z  NEW pod: "head … left 2 Batch task(s) running; terminated them"
02:31:56Z  head GONE; both tasks FAILED, reason "campaign … cancelled via sms-api"
```

No resubmission (contrast the inline reap: terminating 10 produced 9 fresh). The
concurrently running 562 was untouched. Evidence on #481. One presentation gap found
on the way: `GET /simulations/{id}/status` says `"unknown"` for a cancelled campaign
because it re-derives from the (deleted) head Job instead of trusting the terminal DB
row — **viva-api#484**.

*Original design, kept for the record:* **Decided: close #478 unmerged** and do this
properly. Until it lands, 0.9.112 keeps #473's grace period and #474's ownership guard,
so **the resubmission race is live** — worth knowing if anyone cancels a campaign
meanwhile.

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
- ~~Confirm **#727** actually satisfies the molecular analyses~~ — **it does**: sim 574's
  `cd1_transcriptomics` and `cd1_proteomics` both `ok`, via the staged cache (#742) rather
  than #727's identity pointer, which the Nextflow sweeps never carry.
- **`cd1_exchange_fluxes` vs `ecoli-metabolism-redux` — verified 2026-09-08 19:34Z (sim 679),
  and it IS the redux listener set.** I had marked this "superseded" on @eagmon's reading that
  the column is emitted at ≥ #741; the verification run on simulator 172 (v2ecoli `e4db5e67`)
  came back **10/11 with the same binder error**, so I read the history schemas directly:

  | run | metabolism | `fba_results` cols | `external_exchange_fluxes` |
  |---|---|---|---|
  | sim 679 (Nextflow, `j3` → redux, `e4db5e67`) | redux | 65 | **absent** |
  | Run 4 genotype 2 `_with_trp` (MNP, simulator 166) | classic | 18 | **present** |

  Redux emits per-molecule `estimated_exchange_dmdt__<MOLECULE>[p]` columns instead. Both
  readings were right within scope: the whole-`listeners` emit carries everything redux
  *produces*; redux never produces that column name. Not a pin issue, not a path issue.
  **It matters for the real Run 2, which is a redux run** — as the analysis stands the
  deliverable will be 10/11. Needs a redux-aware binding in `cd1_exchange_fluxes`; handed
  to @eagmon with the column names (item C / #448).

  **20:40Z — it is two gaps, not one (settled against Alex's Run 2, sim 666):**
  1. *Mine:* sim 679's dispatch carried no `exchange_fluxes`/`exchange_flux_basis`, so the
     `ExchangeFluxListener` never mounted and 679 has no `listeners__exchange_flux__*`
     columns — two KPIs unanswerable. On `workflow_nf` those keys reach a lineage **only via
     `injected_processes`** (item **G**, biting concretely). Every Nextflow re-fire must carry
     `exchange_fluxes: {glucose_exchange: GLC, violacein_exchange: VIOLACEIN}` and
     `exchange_flux_basis: gdcw` inside the variant's `injected_processes`.
  2. *The analysis's:* `cd1_exchange_fluxes.py:43` hard-binds
     `listeners__fba_results__external_exchange_fluxes`. Sim 666 — which *did* carry the
     config — has `listeners__exchange_flux__{glucose,violacein}_exchange` and 53
     `estimated_exchange_dmdt__*` columns (incl. `VIOLACEIN[c]`) and **still no
     `external_exchange_fluxes`** (247 columns). So 666's own analysis pass will fail the same
     way. The redux binding is needed regardless; @cplong90's spec: compartment-agnostic
     `estimated_exchange_dmdt__` prefix (violacein is the one `[c]` exchange) and flip the
     LP-raw sign.
- ~~**Raise the `analysis` label's base memory**~~ — **done, viva-api#495**:
  `DEFAULT_NF_RESOURCES["analysis"]` 16 → **32 GB** base (still `×attempt` on 137), with a
  test pinning ≥ 32. **Live on `smsvpctest` as of 0.9.122** (deploy #498, 12:31Z; the
  pod's `analysis` line verified as `_scaled_memory(32)`). The db-migration overlay,
  which two intervening deploys had left at 0.9.115, is back in step.

### Phase 4 — Ordinal identity instead of string matching

`simulation.database_id` is already monotonic. Use it for **attribution**, not path
derivation — paths are constrained by **E** and by resume sharing a work dir:

- ownership asks "is a live run with a higher `database_id` sharing this campaign?"
  rather than comparing sanitised strings
- cache paths and the shared results layout stay untouched, so **no cross-dispatcher
  agreement is required** — chain-dispatch and Ray need not adopt anything

### Phase 5 — Hygiene

- ~~#467~~ — fixed by eagmon in #475; close the issue citing the PR.
- ~~Close **#478** unmerged, recording *why* on the thread~~ — done; superseded by #481,
  and the thread links forward to it.
- ~~Declare `emit_paths` in `workflow_nf`'s generator parameters (**G**) — and the other
  six unreachable keys, `media` first.~~ — **done, v2ecoli#746**: all sixteen forwarded
  lineage knobs (the seven unreachable ones *and* the nine that only rode inside
  `injected_processes`, `exchange_fluxes` among them) are declared generator parameters,
  threaded into every lineage config only when set. `_KNOWN_UNREACHABLE` is empty and
  asserted to stay so. Needs a sms-ecoli re-pin + simulator before a dispatch can use them;
  until then `injected_processes` remains the route on simulator 172.
- ~~**viva-api#484**~~ — **fixed, viva-api#514**: a terminal HpcRun row is reported without
  asking a backend job that may already be gone. Takes effect on the next api deploy.
- **process-bigraph#208** — dotfile the port manifest so no output glob can catch it.
- **Instrument caution from @cplong90 (sms-ecoli#166, 02:02Z), general to PBG artifacts:**
  `final_state.json` cannot render any config field whose schema resolves to a bare `Node` —
  `_type: "quote"` fields *and* `{}`-default fields with no `_type` — so `injected_processes`
  and `exchange_fluxes` read `{}` on a perfectly healthy run. Read the container log, not the
  artifact, when asking what reached a node. (His `-n`-is-simulated-time finding and the three
  `inject.py` copies are MNP-path issues; `LineageStep` invokes once via `run_step` and does not
  take `-n`.)
- `discovery` should list nested configs, or document that nested paths are accepted.
- ~~Guard `test_cli_e2e.py` behind an explicit opt-in env var~~ — **done, viva-api#515**:
  `VIVA_LIVE_E2E=1` is required; verified the file skips with the tunnel open.

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
| 2026-09-08 | v2ecoli#736 merged (`2d20a158`); sms-ecoli#270 re-pins to it; simulator **161** built; the 3×2 re-run dispatched as sim **562** |
| 2026-09-08 | **Phase 2 shipped**: viva-api#481 merged, deployed as 0.9.115 (#483 — first build raced the bump; rebuilt the same tag from a `main` that had it). **Live cancel + pod-restart test PASSED** on sim 567: the pod that never received the cancel reaped both tasks at 02:31:41Z; no resubmission. viva-api#484 filed for the `/status` presentation gap |
| 2026-09-08 | **sim 562 FAILED at 03:33Z with blocker 6** (A.6): all three lineages SUCCEEDED (94/94/73 m, real data), then the gather collided on `sweep_dir.json` — the run_step port manifest my `sweep_*` glob also matched. Fixed as v2ecoli#739 (`type: "dir"` + a structural fnmatch test); process-bigraph#208 filed upstream. Seed 0's 552 MB is intact in its work dir |
| 2026-09-08 | v2ecoli#739 merged; sms-ecoli#281 re-pins (base had moved to `a9cf24ed` under me — verified forward); simulator **164**; resumed re-run as sim **570** — nothing cached (image change re-hashes every task) |
| 2026-09-08 | **sim 570 FAILED at 06:09Z with blocker 7** (A.7) — but blocker 6 is confirmed fixed (1.62 GB, three sweeps) and **the gather ran for the first time ever**. It died in `resolve_sim_data`: the ParCa cache was never staged into the gather. Fixed as v2ecoli#742 |
| 2026-09-08 | v2ecoli#742 merged; sms-ecoli#285 re-pins; simulator **167**; sim **574** dispatched 06:53Z (the CLI showed a bare "HTTP Error" both for the build and the dispatch — a tunnel transport failure on the *response*; the server had done the work each time. Check before retrying) |
| 2026-09-08 | **GATE 4 CLOSED — sim 574 COMPLETED 08:40:42Z.** Three sweeps, gather ran, `cd1_*` multiseed TSVs carry seeds 0/1/2 × gens 0/1, 1.65 GB + 32 MB analysis. `analysis.json` PARTIAL (10/11; `cd1_exchange_fluxes` binder error on the redux listener set → @eagmon). Gather OOM'd at 16 GB, retry at 32 GB succeeded — raise the label's base memory |
| 2026-09-08 | viva-api#495: gather base memory 16 → 32 GB (the size 574's successful retry ran at) |
| 2026-09-08 | **0.9.122 deployed** (#498): the 32 GB default is live on `smsvpctest`; verified on the pod. 0.9.120/0.9.121 were @AlexPatrie's intervening rolls and predated #495 |
| 2026-09-08 | 12-hour sync at 13:15Z: sms-ecoli `main` → `bc0ff34e` (v2ecoli `e4db5e67`: #741 emit-robustness, #743 coupled emit, #738); simulator 167 predates it. @eagmon: `external_exchange_fluxes` is emitted at ≥ #741 — my redux diagnosis superseded, pending verification on a newer image. Runs 1–4 dispatching on MNP (Alex), where analyses need a manual flush; the Nextflow gather auto-runs. Alex closed the `media` question (not urgent; MNP/chain have their own routes). @cplong90 independently confirmed the J3 probe consumed the prebuilt founder caches correctly |
| 2026-09-08 | Gate 1b run dispatched: sim **577** (`sim167-gate1b-founders-3x1-fc4d`), 3 seeds × 1 gen, `--independent-founders`, same `j3` variant as 574 — the shared-founder control, in which seeds differ in only **1.4–1.6 %** of 16,321 bulk counts at t=0 |
| 2026-09-08 | **GATE 1b CLOSED — sim 577 COMPLETED ~14:50Z.** Independent founders: 30.3–30.7 % of 16,321 bulk counts differ at t=0 between seeds, vs 1.4–1.6 % for the shared-founder control (574). v2ecoli#731 verified on infrastructure |
| 2026-09-08 | 7-hour sync 19:40Z: Alex superseded the "stale caches" line — fresh K4/J3 chassis at commit `2fddfcb8`, Run 1 cell-only (665) and **Run 2 (666, 8 gens)** dispatched on MNP; Run 1 coupled on its 3rd re-fire past v2ecoli#745/sms-ecoli#289; Run 4's second config needs a chassis rebuild (680); Run 3 unchanged. Cluster 0.9.125. @cplong90: `inputs_hash` can condemn but not clear a pin. New code not touching this path: viva-api#502/#504/#506, v2ecoli#744/#745 |
| 2026-09-08 | Alex: no collision with 683 — "go ahead" (22:05Z). Xarray root cause = viva-api `run_pbg._redirect_emitters` (#520, deployed 0.9.127; cluster rolled 0.9.126 → 0.9.127 for #513/#520). Alex's exact-match 4-gen re-fire (681) reached gen 3 clean. 683 at 60 min: 10/10 lineages RUNNING, 0 retries |
| 2026-09-08 | **Nextflow Run 2 dispatched: sim 683** (shape A on simulator 172; mirrors 666's spec with independent founders; parquet-only, gather in-campaign). Announced on #166 |
| 2026-09-08 | **Alex's Run 2 (sim 666) FAILED 21:08Z** — the 665 xarray bug at the generation-4→5 boundary (seed 6, `emitstep_gen=4` missing). My "not exposed" claim retracted on #166 with the traceback; parquet history 0–4 for all 10 seeds is intact. v2ecoli#746 merged (`7cb19315`) |
| 2026-09-08 | Phase 5 pass while 666 runs: v2ecoli#746 (16 lineage knobs declared — G closed), viva-api#514 (#484), viva-api#515 (e2e opt-in). Run 2 hedge command pre-staged in both shapes with `exchange_fluxes` in `injected_processes` |
| 2026-09-08 | 20:40Z: answered @cplong90 and @AlexPatrie on #166 with measurements — 666 is parquet (not xarray-exposed); 679 omitted `exchange_fluxes` (gap 1, mine — must ride in `injected_processes` on this path); `cd1_exchange_fluxes` hard-binds `external_exchange_fluxes`, absent even on 666 (gap 2, the redux binding, @eagmon). Hedge offer for a Nextflow Run 2 replication stands |
| 2026-09-08 | **sim 679** (`sim172-exch-verify-2x1-6add`, simulator 172 = sms-ecoli `7e7fce1` / v2ecoli `e4db5e67`) COMPLETED 19:34Z: image validated for Run 2 — 10 analyses `ok`, gather **succeeded first try at 32 GB** (#495 live), 101 objects / 678 MB. `cd1_exchange_fluxes` still 10/11: schema read shows redux emits `estimated_exchange_dmdt__*`, never `external_exchange_fluxes` (classic does). Redux binding → @eagmon |
| 2026-09-08 | Team status (Alex, [sms-ecoli#166 at 15:04Z](https://github.com/CovertLabEcoli/sms-ecoli/issues/166#issuecomment-5587273617), MNP path): Run 1 coupled **10/10 proven**, content-verified; Run 4 `minimal` **42/42** and `_with_trp` **41/42** (genotype 7: `NegativeCountsError`, WATER in `ecoli-rna-degradation`, to the science team); Run 1 cell-only and Run 2 blocked on **stale founder caches** (old v2ecoli pin) — fresh chassis rebuilding; Run 3: #741 now surfaces two real bugs (Eran's). Chris on the Run 1 data: "looking great so far" |
