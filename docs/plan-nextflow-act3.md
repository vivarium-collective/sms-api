# Nextflow dispatch, act 3: all four CD2 workloads on the Nextflow path

**Status (2026-09-09 05:05Z): PHASE 1 (Run 4) waits on Alex's cache rebuild at `6299ba5` (eagmon confirmed the real scale is 4 × 8 × 84); PHASE 3 (Run 1 cell-only) pilot running as sim 734 on simulator 173 after 732 exposed that pre-#746 images reject the top-level knobs.** Act 2 closed gates 4 and 1b and
put the real Run 2 shape on the path (sim 683, 10 × 8, independent founders, gather
in-campaign — still running). This act takes the other three workloads across, in
the order that risks least and proves most, **without touching any other dispatch
mechanism**: every change lands in `workflow_nf.py` / `lineage_step.py` / the
Nextflow renderer / viva-api's `K8S_NEXTFLOW` branch, or in a planner script that
never talks to the API. `lineage_ray_batch`, `mbp_dispatch`, chain dispatch and
`run_pbg.py` are out of bounds for this act. First deliverable landed:
`scripts/cd2_nextflow_dispatches.py` (the translator).

> Companion to [`plan-nextflow-dispatch.md`](plan-nextflow-dispatch.md) (act 1, the
> design and gate table) and [`plan-nextflow-act2.md`](plan-nextflow-act2.md) (act
> 2, the execution record). Same house style: status first, corrections inline.

---

## What the team runs today, and what the Nextflow path already has

Surveyed 2026-09-09 from `sms-ecoli/scripts/dispatch/cd2/run{1..4}-local.sh` (the
byte-for-byte mirrors of the real container commands), `gen_cd2_cellonly_dispatches.py`,
`build_run4_founder_caches.py`, the four `configs/cd2/run*.json`, and viva-api's
builders.

| Run | Path today | Sweep dimension today | On `workflow_nf` |
|---|---|---|---|
| **2** J3 (violacein) | `lineage_ray_batch`, ten dispatches of one (one founder cache per seed) | per-seed founders | **done as one campaign** — sim 683: ten seeds, `--independent-founders`, or ten one-seed variants with per-variant `cache_uri` |
| **1** K4 cell-only | same as Run 2 | per-seed founders (`…-founder-seed{N}` at commit `ca79191f`) | same shape as Run 2; nothing new |
| **1** K4 coupled | `mbp_dispatch` → `run_mbp_tracked.py --variant reactor-bird-coupled-batch-multigen` | per-seed founders, one job each | **not a lineage** — would need a new `MbpStep`. Deferred: works on MNP today (669 proven) |
| **4** FSS genotypes | `lineage_ray_batch`, **one dispatch per (genotype, medium)**: `{"media", "n_seeds": 1, "n_generations": 2}`; identity lives entirely in the cache `cd2-run4-carina-genotype{N}` | 42 caches × 2 media = 84; config B 16 × 2 = 32 | variants with per-variant `cache_uri`, one campaign per medium (`media` knob). **The 336-scale gather is the unknown** |
| **3** cocktail (mecillinam/sulfadiazine) | chain dispatch on `ecoli_baseline`, nested `injected_processes` (`add_processes` ×8, `process_configs`, `seed_bulk_species`, …) | **none** — `field_timeline.timeline` is `[]`; vEcoli's variants grammar is un-ported | nested block rides per variant unchanged; a dose sweep is *expressible* here via per-variant `injected_processes_patch` — a capability MNP lacks. The private vEcoli fork is a **build-time** image flag (`simulator latest --stage-private-fork --vecoli-private-commit`), so tasks inherit it with no Nextflow change |

