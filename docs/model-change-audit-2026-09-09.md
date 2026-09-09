# Model-change audit: v2ecoli and sms-ecoli (2026-09-09)

**Question asked (Jim, 2026-09-09):** have changes been made to the *model itself* — equations, parameters, defaults, media data, and the declared input/output relationships between processes — as opposed to workflow, dispatch, emitters, analysis, tests and tooling? There may be no clean separation; where the boundary is blurry is itself part of the answer.

**Who this is for:** Eran Agmon and Chris Long, the people. The two repos' commit history is largely Claude sessions posting under the team's GitHub logins, so "reviewed under login X" below never means "a human read it".

**Method.** Two independent auditors (one per repo, same rubric) walked every commit on `main` — v2ecoli from the April port (`68e4c12ab`, 2026-04-10) to today; sms-ecoli's full history — classified every commit touching a model path by reading its diff, and recorded reviews per PR. Categories: **A** model semantics changed (equations, rate laws, objective terms, constants, result-changing defaults, media/condition data, ParCa fitting, initial state, division rules, which processes run); **B** declared process interfaces or wiring changed (ports, topology, injected processes, new stores, forced-bound hooks); **C** opt-in behind a knob with defaults unchanged; **D** mechanical; **P** ParCa/reconstruction port (v2ecoli); **E** experiment design (sms-ecoli). Robustness that changes a result on a path that previously crashed is counted as A, and the reports say so where it applies. This document is the merged executive summary; the two full reports follow as appendices with every commit listed.

## Headline findings

