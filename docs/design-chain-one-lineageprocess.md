# Design: chain dispatch runs a whole lineage in ONE LineageProcess

**Status:** DESIGN — awaiting sign-off before implementation.
**Owner:** (advance_generation #38 / driver adoption #761 author)
**Motivates:** Run 3 (mecillinam+sulfadiazine) dose never delivers on chain dispatch.

## Problem (confirmed, data + code)

Chain dispatch submits **N seeds × G generations = N·G separate Batch jobs**, one
per `(seed, generation)` (`_seed_generation_command`, `n_generations=1`,
`initial_generation_index`, S3 daughter-state checkpoint between jobs). Routing:

```
# simulation_service_ray.py:2849-2856
composite = getattr(config, "composite", None)
n_generations = int(config.generations or 1)
if composite is None and n_generations > 1:
    return await self._submit_chain_dispatch_background(...)   # <-- per-gen jobs
```

Each job is a **fresh `LineageProcess`** (`v2ecoli/workflow/lineage.py`). The
`field_timeline` injected process fires an entry when
`local global_time + lineage_time_offset >= scheduled_time` (sms-ecoli
`field_timeline.py`). `lineage_time_offset` is a **process-level accumulator**:
it starts at 0.0 and accumulates the summed prior-generation durations **within
one LineageProcess** (`lineage.py`), and each generation's inner `global_time`
restarts at 0 (`run_pbg.py`).

Because chain dispatch runs one LineageProcess **per generation job**, the offset
resets to 0 on every job → `field_timeline`'s `DOSE_ONSET_TIME_S=10000`
(cumulative-lineage) entry is compared against a per-generation clock that only
reaches ~2500-3140 s → **it never fires, at 8 or 20 generations.** Every Run 3
chain sweep is a silent no-dose control.

**Verified from S3 (sim186, 2026-09-09):** all 36 cocktail combos show
`mecillinam[p]=0`, `CPD-20940[c]=0`, byte-identical FBA fluxes control-vs-dose,
identical growth. Generations reset global_time (gen0 0→2528, gen1 0→2806,
gen2 0→3140); cumulative 3-gen = 8474 s < 10000 s. (Under-scale AND per-job
reset both keep it under onset; this fix removes the per-job reset permanently.)

The Nextflow path already runs all generations in one LineageProcess, so the
offset accumulates and the dose fires there — this change brings chain dispatch
to **parity**, not novelty.

## Approach

Two coupled changes; (1) is the correctness fix, (2) is Eran's "same emitter"
durability ask (parity with #761).

### (1) sms-api — route the non-composite multi-gen shape to ONE LineageProcess job per seed

The one-job, all-generations shape already exists: `_sim_command` with
`n_generations > 1` (line 2046) dispatches `run_pbg.py --composite-id
<batch_baseline>` with `{n_seeds, n_generations, ...}`, which
`ecoli_baseline.baseline()` runs as a single multi-generation LineageProcess.

Change `_submit_chain_dispatch_background` so a `(composite is None,
n_generations>1)` request submits **one job per seed** (or one N-seed job)
running all `n_generations` in one LineageProcess — instead of the per-generation
job loop. The offset then accumulates across generations exactly as Nextflow.

Sub-decisions (see Open Questions):
- **A. Reuse the existing batch_baseline one-job path**, or **B. keep
  `_submit_chain_dispatch_background`'s per-seed structure but submit one
  all-generations job per seed.** Prefer whichever preserves the chain path's
  per-seed injected_processes/variant passthrough and analysis-DAG wiring with
  the least surface change.

### (2) v2ecoli — LineageProcess uses ONE advance_generation emitter across generations

`LineageProcess` currently builds a fresh `XArrayEmitter` per generation
(`_build_emitter` @260) and `close(success=True)` per generation (@369). Migrate
it to the #761 pattern: build once, `advance_generation(agent_id=…,
success=True)` at each division, terminal `close()`. This is Eran's "same
emitter, launch a new internal ecoli model per generation," and gives the
lineage per-generation durability (each gen flushed+consolidated before the next
opens; a long job that fails at gen N retains gens 0..N-1) — which matters now
that one job runs the whole lineage.

Note: the offset/dose fix (1) works WITHOUT (2) (offset is process-level). (2) is
the durability + consistency improvement Eran explicitly asked for.

## Scope / careful items (live-critical dispatch path)

1. **Job timeout + resources** now cover a FULL lineage (like Nextflow), not one
   generation — size the Batch job's timeout/vCPU/memory accordingly.
2. **Daughter-state handoff becomes in-process** (LineageProcess divides
   internally), so the inter-job S3 daughter-state checkpoint machinery
   (`RayLayout.daughter_state_uri`, `initial_carry_state_path`/
   `daughter_state_out_path`) is bypassed on this path. Identify every consumer
   (chain-dispatch resume, analysis daughter grouping, chain progress) and
   migrate or gate — don't break them.
3. **Memory stays bounded** because advance_generation flushes+consolidates per
   generation (no whole-lineage buffer growth).
4. **Resume-from-generation** (nice-to-have, not required): per-gen durability
   makes a resume feasible, but a single long job is the simpler default. Decide
   whether to keep any resume capability.
5. **Verify the dose fires:** an end-to-end check that on the new path
   `lineage_time_offset` accumulates and a `field_timeline` entry at
   `DOSE_ONSET_TIME_S` fires around the expected generation.

## Deliverable

- sms-api PR (+ v2ecoli PR for (2) if kept) with a **test asserting a
  chain-dispatched multi-generation lineage accumulates `lineage_time_offset`
  and fires a `field_timeline` entry at the dose onset** (unit-level on the
  command/dispatch shape + the LineageProcess offset threading; a full Batch run
  is the integration check).
- help-team review; Eran approves the merge.

## Open questions (resolve during implementation)

- Approach A vs B above (reuse batch_baseline path vs one-job-per-seed in the
  chain path). Needs reading `_submit_chain_dispatch_background` end-to-end plus
  its analysis-DAG / chain-progress wiring.
- Do we include (2) in this change or land it as a fast-follow? (Offset fix is
  independent; "same emitter" is Eran's explicit ask, argues for including it.)
- Daughter-state consumers to migrate/gate (item 2) — full list before editing.
- Resource sizing numbers for the full-lineage job (match Nextflow's).