What `workflow_nf` already declares (v2ecoli `f0274348`+): `n_seeds`, `n_generations`,
`variants[]` (each: `variant_name`, `new_genes`, `bundle_overrides`, `cache_uri`,
`injected_processes`, `config_overrides`), `cache_uri`, `independent_founders`,
`analysis_options`/`include_analysis`, `media`, `emit_paths`, `exchange_fluxes`,
`exchange_flux_basis`, `time_step`, and the rest of the 16 lineage knobs (#746).

## The translator — `scripts/cd2_nextflow_dispatches.py`

A **planner**: reads the team's workflow-schema config, applies viva-api's *own*
readers (`injected_processes_from_config`, `analysis_modules_for`) and prints the
exact `atlantis composite nextflow …` command plus the `--params` JSON. It never
calls the API, so the dispatch stays on the proven CLI path and it cannot affect the
other dispatchers. Verified on all four configs, including Run 3's nested block.

```bash
# Run 4, minimal medium, genotypes 1..42 (the strain IS the cache):
uv run python scripts/cd2_nextflow_dispatches.py --run 4 --sms-ecoli ../sms-ecoli \
  --simulator 181 --label fss-minimal --cache-commit <commit> \
  --cache-template 'cd2-run4-carina-genotype{n}' --cache-range 1-42 --media minimal
# Run 1 cell-only, ten one-seed variants from DI's founder mapping:
uv run python scripts/cd2_nextflow_dispatches.py --run 1 --sms-ecoli ../sms-ecoli \
  --simulator 181 --label k4-cellonly --founders out/founder_ensemble_mapping.json
# Run 3, a two-dose pilot (the patch content is met-eng's):
uv run python scripts/cd2_nextflow_dispatches.py --run 3 --sms-ecoli ../sms-ecoli \
  --simulator <private-fork image> --label mec-pilot --variants-json '[...]'
```

Refusals built in: `experiment_id` present in the config (it must stay absent,
sms-ecoli#235), several seeds per founder-cache variant without independent founders
(v2ecoli#693), `PENDING` founder caches, duplicate variant names.

## Phases

| # | Phase | Risk to other paths | Proves |
|---|---|---|---|
| 0 | **Run 2 depth + auto-gather** — sim 683 (running) | none | 8 generations on parquet; the gather at 10 sweeps |
| 1 | **Run 4 pilot**: 3 genotypes × 1 seed × 2 gens on 181, `media=minimal`, then `minimal_plus_tryptophan` | none (translator + existing knobs) | per-variant caches fetch; `media` reaches the lineages; `multivariant` analyses gather across variants |
| 2 | **Run 4 at scale**: 42 × 1 × 8 per medium (84 lineages/campaign), then 4 seeds if wanted (168 → 336) | none; watch the gather's memory (`_scaled_memory`, 32 GB base) and `list_jobs` pagination in the cancel reconciler (already paginated, #481) | the 336-scale gather |
| 3 | **Run 1 cell-only**: 10 one-seed variants on the `ca79191f` founder caches, 10 gens | none | the K4 arm on this path; 11/11 KPIs on 181 |
| 4 | **Run 3**: build a simulator with `--stage-private-fork --vecoli-private-commit <Chris/Mia's commit>`; 1 × 1 pilot with the nested block; then a dose grid via `injected_processes_patch` | none (image flag exists; per-variant injection exists) | the cocktail on this path; the first dose sweep anywhere |
| 5 | **Run 1 coupled** (optional): an `MbpStep` wrapping `run_mbp_tracked.py` | additive only | parity with `mbp_dispatch` |

Gates, in act-1 style: a phase closes only when the campaign's `analysis/` publishes,
every expected `lineage_seed=`/`variant=` partition is present with real history
(>1 column, >0 rows — #475's criterion), and the KPI analyses report `ok`.

## Known risks, stated up front

- **Cache/image commit mismatch.** A `cache_uri` fetch bypasses the schema-3 key, but
  a cache built under an older v2ecoli can still be refused at load. 683 runs a
  `2fddfcb8` cache under image 172 (`e4db5e67`), so at least that span works.
- **The gather at 84–336 sweeps.** 574 needed 32 GB for 3; scaling is unmeasured.
  `_scaled_memory` retries at 2×; the resource label is overridable per dispatch.
- **Run 3's private fork** is a build-time choice per simulator; a campaign on the
  wrong image fails at `!ParameterSerializer[...]` resolution, loudly.
- **`media` names** must be a condition in the cache's `saved_media`.

**Sequence:** [act 1](plan-nextflow-dispatch.md) (design + go/no-go gates) → [act 2](plan-nextflow-act2.md) (gate 4 / 1b closed, blockers, Run 2 on the path) → this document.

## Progress log

| date | event |
|---|---|
| 2026-09-09 | Survey of the four workloads' real dispatch shapes (mirrors, generators, cache builders). Run 4's identity is the cache; Run 3 has no dose sweep today; Run 1 coupled is not a lineage |
| 2026-09-09 | Translator written with 9 tests; verified the API's own config readers on all four CD2 configs. Phase 1 pilot command generated for genotypes 1–3 |
| 2026-09-09 | **Phase 1 fired: sim 724** (`run4-pilot-3g`, simulator 181): genotype caches 1–3 from `ray-parca-cache/b3b4a628a2aea8afe6f9524b6de65c657ff23475/` (the prefix holding all 43 Run 4 caches; `9ce3135` holds 42 more), 1 seed × 2 gens, `media=minimal`, the config's full `multivariant`/`multiseed`/`multigeneration` analysis set, exchange fluxes on. Command generated by the translator verbatim. Translator #533 merged (`30f9ade7`), plan #534 merged |
| 2026-09-09 | **sim 724 FAILED 03:25Z — infrastructure, not the path.** Nextflow rendered three variants and submitted `parca_v0/v1/v2` (cache fetches); `parca_v0` succeeded; `parca_v1`/`parca_v2` failed 4× each with `CannotPullContainerError: … no space left on device` and the head Job hit its backoff limit. Diagnosed by SSM: the spot host running seven of 683's lineages had a **30 GB root at 98 %** (17 GB = the running lineages' own writable layers, 11 GB = one simulator image, nothing reclaimable); the other host was at 79 % with 6.6 GB free — also too small for an 11 GB pull. Launch template `lt-06346ca86b6cec29b` has no block-device mapping |
| 2026-09-09 | Fix applied online (no restart): `modify-volume` both roots to 120 GB + `growpart`/`xfs_growfs` via SSM → 98 % → 26 %, 79 % → 21 %. 683's lineages were one generation from ENOSPC. Durable fix filed as sms-cdk#48; team told on #166. **Re-fired as sim 725** (same translator command) |
| 2026-09-09 | Also this hour, not act 3 but relevant: my viva-api#525 under-run guard refused every chain-dispatch job (Run 3's 720/721): `ecoli_baseline` declares `n_generations` yet runs `-n 1` + `stop_at_division` per generation. @AlexPatrie root-caused and fixed it (#536, exempt `stop_at_division`, bump to 0.9.129). `run_pbg.py` is staged from the api pod, so it needs a roll — overlays bumped and rolling now |
| 2026-09-09 | **sim 725 FAILED 03:40Z — the first act-3 risk, exactly as stated.** Cache fetches all succeeded (disk fix confirmed), render correct (`parca_v{0,1,2}` → `lineage_v{0,1,2}_s0`), then `StaleCacheError: inputs_hash mismatch; files differ: [_helpers.py, ecoli_baseline.py, reactor_bird_coupled.py …]` in every lineage: the caches are from sms-ecoli `b3b4a628` (simulator 166, v2ecoli `2e54e95a`); 181 is `ad5f2f3a`. Same rule as MNP. 166 predates #736/#739/#742 so cannot gather. Route: rebuild the 42 caches at the current commit (`build_run4_founder_caches.py`: one ParCa + 42 deep copies). Asked Alex on #166 (he owns the numbering). 0.9.129 rolled and verified (`stop_at_division` marker on the pod) — Run 3 re-fire unblocked |
| 2026-09-09 | **Team state 02:55–05:00Z** (read from GitHub): eagmon confirmed **Run 4 = 4 seeds × 8 gens × 84 genotypes** (the 116 "done" dispatches were a 1×2 pilot) → Alex rebuilding the chassis (Dispatch 729 on 181; its ParCa landed in the `cd2-run1-k4-chassis/` variant slot, 181's stock slot is untouched — no collision) then the 42 genotype caches at `6299ba5`; he asked me to hold off minting a parallel cache set, so the Nextflow Run 4 campaign will use his rebuilt caches on 181. **Run 2 reopened** (681 had one shared founder, 4 gens) → Alex re-fired 10×10 with per-seed founders (728/730/731/733); Chris: nothing needs rebuilding. **Run 3**: sms-ecoli#299 (Alex) generates the real 36-combo mecillinam×sulfadiazine configs, one dispatch per point; eagmon's audit says the ports are faithful but *no drug dose reaches the cell* and the sulfadiazine kill mechanism is missing from native metabolism — a science blocker with no owner yet; Bug B (`AmbiguousLookupError`) confirmed fixed on 0.9.129. **Run 1 coupled 10/10 complete**, all content-verified. eagmon opened viva-api#542 for the same ParCa-list 500 as my #541 (reconciled on his PR) |
| 2026-09-09 | **Pivot to phase 3 while Run 4 waits.** Run 1 cell-only's ten founder caches (`…founder-seed{0..9}` at `ca79191f`) match simulator **173** (v2ecoli `e4db5e67`: has #736/#739/#742, not #746). Translator gained: fluxes inside every variant's injection block (#544, merged) and `--legacy-image` (#546) after **sim 732 failed at render** — on a pre-#746 image `to_document` *raises* `KeyError: unknown override(s): ['exchange_flux_basis', 'exchange_fluxes']` rather than swallowing them. **Re-fired as sim 734** (founders seed0/seed1 × 1 × 2 gens, legacy mode) |
| 2026-09-09 | 683 at 05:00Z: 7 of 10 lineages finished, s1/s6/s7 still running (7 h 15 m in); the 32 GB gather follows |