1. **v2ecoli: 1,698 commits (705 at PR level); 261 touch a model path — A 35, B 37, C 29, P 22, D 138**, plus three A-grade commits living entirely under `v2ecoli/workflow/`. Almost no equation was edited after the port settled: rate-law/stoichiometry/constant edits inside core process files are in the single digits. The model changed in four other places instead — **ParCa/reconstruction parameters, the environment↔reactor coupling, the injection harness (whether a declared perturbation reached the cell at all), and composite wiring/defaults.**
2. **sms-ecoli: 1,426 commits in two eras.** Until 2026-08-27 (#127) it *was* the v2ecoli repo (514 commits under a vendored `v2ecoli/`, 27 of them bulk `sync:` imports — not auditable from subjects). In the dependency era, **45 commits touch model paths — A 23, B 7, C 1, D 9, E 5**, plus two A-in-effect commits outside model paths (#191: 23 configs had silently run wild-type; #313: `--aeration-schedule` wrote a dead key, Run 1 ran flat at exit 0).
3. **Review coverage is thin.** v2ecoli: of ~72 A/B commits, six carry any cross-login review or comment; no PR under `eagmon` carries a review under `cplong90`; the whole April–May port era (21 A/B commits, incl. the per-process RNG-seed change and the EcoCyc 29.6→29.1 rollback) went in as direct commits with no PR. sms-ecoli: only 2 of 30 A/B commits carry any GitHub review; the rest were merged by their own author.
4. **Pin bumps are model changes in disguise.** sms-ecoli has 28 v2ecoli bumps since 2026-09-04 (the pin floated on `main` the first week). Two are model-semantic and say nothing about it: #305→#307→#310 is a revert-and-reland of the `imposed_flux_bounds` hook, so #306's DHPS process is inert on any pin before `fa99c6e9` — the same config yields different biology depending on the pin; and #280 carries the upstream half of the ParCa `flat_overrides` (#738). Seven `ecoli-sources` bumps carry reconstruction data; #301's own text notes that pinned package is a stale snapshot carrying 5 of the 51 BAD_RXNS.
5. **Two specific items for the scientists (v2ecoli):** (a) #669's subject says "landed ATP-synthase respiration fix" but no ATP-synthase change is on `main` — `atp_synthase_reverse_cap` was tried and withdrawn in-branch ("the defect is STOICHIOMETRIC"); the biomass-yield/respiration defect is open. (b) The DnaA revert (#244) was partial — the execution layers came out, but the 307→315 DnaA-box initial state, the equilibrium ports/hydrolysis flux and the dnaA autoregulation term remain on `main`; the initial-state change is not gated.
6. **Today's changes (2026-09-09), for the record:** v2ecoli #753 (DHPS in Metabolism, reverted by #755), #755 (generic `imposed_flux_bounds` input on Metabolism — B), #758 (`environment` emit path on the coupled composite — emit-only, but it is a hashed cache input), #761 (xarray lineage emitter — emitter-only). sms-ecoli #297 (LP solver fallback — A where it engages), #301 (51 BAD_RXNS zeroed unconditionally, was `[]` — A), #303/#306 (sulfadiazine transport + injected DHPS — A/B), #304 (well-mixed field floored at 0 — A), #308 (plain FBA objective, opt-in, default `classic` — C), #309/#312 (Run 3 scale and generator base config — E/A), #313 (aeration mount — A in effect), #314 (pg-maturation skips a non-integrable tick — A where it previously crashed).

## Where the model/non-model boundary is blurry (both auditors, condensed)

There is no clean separation, and the reason is structural: v2ecoli expresses biology as *wiring*, so a wiring change is a biology change and the same file holds both. `ecoli_baseline.py` (2,406 lines) is at once the model definition and the dispatch config — `BASE_EXECUTION_LAYERS`, which decides what runs, sits near S3 paths and Ray knobs; the DnaA episode was a five-line edit there. `_helpers.inject_flow_dependencies` turns wiring into execution order through a `priority` integer (#543: injected steps tied at 1.0 made the *same build* pass and fail across runs). The two `inject.py` files (3,282 lines) are nominally a comparison harness and in practice decide what the model is. Division is spread across four files, one of which (`workflow/lineage.py`) the rubric calls non-model yet holds three A-grade commits. The reactor/environment steps contain no rate law but decide the concentration the cell is told it is in, and several of their fixes were *type declarations* (`map[float]`→`overwrite[…]`). ParCa is a "port" bucket but a ParCa change is a parameter change. In sms-ecoli, `configs/` is simultaneously model and experiment (one CD2 JSON holds injected processes, `flow` order, kinetic parameters, seeded species, the ParCa bundle, the dose schedule, the seed/generation scale *and* the analysis list); `bridge/` generators are model authorship (94 lines define Run 3's independent variable); and runners can silently un-apply a declared model (#191, #313), which makes the most dangerous commits the ones *not* in a model path. No media or condition data is defined in sms-ecoli at all — media changes reach CD2 invisibly through the pins. The one clean boundary is emitters and analyses: those only change what is recorded.

## What the auditors could not verify

The initial v2ecoli port (+8,707/−4,672) and the v2parca vendoring (+188,866 lines) are unverifiable from this repo; two commits move defaults into binary dill pickles; #138 deleted ~149k lines of flat data to an external bundle whose byte-identity cannot be checked; #89's "bit-identical" claim is a 0.5 %-tolerance benchmark; and the sms-ecoli vendored era is opaque to subject-level audit.

## Engineering suggestions (process, not model)

These are about how changes flow, not what the model should be: (1) treat `ecoli_baseline.py` execution layers, `inject.py`, `injection_topologies.py`, `configs/cd2/*.json` `process_configs`, `bridge/`, and every `INPUT_FILES` member as **model-bearing paths** that require a review by the other scientist's login before merge; (2) require a pin-bump PR to name the model-semantic commits it imports (the DHPS hook revert/reland is the cautionary example); (3) record the simulator id and both repo commits in `run_identity.json` (the same provenance gap Chris and eagmon raised today), so "which model ran" is answerable from the artifact; (4) add a rendered-document structural test that the set of processes and ports in a built baseline matches a checked-in manifest, so a wiring change cannot land silently.

---

# Appendix A — v2ecoli full report

## v2ecoli: which commits changed the biological model?

**Audit target:** `origin/main` of `vivarium-collective/v2ecoli`, from the initial commit
`68e4c12ab` (2026-04-10, *"Initial v2ecoli: pure process-bigraph partitioned E. coli model"*)
to the tip `8ab975971` (2026-09-09, `#761`).
**Method:** read-only `git log` / `git show` / `git diff` at the **first-parent** level, so each
row is one squash-merged PR or one true merge commit. Diffs were read for every A/B candidate;
subject lines alone were never used to classify. Nothing was pushed, checked out, or posted.

---

## 1. Totals

| quantity | count |
|---|---|
| commits in range (all, incl. branch commits) | **1698** |
| non-merge commits | 1457 |
| merge commits | 241 |
| **first-parent commits (the PR/direct-commit level this audit works at)** | **705** |
| **first-parent commits touching a model path** | **261** (37%) |

Model paths counted: `v2ecoli/processes/**`, `v2ecoli/steps/**`, `v2ecoli/composites/**`,
`v2ecoli/cell_shape.py`, `v2ecoli/library/{sim_data,schema,division,vivarium_bridge,cache_version,initial_conditions,make_media,upstream_division,inject}.py`,
`v2ecoli/data/**`, `scripts/_compare/inject.py`.

### Category counts (of the 261)

| category | count | share |
|---|---|---|
| **A** — model semantics changed | **35** | 13% |
| **B** — declared interfaces / wiring changed | **37** | 14% |
| **C** — opt-in, defaults unchanged | **29** | 11% |
| **P** — ParCa / reconstruction port | **22** | 8% |
| **D** — mechanical / non-semantic | **138** | 53% |

Of the 22 **P** commits: 6 are semantics-changing (`P-A`), 4 opt-in (`P-C`), 1 interface (`P-B`),
11 mechanical (`P-D`). The 6 `P-A` commits are listed in the A table below, since a ParCa
parameter change is a model change by any reading a biologist would accept.

Three further **A**-grade commits live *entirely outside* the nominal model paths, under
`v2ecoli/workflow/` — they are listed in the A table and marked ⚠. They are not counted in the
261 (that is the point of §4).

**Author distribution of the 261** (git author, not necessarily the person — see §6 on logins):
Eran Agmon 181 + "Eran" 32 = 213, cplong90 26, Jim Schaff 14, A.P. (Alex Patrie) 8.

### The headline finding

**Almost no equation in the whole-cell model was ever edited.** Across all 261 model-path
commits, the number that altered a rate law, stoichiometry, or kinetic constant inside a core
biological process file (`transcript_initiation`, `transcript_elongation`,
`polypeptide_initiation`, `polypeptide_elongation`, `rna_degradation`, `rna_maturation`,
`protein_degradation`, `complexation`, `equilibrium`, `chromosome_replication`,
`chromosome_structure`, `tf_binding`, `tf_unbinding`, `two_component_system`, `metabolism`)
is in the **single digits** after the April port settled — and every one of those is listed
in §2.

Where the model *did* change, it changed in four other places:

1. **ParCa / the reconstruction** — parameter values and fitting logic (`P-A`).
2. **The environment ↔ reactor coupling** — what concentration the cell is told it is in.
3. **The comparison/injection harness** — whether a declared perturbation actually reached
   the cell at all.
4. **Composite wiring and defaults** — which processes run, and what daughters inherit.

---

## 2. Every A and B commit (most recent first)

**Review column:** counts GitHub reviews/comments left by the logins `eagmon` and `cplong90`
on that PR, *excluding the PR author's own*. Both people's Claude sessions post under the same
logins, so this says **"reviewed under login X"**, not "a human read it". `—` = no PR number in
the subject (direct commit to a branch that was merged).

### A — model semantics changed

| sha8 | date | author | PR | files | what changed | review |
|---|---|---|---|---|---|---|
| `6c00a11fd` | 2026-09-04 | Eran Agmon | #683 | `composites/ecoli_baseline.py` | Threads `cache_dir` into the injection spec. A swapped **MetabolismRedux** previously got an **empty config — 0 metabolites, 0 homeostatic targets** — collapsed after one tick, and still reported success. Perturbed runs now compute real metabolism. | none |
| `5add30cf9` | 2026-09-04 | cplong90 | #679 | `steps/reactor_cell_coupler.py` | The cell's **dissolved-O₂ view** is published *after* this tick's consumption. Before, it read the top of a sawtooth = exactly one tick of O₂ transfer (0.0011881823 mM, 118.8× above metabolism's 1e-5 import threshold), so a cell in an anoxic reactor was told O₂ was available forever, and **O₂ availability scaled with the integration timestep**. CO₂/glucose/ammonium deliberately not changed. | none |
| `9785729c0` | 2026-09-02 | Eran Agmon | #653 | `scripts/_compare/inject.py` | `pbg_native` injected stores are now created carrying their **declared `_type`**, so an `overwrite[…]` output composes forward. Before, the `field_timeline → fields → well_mixed_field → boundary.external` drug-delivery chain was **inert** and the transport process read `external=None → NaN`. Also applies a config `initial_state` on that path. | none |
| `268515f0d` | 2026-09-02 | cplong90 | #638 | `steps/reactor_cell_coupler.py`, `composites/reactor_bird_coupled.py`, `steps/environment_mirror.py`, `library/cache_version.py` | Medium **ammonium becomes a finite, drawn-down pool** published to `environment.external_concentrations` as `AMMONIUM[c]` (new default `ammonium_medium_mM = 60`; the cell previously read the static 30.272 mM recipe value and could never exhaust it). Also declares a new `kla_co2` store leaf (a B-change). Behaviourally inert above the 1e-5 mM import threshold — but exhaustion is now a one-tick cliff. | rev:eagmon×1 |
| `63cd60f76` | 2026-09-02 | cplong90 | #648 | `composites/ecoli_population.py`, `reactor_bird_coupled.py` | `injected_processes` now threaded through the **population** and **reactor-coupled** composites. Before, those two paths built whatever metabolism the cache defaulted to, so an injected heterologous pathway was **never in the slot**, nothing raised, and the trajectory still looked plausible. | cmt:cplong90×1 (self), rev:eagmon×1 |
| `0c76bb542` | 2026-09-01 | Eran Agmon | #640 | `composites/ecoli_baseline.py`, `steps/batch_baseline_runner.py` | **Batch mode** (`n_seeds>1` or `n_generations>1`) silently dropped `injected_processes`, `features`, the four feature toggles (`ppgpp_regulation`/`trna_attenuation`/`supercoiling`/`mass_conservation`), `exchange_fluxes`, and both PDMP initiation modes — **every generation was built basal**. Single-cell runs were unaffected. | cmt:cplong90×1 |
| `167668af5` | 2026-08-31 | cplong90 | #632 | `steps/reactor_cell_coupler.py` | The coupler read `agents.*.environment.exchange` as a per-tick delta when it is a **lineage-cumulative total**, so the reactor drained by *elapsed time*, ~N/2 too much over N ticks (apparent yield 0.0006 g/g against a ~0.54 ceiling). Now differenced per agent. **Coupling error 1000× → 1.6×.** The test that certified the coupling contained the same error and could not fail. | none |
| `44bd8ea15` | 2026-08-30 | Eran Agmon | #591 | `steps/lineage_bookkeeper.py` (new), `composites/ecoli_population.py`, `reactor_bird_coupled.py` | New `LineageBookkeeper` Step prunes the un-followed sibling and writes `lineage.doublings` **on the division tick**. Before, `PopulationAggregator`/`ReactorCellCoupler` integrated the wrong represented population for `chunk_boundary − division_tick` ticks, so **the reactor trajectory depended on `chunk`, an emit-cadence knob**. Active only when `single_daughters=True`; no-op otherwise. | cmt:cplong90×2 |
| `6bcc29d66` | 2026-08-28 | Eran Agmon | #623 | `composites/ecoli_baseline.py`, `_helpers.py`, `steps/division.py` | `config_overrides` now propagate to **daughter rebuilds**. Before, a variant / sensitivity-sweep / knockout perturbation applied to generation 1 only, and every daughter silently reverted to the unperturbed cached config. Breaks/fixes every multi-generation perturbation study. | none |
| `2ecb11cab` | 2026-08-27 | Eran Agmon | #610 | `library/division.py` | Division was inferred by **substring-matching `'divide'`/`'division'` in an exception message**, so a `ZeroDivisionError` ("float division by zero") was recorded as a genuine division — the generation reported `divided=true` after ~1 s and the real error was masked. Builtin computation errors are now excluded and re-raised. **Changes recorded lineage outcomes on any affected past run.** | none |
| `8f5580622` | 2026-08-27 | Eran Agmon | #612 | `processes/polypeptide_elongation.py`, `steps/partition.py` | `Evolver.update` now returns a `next_update_time` reschedule instead of `{}` when its paired Requester has not run — the `{}` read as a non-advancing 0.0 interval and **deadlocked the composite on fast-growth media**. This is a change to partition/scheduling semantics. Plus a pint-safe `aa_in_media` compare that previously *raised* on `with_aa`/`succinate` media. | none |
| `89e94aa37` | 2026-08-27 | cplong90 | #607 | `composites/vecoli.py`, `library/vivarium_ecoli_engine.py` | `agent_id` — **whose string length IS the fork's generation index** (`generation = len(agent_id)`) — was missing from `VivariumEcoliProcess.config_schema` and pinned to `"0"`. The genuine-vEcoli reference arm therefore ran **every generation as the founder**, and a config's staged induction (`induction_gen`) could never fire. Runs completed, every observable populated, metadata recorded the variant as applied. | none |
| `f2038e39a` | 2026-08-27 | Eran Agmon | #611 | `workflow/lineage.py` ⚠ *outside the nominal model paths* | `LineageProcess._build_generation` dropped `baseline()`'s feature-selection kwargs, so an arm setting `mecillinam=True` never enabled the `cell_geometry` deriver; `periplasm.global.volume` / `cytoplasm.global.volume` / `boundary.outer_surface_area` stayed at their 0-defaults and the antibiotic-transport unit conversion divided by zero. | none |
| `2fa846368` | 2026-08-20 | cplong90 | #548 | `processes/metabolism.py`, `steps/environment_mirror.py` | `exchange_data.constrained`/`unconstrained` redeclared `overwrite[…]` so the store **can drop a key** — which is how "max flux 0" is expressed. Before, a carbon source that fell below the import threshold kept its stale 20.0 mmol/gDCW/h cap and **the cell went on consuming a substrate that was gone** (measured in the plain baseline composite). Also: `unconstrained` leaked +18 entries/tick. | none |
| `25a6a7949` | 2026-08-21 | cplong90 | #568 | `processes/metabolism.py`, `steps/environment_mirror.py`, `steps/media_update.py` | `boundary.external` redeclared `map[overwrite[float[mM]]]` and **both writers switch from a delta to an absolute concentration**. Metabolism seeds 9 "unlimited" molecules at `inf`; no delta can move `inf` (`inf + −inf = NaN`), so O₂ and 8 others were **undrivable by any driver or reactor**. | none |
| `1e6ecc5a8` | 2026-08-21 | cplong90 | #550 | `steps/environment_mirror.py`, `reactor_cell_coupler.py`, `reactor_millard_env_bridge.py` | Three defects on the reactor→cell path: (1) `EnvironmentMirror` matched **zero** molecules every tick (compartment-tagged `OXYGEN-MOLECULE[p]` vs bare `boundary.external` keys) and failed closed *silently* — nothing the reactor computed ever reached the cell; (2) glucose had no bulk→cell path at all; (3) exchange scale `cells_per_agent → cell_count/n_agents` (was under-scaled by 2^doublings under `representative_doubling`). | none |
| `fdeb3243d` | 2026-08-19 | cplong90 | #539 | `steps/population_aggregator.py`, `steps/reactor_cell_coupler.py` | Biomass source `listeners.mass.cell_mass` → **`dry_mass`**: `total_biomass_gDW`, `biomass_concentration_gL` and `od600` all drop by the measured wet/dry ratio **3.3315**, and the coupler feeds that into the reactor. | none |
| `f98218a93` | 2026-08-19 | cplong90 | #535 | `scripts/_compare/inject.py` | Injected fork processes take their config from the **fork's** `LoadSimData`, not the installed vEcoli. 4 processes had silently lost keys, 3 had different values (one id list 51 vs 172 entries). Silent fallback is now a hard error. Injected/comparison runs only. | none |
| `3c5fe1a2c` | 2026-07-26 | Eran Agmon | #393 | `composites/__init__.py`, 8 `workspace/studies/*/study.yaml` | `condition` replaced by a real **`media`** param: `acetate → minimal_acetate`, `succinate → minimal_succinate`, `no_oxygen → minimal_minus_oxygen`, `with_aa → minimal_plus_amino_acids`. Four other studies fall back to `minimal`. **Media data values changed for those studies.** | none |
| `8d636e06c` | 2026-06-29 | cplong90 | #293 | `workflow/lineage.py` ⚠ *outside the nominal model paths* | Daughters inherited the mother's raw `environment.exchange_data` dict, losing the store's `overwrite` updater and falling back to an **accumulating** `map[float]`. `ExchangeData` writes the FBA import bound every tick, so in **generations ≥ 1 the glucose uptake bound ballooned** (`b0 + cap·tick`, thousands of mmol/gDCW/h within one generation), voiding every exchange constraint in daughters. Gen 0 unaffected. | cmt:cplong90 (self), rev:eagmon×1 |
| `7fca16ce7` | 2026-06-03 | Eran Agmon | #127 | `workflow/lineage.py` ⚠ *outside the nominal model paths* | `LineageProcess._run_until_division` looked the survivor cell up by `self._agent_id`, but the inner baseline composite always names its single cell `"0"` while `_agent_id` accumulates phylogeny suffixes (`"0" → "00"`). So generation 0 divided and **generations ≥ 1 never saw the `MarkDPeriod` divide flag** — they ran to `max_duration_per_gen` without dividing. The "only gen 0 divides" multigen bug. | none |
| `9675fe4f7` | 2026-06-27 | Eran Agmon | #289 | `library/sim_data.py`, `upstream_division.py`, `vivarium_bridge.py`, `cache_version.py` | **`media_timeline` is now derived from the condition's `nutrients`.** Previously setting `condition` alone left media at `'minimal'`, so every non-basal condition silently ran the *wrong media* — `no_oxygen` ran **aerobic**. | none |
| `29c4dc262` | 2026-06-24 | Eran Agmon | #271 | `steps/division.py`, `processes/transcript_initiation.py`, `parca/.../process/transcription.py`, `composites/baseline.py`, `_helpers.py` | Three semantic changes in one PR: (1) **`Division.d_period` defaults to `True`** — division fires on the D-period flag and the **dry-mass threshold is no longer consulted**; new `divide` port wired to `MarkDPeriod`. (2) **ppGpp TF scaling**: the hard `ppgpp_scale[==0] = 1` switch becomes a Hill gain `b²/(b+K)` with a new constant **K = 1e-11**. (3) ParCa ppGpp fit gains an `adjustment = 1` floor for genes in the `≤1e-10·max` dust band. | none |
| `bf60df0d4` | 2026-06-16 | Eran Agmon | #244 | `composites/baseline.py` | **Reverts the DnaA machinery out of `BASE_EXECUTION_LAYERS`** (layers 2/2b–2e: `dnaa_box_binding_listener`, `dnaa-box-binding`, `rida`, `ddah`, `dars`) one day after it landed default-on. The steps stay in the tree as dormant infrastructure. | none |
| `717b976af` | 2026-06-15 | Eran Agmon | #137 | `composites/baseline.py`, `processes/equilibrium.py`, `transcript_initiation.py`, `chromosome_structure.py`, `library/initial_conditions.py`, `locus_copy_number.py`, `steps/{dnaa_box_binding,rida,ddah,dars}.py`, `steps/derivers/dnaa_box_binding.py`, `steps/division.py`, `parca/.../replication.py`, `flat_overrides/dna_sites.tsv` (+5064) | **DnaA replication-initiation went ON BY DEFAULT** — the five steps were appended straight into `BASE_EXECUTION_LAYERS`, not behind a `FEATURE_MODULES` entry. `equilibrium.py` gains two ports and injects extra `DNAA-INTRINSIC-HYDROLYSIS-RXN` flux; `transcript_initiation.py` gains **dnaA autoregulation** (`promoter_init_probs[TU 2778] *= (1−s·f)`, `AUTOREG_STRENGTH=0.8`); `initial_conditions.py` goes from **307 → 315 DnaA boxes**. ⚠ The `baseline.py` half was reverted by `bf60df0d4` the next day; **the 315-box initial state and the process/ParCa edits were not.** | cmt:eagmon×1 (self) |
| `4c439bd0e` | 2026-06-06 | Eran Agmon | #128 | `steps/division.py` | Coerces `dry_mass` and `division_threshold` to plain fg floats. Per the commit's own account, the prior Quantity-vs-float comparison raised and was **swallowed by process-bigraph**, leaving `division_threshold` stuck on the string `"mass_distribution"` — **cells never divided**. Units plumbing in form; restoring division in effect. | none |
| `5e7f02a00` | 2026-06-06 | Eran Agmon | #123 | `processes/equilibrium.py`, `parca/.../process/equilibrium.py`, `flat/equilibrium_reaction{s,_rates}.tsv`, `getter_functions.py`, `library/{function_registry,sim_data}.py`, `parca/steps/step_05_fit_condition.py` | **No existing rate value changed** (0 rows differ). What changed: **2 new reactions added to the default equilibrium network** — `DNAA-INTRINSIC-HYDROLYSIS-RXN` (fwd 1.4e-05 / rev 1.0e-15) and `MONOMER0-4565_RXN` (fwd 1 / rev 1.0e-07); a new `integrate_dt` column and a **two-phase ODE solve**; `WATER`, `Pi`, `PROTON` added to the tracked molecule set; and `_moleculeRecursiveSearch`'s guard `val != 0 → val < 0`, which affects **all** multi-product reactions. | none |
| `e8d61b1d0` | 2026-06-18 | Eran Agmon | #275 | `parca/steps/step_02_input_adjustments.py` | **P-A.** `balance_translation_efficiencies` now strips the `[c]` compartment tag before matching group ids. Before, **no group ever matched**, so ribosomal-protein translation efficiencies were never averaged. ParCa output → sim results change. | none |
| `ebb3c7c0f` | 2026-08-06 | Eran Agmon | #468 | `parca/reconstruction/ecoli/sources.py` | **P-A.** Precedence flip: a variant bundle's generated keys now beat `parca_overrides.tsv`. Changes which file feeds ParCa — hence `sim_data` — for variant/KO bundles (e.g. a KO's corrected `dna_sites` is no longer clobbered back). WT bundles byte-identical. | none |
| `13bcc44a9` | 2026-08-24 | cplong90 | #590 | `parca/reconstruction/ecoli/knowledge_base_raw.py` | **P-A.** New-gene insertions now also join reactions / kinetics / operons / exchange sets, with a coordinate conversion and a collision guard. Shipped in-repo payloads unaffected; an external payload shipping those files gets materially different `sim_data`. | rev:eagmon×1 |
| `e9e4c6930` | 2026-08-01 | Eran Agmon | #446 | `parca/composite.py`, `step_09_final_adjustments.py`, `library/cache_version.py` | **P-A.** Default flipped to **fail-loud**: a failed mechanistic fit aborts instead of landing a partially-fit pickle; `load_cache_bundle` verifies on every call (`StaleCacheError`); `SCHEMA_VERSION` 1→2 **invalidates every existing cache**. Runs that previously succeeded with silently degraded ParCa output now abort. | cmt:eagmon×1 (self) |
| `a9cf24ed8` | 2026-09-07 | Eran Agmon | #738 | `parca/.../process/translation.py`, `knowledge_base_raw.py`, 3 new `flat_overrides/*.tsv` | **P-A — the clearest unconditional biological-parameter change in the recent history.** Three vEcoli-private reconstruction overrides become effective on *every* ParCa build: **pABA (`P-AMINO-BENZOATE`, 8.0e-6 M) and DHPPP (`CPD0-1080`, 1.0e-8 M) become homeostatic FBA concentration targets**; **TU0-941's measured RNA half-life is removed** so it is solved from cistron half-lives; and **MurD (`UDP-NACMURALA-GLU-LIG-MONOMER`) protein half-life is pinned to 1914.725 min at the *highest* priority** in the degradation-rate selection cascade (ahead of measured and pulsed-SILAC). | cmt:eagmon×4 (self) |

#### A commits from the April–May port era

None of these went through a PR — they are direct commits on the branch that became `main`,
so **no review of any kind is recorded for any of them.**

| sha8 | date | author | files | what changed |
|---|---|---|---|---|
| `38ee8d22c` | 2026-05-25 | Eran Agmon (#76) | `composites/baseline.py` | **Per-process RNG seeds.** Every stochastic process previously inherited one cache-derived seed; now each gets `crc32(process_name, master_seed) & 0x7FFFFFFF`. **Silently changes every trajectory** in the repo from this commit on. Review: none. |
| `d6743606f` | 2026-05-06 | Eran Agmon (#30) | `steps/allocator.py`, `steps/exchange_data.py` | `allocate`/`request` retyped `overwrite[map[…]] → map[…]`. With `overwrite`, **any per-process sub-key write replaced the whole map and dropped sibling processes' allocations.** Review: none. |
| `2147fca41` | 2026-04-13 | Eran | `steps/division.py` | Division exceptions were silently swallowed by process-bigraph; now wrapped and re-raised, and the daughter build moves to `build_document`. **Division that previously never happened now happens.** |
| `c2c95db2e` | 2026-04-12 | Eran | `generate_departitioned.py`, `generate_reconciled.py`, `library/{division,schema}.py`, `steps/listeners/*` | **8 processes had been silently dropped** from the departitioned/reconciled architectures (`config is None → skip`); re-registered as standalone Steps. Also fixes `bulk_name_to_idx`'s `id()`-only cache key (a GC'd-address collision produced **stale, out-of-range bulk indices**). |
| `0e282f535` | 2026-04-11 | Eran | `generate.py`, `processes/{rna_maturation,polypeptide_initiation,transcript_initiation,chromosome_replication}.py` | 4 processes leave the allocator; `allocator_1` deleted. They now read **un-partitioned** bulk counts and no longer compete for resources. |
| `1a5c0abe2` | 2026-04-11 | Eran | `generate.py`, `processes/{equilibrium,two_component_system,complexation,tf_binding,rna_degradation}.py` | Equilibrium / TwoComponentSystem / Complexation promoted `PartitionedProcess → Step`. **Equilibrium's greedy flux correction now runs against full counts, not allocated counts**, and the three vanish from the allocator, changing what the remaining partitioned processes get. |
| `0223c7078` | 2026-04-11 | Eran | `generate*.py`, `steps/ppgpp_initiation.py`, `processes/protein_degradation.py` | `DEFAULT_FEATURES = [] → ['ppgpp_regulation','trna_attenuation']`; `ppgpp_state` outputs additive → `overwrite[]` (`frac_active_rnap` had exceeded 1.0 after 4 ticks); ProteinDegradation moved out of `allocator_2`. |
| `0641f9800` | 2026-04-11 | Eran | `processes/{complexation,equilibrium,two_component_system,protein_degradation,metabolism,metabolism_simple}.py` | **Complexation now runs one Gillespie draw and reuses it in evolve** (was two independent draws) → different RNG stream; **ProteinDegradation stops requesting/consuming allocated water** and applies `n_to_degrade` directly; **`reduce_murein_objective` and its `CPD-12261[p] /= 2.27` objective adjustment are deleted.** |
| `bd48262f0` | 2026-04-11 | Eran | `steps/trna_attenuation.py` (new), `processes/transcript_elongation.py`, `generate.py` | tRNA attenuation, previously always-on, becomes a feature module **absent from `DEFAULT_FEATURES` — off by default** (until `0223c7078`). |
| `09094fe16` | 2026-04-11 | Eran | `processes/{chromosome_structure,transcript_initiation}.py`, `steps/ppgpp_initiation.py` (new), `generate.py` | Supercoiling (270 lines) removed from ChromosomeStructure and ppGpp regulation extracted; `DEFAULT_FEATURES = []`. Both previously always-on features become off by default. **Supercoiling is never re-enabled by default and is still off at the tip.** |
| `3a8add97e` | 2026-04-10 | Eran | `generate.py`, `library/ecoli_step.py`, `steps/partition.py` | Seeds `next_update_time = 0.0` for every partitioned process — requesters/evolvers gate on it, so **they had never fired**. Benchmark goes from not-growing to `dry_mass 384.6 fg` vs vEcoli's 384.5 fg. |
| `c454a2726` | 2026-04-20 | Eran Agmon (#25) | 10 `parca/.../flat/*.tsv`, `models/parca/parca_state.pkl.gz` | **P-A.** Rolls the BioCyc/EcoCyc knowledge base back **v29.6 → v29.1**: real value changes (formulae e.g. `S4Fe3 → HS4Fe3`, metabolites added/removed, name/synonym fields), and rebuilds the ParCa fixture in full mode. **This is not reformatting.** Review: none. |

### B — declared interfaces / wiring changed

| sha8 | date | author | PR | files | what changed | review |
|---|---|---|---|---|---|---|
| `8cf9a4bc8` | 2026-09-09 | Eran Agmon | #755 | `processes/metabolism.py`, `library/sim_data.py` | Metabolism gains a declared **`imposed_flux_bounds`** input store (`map[map[float]]`, default `{}`) + a `TOPOLOGY` entry, applied before the LP solve via `_apply_imposed_bounds`. Reverts #753's `sulfadiazine` flag so the process carries no drug knowledge. Empty store = strict no-op. | cmt:eagmon×2 (self) |
| `034fd6f3b` | 2026-09-07 | Eran Agmon | #737 | `library/inject.py`, `processes/metabolism.py`, `scripts/_compare/inject.py` | Classifies a pbg-native **deriver as a *step*** at injection (it had been interval-scheduled, stalling `global_clock` at tick 2 — the "one-tick collapse"). Plus a unit-safe AA-availability compare at `metabolism.py:841` that previously *raised* on `basal_with_trp`. | none |
| `91b905a79` | 2026-09-04 | Eran Agmon | #684 | `library/inject.py` (new, +1832) | Wheel-shipped native-injection resolver + a `register_native_injection(...)` **registry** replaces a hardcoded `sms_modules` class map, and the bare `from scripts._compare.inject` import (which resolved to whichever repo's `scripts/` was on `sys.path` — on the pod, sms-ecoli's vendored copy). A registered class that will not import now **raises** instead of silently defaulting. | none |
| `3084a15f9` | 2026-09-03 | Eran Agmon | #672 | `composites/_helpers.py` | Config-declared extra emit store paths folded into the emit schema + topology, **and cumulative lineage time exposed to injected processes** as a new readable input (a lineage's inner composite restarts `global_time` at 0 each generation). | none |
| `803393d77` | 2026-09-03 | cplong90 | #658 | `composites/ecoli_baseline.py` | `injected_processes["seed_exchange_species"]` lets a caller declare exchange ids to seed at 0.0 (`setdefault`). `environment.exchange` is a bare-float map that **updates existing keys and never adds one**, so an injected subsystem secreting an unregistered species wrote into a key nobody created and every reader saw bit-exact zero. | none |
| `ca3dc931f` | 2026-09-02 | Eran Agmon | #655 | `scripts/_compare/inject.py` | Native-path deserialization gate: `!ParameterSerializer[…]` / `!units[…]` config tags now resolve against the **fork's** `param_store` before reaching a `pbg_native` process. Raw tag strings had been reaching numeric comparisons. Raises when a tag is present but no fork is reachable. | none |
| `cad6e4598` | 2026-09-02 | Eran Agmon | #651 | `composites/ecoli_baseline.py`, `ecoli_v1_hybrid.py` (deleted), `steps/division.py` | Retires `ecoli_v1_hybrid` and removes fork-sourcing entirely; `ecoli_baseline` is native-only. | none |
| `a407c9a75` | 2026-08-30 | Eran Agmon | #631 | `composites/ecoli_baseline.py`, `ecoli_v1_hybrid.py` (new), `steps/division.py` | `ecoli_baseline` becomes native-only and **rejects a non-empty `injected_processes.fork_repo`**; fork-wrapping moves to a new `ecoli_v1_hybrid` composite over the same generator body. | none |
| `a35cbdd15` | 2026-08-30 | Eran Agmon | #629 | `library/sim_data.py` (−189), `composites/ecoli_baseline.py`, `steps/derivers/cell_geometry.py` | Drug-agnostic seam: adds `seed_bulk_species` + `requires_features` injection declarations and **retires the `mecillinam` / `amp_lysis` flags** together with the `mecillinam → cell_geometry` auto-enable. `cell_geometry` becomes a neutral engine feature. | none |
| `6107a0f6d` | 2026-08-25 | cplong90 | #594 | `steps/derivers/exchange_flux_listener.py`, `steps/division.py`, `composites/_helpers.py` | Listener gains a new read port `mass → listeners.mass` and a `basis` config; `Division` declares and threads `exchange_fluxes` so generation-≥2 daughters keep the leaves (they had been constant 0.0). | none |
| `e0c800285` | 2026-08-22 | Eran Agmon | #575 | `composites/vecoli.py`, `ecoli_baseline.py`, `library/vivarium_ecoli_engine.py` | Bulk observables move off a top-level `bulk` port onto `listeners.observable_bulk.<id>`; new `observables` param (default `[]`). | none |
| `47e7c01cc` | 2026-08-19 | cplong90 | #543 | `scripts/_compare/inject.py` | **Injection order/priority semantics.** Injected steps get strictly descending priorities below the baseline minimum, replacing an arbitrary shared `1.0`. The tie was **intermittent run-to-run** — whichever tied step ran first decided whether a consumer saw a populated store or an empty one. | cmt:cplong90 (self) |
| `8f1de5ea6` | 2026-08-17 | Eran Agmon | #525 | `library/vivarium_bridge.py` | `attach_pint_ports` now also governs the **declared** schema, so a bridged port is declared Quantity-typed rather than `overwrite[float]` and subtype-resolves on a shared store. | none |
| `56589f5d1` | 2026-08-17 | Eran Agmon | #522 | `scripts/_compare/inject.py` | Injection auto-defer scoped to **pre-injection** roots (a store an earlier spec introduced keeps its real typing); new generic `extra_bulk_species` / `shape_seed_param_store` / `shape_seed_literal` seams that add bulk species and seed store initial values. | none |
| `6952797a0` | 2026-08-14 | Eran Agmon | #493 | `scripts/_compare/inject.py` | Deeply-nested scattered fork topologies are no longer collapsed to their `_path` base (previously wired to a bare `[]`) — wired leaf-by-leaf onto real composite stores, and leaf stores seeded with the schema `_default`. | none |
| `998bd1551` | 2026-08-13 | Eran Agmon | #491 | `scripts/_compare/inject.py` | For process names shared with the installed vEcoli, the **fork's** class (and its store layout) is what runs. | none |
| `6116a8234` | 2026-08-13 | Eran Agmon | #489 | `library/vivarium_bridge.py` | Config `!ParameterSerializer`/`!units` tags deserialized against the fork's param_store; the bridged process's `initial_state()` now overlays the translated port `_default`s. | none |
| `029cd6731` | 2026-08-14 | cplong90 | #476 | `parca/.../knowledge_base_raw.py` | **P-B.** Removes the `gene_deletions` ctor param and 6 deletion methods (moved to ecoli-sources). No in-repo caller passed it; an external one now gets a loud `TypeError`. | cmt:cplong90 (self) |
| `3dbb09bb6` | 2026-07-27 | Eran Agmon | #407 | `steps/division.py`, `composites/_helpers.py`, `ecoli_baseline.py` | Daughters rebuild **with** the injected/swapped-process spec. Before, they silently reverted to the plain FBA baseline at division, so a multi-generation redux/swap study only perturbed generation 1. | none |
| `ee74c4c57` | 2026-07-27 | Eran Agmon | #396 | `scripts/_compare/inject.py` | Any vivarium `Step` subclass is now injected as a pbg **step** (in-tick, cascade-applied) rather than an interval-scheduled process. | none |
| `39101963c` | 2026-07-26 | Eran Agmon | #392 | `composites/ecoli_structural.py` | `EcoliPackStep` appended unconditionally + registered via `core_extensions`; previously dropped on every real run. Writes pack artifacts only. | none |
| `aada8d108` | 2026-07-26 | Eran Agmon | #384 | `composites/ecoli_structural.py`, `structural/*` | Pack step gains `active_RNAP` / `active_replisome` / `chromosome_domain` input ports; new `envelope` param (default **True**) and changed nucleoid constants. Affects the 3D artifact, not WCM state. ("parsimony" here is the 3D packing library, **not** pFBA.) | none |
| `d83777b1a` | 2026-07-25 | Eran Agmon | #370 | `bridge.py`, `composites/colony.py`, `colony.py`, `types/__init__.py` | `EcoliWCM` port types renamed to unit-named float subtypes (`map[millimolar]`, `radian`, `femtogram`…). They `_inherit: float`, so values are unchanged. | none |
| `60af7cb3c` | 2026-07-24 | Eran Agmon | #361 | `processes/transcript_initiation.py`, `library/schema_types.py`, `types/__init__.py` | `_evolve` decomposed **behaviour-preservingly** (RNG call order preserved); **two dead input ports removed** (`active_RNAPs`, `listeners.mass.cell_mass`) — still present in outputs/TOPOLOGY. `*_ARRAY` constants become registered biological type names resolving to the same structure. Despite the title, **not** a biology change. | none |
| `868cf2a36` | 2026-07-24 | A.P. | #356 | `steps/batch_baseline_runner.py`, `types/__init__.py`, `library/parallel_seeds.py` | Batch port declared by registered type **name** (`"inplace_dict"`) rather than an instance that serialized to a non-reparseable repr; same resolved type. | none |
| `010bf7540` | 2026-06-16 | Eran Agmon | #243 | `composites/baseline.py` | Injects `ShapeStep` and a new top-level `shape` store into the baseline (`width_um=1.0`, `density_g_per_ml=1.1`, `periplasm_fraction=0.2`). **Read-only deriver — nothing in the model reads `shape`.** | none |
| `1bca6e82e` | 2026-06-13 | Eran Agmon | #208 | `steps/derivers/counts_deriver.py`, `library/sim_data.py`, `parca/.../two_component_system.py` | New **`promoters` port** (`('unique','promoter')`) + a `tf_ids` config on `counts_deriver`; folds promoter-bound TF subunits into the monomer total and reorders the unpack cascade (TCS → equilibrium → complexation). ParCa side canonicalizes mismatched subunit compartment tags (such subunits had been silently dropped). Emitted `listeners.monomer_counts` values change materially; **no feedback into the simulation**. | none |
| `ba6769052` | 2026-06-12 | Eran Agmon | #100 | `processes/{metabolism,transcript_initiation,polypeptide_initiation}.py`, `composites/baseline.py`, `steps/fba_flux_coupler.py`, `data/millard_v2ecoli_reaction_map.yaml` | **The FBA bridge's hook is force-bound but off:** `Metabolism.TOPOLOGY` gains `pinned_flux_targets → ('pinned_flux_targets',)` with `_default {}` (empty ⇒ `_apply_flux_pins` early-returns, LP identical) plus a new `listeners.fba_bridge.relaxed_reactions` output. The `FBAFluxCoupler` that writes those pins lives only in `millard_fba_bridge_harness`, not in `baseline`. Core-process PDMP kinetics are opt-in (`transcript_initiation_mode`/`polypeptide_initiation_mode` default `"discrete"`). | cmt:eagmon×31 (self) |
| `693a220c0` | 2026-05-30 | Eran Agmon | #105 | 12 process files, `steps/listeners/{mass_listener,mass_conservation}.py`, `steps/ppgpp_initiation.py`, `composites/baseline.py` | Declared port types `float[fg]` → `quantity[float,fg]` across the whole surface; also adds an opt-in `mass_conservation` feature (default OFF). | cmt:eagmon×2 (self) |
| `5e30aa0f3` | 2026-05-13 | Eran Agmon | #37 | `composites/{baseline,_helpers}.py` (new), `steps/division.py`, `library/cache_version.py` | Replaces the hand-rolled `generate*.py` factories with `@composite_generator` functions. **Daughter documents are now built by calling `baseline()` and overlaying divided state**, rather than `build_document(d_data, …)`. | none |
| `704b8afc7` | 2026-04-12 | Eran | — | `processes/chromosome_replication.py`, `steps/listeners/rna_synth_prob.py` | Adds `global_time` to `TOPOLOGY` **and** `inputs()`. Effect: replication stops raising `KeyError('global_time')` at ~23 min, so the cell cycle reaches division. | — (direct commit) |
| `bff33e036` | 2026-04-11 | Eran | — | `library/ecoli_step.py` + 10 process files | `__init__` → `initialize()`; every declared port gains an inline `_default`. | — |
| `967f63891` | 2026-04-10 | Eran | — | `library/ecoli_step.py`, `library/port_defaults.pickle` (new, 713 KB), 10+ process files | **Deletes `ports_schema` (−1098 lines).** Port pre-population defaults now come from a dill pickle keyed by class name. | — |
| `9531bbd39` | 2026-04-10 | Eran | — | 10+ process files | Adds `port_defaults()` to every process. | — |
| `247578781` | 2026-04-10 | Eran | — | 10 partitioned process files | Adds explicit `inputs()`/`outputs()` alongside the still-present `ports_schema`. | — |
| `5263924a3` | 2026-04-10 | Eran | — | `generate.py`, `steps/base.py`, `steps/partition.py` | Rewires per-process `request_<proc>`/`allocate_<proc>` stores into shared `request`/`allocate` maps (the vEcoli pattern); also drops `_protect_state()` around `update()`. | — |
| `a8de7718f` | 2026-04-10 | Eran | — | `library/ecoli_step.py` + 10 process files | WIP continuation of the port: exact-schema declarations. | — |
| `339429637` | 2026-04-10 | Eran | — | 34 files, +8707/−4672 across `processes/`, `library/{schema,schema_types,data_predicates,ecoli_step}.py` | **The initial port** of the vEcoli processes "with exact schemas" — establishes the entire declared surface. Too large to verify line by line; see §6. | — |

---

## 3. C — opt-in, defaults preserve prior results

These add model content but cannot change a run that does not ask for them. **Knob and default
are stated for each.** Several of them are genuinely new biology hiding behind a `False`.

| sha8 | date | PR | knob → default | one-line |
|---|---|---|---|---|
| `b7978a8a6` | 2026-09-09 | #753 | `sulfadiazine` → `False` | **New rate law**: cytoplasmic sulfadiazine (`CPD-20940[c]`) competitively inhibits DHPS (`H2PTEROATESYNTH-RXN`) against PABA, capping its FBA upper bound (kcat 0.38, km_paba 7.82e-3, k_i 5.15e-3). **Reverted the next day by `8cf9a4bc8` / #755** and moved out to the injected layer. |
| `f7ce41ff7` | 2026-09-04 | #669 | `d_period_cv` → `0.0` (also settable by env var `V2E_D_PERIOD_CV`) | **Stochastic D-period**: the scheduled `division_time` is drawn per division from `Normal(1.0, cv)·D_period`, floored at 0.5. The model was under-dispersed (CV ~7% vs a biological 10–30%). Also, in `parca/wholecell/utils/modular_fba.py`, tiny-negative homeostatic targets (e.g. ≈−1.5e-6 for `BIOTIN[c]` under acetate/succinate) are now **clamped to 0 instead of raising** — enabling conditions that previously could not run at all. ⚠ **The PR subject says "landed ATP-synthase respiration fix"; no ATP-synthase change is on `main`.** `atp_synthase_reverse_cap` was explored inside the branch and dropped ("no ATP-synthase FLUX BOUND simultaneously forces respiration, reproduces the measured yield, and preserves growth; the defect is STOICHIOMETRIC"). |
| `af4ef87c3` | 2026-09-06 | #712 | `independent_founders` → `False`, `founder_sim_data` → `""` | **Initial-state generation.** By default every seed of a multiseed ensemble starts from the *same* cached founder, so multiseed spread reflects only downstream stochasticity, not cell-to-cell founder variability. Opt-in re-draws the founder per `lineage_seed`. |
| `0b1aacfd3` | 2026-08-30 | #592 | `carbon_exhaustion_arrest` → `False`, `carbon_source_ids` → `[]` | **New starvation physics.** With glucose import forbidden the homeostatic FBA still produced biomass precursors at full rate — objective unchanged (3.05204 → 3.05205) and +14.2 fg dry mass over 160 ticks at zero external carbon. Opt-in zeroes the *net supply* of biomass monomers when no carbon source is importable. Inherited wcEcoli behaviour, not a v2ecoli regression. |
| `4bd71ca43` | 2026-08-25 | #598 | `exchange_flux_basis` → `"counts"` | Lets a study declare which quantity the exchange-flux leaf carries; the `gdcw` arm adds a mass-basis rate. |
| `cd1b881ae` | 2026-08-24 | #593 | `transport` → `"local"` | Exposes the previously-hardcoded colony transport param. |
| `e10864031` | 2026-08-24 | #579 | `mecillinam` → `False`, `amp_lysis` → `False` | Candidate mecillinam antibiotic support (bulk species + geometry). `cell_geometry` auto-enabled only under `mecillinam=True`; `DEFAULT_FEATURES` unchanged. Both flags **removed** again by #629. |
| `576f887b8` | 2026-08-23 | #578 | `stop_at_division` → `False` | Routes single-cell builds through the lineage path so a run bounds at one cycle; default path bit-identical. |
| `2fff48457` | 2026-08-20 | #556 | `exchange_fluxes` → `{}` | New `exchange_flux` feature module + listener; not in `DEFAULT_FEATURES`. |
| `12cbca96a` | 2026-08-15 | #503 | `whole_config` → `""`, `variant` → `0`, `observable_bulk_ids` → `[]` | Generic variant-sweep phenotype capability for the whole-config WCM node. |
| `fbfd24408` | 2026-08-13 | #487 | `initial_carry_state_path` → `""`, `initial_generation_index` → `0`, `daughter_state_out_path` → `""` | Checkpoint/resume keys through the batch path. |
| `7e7069bcc` | 2026-08-03 | #449 | `match_simdata` → `None` | Overlays reference-vEcoli t=0 bulk counts onto the initial state. Never runs by default. |
| `1b6f28b48` | 2026-07-30 | #420 | `exchange_data.glc_uptake_cap_aerobic` → `None` | Configurable aerobic glucose-uptake cap; `None` preserves the stock **20.0 mmol/gDCW/h**. |
| `2dfeeeb97` | 2026-07-25 | #373 | `knockouts` → `None`, `media` → `"minimal"`, `n_seeds`/`n_generations` → `1` | Folds the KO / media / batch composites into `baseline`; single-cell path verified bit-identical. |
| `5449a1d8b` | 2026-07-25 | #371 | new composite `baseline_parsimony` | Wraps `baseline()` untouched plus one extra final 3D-pack layer. |
| `ddfaddda2` | 2026-07-24 | #357 | new composites `KO_baseline` / `KO_batch_baseline`; `base_config_overrides` → `{}` | Translation-level gene knockouts (KO = translation-efficiency multiplier 0). Baseline unchanged. |
| `6b57bd322` | 2026-07-22 | #351 | new composite `batch_baseline` | N baseline lineages fanned over Ray. |
| `52657bf7d` | 2026-06-30 | #326 | `injected_processes` → `None`/`{}` | Bridged v1 process is presented its full declared state (sentinel-`None` leaves the pbg store drops). |
| `69cf48d60` | 2026-06-30 | #325 | `injected_processes` → `None`/`{}` | Generalizes fork-process resolution/injection. |
| `4c042689a` | 2026-06-29 | #313 | `strip_pint_ports`/`attach_pint_ports` → `None` | Per-port pint strip/attach at the v1-bridge boundary. |
| `26515af8c` | 2026-06-29 | #311 | `swap_processes`/`exclude_processes`/`defer_ports` → `None` | The mechanism by which **MetabolismRedux replaces baseline metabolism**. Guarded on `if injected_processes and (…)` — dead branch by default. **MetabolismRedux is not the default metabolism.** |
| `c17d44d7b` | 2026-06-14 | #69 | `features` → `[]` | The bioreactor-coupling family. Its only edit to `baseline.py` is the per-call `features` knob; every coupled composite is a separate generator. |
| `0e5bbfcd0` | 2026-06-12 | #161 | the four feature toggles, all at their prior values | Promotes feature modules from module-global `enable_features()` to declared generator knobs. **No default changed**: the resulting set is still exactly `['ppgpp_regulation']`. |
| `3af8bb520` | 2026-05-29 | #72 | new composite family `millard_pdmp_baseline` | ~3,000 lines of PDMP/LQR model code registered alongside `baseline`; `baseline` untouched. ⚠ The new rate laws in that family were not read. |
| `7677ea51a` / `b5114e63c` | 2026-05-22 | #65 / #66 | new composite family, then reverted | DnaA replication-initiation investigation added as a separate recipe family (`baseline.py` untouched), then reverted wholesale four weeks before the #137 attempt that *did* touch the baseline. |
| `a84041824` | 2026-05-15 | #40 | new composite `colony` | Colony composite generator. |
| `1b44181a9` | 2026-04-11 | — | `fraction_active_rnap_bound`/`_free`/`ppgpp_km_squared` → `None` | Inlines the Hill function `f = ppgpp²/(km²+ppgpp²)` in `PpgppInitiation`; `None` falls back to the legacy `get_rnap_active_fraction_from_ppGpp` callable. |
| `c919bd1d6` | 2026-04-11 | — | new generator `departitioned` | Adds the departitioned architecture as a separate generator; baseline unchanged. |
| `db7719f04` | 2026-08-19 | #531 | **P-C.** `rnaseq_source` → `"reference"` | Experimental RNA-seq tier; the default path computes `seq_data` exactly as before. |
| `41a3fa19e` | 2026-08-18 | #528 | **P-C.** `new_genes` → `""`, `bundle_overrides` (declared but never read → now effective) | A private payload can contribute a new-gene insertion end to end; `SourceBundle` overrides become a chain **on top of** `_DEFAULT_OVERRIDES`. Default build numerically unchanged. |
| `c2fb6bd94` | 2026-08-05 | #455 | **P-C.** `gene_deletions` → `None` (no caller at that commit) | Chromosome-level gene deletion with a corrected coordinate transform; fixes 4 real defects in the upstream transform (off-by-one splice, wrong "before" guard, unbound var, remove-during-iterate). |
| `bcd9d15bf` | 2026-08-05 | #457 | **P-C.** `bundle_manifest`/`bundle_overrides` → `''` | A ParCa build can declare the genotype it is for; declared-vs-injected mismatch only warns. |

---

## 4. Where the model/non-model boundary is blurry

There is **no clean separation in this repo**, and the reason is structural rather than
accidental: v2ecoli expresses biology as *wiring*, so a change to the wiring is a change to the
biology, and the same file holds both. Concretely, six places do double duty.

**`v2ecoli/composites/ecoli_baseline.py` (2,406 lines) is simultaneously the model definition and
the dispatch configuration.** `BASE_EXECUTION_LAYERS` — the list that decides *which processes run
and in what order within a tick* — sits a few hundred lines from checkpoint paths, emitter
selection, Ray batch knobs and S3 output directories. `DEFAULT_FEATURES = ['ppgpp_regulation']`
is a one-line literal in the same file. The whole DnaA episode is the proof: `717b976af` (#137)
turned DnaA replication initiation **on by default** by appending five entries to that list, and
`bf60df0d4` (#244) turned it off again one day later by deleting them — a two-line diff in a file
whose other 2,400 lines are plumbing. Worse, the revert was partial: `baseline.py` went back, but
the `315`-DnaA-box initial state in `library/initial_conditions.py`, the two new ports and the
extra hydrolysis flux in `processes/equilibrium.py`, and the dnaA autoregulation term in
`processes/transcript_initiation.py` all stayed. Reading `git revert` at the commit level would
have told you the mechanism was gone; it isn't.

**`_helpers.inject_flow_dependencies` is where "wiring" becomes "execution order".** It assigns
each step a numeric `priority` and threads `_layer_token_N` in/out ports so the layers execute in
sequence. Nothing about it looks biological, and it decides whether Equilibrium sees allocated or
full counts. The same function is why `47e7c01cc` (#543) matters: injected steps all landed on the
default `priority = 1.0`, tied with each other, and the scheduler's arbitrary choice between two
tied steps decided whether a consumer read a populated store or an empty one — **the same build
passed and failed across repeat runs.** That is a results-affecting property of a priority integer.

**`scripts/_compare/inject.py` and `v2ecoli/library/inject.py` (1,430 + 1,852 lines) are the
comparison *harness*, and they decide what the model is.** Injection order (#543), which class
gets instantiated (#491), where its config comes from (#535, #489), whether a config's serializer
tags are resolved into real Quantities (#655), whether a store is typed so an `overwrite[…]`
output composes forward (#653), whether a swapped process is scheduled as a step or a process
(#396, #737) — every one of those changes what a perturbed run computes, and none of them is in a
file a biologist would open.

**Division is spread across four files, none of which is obviously "the model".**
`v2ecoli/steps/division.py` (the rule), `v2ecoli/library/division.py` (the `divide_cell`
mechanics and, since #610, the *classification of an exception as a division*),
`v2ecoli/composites/_helpers.py` (the daughter-rebuild branch), and — critically —
**`v2ecoli/workflow/lineage.py`, which the audit rubric explicitly calls non-model.** Three of the
A-grade commits in §2 live entirely in that last file: `#293` (daughters inherited an
*accumulating* `exchange_data` store, so the glucose uptake bound ballooned to thousands of
mmol/gDCW/h in every generation ≥ 1), `#127` (only generation 0 ever divided in a multigen run),
and `#611` (the lineage builder dropped `baseline()`'s feature kwargs). `lineage.py` also owns
`select_carry_daughter` — the policy of which daughter is carried forward — and the founder-seed
derivation. Anything that reads "workflow" in this repo may still be deciding what the cell does.

**The environment/reactor coupling files are physiology written as plumbing.**
`steps/reactor_cell_coupler.py`, `steps/environment_mirror.py`, `steps/exchange_data.py` and
`steps/media_update.py` contain no rate law, but they determine the concentration the cell is told
it is in — and six of the A commits are there. Several were *typing* changes:
`map[float]` → `overwrite[…]` on `exchange_data.constrained` (#548) is what let the store drop a
key, which is how "max flux 0" is expressed to the FBA; `map[overwrite[float[mM]]]` on
`boundary.external` (#568) is what made nine `inf`-seeded molecules drivable at all. **In this
codebase a schema declaration is a biological statement**, and the difference between
`overwrite[map[…]]` and `map[overwrite[…]]` was, in #568's own probe, the difference between the
cell keeping its media and losing it.

**ParCa is a category of its own that nobody can call non-model.** `v2ecoli/processes/parca/**`
was carved out as `P` because it is a vendored port, but a ParCa change *is* a parameter change:
`#738` made pABA and DHPPP homeostatic FBA targets and pinned MurD's half-life on **every** build,
`#25` rolled the whole EcoCyc knowledge base back from v29.6 to v29.1, and `#275` fixed a
compartment-tag match that meant ribosomal-protein translation efficiencies had **never** been
averaged. Meanwhile `library/cache_version.py` — pure infrastructure by name — holds `INPUT_FILES`,
the list that decides when a ParCa cache is stale, and `ecoli_baseline.py` is *in* that list. An
edit to the composite invalidates every cached reconstruction.

The one genuinely clean boundary: **emitters and analyses really are non-model.** Everything
under `library/{parquet,xarray,sqlite}_*`, `composites/workflow_nf.py`, `nf-render` and the
visualization steps changes what is *recorded*, never what is computed — including the ones whose
titles sound alarming (#758's missing `environment` emit path, #761's zarr zero-arrays, #641's
hive partition). The listener `overwrite[]` fixes (#60, #51, #185) are in the same class: they
changed emitted numbers by ~10³× without touching a simulated one.

---

## 5. Default values that changed over the history

Ordered oldest → newest. "⚠" marks a default whose change altered results on the path people
were actually running.

| # | knob / constant | old → new | commit | PR |
|---|---|---|---|---|
| 1 ⚠ | `DEFAULT_FEATURES` (supercoiling, ppGpp) | always-on → `[]` | `09094fe16` | — |
| 2 ⚠ | `DEFAULT_FEATURES` (tRNA attenuation) | always-on → absent | `bd48262f0` | — |
| 3 ⚠ | `DEFAULT_FEATURES` | `[]` → `['ppgpp_regulation','trna_attenuation']` — **supercoiling never returns** | `0223c7078` | — |
| 4 ⚠ | `ppgpp_state.basal_prob` / `.frac_active_rnap` | additive → `overwrite[…]` (`frac_active_rnap` had exceeded 1.0 after 4 ticks) | `0223c7078` | — |
| 5 ⚠ | allocator membership | ProteinDegradation out (`0223c7078`); Equilibrium/2CS/Complexation out (`1a5c0abe2`); RnaMaturation/PolypeptideInitiation/TranscriptInitiation/ChromosomeReplication out (`0e282f535`) — only RNA degradation + the two elongations remain partitioned | 3 commits | — |
| 6 ⚠ | Complexation Gillespie draws per tick | 2 independent → 1 reused | `0641f9800` | — |
| 7 ⚠ | `Metabolism.reduce_murein_objective` + `conc_updates["CPD-12261[p]"] /= 2.27` | present (`False` default) → **deleted** | `0641f9800` | — |
| 8 ⚠ | `next_update_time` per partitioned process | unset → `0.0` (they had never fired) | `3a8add97e` | — |
| 9 | `timestep` default | `1.0` → `1` (type only) | `4051c60b3` | — |
| 10 | `trna_attenuation` in `DEFAULT_FEATURES` | on → off again, "to match v1 default" | `c9053136b` (2026-04-12) | — |
| 11 ⚠ | **ParCa knowledge base** | EcoCyc **v29.6 → v29.1** across 10 flat TSVs + a full fixture rebuild | `c454a2726` | #25 |
| 12 ⚠ | `allocate`/`request` store type | `overwrite[map[…]]` → `map[…]` (the `overwrite` had been dropping sibling processes' allocations) | `d6743606f` | #30 |
| 13 ⚠ | **per-process RNG seed** | one shared cache-derived seed → `crc32(process_name, master_seed)` — changes every trajectory | `38ee8d22c` | #76 |
| 14 | `mass_conservation` feature | new, **off** | `693a220c0` | #105 |
| 15 ⚠ | `Division.d_period` | absent → **`True`**; division fires on the D-period flag and the **dry-mass threshold is no longer consulted** | `29c4dc262` | #271 |
| 16 ⚠ | ppGpp TF scaling for zero-basal genes | hard switch `ppgpp_scale[==0] = 1` → Hill gain `b²/(b+K)`, **new constant K = 1e-11** | `29c4dc262` | #271 |
| 17 ⚠ | ParCa ppGpp `adjustment` for dust-band genes | `new_prob/old_prob` → `1.0` when `old_prob ≤ 1e-10·max` | `29c4dc262` | #271 |
| 18 | daughter composite emitter | `"parquet"` → `"null"` when no override | `29c4dc262` | #271 |
| 19 ⚠ | **equilibrium network** | +2 reactions (`DNAA-INTRINSIC-HYDROLYSIS-RXN` fwd 1.4e-05 / rev 1.0e-15; `MONOMER0-4565_RXN` fwd 1 / rev 1.0e-07), +3 tracked molecules (WATER, Pi, PROTON), two-phase ODE solve, recursion guard `val != 0 → val < 0` | `5e7f02a00` | #123 |
| 20 ⚠ | `media_timeline` | `(0,'minimal')` → `(0, <condition's nutrients>)` — `no_oxygen` had been running **aerobic** | `9675fe4f7` | #289 |
| 21 ⚠ | `BASE_EXECUTION_LAYERS` | + 5 DnaA layers … then − all 5 one day later | `717b976af` → `bf60df0d4` | #137 → #244 |
| 22 | `DNAA_AUTOREG_STRENGTH` / `RIDA,DDAH,DARS1,DARS2_RATE_MULTIPLIER` | n/a → `0.8` / `1.0` (env-overridable) | `717b976af` | #137 |
| 23 ⚠ | DnaA box count in the initial state | **307 → 315** — *survives the #244 revert* | `717b976af` | #137 |
| 24 | `monomer_counts` updater | `overwrite` → accumulate → `overwrite` (emitted values inflated ~10³× in between) | `f619fd13a` → `8fb343be0` | #164 → #185 |
| 25 | `ShapeStep` output | `map[float]` (accumulating) → `map[overwrite[float]]` | `5c6fc5b92` | #250 |
| 26 | `DEFAULT_SINGLE_CELL_VISUALIZATIONS` / `DEFAULT_COLONY_VISUALIZATIONS` | `[]` → 8 panels / → `[]` | `9ff818470` / `6637b2581` | #344 / #414 |
| 27 | `EcoliPackStep.envelope` `True`; `Chromosome(beads)` 34000→90000, `spacing` 135.0→22.0, `bead_radius` 12.0→10.0, `supercoil`→`None` | 3D pack artifact only | `aada8d108` | #384 |
| 28 ⚠ | **study media** | `acetate → minimal_acetate`, `succinate → minimal_succinate`, `no_oxygen → minimal_minus_oxygen`, `with_aa → minimal_plus_amino_acids`; 4 other studies fall to `minimal` | `3c5fe1a2c` | #393 |
| 29 ⚠ | `FinalAdjustmentsStep.allow_partial_fit` | implicit "continue" → **`False`, abort**; `cache_version.SCHEMA_VERSION` 1 → 2 (invalidates every cache) | `e9e4c6930` | #446 |
| 30 ⚠ | `SourceBundle` precedence | `parca_overrides.tsv` always wins → **variant-generated keys win** | `ebb3c7c0f` | #468 |
| 31 ⚠ | injected fork process class / config source | installed vEcoli → **the fork's own** | `998bd1551` / `f98218a93` | #491 / #535 |
| 32 ⚠ | injected-step priority | all tied at `1.0` (run-to-run nondeterminism) → strictly descending below the baseline minimum | `47e7c01cc` | #543 |
| 33 | XArray transducer `buffer_size` | `3`/`4` → `600` | `81b0c996e` | #558 |
| 34 ⚠ | `exchange_data.constrained`/`unconstrained` | `map[float]`/`list[string]` → `overwrite[…]` (the store can now drop a key) | `2fa846368` | #548 |
| 35 ⚠ | `boundary.external` write semantics | **delta → absolute**; declared `map[overwrite[float[mM]]]` | `25a6a7949` | #568 |
| 36 ⚠ | reactor exchange population scale | `cells_per_agent` → `cell_count / n_agents` (was under-scaled by 2^doublings) | `1e6ecc5a8` | #550 |
| 37 ⚠ | population/reactor biomass source | `listeners.mass.cell_mass` → **`dry_mass`** — `total_biomass_gDW`, `biomass_concentration_gL`, `od600` all ÷ **3.3315** | `fdeb3243d` | #539 |
| 38 | `mecillinam` / `amp_lysis` | new, `False` … then **removed entirely** | `e10864031` → `a35cbdd15` | #579 → #629 |
| 39 ⚠ | reactor medium ammonium | static `30.272 mM` (recipe, undrawable) → finite pool, default **`ammonium_medium_mM = 60`**, drawn down and published as `AMMONIUM[c]` | `268515f0d` | #638 |
| 40 ⚠ | cell's dissolved-O₂ view | pre-consumption (a `dt`-scaled sawtooth peak) → **post-consumption** | `5add30cf9` | #679 |
| 41 | `d_period_cv` | new, `0.0` (env `V2E_D_PERIOD_CV`) | `f7ce41ff7` | #669 |
| 42 | FBA homeostatic-target guard | `coeff < 0` raises → `−1e-4 < coeff < 0` **clamped to 0** | `f7ce41ff7` | #669 |
| 43 | `carbon_exhaustion_arrest` | new, `False` | `0b1aacfd3` | #592 |
| 44 | `independent_founders` | new, `False` | `af4ef87c3` | #712 |
| 45 | `sulfadiazine` | new, `False` … **reverted one day later** | `b7978a8a6` → `8cf9a4bc8` | #753 → #755 |
| 46 ⚠ | **ParCa reconstruction overrides** | inert → **effective on every build**: pABA `8.0e-6 M` and CPD0-1080 `1.0e-8 M` become homeostatic targets; TU0-941 measured RNA half-life removed; MurD half-life pinned to `1914.725 min` at highest priority | `a9cf24ed8` | #738 |

**Never changed, verified across the whole range:** `DEFAULT_FEATURES == ['ppgpp_regulation']`
(so **supercoiling, tRNA attenuation and mass conservation are all off in the default baseline
today**, while `LoadSimData`'s own `trna_attenuation` argument still defaults to `True` — a
discrepancy worth a look); the stock aerobic carbon-uptake cap `20.0 mmol/gDCW/h`;
`transcript_initiation_mode` / `polypeptide_initiation_mode` = `"discrete"`;
`pinned_flux_targets` = `{}`; `imposed_flux_bounds` = `{}`; MetabolismRedux is **not** the
default metabolism.

---

## 6. Honest statements of uncertainty

**The initial port cannot be verified from this repo.** `339429637` alone is +8,707/−4,672 across
34 files, and there is no working prior baseline here to diff results against — *"ported with exact
schemas"* is an authorial claim, not a checkable one. The same applies to `a8de7718f`,
`5263924a3`, and to `a484baf06` (#16), which vendors 271 files / +188,866 lines of v2parca. #16
looks like a pure additive move (its only deletions are outside `parca/`), but byte-identity
against the upstream v2parca repo is **unverified** — that repo is not checked out here.
Any of these could carry an A-grade transcription error inside the ported math and this audit
would not see it.

**Two commits move defaults into binary dill pickles** — `23def1d32` (`config_defaults.pickle`)
and `967f63891` (`port_defaults.pickle`, 713 KB). Whether the extracted values equal the class
`defaults` dicts they replaced is **not visible in a diff**. `23def1d32` additionally strips units
off defaults (`8.39 * units.mmol/(units.g*units.h)` → `8.39` with type `'unum'`), so correctness
depends on the type reattaching the unit.

**Three "bit-equivalent" performance claims are plausible but not proven.** `04c44b858` (#89) adds
a BDF `jac_sparsity` hint, which changes scipy `num_jac`'s finite-difference grouping — the
estimated Jacobian is not guaranteed identical and BDF's step sequence can diverge. The commit
says "bit-identically" but the stated verification is `bench_equiv.py --tol-rel 0.005`, a 0.5%
tolerance. Its FBA bound diff-cache has the same character (GLPK sees a different call sequence).
`554022238` (#96, numba) and `412f912a7` (#98, stable argsort) do look genuinely order-preserving.

**A window of possibly-corrupt runs.** `a512c9df8` introduced an `id(bulk_names)`-keyed sorter
cache; `c2c95db2e` later fixed it explicitly ("numpy arrays get GC'd and their addresses reused …
stale sorter indices that overflow"). **Any run between those two commits may have used wrong bulk
indices.**

**`9ae357c6a` (#138) deleted ~149k lines of flat TSV/FASTA** and re-sourced them from a pinned
external `ecoli_sources` bundle. Classified `P-D` on the strength of the mechanism, but byte-identity
of the relocated values **could not be checked** — the files are gone from the tree. If any value
differs, that commit is silently A.

**Blast radius not visible from here.** `13bcc44a9` (#590) only matters if an external new-gene
payload (e.g. sms-ecoli's violacein insertion) ships the newly-joined reaction/kinetics/operon
files; from this repo we cannot tell. `#531`/`#528` add attributes to `sim_data`/`SourceBundle` —
whether they perturb the ParCa `inputs_hash` (and so force cache misses / `StaleCacheError` against
existing caches) is outside those diffs.

**Two more that could be A depending on your definition.** `5e30aa0f3` (#37) changed how daughter
documents are built — fresh `baseline()` plus an overlay of `bulk`/`unique`/`environment`/`boundary`
with the mass listener reset and re-seeded, instead of `build_document(d_data, …)`. Whether the
daughter's *non-overlaid* sub-stores (`process_state`, `next_update_time`, listeners) match the
divided state is not statically verifiable. And `3af8bb520` (#72) adds ~3,000 lines of new PDMP/LQR
model code; it is `C` because it is a separate composite family, but **its rate laws were not read**.

**Review coverage.** For every A and B commit above, the "review" column counts reviews and
comments left by the logins `eagmon` and `cplong90`, **excluding the author's own**. The result:
of the ~72 A/B commits, **six** carry any cross-login activity — `#293`, `#590`, `#455`, `#457`,
`#638`, `#648` (a review under `eagmon` on a PR authored under `cplong90`), plus comment-only
activity on `#640`, `#592`, `#591`, `#531`, `#559`, `#420`. **No PR authored under `eagmon` in the
entire range carries a review or comment from `cplong90`** except those four comment threads. The
whole April–May port era — 21 A/B commits, including the RNG-seed change, the allocator
membership changes, the EcoCyc rollback and the initial port itself — went in as **direct commits
with no PR at all**, so no review of any kind is recorded. And because both people's Claude
sessions post under the same GitHub logins, even a recorded review says *"reviewed under login X"*,
not *"a human read it"*.

---

## 7. Two specific things the scientists should know

1. **`#669`'s subject line says "+ landed ATP-synthase respiration fix". No ATP-synthase change is
   on `main`.** The branch diagnosed the defect (ATP synthase running in reverse: forward flux 0,
   hydrolysis 7.48 — zero respiratory ATP), tried `atp_synthase_reverse_cap` (default 4.5), and
   then explicitly withdrew it: *"no ATP-synthase FLUX BOUND simultaneously forces respiration,
   reproduces the measured yield, and preserves growth. The defect is STOICHIOMETRIC."*
   `git grep atp_synthase_reverse_cap origin/main` returns nothing. What actually landed from that
   PR is the `d_period_cv` knob (default 0.0) and the FBA negative-target clamp. **The biomass-yield
   / respiration defect is open.**

2. **The DnaA revert was partial.** `#244` removed the five DnaA steps from
   `BASE_EXECUTION_LAYERS`, but `#137`'s edits to `processes/equilibrium.py` (two new ports, extra
   `DNAA-INTRINSIC-HYDROLYSIS-RXN` flux), `processes/transcript_initiation.py` (dnaA autoregulation,
   gated on `promoter_fraction > 0`), `processes/chromosome_structure.py` (DnaA released to bulk on
   fork passage) and `library/initial_conditions.py` (**307 → 315 DnaA boxes in every initial
   state**) are all still on `main`. The gates make them inert while the steps are unwired, but the
   initial-state change is not gated.

---

# Appendix B — sms-ecoli full report

## sms-ecoli model-change audit

**Repo:** `CovertLabEcoli/sms-ecoli` @ `origin/main` (fetched 2026-09-09)
**Question:** which commits changed the *biological model* — injected processes, their
parameters, declared inputs/outputs and wiring, the CD2 run configs, and media/condition
data — as opposed to dispatch, analysis, tests, docs and tooling?
**Method:** every commit on `origin/main` was enumerated; every commit touching a model
path was read as a diff (not classified from its subject). Squash-merge, so one commit = one PR.

---

## 0. The one thing to read first: this repo has two eras

`origin/main` is 1426 commits deep and starts **2026-04-10**, because sms-ecoli *is* the
old v2ecoli repo. There is a hard boundary at **2026-08-27**:

| era | dates | where the model lived | commits |
|---|---|---|---|
| **vendored** | 2026-04-10 → 2026-08-27 | the whole v2ecoli model tree was checked in under `v2ecoli/`, kept current by a `sync_upstream.sh` merge | 514 commits touched `v2ecoli/`; 115 touched `v2ecoli/processes/`, 107 `v2ecoli/composites/`; **27** of them are bulk `sync: bring sms-ecoli up to date with v2ecoli` imports |
| **dependency** | 2026-08-27 (`f13aca0b`, #127) → today | `v2ecoli` is a git dependency pinned by rev in `pyproject.toml`; sms-owned model code lives in `sms_modules/` (created 2026-08-27, #124/#137) | the 45 commits audited below |

**Consequence for the scientists:** for anything before 2026-08-27, "which commit changed
the model" is not answerable from this repo's subjects — 27 `sync:` commits each imported
an arbitrary slice of upstream model change (one is labelled "289 commits"). From
2026-08-27 on, upstream model change enters *only* through a `v2ecoli` pin bump (§4), and
sms-owned model change is visible in `sms_modules/` and `configs/`. The audit below covers
the dependency era in full and treats the vendored era as a single, unauditable-by-subject
block.

---

## 1. Totals

- Commits on `origin/main`: **1426**
- Commits touching declared model paths (`sms_modules/processes/**`, `sms_modules/injection_topologies.py`, `sms_modules/bridge/**`, `configs/**`, `models/**`): **45** in the dependency era (+3 in June 2026 that only touched `configs/cond_*.json`, counted in the 45), plus the 514 vendored-tree commits noted above.
- `sms_modules/composites/**` does not exist — there are no composites in this repo; composition happens through `configs/` + the injection seam.
- v2ecoli pin bumps: **28** (§4). bigraph-schema/process-bigraph pin changes: 6. ecoli-sources / ecoli-sources-private pin bumps: 7.

| category | count |
|---|---|
| **A — model semantics changed** | **23** (+2 more outside the declared model paths, §2b) |
| **B — declared interfaces / wiring changed** | **7** |
| **C — opt-in, defaults unchanged** | **1** |
| **D — mechanical / non-semantic** | **9** |
| **E — experiment design** | **5** |

Authorship of the 30 A+B commits: **eagmon 22**, **AlexPatrie 3**, **jcschaff 2**,
**cplong90 3**. Reviews: **only 2 of the 30 carry any GitHub review at all** (see the
`review` column) — the rest were merged by their own author with no recorded review or
comment. That is the single most important governance fact in this audit.

---

## 2a. Category A and B commits (most recent first)

`review` column: `eagmon`/`cplong90` review or comment *under that login* (their Claude
sessions post under the same logins, so a comment is not proof a human read it).

| sha | date | author | PR | files | what changed | cat | review |
|---|---|---|---|---|---|---|---|
| `2a3c3661` | 2026-09-09 | jcschaff | [#314](https://github.com/CovertLabEcoli/sms-ecoli/pull/314) | `processes/pg_maturation.py` | A tick whose `listeners.mass.cell_mass` is NaN/zero (a daughter's first tick) is **skipped** with a RuntimeWarning and an empty update instead of aborting the lineage. Changes results only where it previously crashed (`solve_ivp: y0 must be finite`). | **A** | comment under `eagmon` |
| `50cb3e4e` | 2026-09-09 | AlexPatrie | [#312](https://github.com/CovertLabEcoli/sms-ecoli/pull/312) | `bridge/antibiotic_cocktail_sweep.py`, `configs/cd2/run3_sweep/combo_00..35.json` | Repoints the dose-sweep generator's default base from `experiments/antibiotic_cocktail_native_run.json` (no sulfadiazine transport) to `configs/cd2/run3_antibiotic_pg_sulfadiazine.json` (transport + DHPS wired), and **commits the 36 resolved combos**. The generated system is materially different from before. | **A** (also E) | none |
| `588bb043` | 2026-09-09 | eagmon | [#306](https://github.com/CovertLabEcoli/sms-ecoli/pull/306) | `processes/sulfadiazine_dhps_inhibition.py` (new), `injection_topologies.py`, `configs/cd2/run3_antibiotic_pg_sulfadiazine.json`, `scripts/_compare/inject.py` | New injected process: competitive-inhibition rate law `v = kcat·[DHPS]·[PABA]/(km_paba·(1+[sulfa]/k_i)+[PABA])`, defaults kcat 0.38, km_paba 7.82e-3, k_i 5.15e-3; emits `{H2PTEROATESYNTH-RXN: upper_bound}` to a **new agent-root store `imposed_flux_bounds`**. Inert until the v2ecoli pin carries #755. | **A** (also **B**) | comment under `eagmon` (self) |
| `6c438e50` | 2026-09-09 | eagmon | [#301](https://github.com/CovertLabEcoli/sms-ecoli/pull/301) | `processes/metabolism_redux.py` | **51 `BAD_RXNS` hardcoded and zeroed unconditionally on every run** (previously a config list defaulting to `[]`, which no config supplied). Changes the LP feasible region on every redux run. | **A** | none |
| `0f7c2216` | 2026-09-09 | eagmon | [#304](https://github.com/CovertLabEcoli/sms-ecoli/pull/304) | `processes/well_mixed_field.py` | Field concentration floored at 0 (`max(0.0, …)`) to match vEcoli's `nonnegative_accumulate`. Previously a pool-exceeding uptake drove `boundary.external` negative. | **A** | none |
| `3a52c450` | 2026-09-09 | eagmon | [#303](https://github.com/CovertLabEcoli/sms-ecoli/pull/303) | `configs/cd2/run3_antibiotic_pg_sulfadiazine.json` | Wires the sulfadiazine 4-reaction transport sub-block into Run 3: stoichiometry (periplasm/cytoplasm diffusion + export) **and its kinetic parameters** (permeabilities 3.8539e-6 / 3.8e-6 dm/s, areas 4.52e-10 / 3.8952e-10 dm², efflux kcat 0.63 /s, km 0.247 mM, enzyme_conc 0.0), plus `CPD-20940[p]/[c]` in `extra_bulk_species` and two efflux complexes in `concentrations_deriver.bulk_variables`. | **A** (also **B**) | comment under `eagmon` (self) |
| `1dbff758` | 2026-09-09 | AlexPatrie | [#299](https://github.com/CovertLabEcoli/sms-ecoli/pull/299) | `bridge/antibiotic_cocktail_sweep.py` (new) | Defines the **dose grid and onset time** for Run 3: mecillinam `[0, 1e-5, 1e-4, 1e-3, 1e-2, 0.1]` mM × sulfadiazine `[0, 1e-4, 1e-3, 1e-2, 0.1, 1]` mM, `DOSE_ONSET_TIME_S = 10000.0`, baked into `field_timeline.timeline`. Ported from vEcoli-private `antibiotic_cocktail_timeline.py`. | **A** | none |
| `cd0d3021` | 2026-09-08 | jcschaff | [#297](https://github.com/CovertLabEcoli/sms-ecoli/pull/297) | `processes/metabolism_redux.py` | Network-flow LP retries on **HIGHS then CLARABEL** when the requested solver (GLOP, default unchanged) raises or is non-optimal. **Classified A, not C**, per the rubric: on ticks GLOP answers, output is byte-identical; on ticks that previously killed the lineage a result now exists, and the PR itself states the norm-1 objective means a fallback may return a *different optimal vertex*. | **A** | **APPROVED by `eagmon`** |
| `77248228` | 2026-09-08 | AlexPatrie | [#292](https://github.com/CovertLabEcoli/sms-ecoli/pull/292) | `configs/mecillinam_wellmixed.json` | Drops `gillespie.species`'s orphan `{"species": {"bulk": [...]}}` nesting — flattens the wire to `bulk` (second half of "Bug B"). | **B** | none |
| `4e7d1d19` | 2026-09-08 | AlexPatrie | [#291](https://github.com/CovertLabEcoli/sms-ecoli/pull/291) | `configs/mecillinam_wellmixed.json` | Drops `mecillinam.species`'s redundant scattered wire (`_path: ["null"]` + `external → ../boundary/external/mecillinam`). | **B** | none |
| `b2676fe2` | 2026-09-07 | eagmon | [#272](https://github.com/CovertLabEcoli/sms-ecoli/pull/272) | `configs/cd2/run4_fss_bioproduction.json` (new), 3 `configs/experiments/*_vecoli_ref.json`, **`models/parca/flat_overrides/{metabolite_concentrations_added,protein_half_lives_modified,rna_half_lives_removed}.tsv`**, `models/parca/reconstruction_bundle_overrides.tsv` | Syncs vEcoli-private #93 configs and **stages reconstruction-parameter overrides**: added metabolite concentrations, modified protein half-lives, removed RNA half-lives. This is model *data* entering the ParCa. | **A** (also B/E) | none |
| `df53f704` | 2026-09-07 | eagmon | [#266](https://github.com/CovertLabEcoli/sms-ecoli/pull/266) | `configs/cd2/run1_k4_cellonly.json`, `configs/cd2/run2_j3_injected_metabolism.json` (both new) | Lands the two cell-only CD2 run configs: `swap_processes {ecoli-metabolism → ecoli-metabolism-redux}`, `exclude_processes [exchange_data]`, and a 10-entry `flow` block ordering every listener after redux. | **B** | comment under `cplong90` |
| `17d67194` | 2026-09-04 | eagmon | [#213](https://github.com/CovertLabEcoli/sms-ecoli/pull/213) | `processes/field_timeline.py`, `analyses/*` | Two new model knobs on the dose-delivery process: **`decay_rates`** (a listed molecule is delivered as `conc·exp(-k·t)` — mecillinam k = ln2/1.4 h = 1.375e-4 /s, Brouwers 2020) and **`lineage_time_offset`** so an absolute-time dose entry fires against *cumulative* lineage time rather than the per-generation clock that restarts at 0. Both default to no-change. | **A** | none |
| `6ccb5cf1` | 2026-09-03 | eagmon | [#206](https://github.com/CovertLabEcoli/sms-ecoli/pull/206) | 4 configs | Adds `bundle_overrides: models/parca/violacein_bundle_overrides.tsv` to Run-4 `parca_options` — changes the reconstruction the violacein sims are built from. | **A** | none |
| `b2088be1` | 2026-09-03 | eagmon | [#203](https://github.com/CovertLabEcoli/sms-ecoli/pull/203) | `processes/pg_maturation.py`, `processes/pg_shape.py` | **Peptidoglycan mechanics corrections**: `prop_crosslinked` 0.20 → **0.28** (eLife 72863 supp 2); initial glycan pool split 2/3 : 1/3 instead of all-in-one; `b = 1 - pi_out·beta` → `1 + pi_out·beta` (sign); `a_z` denominator `Etheta` → **`Ez`**; `stress_theta = stress_z.to(...)` → `stress_theta.to(...)`. Four of five are outright bug fixes to the mechanics. | **A** | none |
| `279b7bb1` | 2026-09-03 | eagmon | [#199](https://github.com/CovertLabEcoli/sms-ecoli/pull/199) | `configs/three_arm/antibiotic_cocktail.json` | Topology keys `external` → `external_mecillinam` / `external_sulfadiazine` (**B**) **and** the three pg-shape failure policies `raise_lysis` → **`lyse`** (**A**: the cell now lyses where it previously raised). | **A** (also **B**) | none |
| `76b73a19` | 2026-09-02 | cplong90 | [#183](https://github.com/CovertLabEcoli/sms-ecoli/pull/183) | `configs/meteng_vio_gfp_composed_constitutive.json`, `models/parca/composed_overlay.tsv`, `models/parca/new_gene_data/gfp/*.tsv` (7 files) | Commits the **GFP new-gene cassette data** and the composed vio+GFP overlay, making a two-insertion strain buildable from committed code. The config's own note documents a silent positional-ordering hazard between `rel_exp_adj_list` (RNA order, vio first) and `rel_trl_eff_adj_list` (monomer order, gfp first). | **A** | **APPROVED by `eagmon`** |
| `fff9091a` | 2026-09-01 | eagmon | [#182](https://github.com/CovertLabEcoli/sms-ecoli/pull/182) | `configs/mecillinam_wellmixed.json` (new) | Brings the mecillinam target-engagement run definition in-repo (retires the vEcoli-private#91 dependency). | **B** | none |
| `fb1d0250` | 2026-09-01 | eagmon | [#177](https://github.com/CovertLabEcoli/sms-ecoli/pull/177) | `configs/three_arm/spatial.json` (new) | Defines the **spatial environment** the three-arm configs inherit: 50 µm × 50 µm bounds, 10×10 bins, depth 3000 µm, diffusion 1e-2 µm²/s, uniform GLC **1.0 mM**. This is media/field data. | **A** | none |
| `677bbe90` | 2026-09-01 | eagmon | [#175](https://github.com/CovertLabEcoli/sms-ecoli/pull/175) | `processes/metabolism_redux.py` | Exchange metabolites with no row in the reduced network (e.g. `L-SELENOCYSTEINE[c]`) are dropped with a once-per-set warning instead of raising `KeyError` on the first update. Author argues it is a no-op for the LP; **classified A** because it changes results on a path that previously crashed. | **A** | none |
| `2dac7051` | 2026-08-31 | eagmon | [#138](https://github.com/CovertLabEcoli/sms-ecoli/pull/138) | `processes/gillespie.py`, 14 `configs/three_arm/*` | **Zero-volume guard in gillespie**: `kf_count = kf/denom if denom > 0 else 0.0`. Without it the first tick of a generation raised `ZeroDivisionError`, which the lineage runner's division-detector misread as a *cell division* — spawning a daughter every tick until the cell starved. Also lands the native / vecoli-free arm configs. | **A** (also B/E) | none |
| `59391f8f` | 2026-08-31 | eagmon | [#167](https://github.com/CovertLabEcoli/sms-ecoli/pull/167) | `configs/pathway_expression_carina_final.json`, `configs/fss_pathway_oe_tnaA_trpR_knockout_carina.json` | Adds the CD2 Run 4 pathway-expression and tnaA/trpR-KO run definitions. | **B** | none |
| `9e204009` | 2026-08-30 | eagmon | [#162](https://github.com/CovertLabEcoli/sms-ecoli/pull/162) | `processes/metabolism_redux.py` | Homeostatic `dm/dt` floored at `-counts`, so a bulk count can never go negative. Previously the violacein intermediates (target 0.0, consumed by the pathway ODE) went negative from tick 1 and poisoned `divide_bulk`'s binomial split at first division — every native violacein lineage silently stalled at generation 0. | **A** | none |
| `0cb3f361` | 2026-08-30 | eagmon | [#157](https://github.com/CovertLabEcoli/sms-ecoli/pull/157) | 9 `configs/three_arm/*_vecoli_free.json` | Adopts the drug-agnostic `seed_bulk_species` seam + `requires_features: [cell_geometry]`; carries **molar masses** (mecillinam[p] 325.426, mecillinam_hydrolyzed[p] 343.426 g/mol) and the `complex_with` binding declaration. | **B** | none |
| `96e85087` | 2026-08-30 | eagmon | [#155](https://github.com/CovertLabEcoli/sms-ecoli/pull/155) | `processes/metabolism_redux.py` | Adds `VIOLACEIN[c]` to `exchange_molecules` in the process (not the ParCa), creating a **secretion reaction** that a v2ecoli-native cache does not carry. Without it the native candidate secreted zero violacein and every bioproduction comparison was broken. | **A** | none |
| `86375737` | 2026-08-29 | eagmon | [#152](https://github.com/CovertLabEcoli/sms-ecoli/pull/152) | `processes/metabolism_redux.py` (+506 lines), `scripts/_compare/inject.py` | Ports the **violacein pathway kinetic ODE** from the fork: `S_VIO` stoichiometry, `NG_CPD_IDS`, `VIO_CONC_FLOOR = 1e-30`, `forward_step_np` (numpy translation of the fork's jax RHS, verified rtol 1e-6), the FBA export flux-pin, glucose-sign fix, and **`VIO_NADH_RXNS`** — 3 NADH reaction twins disabled so FBA cannot carry flux through them. | **A** | none |
| `6b213f5b` | 2026-08-28 | eagmon | [#147](https://github.com/CovertLabEcoli/sms-ecoli/pull/147) | `processes/metabolism_redux.py` | Exchange delta store changed from `environment.exchanges` (`map[overwrite[float]]`, orphaned — nothing read it) to **`environment.exchange`** (`map[float]`, accumulating), with **compartment-stripped keys** (`GLC[p]` → `GLC`). Before this, every exchange-flux KPI on the native arm reported 0.0. | **B** | none |
| `8d9d2a93` | 2026-08-28 | eagmon | [#148](https://github.com/CovertLabEcoli/sms-ecoli/pull/148) | 6 new `processes/*.py` (`permeability`, `antibiotic_transport_odeint`, `concentrations_deriver`, `field_timeline`, `well_mixed_field`, `gillespie`), `injection_topologies.py` (+189), 24 configs | Lands the **entire v2-native antibiotic process layer** (2137 lines) plus its per-process native topologies and 12 fork-free run configs. This is the commit that put the antibiotic mechanism into this repo. | **A** (also **B**) | none |
| `c2360dfd` | 2026-08-28 | eagmon | [#142](https://github.com/CovertLabEcoli/sms-ecoli/pull/142) | `processes/metabolism_redux.py` (new, 758 lines), `injection_topologies.py` (new, 68), 2 configs, `models/parca/new_gene_data/violacein_MG1655_M5/*.tsv` (12 files), `models/parca/violacein_bundle_overrides.tsv` | Lands the **native `MetabolismReduxClassic`** port (cvxpy `NetworkFlowModel` LP), the `NATIVE_INJECTION_TOPOLOGIES` map, and the **violacein new-gene dataset** (genes, RNAs, proteins, metabolites, metabolic reactions, kinetics, transcription units). | **A** (also **B**) | none |
| `d6f90f95` | 2026-08-27 | eagmon | [#137](https://github.com/CovertLabEcoli/sms-ecoli/pull/137) | `processes/pg_maturation.py`, `processes/pg_shape.py`, `processes/_pg_dividers.py` (all new, 2135 lines) | Lands the sms-owned **peptidoglycan maturation and shape** process ports, with their division-state dividers. | **A** | none |

## 2b. Two more A commits that sit *outside* the declared model paths

Listed separately because the rubric puts runners under "non-model — unless they change
what is simulated". Both change what is simulated.

| sha | date | author | PR | file | what changed | review |
|---|---|---|---|---|---|---|
| `0d1bace2` | 2026-09-09 | cplong90 | [#313](https://github.com/CovertLabEcoli/sms-ecoli/pull/313) | `scripts/run_mbp_tracked.py`, `scripts/scheduled_aeration.py` (new) | `--aeration-schedule` **parsed the file, wrote a dead config key, and exited 0 with nothing mounted**. CD2 Run 1's re-fire ran flat at 1.5 L/min on all ten seeds and raised nothing. Now the `ScheduledAeration` Step is actually mounted at flow position 0. Bioreactor (MBP), not the cell model. | none |
| `e9e79d0b` | 2026-09-02 | cplong90 | [#191](https://github.com/CovertLabEcoli/sms-ecoli/pull/191) | `scripts/run_condition_multigen_parquet.py` | The runner tested only *top-level* swap/add/exclude keys; **23 configs nest the block under `injected_processes`**, so for those the resolver returned None, the runner built plain native metabolism, and the sweep emitted a bit-exact 0.0 product at exit 0 with no warning. A silent wild-type sweep on 23 declared-strain configs. | none |

---

## 3a. Category C — opt-in, defaults unchanged (1)

| sha | date | PR | one-line |
|---|---|---|---|
| `c5c4f143` | 2026-09-09 | [#308](https://github.com/CovertLabEcoli/sms-ecoli/pull/308) | New `objective_formulation` knob on `MetabolismReduxClassic`, **default `"classic"`**; the `"plain"` path ports vEcoli MASTER's plain-redux FBA objective (5 differences: homeostatic denominator includes the dm targets; mass-weighted secretion; split kinetics slack vars; GAM; active-constraints mask). All plain-path plumbing is inert under the default. Comment under `eagmon` (self); no separate review. |

## 3b. Category D — mechanical / non-semantic (9)

| sha | date | PR | one-line |
|---|---|---|---|
| `e1bda211` | 2026-09-08 | #295 | Declares the ptools 5-view multigeneration analysis suite on all 4 CD2 run configs and drops the per-view `n_tp: 10`. Analysis output only — but it lives in `configs/`, see §5. |
| `cbf56284` | 2026-09-06 | #241 | Renames `configs/three_arm/` → `configs/experiments/`, drops the `_vecoli_free` suffix. 38 files, no content change. |
| `70033276` | 2026-09-03 | #209 | Adds `ProcessContract` metadata (summary/math/symbols) to the 5 antibiotic/field processes. The PR states: imports + the attribute only, no behavior change. Valuable *documentation* of the rate laws for reviewers. |
| `ba5c69a1` | 2026-09-03 | #198 | Swaps `cell_cell_heterogeneity` for `doubling_time_hist` / `mass_fraction_summary` in 3 configs' analysis blocks. |
| `3637f391` | 2026-09-03 | #201 | Rewrites stale "drug-blind" `_note` prose in 16 configs. Text only. |
| `416f0040` | 2026-08-31 | #164 | Emits `violacein_production_flux` as a flat `overwrite[float]` listener leaf so the ParquetEmitter can column-ise it. Adds an output; does not change the simulation. |
| `91455d7d` | 2026-08-27 | #124 | Creates `sms_modules/` (bridge scaffolding, empty `processes/`). |
| `f13aca0b` | 2026-08-27 | #127 | The vendored-tree retirement itself; the only `models/` change is moving a species-map YAML. |
| `c5a63890` | 2026-06-27 | — | Removes the `configs/cond_*_1x4.json` override files with the manifest framework. |

## 3c. Category E — experiment design (5)

| sha | date | PR | one-line |
|---|---|---|---|
| `f0a9d1b0` | 2026-09-09 | #309 | **Run 3 scale: `generations` 8 → 20, `n_init_sims` 1 → 4** (Eran confirmed 4 seeds × 20 generations × the 36-dose grid). Comment under `eagmon` (self). |
| `0651836c` | 2026-09-05 | #230 | Deletes `configs/meteng_vio_gfp_composed_constitutive.json` as fork-mirror residue — removes a run that #183 had just added. |
| `188da919` | 2026-08-31 | #171 | Run 4 screens the **native_oe** overexpression design instead of the tnaA/trpR knockout: one config added (448 lines), the other deleted. Changes which strains are simulated. |
| `e1ca115a` | 2026-06-27 | — | In-repo 1×4 override configs for the 5-condition run (acetate / basal / no-oxygen / succinate / with-AA). These are pure scale overrides (`n_init_sims: 1, generations: 4`) that `inherit_from` condition files living upstream — **the media definitions themselves are not in this repo.** |
| `f4eb0d9c` | 2026-06-27 | — | Adds the baseline 4×4 statistical manifest. |

---

## 4. v2ecoli pin history (each bump imports whatever v2ecoli changed)

The pin is the *only* channel by which upstream model change enters this repo after
2026-08-27. Oldest → newest.

| date | sha | PR | rev | what the message claims it carries |
|---|---|---|---|---|
| 2026-08-27 | `f13aca0b` | #127 | `branch = "main"` (floating) | the migration itself — **unpinned for the first week** |
| 2026-09-04 | `0b1ddc70` | #197 | `3084a15f` | #672 framework: emit paths + lineage time (first real pin) |
| 2026-09-04 | `538e8c61` | #221 | `ee85b95f` | #688 sentinel fix |
| 2026-09-05 | `266ed001` | #228 | `5db52446` | + process-bigraph pinned by rev not tag |
| 2026-09-06 | `819aadae` | #239 | `bcdade98` | run4 hive-parquet |
| 2026-09-06 | `ba049aa2` | #249 | `81183852` | advance to main; process-bigraph → #205 head |
| 2026-09-07 | `4cbe2c42` | #250 | `6eb4d675` | publishDir |
| 2026-09-07 | `759cbcd0` | #252 | `06eeae43` | re-pin both to main (#205 merged) |
| 2026-09-07 | `c2af6739` | #258 | `76610ece` | two remaining gate-4 fixes |
| 2026-09-07 | `5009eaf8` | #260 | `4bde4aaa` | colony build fix |
| 2026-09-07 | `2dd5fef0` | #261 | `6029c7fe` | analysis_options reachable via dispatch |
| 2026-09-07 | `c86f1a60` | #263 | `5836ff2f` | founders + pre-built cache + sim_data |
| 2026-09-07 | `1b01fc34` | #264 | `32ca56da` | Run 3 one-tick-collapse debug instrumentation |
| 2026-09-07 | `e85fe0bc` | #267 | `5f6a7d54` | (bundled with the ptools_metabolites change) |
| 2026-09-07 | `5fff5c79` | #270 | `2d20a158` | blocker 5 + one-tick collapse + **ParCa cache schema 3** |
| 2026-09-07 | `2e82279b` | #280 | `a9cf24ed` | **#738 reconstruction overrides** |
| 2026-09-07 | `8237e75b` | #281 | `2e54e95a` | blocker 6: sweep output typed as a dir |
| 2026-09-08 | `1c66700a` | #285 | `b9942d78` | blocker 7: gather stages the ParCa cache |
| 2026-09-08 | `55356900` | #286 | `087a030c` | #741 emit fix + #671 ptools scales |
| 2026-09-08 | `bc0ff34e` | #287 | `e4db5e67` | #743 coupled molecular emit |
| 2026-09-08 | `b7e65278` | #294 | `f0274348` | **#747 redux exchange-flux binding**, #746 lineage knobs |
| 2026-09-08 | `6299ba53` | #298 | `ad5f2f3a` | bigraph-schema jump fix — unblocks CD2 Run 3 |
| 2026-09-09 | `30b604b6` | #302 | `033a4a17` | #750 per-variant ParCa cache names, #749 |
| 2026-09-09 | `385abec9` | #305 | `0a301c18` | #751 gather knobs, #752 one gather per variant, **#753 DHPS inhibition** |
| 2026-09-09 | `74ffb930` | #307 | `8cf9a4bc` | **revert** of the generic hook (#755) |
| 2026-09-09 | `4bd7c82a` | #310 | `fa99c6e9` | **#755 generic flux-bound hook** — restores cache-compatible `sim_data.py`; #754, #756 |
| 2026-09-09 | `69f982b5` | #311 | `b9ff70b5` | analysis sweep_dir S3 fix |
| 2026-09-09 | `64d3720b` | #317 | `f99b0ca5` | #760 per-variant gather reads its staged config |
| 2026-09-09 | `e40f8699` | #319 | `8ab97597` | #761 zarr/xarray lineage emitter fix |

**Two of these are model-semantic, not plumbing**, and neither says so in its subject:
- **#305 → #307 → #310** is a *revert-and-reland cycle* around the `imposed_flux_bounds`
  generic hook. `#306`'s DHPS process is **inert** on any pin before `fa99c6e9`. So the
  same sms-ecoli config produces a different biology depending on which pin it runs
  against, with nothing in the config to say so.
- **#280 (`a9cf24ed`, "#738 reconstruction overrides")** is the upstream half of the
  `models/parca/flat_overrides/*.tsv` staged by `b2676fe2` (#272) two commits later.

Other pinned model inputs (not v2ecoli):
`ecoli-sources` `8d468b17 → af2bed7d → ce57e571 → 835d8d89 → 8348cb56 → e0fcfab1 →
0b07d7d9 → 2dfabd52 → 840bc973` (7 bumps, Jun–Aug 2026) and `ecoli-sources-private`
`f59a346e → be3c5884 → 63d42e4b → 65015df8`. These carry the reconstruction data.
Note #301's PR text: the installed `ecoli-sources@840bc973` is a **stale snapshot** whose
`metabolism_redux.py` carries only 5 of the 51 `BAD_RXNS` — a pinned data package and a
hand-ported process disagreeing about the model.

---

## 5. Where the model / non-model boundary is blurry

There is no clean separation in this repo, and the blur is load-bearing in four places.
**First, `configs/` is simultaneously the model and the experiment.** A single CD2 run
config carries, in one JSON object: which processes are injected (`add_processes`), which
are replaced (`swap_processes: ecoli-metabolism → ecoli-metabolism-redux`), the execution
order (`flow`), the *kinetic parameters* of the injected processes (`process_configs` —
`kcat 0.63`, `km 0.247`, membrane permeabilities), the species seeded into the cell
(`extra_bulk_species`, with molar masses), the ParCa reconstruction it is built from
(`parca_options.bundle_overrides`), the dose schedule, *and* the scale (`generations`,
`n_init_sims`) and the list of analyses to render. `#295` and `#309` touch the same file
type as `#303` and `#306`, and only reading the hunks separates "declared a new plot" from
"changed the transport kinetics". **Second, `sms_modules/bridge/` generators are model
authorship, not tooling.** `antibiotic_cocktail_sweep.py` is 94 lines of Python that
*defines the dose grid and onset time* — the independent variable of Run 3 — and then
writes 36 configs. Changing one literal there changes the experiment's stimulus; changing
its default base-config path (`#312`) changes the *system* being dosed. **Third, the
injection seam `scripts/_compare/inject.py` is wiring code living under `scripts/`.** It
resolves which native class fills a swapped slot, assembles its config, and bridges units;
`#222` fixed a double-wrap that produced `mmol²/L²`, `#189`/`#194`/`#196`/`#276` ported
seam fixes, and `#274` made a fork-free redux swap with no `cache_dir` refuse loudly.
By path it is tooling; by effect it decides what model is built. **Fourth, runners can
silently un-apply the model.** `#191` and `#313` are both cases where a declared model
element — an injected strain, an aeration ramp — was parsed, accepted, and then never
mounted, producing a completed run at exit 0 with no warning. Those are the most dangerous
commits in this audit precisely because they are not in a model path. A related structural
point: `sms_modules/analyses/**` is genuinely non-model, but several analyses
(`mec_ic50`, `mecillinam_species`) *reconstruct cumulative lineage time* because the
simulation's `global_time` restarts each generation — an analysis compensating for a model
property, which means an analysis bug and a model bug look alike from the plot.

Finally, and separately: **no media or condition data is defined in this repo.** The June
`cond_*_1x4.json` files `inherit_from` condition definitions that live upstream, and
`configs/three_arm/spatial.json` (GLC 1.0 mM uniform, `#177`) is the only environment
composition written here. Media changes reach CD2 through the v2ecoli / ecoli-sources
pins, invisibly.

---

## 6. Parameter and default values that changed

| what | old → new | commit / PR |
|---|---|---|
| `prop_crosslinked` (pg_maturation) | 0.20 → **0.28** (eLife 72863 supp 2) | `b2088be1` #203 |
| initial glycan pool split (pg_maturation) | `[(1-p)·n, 0]` → `[(1-p)·(2/3)·n, (1-p)·(1/3)·n]` | `b2088be1` #203 |
| pg_shape `b` | `1 - pi_out·beta` → **`1 + pi_out·beta`** | `b2088be1` #203 |
| pg_shape `a_z` denominator | `t·Etheta` → **`t·Ez`** | `b2088be1` #203 |
| pg_shape `stress_theta` | `stress_z.to(...)` → `stress_theta.to(...)` | `b2088be1` #203 |
| pg-shape failure policies (×3: critical_stress, insufficient_glycans, infeasible_physics) | `"raise_lysis"` → **`"lyse"`** | `279b7bb1` #199 |
| `BAD_RXNS` (metabolism_redux) | config list, default `[]`, never supplied → **51 IDs, hardcoded, applied unconditionally** | `6c438e50` #301 |
| `objective_formulation` (new knob) | — → `"classic"` (default; `"plain"` opt-in) | `c5c4f143` #308 |
| LP solver chain | GLOP only → **GLOP → HIGHS → CLARABEL** on raise/non-optimal | `cd0d3021` #297 |
| homeostatic `dm/dt` | unclamped → **floored at `-counts`** | `9e204009` #162 |
| `exchange_molecules` | — → **`VIOLACEIN[c]` added** (creates the secretion reaction) | `96e85087` #155 |
| `VIO_NADH_RXNS` | — → **3 NADH reaction twins disabled** (membership-gated) | `86375737` #152 |
| `VIO_CONC_FLOOR` | — → `1e-30` | `86375737` #152 |
| well-mixed field concentration | unbounded → **`max(0.0, …)`** | `0f7c2216` #304 |
| gillespie `kf_count`/`kr_count` at zero volume | `ZeroDivisionError` → **`0.0`** | `2dac7051` #138 |
| `field_timeline.decay_rates` (new) | — → `{}` default; mecillinam **k = ln2/1.4 h = 1.375e-4 /s** | `17d67194` #213 |
| `field_timeline.lineage_time_offset` (new) | — → `0.0` default | `17d67194` #213 |
| exchange store | `environment.exchanges` (overwrite, orphaned) → **`environment.exchange`** (`map[float]`, accumulating), compartment-stripped keys | `6b213f5b` #147 |
| sulfadiazine periplasm permeability | — → **3.853875269058028e-06** dm/s | `3a52c450` #303 |
| sulfadiazine cytoplasm permeability | — → **3.7999999999999996e-06** dm/s | `3a52c450` #303 |
| sulfadiazine diffusion areas | — → 4.5199999999999984e-10 / 3.895217919577645e-10 dm² | `3a52c450` #303 |
| sulfadiazine efflux (both compartments) | — → kcat **0.63** /s, km **0.247** mM, n 1.0, **enzyme_conc 0.0** (⇒ accumulation is passive diffusion) | `3a52c450` #303 |
| DHPS inhibition kinetics (new process) | — → kcat **0.38**, km_paba **7.82e-3** mM, k_i **5.15e-3** mM, cell_density 1100.0, rxn `H2PTEROATESYNTH-RXN` | `588bb043` #306 |
| mecillinam dose grid | — → `[0, 1e-5, 1e-4, 1e-3, 1e-2, 0.1]` mM | `1dbff758` #299 |
| sulfadiazine dose grid | — → `[0, 1e-4, 1e-3, 1e-2, 0.1, 1]` mM | `1dbff758` #299 |
| dose onset time | — → **10 000 s**, both drugs | `1dbff758` #299 |
| Run 3 `generations` / `n_init_sims` | 8 / 1 → **20 / 4** | `f0a9d1b0` #309 |
| spatial environment (three_arm base) | — → 50×50 µm, 10×10 bins, depth 3000 µm, diffusion 1e-2 µm²/s, **GLC 1.0 mM** uniform | `fb1d0250` #177 |
| seeded drug molar masses | — → mecillinam[p] **325.426**, mecillinam_hydrolyzed[p] **343.426** g/mol | `0cb3f361` #157 |
| ParCa reconstruction overrides | — → added metabolite concentrations, modified protein half-lives, removed RNA half-lives (3 TSVs + bundle overrides) | `b2676fe2` #272 |
| Run-4 ParCa `bundle_overrides` | absent → `models/parca/violacein_bundle_overrides.tsv` | `6ccb5cf1` #206 |
| MBP aeration | parsed but **never mounted** (flat 1.5 L/min on all 10 seeds) → ramp actually mounted | `0d1bace2` #313 |

