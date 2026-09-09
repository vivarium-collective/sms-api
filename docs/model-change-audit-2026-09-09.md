# Model-change audit: v2ecoli and sms-ecoli (2026-09-09)

> Two passes. **Part 1** classifies every commit by *effect* (did the model change?). **Part 2**, added the same evening at Jim's request, re-classifies the same commits by the *context* they were made in — migration of a scientific artifact, translation correction, scientific refinement, or plumbing — and answers whether the plumbing PRs made modeling decisions. Appendices A–B are Part 1's full reports; C–D are Part 2's; E is Part 2's rubric.

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

# Part 2 — the same changes, classified by the context they were made in (2026-09-09, second pass)

**Question asked (Jim, 2026-09-09):** the models were migrated from a repo with the v1 vEcoli structure and had to be injected and somewhat refactored — a migration PR is the transfer of a scientific artifact and should say so; recent composition debugging may have corrected translation mistakes; and Alex's and Jim's plumbing PRs, even where a Claude session wrote them with a scientific-sounding rationale, were never meant to make modeling decisions. So: for each change, is it debugging software or refining the science, judged by the PR's own context?

**Method.** Same two repos, same commit lists as Part 1 (every A/B/P-A row, plus sms-ecoli's C/E rows and the model-semantic pin bumps). This pass read the PR body, every comment and review, and the commit message, and classified **intent** and **authority** rather than effect: **M** migration of a named source (with the fidelity claim and admitted deviations recorded); **T** translation correction (the stated reason is "v2 diverged from vEcoli; restore it"); **S** a scientific refinement or modeling choice with no source-model authority (justification quoted verbatim); **W** plumbing; **W!** plumbing whose diff nonetheless embedded a modeling decision. Authority = what the PR appeals to: vEcoli, a citation, a team decision, "it no longer crashes", or nothing. The rubric is Appendix E; the two full reports are Appendices C and D.

## Headline findings

1. **The engineers' plumbing PRs did not make modeling decisions.** v2ecoli: one A/B row under an engineer login in the whole history (#356, a serialization-name fix that resolves to the identical type), zero W!. sms-ecoli: eight rows under `AlexPatrie`/`jcschaff`, seven clean W and one W! by the letter only — #312 repointed the Run 3 sweep generator's default base to the config that the scientist-login PRs #303/#306/#309 had just designated as Run 3. #299's dose grid, onset and scale were checked byte-for-byte against `vEcoli-private@antibiotics-cd2`'s `antibiotic_cocktail.json` and are identical. #297 (solver fallback) disclosed its degenerate-vertex consequence to @cplong90 and is the only PR in the debugging era where a modeling-relevant consequence was written down, addressed to a named scientist and approved on the record. #314 (skip a non-integrable tick) changes behaviour only on a path that previously killed the lineage; its residual risk is governance (nothing counts skipped ticks), not physics.
2. **Where plumbing did embed modeling decisions, it was under scientist logins, and mostly in the original translation.** v2ecoli has 12 W! rows, all under `eagmon`/"Eran", 8 of them April–May port commits and 3 more from June; only one (#393, media substitution "chosen for runnability") is later. sms-ecoli has two: #162's non-negativity clamp on the homeostatic dm/dt of **every** metabolite on every redux tick, added to fix a crash that the source model avoids structurally (log-space intermediates) — no source authority, no citation, no review, in every native redux result since 2026-08-30; and #230, which deleted a run config three days after it was approved, mislabelled as fork residue.
3. **The largest single item is not in Part 1's tables at all.** Direct commit `c9053136b` (2026-04-12), whose body opens "Lexical cleanup, no behavior change", also changed `DEFAULT_FEATURES` from `['ppgpp_regulation','trna_attenuation']` to `['ppgpp_regulation']` with the comment "disabled to match v1 default". tRNA attenuation has been off by default in every v2ecoli run since and still is at the tip (`ecoli_baseline.py:601`). The cited authority is "v1 default", so this may be a *correct* translation — but it landed inside a commit that declared itself behaviour-neutral, verified by a dry-mass trajectory that could not detect it. Supercoiling, extracted as a feature module the same week and "previously always-on", was never restored. **Whether vEcoli's defaults actually have these two off is a question only Eran and Chris can answer**, and it matters for every comparison the project has published.
4. **The migration's fidelity claim is thinner than its README.** The initial port names its source as a *branch* (vEcoli "composite") and pins it as an editable local path, never a commit; the "identical biological output" claim in the README rests on one scalar at t = 60 s (384.6 vs 384.5 fg). The best number the repo ever published is #112's 0.27 % dry-mass agreement at 2,520 s — but the reference arm's sim_data was regenerated out-of-repo, not archived. #89's title says "bit-equivalent"; its body says 0.5 % relative tolerance on four scalars. The knowing deviations — seven processes taken out of the allocator on asserted biology, the murein FBA objective adjustment deleted as a "testing hack", per-process RNG re-seeding, supercoiling off, the EcoCyc 29.6→29.1 rollback landed under a CI/caching PR with "biology-domain work, not in scope" deferred and never resumed — are each in a commit body and nowhere a scientist would read them together.
5. **sms-ecoli's migration is better documented than v2ecoli's, and says plainly that it is transferring an artifact.** #137 (peptidoglycan) claims "verbatim physics, diff-verified byte-identical" and its plan says "do NOT re-derive or improve the biophysics"; #152's numpy ODE matches the fork's jax RHS to ~1.8e-12; #156 exists only to prove parity (four processes at rel 1e-6, no divergences). Deviations are declared: a reconstructed `DEFAULT_MEDIA_RECIPES` fallback in pg_shape (media data authored here, not ported); gillespie on tau-leaping because CI has no C++ toolchain; #148's whole antibiotic layer landing with the dose inert ("drug delivery is v2ecoli-blocked"); #152's 2–3× violacein titer gap declared "a finding, not a bug" with no scientist comment. The design doc's fidelity programme (three arms: Arm1≠Arm2 ⇒ bridge bug, Arm2≠Arm3 ⇒ port bug) was never completed — Arm 1 became reference-only before any port after #137.
6. **The translation corrections are real and are the right kind of fix.** Nine T rows in v2ecoli and six in sms-ecoli each name the vEcoli behaviour they restore (e.g. #304 "match vEcoli's nonnegative_accumulate", #203's three peptidoglycan mechanics bugs from vEcoli-private #93 — which was still a draft when adopted; #156's parity test had deliberately locked the bugs in and had to be rewritten). One caveat for the scientists: #203 keeps one of the source's remaining inconsistencies on purpose "to mirror the source".
7. **The S list is short and belongs to Eran and Chris.** v2ecoli: #638's 60 mM ammonium pool ("~2× the M9 value, sized so nitrogen is not the binding constraint"), #137/#123's DnaA machinery (the only rows with evidence of a named non-Claude scientist — 8 feedback rounds with Rashmi/Haochen, kept as files rather than comments, merged from Draft by mistake), #243's Shape deriver (the only literature citation in the audit), #271's ppGpp Hill gain `b²/(b+K)`, K = 1e-11, chosen to make two engines agree and absent from its PR body. sms-ecoli: #199's `raise_lysis → lyse` policy (title says eagmon-approved, thread records no approval), #213's first-order mecillinam decay (Brouwers 2020, opt-in), #309's Run 3 scale ("Eran confirmed", reported not linked), #171's Run 4 strain choice. Two adjacent numbers with no primary citation anywhere in either repo: #306's DHPS kinetics (kcat 0.38, km 7.82e-3, k_i 5.15e-3).
8. **Governance is the gap, not intent.** Zero inline review comments across all 67 v2ecoli PRs and all 43 sms-ecoli PRs examined; every comment and review under the same two logins; #128 self-flagged "⚠️ Behavioral change — please review" (division moved from D-period- to mass-gated) and received nothing; five sms-ecoli PRs carry a self-comment "held for Eran's go" and merged 2–20 minutes later with no recorded go; #244 claims "un-wires all dnaA mechanisms" and is true only of the execution-layer list.

## Cross-tabs

**v2ecoli (84 rows):** M 11 · T 9 · S 6 · W 46 · W! 12. By login: `eagmon`/"Eran" 67 rows (all 12 W!), `cplong90` 16 (0 W!), `AlexPatrie` 1 (W), `jcschaff` 0.
**sms-ecoli (50 rows, three carrying two intents):** M 17 · T 6 · S 4 · W 23 · W! 3. By login: scientist 42 rows (2 W!), engineer 8 rows (1 W!, #312, see finding 1).

## What this means for how we work (process, not model)

- A **migration PR** should name its source to the commit, state its fidelity criterion before measuring, and list "changed on the way" under its own heading. #208 and #738 in v2ecoli and #137/#152/#156 in sms-ecoli are the templates; the April port is the anti-template.
- A **plumbing PR that must choose a value or a rule** should do what #297 did: a "caveat (science side)" section addressed to a named scientist, and merge only on that person's approval. #162 is the counter-example.
- **Feature defaults are model content.** `DEFAULT_FEATURES`, `BASE_EXECUTION_LAYERS`, the failure policies and the `flow` blocks should be diffed and named in every PR that touches them, and a checked-in manifest test (Part 1, suggestion 4) would have caught `c9053136b`.
- The two open questions for Eran and Chris the people, stated as questions: (a) are tRNA attenuation and supercoiling meant to be off by default, as vEcoli's defaults or as a v2 choice? (b) is #162's global clamp the intended model, or should the violacein intermediates live in the ODE's log-space state as they do in the fork?

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

---

# Appendix C — v2ecoli intent report (Part 2)

## v2ecoli intent audit (second pass): why was each model-changing commit made?

**Scope.** Every row of the first-pass report's §2 tables — A (32 rows), "A commits from the
April–May port era" (12 rows), B (38 rows) — plus the initial commit `68e4c12ab`, plus one
addendum row the first pass did not surface (`c9053136b`, §6). **84 rows total.**
**Method.** For each row: the PR body, every PR comment, every PR review, every inline review
comment (`gh api .../pulls/N/comments`), and the squashed commit body. Read-only; nothing
posted, pushed or checked out. Times are UTC.

**Two facts to hold while reading the review column.**
1. **Every inline review comment count in this audit is zero.** `gh api .../pulls/<N>/comments`
   returned `0` for all 67 PRs queried. There is no line-level review anywhere in the
   model-changing history of this repo.
2. **Every comment and every review on every PR in this set was posted by `eagmon` or
   `cplong90`** — the two scientist logins, which are also the logins their Claude sessions post
   under. No third party ever commented. A PR body or review written by a Claude session is not
   a human endorsement, and this audit never records one as such.

---

### 1. Totals

#### Intent × effect

Effect codes are taken from the first pass unchanged (A = model semantics, B = declared
interfaces/wiring, P-A / P-B = the ParCa/reconstruction equivalents, "port" = the initial commit).

| intent | A | P-A | B | P-B | port | **total** |
|---|---|---|---|---|---|---|
| **M** migration | 1 | 1 | 8 | 0 | 1 | **11** |
| **T** translation correction | 5 | 1 | 3 | 0 | 0 | **9** |
| **S** scientific refinement | 3 | 0 | 3 | 0 | 0 | **6** |
| **W!** plumbing that decided modeling | 11 | 1 | 0 | 0 | 0 | **12** |
| **W** plumbing | 19 | 3 | 23 | 1 | 0 | **46** |
| **total** | **39** | **6** | **37** | **1** | **1** | **84** |

#### Intent × login class

Login classes per the rubric. `AlexPatrie` / `jcschaff` = engineer; `eagmon`, `cplong90`,
git authors `Eran` / `Eran Agmon` = scientist. **The logins are Claude sessions much of the
time; this table says "authored under login X", not "person X typed it".**

| intent | eagmon / "Eran" | cplong90 | AlexPatrie | jcschaff | total |
|---|---|---|---|---|---|
| M | 11 | 0 | 0 | 0 | 11 |
| T | 6 | 3 | 0 | 0 | 9 |
| S | 5 | 1 | 0 | 0 | 6 |
| **W!** | **12** | **0** | **0** | **0** | **12** |
| W | 33 | 12 | 1 | 0 | 46 |
| **total** | **67** | **16** | **1** | **0** | **84** |

**The headline answer to "did the plumbing PRs make modeling decisions".** Only **one** row in
the whole A/B set is under an engineer login (`868cf2a36`, AlexPatrie, #356), and it is clean
`W` — a serialization-format fix that resolves to the identical registered type, with the PR
saying so explicitly. **Zero W! rows under engineer logins.** All 12 W! rows are under
`eagmon` / `Eran`; **`cplong90` has none either.**

The W! population is also *old*: 8 of 12 are from the April–May port window and 3 more from
June. Only one (`3c5fe1a2c`, #393, 2026-07-26) is later. The "plumbing PRs made modeling
decisions" risk Jim was looking for is real but it is **concentrated in the original
translation, not in the recent dispatch work.**

---

### 2. The migration: what was claimed, and what was verified

#### 2a. The initial port (April 2026, direct commits, no PR, no review)

**`68e4c12ab` (2026-04-10, "Initial v2ecoli: pure process-bigraph partitioned E. coli model").**
The entire commit body is four lines: *"Port of vEcoli's composite branch to pure
process-bigraph with no vivarium-core dependency. Partitioned architecture only
(requester/allocator/evolver pattern)."* **The source is named as a branch, never as a commit.**
No vEcoli SHA appears in this or any other April commit — I grepped every commit body from
2026-04-09 to 2026-04-25 for a SHA or a `CovertLab` reference and found none. `pyproject.toml`
at this commit pins the source as `vecoli = { path = "../vEcoli", editable = true }` — a local
editable sibling checkout. **The scientific artifact that was transferred is therefore
identified only as "whatever was in `../vEcoli` on that machine on 2026-04-10."** That is the
single most consequential provenance gap in the repo.

**`339429637` (2026-04-10, "Port processes from vEcoli composite branch with exact schemas",
34 files, +8707/−4672).** The declared-surface port. *"Replace all process files with vEcoli
versions (exact config_schema, inputs/outputs, topology, and update logic)"*, *"Copy schema.py,
schema_types.py, data_predicates.py from vEcoli"*, *"Regenerate sim_data_cache.dill from
vEcoli's LoadSimData"*. Fidelity claim: **"exact"**, asserted, not measured. The body ends with
an admission that the port is incomplete: *"WIP: Process __init__ methods still reference
defaults keys not in config cache."* No review of any kind.

**`a8de7718f` / `5263924a3` / `247578781` / `9531bbd39` / `967f63891` / `bff33e036`
(2026-04-10→11).** The six-step schema migration. Each says explicitly that vEcoli's own type
declarations did not survive the transfer intact: `a8de7718f` — *"vEcoli's string-based port
types … don't parse correctly in current bigraph-schema. Need to replace inputs()/outputs()
return values with object-based types … while keeping all other process code from vEcoli."*
`967f63891` deletes `ports_schema` (−1098 lines) and replaces per-port pre-population with a
713 KB dill pickle of extracted vEcoli defaults. The fidelity evidence offered at each step is a
**single scalar at a single time point**: *"Benchmark: 384.6fg, 1.12x — no regression."* Three
of the six commits carry that identical line. No review.

**`3a8add97e` (2026-04-10, "Fix partitioned architecture: cell now grows correctly").** The
commit that made the port viable: *"Initialize next_update_time for all partitioned processes
(0.0)"* — requesters/evolvers gate on it, so they had never fired. The fidelity claim for the
whole port is stated here in full: *"Benchmark (60s): dry_mass=384.6fg (matches vEcoli 384.5fg),
1.12x ratio."* **That is the entire verified basis of "identical biological output": one mass
number, at t = 60 s, before the first replication event.**

**The README and STATUS of that week (`a3e5bbadc`, 2026-04-11)** state the fidelity claim to the
public: *"It ports all 55 biological processes from vEcoli with identical biological output and
comparable performance"*, with a table row *"Mass difference | — | 0.0%"* footnoted to the same
60-second benchmark. STATUS.md is more honest in the same commit: *"Config defaults loaded from
pickle … rather than inline in source files"*, *"WCM division fires via exception handling
(Division step tries structural modification that crashes — bridge catches and handles)"*,
*"Daughter EcoliWCM processes start fresh (don't inherit mother's internal state)"*.

**`0641f9800` / `1a5c0abe2` / `0e282f535` (2026-04-11) — what was knowingly changed.** These are
the three "remove partitioning ceremony" commits, and they are the ones a reader of the README
would not expect. Seven processes are promoted `PartitionedProcess → Step` on **asserted
biological grounds with no vEcoli authority cited** — *"TF-ligand binding is local"*,
*"phosphotransfer is system-specific"*, *"water/NMP competition is marginal"*, *"RNAP pool not
shared with ribosome init"*. vEcoli partitions all seven. `0641f9800` additionally states
*"Metabolism: remove reduce_murein_objective testing hack"* — deleting an FBA objective
adjustment (`CPD-12261[p] /= 2.27`) — and changes Complexation to *"cache Gillespie result from
request phase, only re-run in evolve if allocation differs"*, a different RNG stream. All three
are classified **W!** below.

**`09094fe16` / `bd48262f0` / `0223c7078` (2026-04-11) — features knowingly dropped, then two of
three restored.** `09094fe16` extracts supercoiling (a 270-line block out of `ChromosomeStructure`)
and ppGpp regulation into feature modules and sets `DEFAULT_FEATURES = []`; `bd48262f0` does the
same for tRNA attenuation. Both were, in the commits' own words, *"previously always-on"*.
`0223c7078` restores two of them the same day — *"DEFAULT_FEATURES now includes ppgpp_regulation
and trna_attenuation … These were previously always-on but were disabled when the features were
extracted as composable modules"* — and **silently leaves supercoiling out. It is still off at
the tip** (`DEFAULT_FEATURES = ['ppgpp_regulation']`, `ecoli_baseline.py:601`). tRNA attenuation
was then turned off again the next day by a commit that declared itself behaviour-neutral (§6).

**`c454a2726` (2026-04-20, merged as #25) — the EcoCyc rollback.** PR #25's body is entirely
about cache fingerprinting and CI and **does not mention a knowledge-base change at all**. The
squashed commit body does, in full: *"v2parca commit 226dcce refreshed 10 BioCyc-sourced TSVs
from the EcoCyc API (v29.1 → v29.6). The refresh introduced inconsistencies that make
`SimulationDataEcoli.initialize()` raise"*, and then: *"Until the data inconsistencies are fixed
properly (biology-domain work, not in scope here), roll the 10 refreshed TSVs back to the
pre-226dcce state."* Two named breakages (a hybrid-TU check on TU0-6021; a ~15 Da mass-balance
assertion on MONOMER-51_ACETOACETYL-COA_RXN), and the note that *"Upstream vEcoli ParCa fails
identically — this is inherited from their KB."* The whole-cell model has run on EcoCyc **v29.1**
ever since, and the deferral was never picked up. Classified **W!**.

#### 2b. Later migration PRs (porting from vEcoli / vEcoli-private / the fork)

**#208 `1bca6e82e` (2026-06-13) — the model M row, and the best-documented one.** *"Ports the one
science improvement from vEcoli `master` since v2ecoli forked (2026-04-10) that is both important
and portable: the two-component-system / monomer-counts correctness bundle (upstream PR #415)."*
Source named down to the upstream PR. **Two deviations declared under their own heading, "Two
deliberate adaptations vs upstream":** (1) *"`raise` → `warn` on compartment mismatch. Upstream
raises to force a `modified_proteins.tsv` edit; in v2ecoli that flat file ships in the pinned
`ecoli_sources` package (not editable here)"*; (2) a *"Defensive `getattr` fallback to
`molecule_names`"* because v2ecoli builds sim_data from a pickled fixture. It also states what
is **not** yet true: *"A full ParCa re-run … activates the 4-extra-monomers + compartment
canonicalization in real sim_data (the fixture currently predates the port)."* This is what a
migration PR should look like. Review: none.

**#738 `a9cf24ed8` (2026-09-08) — the three vEcoli-private reconstruction overrides.** *"the
v2ecoli code that consumes them was never ported — so the parameters were **inert** … This ports
the vEcoli-private **code halves** faithfully (exact diffs, no approximation)."* Each of the
three cites its vEcoli-private commit (#84; #79 / `f4e9cc0a`; `b3e5a737` + `1bcbf91e`) and the
data files are *"copied verbatim from vEcoli-private's base flat"*. Declared deviation: the data
ships as v2ecoli `flat_overrides/` rather than in the base bundle, *"so a plain `v2ecoli-parca`
resolves them"* — i.e. **the port makes the three parameters unconditional on every ParCa build**,
which the PR states plainly. Verification is a full 52-condition chassis build with numbers
(pABA 8e-6 M, DHPPP 1e-8 M, MurD half-life 1914.725 min vs *"36 s before this PR"*). The comment
thread is four consecutive self-comments by `eagmon` that assert the TU0-941 item is inert,
retract that, then re-assert it — a visible correctness wobble with no second party. Net effect
is two effective and one staged override, unconditional, unreviewed by anyone else.

**#468 `ebb3c7c0f` (2026-08-07) — precedence, not a port, but a reconstruction-authority
decision.** *"v2ecoli's four whole-file overrides won over **any** base — including a genotype
variant. One of those keys is `dna_sites`."* The fix protects a variant's own generated keys.
The reason it was done this way rather than upstreaming the data is stated and is scientific:
*"those boxes are **Phase-1-provisional** (low-affinity coords eyeballed, re-anchored in Phase 2
per `407b5b42`) … Promoting still-changing model content into the shared supplier package is
wrong."* Authority is the design thread on issue #466. WT bundles byte-identical.

**#590 `13bcc44a9` (2026-08-24) and #637 (2026-08-31), both cplong90 — the new-gene-insertion
joins.** #590: *"`KnowledgeBaseEcoli` joins **8 of the 12** files a new-gene insertion can ship"*,
and the three missing ones are the reactions, kinetics and operon — *"every flux and yield readout
is a structural zero that is indistinguishable from a genuine 'not produced' result"*, measured
as *"0 of its reactions reached `reaction_stoich`"*. #637 (a P-C row, outside the first-pass
tables) adds multi-cassette support and establishes by control experiment that cassettes must be
spliced high-to-low: *"The same cassette lands ~1.96 kb apart depending only on whether another
insertion was present."* Both are careful, both are measured, both name the failure mode as
silent. #590 carries the only `APPROVED` review in the P-A set (from `eagmon`).

**#112 (2026-05-31) — the vEcoli vs v2ecoli comparison report.** The strongest fidelity number
the repo ever published for the port as a whole: *"**Result @2520s:** vEcoli **11.9×** vs v2ecoli
**14.9×** wall-time; final dry mass **707.2 vs 705.3 fg**, chromosomes 2/2, forks 4/4."* That is
**0.27% on dry mass at 2520 s** — a real, run-to-division comparison, and materially better
evidence than the April benchmark. Note it also records that *"vEcoli's `sim_data` was regenerated
from current master via ParCa (out-of-repo)"* — the reference arm's parameters were rebuilt, not
archived. Merged 21 seconds after it was opened.

**#89 (2026-05-28) — the "bit-identical" claim, checked.** The PR title says *"bit-equivalent
kinetics + metabolism speedups"*, but the body's actual claim is weaker and is stated honestly:
*"All changes preserve trajectory equivalence at every 120 s sample point of `dry_mass`,
`cell_mass`, `effective_elongation_rate`, and `fba_objective`, verified at **`tol_rel=0.005`**."*
**0.5% relative tolerance on four scalars is not bit-identity**, and the PR does not claim it is —
but the word "bit-equivalent" in the title does, and that is the phrase that propagates. The same
PR volunteers a correction of its own earlier numbers (*"Earlier non-paired measurements quoted
higher numbers — 5–7% — but those were partly thermal drift artifacts"*), so the honesty is real;
the title is the problem.

#### 2c. Do the descriptions make clear that a scientific artifact was being transferred?

**Partly, and decreasingly with time.** The April commits do say "port … from vEcoli" in their
subject lines, so a reader knows *something* came from elsewhere. What they do not do — not once —
is (a) pin the source to a commit, (b) state a fidelity criterion before measuring, or (c)
separate "translated faithfully" from "changed on the way". The README's *"identical biological
output"* is backed by one scalar at t = 60 s. The knowing deviations — seven processes taken out
of the allocator on asserted biological grounds, the deleted murein objective adjustment, the
per-process RNG change, supercoiling left permanently off, the EcoCyc v29.1 rollback — are each
described somewhere in a commit body, but **never in a document that a scientist reading the
README would find**, and never together. STATUS.md's "Known Limitations" section, which is the
one place a reader would look, lists none of them.

By contrast the *later* migration PRs (#208, #738, #590, #637) are exemplary on exactly the axes
the early ones miss: named upstream commit, explicit "deliberate adaptations vs upstream"
sections, measured before/after values, and an honest statement of what is still inert. The
practice improved. It improved **after** the artifact had already been transferred.

---

### 3. Full table (most recent first)

`sha8 | date | PR | login (class) | effect | intent | authority | stated motivation | embedded modeling decision | human endorsement?`
Quotes are ≤ 40 words. "endorsement" = a comment/review by the *other* scientist login, and is
still not proof a person read it. `sc` = scientist login, `eng` = engineer login.

#### A — model semantics

| sha8 | date | PR | login | eff | intent | authority | stated motivation | decision embedded | endorse? |
|---|---|---|---|---|---|---|---|---|---|
| `a9cf24ed8` | 09-08 | #738 | eagmon (sc) | P-A | **M** | vEcoli-private | "This ports the vEcoli-private **code halves** faithfully (exact diffs, no approximation)." | — (deviation: data ships as v2ecoli overrides, so effective on *every* build) | no — 4 self-comments incl. a claim, retraction, re-claim |
| `6c00a11fd` | 09-04 | #683 | eagmon (sc) | A | W | crash | "a caller that declares only `swap_processes` gets `ecoli-metabolism-redux` built with an **empty config** … one-tick collapse that still reports success" | — | no. Re-lands a change Chris had closed (#667) after replacing it with a guard |
| `5add30cf9` | 09-04 | #679 | cplong90 (sc) | A | W | none (measured) | "a cell in an anoxic reactor was told oxygen was available, indefinitely … The apparent concentration scales with the timestep" | scope choice: O₂ republished post-consumption, **CO₂/glucose/NH₄ deliberately not**, exemption "conditional on CO2 being net-secreted" | no |
| `9785729c0` | 09-02 | #653 | eagmon (sc) | A | W | crash | "its `external` species stayed `None` → `NaN` and the ODE crashed at 1 s with `solve_ivp: y0 must be finite`" | — | no |
| `268515f0d` | 09-02 | #638 | cplong90 (sc) | A | **S** | none | "Ammonium is now a finite medium pool … Before, it was static from the media recipe and effectively infinite." | **`ammonium_medium_mM = 60`**, chosen: "~2× the M9 recipe value (30.272 mM), sized so nitrogen is not the binding constraint at the OD10 working point" | `eagmon` APPROVED review |
| `63cd60f76` | 09-02 | #648 | cplong90 (sc) | A | W | none | "the single-cell path was the only route to an injection, so population- and reactor-scale runs could not express a capability the single-cell path already had" | — (PR retracts its own "silent failure" framing in a second commit) | `eagmon` APPROVED |
| `0c76bb542` | 09-01 | #640 | eagmon (sc) | A | W | none (audit) | "an injected batch run degraded to a **basal FBA lineage with no error**" | — | cplong90 comment (raising the sibling gap) |
| `167668af5` | 08-31 | #632 | cplong90 (sc) | A | W | none (store contract) | "the reactor drained in proportion to **elapsed time rather than cell demand** — over N ticks, ~N/2 too much" | — | no (two self-commissioned review rounds, both described in-body) |
| `44bd8ea15` | 08-30 | #591 | eagmon (sc) | A | W | none (reproducibility) | "they integrate the wrong represented population for `chunk_boundary − division_tick` ticks — a count set by `chunk`, an emit-cadence knob" | — | cplong90 validated and reported **the acceptance bar not met**, then partly retracted; merged anyway |
| `6bcc29d66` | 08-28 | #623 | eagmon (sc) | A | W | none | "every daughter silently reverted to the unperturbed cached configs at division. This breaks any multi-generation perturbation study." | — | no |
| `2ecb11cab` | 08-27 | #610 | eagmon (sc) | A | W | crash | "a **`ZeroDivisionError: float division by zero`** — whose message contains 'division' — is silently mislabeled as a genuine division" | — | no |
| `8f5580622` | 08-27 | #612 | eagmon (sc) | A | W | crash | "returned `{}` (no `next_update_time`), which the global clock reads as a non-advancing 0.0 interval and deadlocks the composite" | scheduling rule: skipped Evolver now reschedules +1 timestep (prior behaviour was a deadlock, so no results moved) | no |
| `89e94aa37` | 08-27 | #607 | cplong90 (sc) | A | **T** | vEcoli (fork) | "the fork's `LoadSimData` computes `generation = len(agent_id)` … That is the only mechanism by which a config's staged shift ever takes effect" | — | no |
| `f2038e39a` | 08-27 | #611 | eagmon (sc) | A ⚠ | W | crash | "a downstream unit conversion `mol / (volume * N_A)` raises **`ZeroDivisionError`** on the first tick"; "Pure wiring fix — every forwarded kwarg already exists on `baseline()`" | — | no |
| `fdeb3243d` | 08-19 | #539 | cplong90 (sc) | A | W | none (definitional) | "Every consumer of those is on a dry basis, so all three were overstated by the wet/dry ratio, **measured at 3.3315**" | — (derived biomass moves 3.33×; underlying sim bit-identical, shown 7200/7200) | no |
| `25a6a7949` | 08-21 | #568 | cplong90 (sc) | A | W | none | "Metabolism seeds **unlimited** molecules at `inf` … and no delta can move `inf`" | deliberate: "**`+inf` is allowed** — it is this model's encoding of 'unlimited'" | no |
| `1e6ecc5a8` | 08-21 | #550 | cplong90 (sc) | A | W | none | "**Zero matches, every tick.** #541's original claim that the reverse path was 'complete for gases' … was wrong: it was complete for nothing." | exchange scale `cells_per_agent` → `population.cell_count`, argued from mass conservation | no |
| `2fa846368` | 08-20 | #548 | cplong90 (sc) | A | W | none (documented contract) | "The store kept the stale 20.0 mmol/gDCW/h cap regardless, and the cell went on consuming a substrate that was gone." | — | no |
| `f98218a93` | 08-19 | #535 | cplong90 (sc) | A | **T** | vEcoli / the fork | "resolving `ecoli.library.sim_data` to the **installed `vecoli` package** rather than to the fork the caller named … The failure is silent." | — | no |
| `3c5fe1a2c` | 07-26 | #393 | eagmon (sc) | A | **W!** | none | "`build_generator` strictly rejects unknown params, and studies carried params/composite-refs the generators don't accept." | **"Comparison studies now run the lightweight `media:` perturbation (chosen for runnability), NOT the calibrated per-condition ParCa re-fit"** | no |
| `8d636e06c` | 06-29 | #293 | cplong90 (sc) | A ⚠ | **T** | **vEcoli** | comment: "Is this bug also in vEcoli? No — it's a port-introduced regression," quoting vEcoli's `"_updater": "set"` on the same store | — | `eagmon` APPROVED |
| `9675fe4f7` | 06-27 | #289 | eagmon (sc) | A | **T** | vEcoli comparison | "a stale per-condition bundle could bake the wrong `media_id` (e.g. `with_aa`→`minimal`) … read as a bogus 'port divergence'" | — | no |
| `29c4dc262` | 06-24 | #271 | eagmon (sc) | A | **W!** | mixed | PR body is *only* about the comparison harness; the three model changes are absent from it | see §4 — `d_period=True` default (cites vEcoli in-code), **ppGpp Hill gain with a new `K = 1e-11`**, ParCa ppGpp `adjustment = 1` floor | no |
| `bf60df0d4` | 06-16 | #244 | eagmon (sc) | A | **W!** | team/process | "PR #137 (a **draft** dnaa investigation PR) was merged to main by mistake … everyone's default `baseline` model changed." | claims "the execution layers are now **byte-identical to pre-#137** (verified)" — but 315 DnaA boxes and the dnaA autoregulation code are still on `main` today (§4) | no |
| `717b976af` | 06-15 | #137 | eagmon (sc) | A | **S** | none / Rashmi | "**Draft — ongoing investigation.**"; "autoregulation **resolves the V-tension** the dnaa-3 V-sweep proved no constitutive V could — it caps the DnaA peak (1567→635, ~2.5×)" | DnaA replication-initiation on by default; `AUTOREG_STRENGTH = 0.8`; 307→315 DnaA boxes | co-authored `@RashmiKaldera`; 8 Rashmi/Haochen feedback rounds exist **as files**, none as GitHub comments |
| `4c439bd0e` | 06-06 | #128 | eagmon (sc) | A | **W!** | crash | "Coerce `dry_mass` (and the stored `threshold`) to plain fg floats" — framed as units plumbing | **self-disclosed**: "Division timing is now **mass-gated** (Division step) rather than **D-period-gated** (MarkDPeriod)" … fires "~27s before" | **no** — the PR says "⚠️ **Behavioral change — please review**" and received zero comments and zero reviews |
| `5e7f02a00` | 06-06 | #123 | eagmon (sc) | A | **S** | none | "DnaA-ATP hydrolysis modeled as a kinetic equilibrium reaction (the mechanism the `dnaa2-bf8b82e-*` runs depend on)" | 2 new default equilibrium reactions; a two-phase ODE solve; and — **not mentioned in the PR** — `_moleculeRecursiveSearch`'s guard `val != 0 → val < 0`, affecting all multi-product reactions | no |
| `e8d61b1d0` | 06-18 | #275 | eagmon (sc) | P-A | **T** | **vEcoli** | "vEcoli strips the tag (`monomer["id"][:-3]`); v2 didn't." Verified: "max\|Δ\| **0.24 → 1.1e-16** (exact)" | — | no |
| `ebb3c7c0f` | 08-06 | #468 | eagmon (sc) | P-A | W | team (#466) | "The override then discarded it and restored **pre-deletion** coordinates. The variant validated, the manifest was correct, and one of its keys never reached ParCa." | precedence rule: a variant's generated keys beat `parca_overrides.tsv` (WT byte-identical) | no |
| `13bcc44a9` | 08-24 | #590 | cplong90 (sc) | P-A | W | none | "every flux and yield readout is a **structural zero that is indistinguishable from a genuine 'not produced' result**" | guard choice: an added TU may not reach back into the original genome — "**Checked rather than clamped**" | `eagmon` APPROVED |
| `e9e4c6930` | 08-01 | #446 | eagmon (sc) | P-A | W | none | "Restores the ParCa cache's two guarantees (they were inoperative) and makes the pipeline fail loud instead of silently shipping a mis-calibrated or partial fit. **Calibration-neutral**" | — (SCHEMA_VERSION 1→2 invalidates every cache; a partial fit now aborts) | no (1 self-comment) |

#### A — April–May port era (direct commits; commit body is the only context except where a PR is noted)

| sha8 | date | PR | login | eff | intent | authority | stated motivation | decision embedded | endorse? |
|---|---|---|---|---|---|---|---|---|---|
| `38ee8d22c` | 05-25 | #76 | eagmon (sc) | A | **W!** | none | PR frames the whole set as "**Eight infrastructure items** … All pure infra — **zero biology coupling**" | per-process RNG seeds via `crc32(process_name, master_seed)` — **changes every trajectory in the repo from this commit on**; the "zero biology coupling" claim is false for item 1 | no |
| `d6743606f` | 05-06 | #30 | eagmon (sc) | A | W | crash | commit body: "`promote()` injected the `overwrite` wrapper at the parent map level, so … siblings [were dropped] … the next Evolver hit `KeyError: 'allocate'`" | — (PR body, an install-simplification PR, never mentions it; the squashed commit body documents it fully) | no |
| `2147fca41` | 04-13 | — | Eran (sc) | A | W | crash | "The resulting ModuleNotFoundError was raised inside `Division.next_update` and silently swallowed by process-bigraph" | — | — (direct commit) |
| `c2c95db2e` | 04-12 | — | Eran (sc) | A | W | prior behaviour | "the departitioned and reconciled generators still expected those 8 to be partitioned and silently returned None for them — so they were dropped from the simulation entirely" | — | — |
| `0e282f535` | 04-11 | — | Eran (sc) | A | **W!** | none | "Part 3 (complete): The allocator now manages only processes with genuine cross-process resource competition." | 4 processes leave the allocator on asserted grounds — "water/NMP competition is marginal", "RNAP pool not shared with ribosome init"; they now read un-partitioned counts | — |
| `1a5c0abe2` | 04-11 | — | Eran (sc) | A | **W!** | none | "Remove PartitionedProcess ceremony where no resource competition exists." | 3 processes → Step on asserted biology ("TF-ligand binding is local", "phosphotransfer is system-specific"); Equilibrium's greedy flux correction now runs on full, not allocated, counts | — |
| `0223c7078` | 04-11 | — | Eran (sc) | A | **T** | prior / wcEcoli | "These were previously always-on but were disabled when the features were extracted as composable modules." | **supercoiling is not restored** and is still off at the tip | — |
| `0641f9800` | 04-11 | — | Eran (sc) | A | **W!** | none | "Simplify process modules: inline ODE solvers, remove partitioning ceremony, add SimplifiedMetabolism" | "**remove `reduce_murein_objective` testing hack**" (deletes the `CPD-12261[p] /= 2.27` FBA objective adjustment); Complexation single Gillespie draw; ProteinDegradation stops consuming allocated water | — |
| `bd48262f0` | 04-11 | — | Eran (sc) | A | **W!** | none | "New `steps/trna_attenuation.py`: TrnaAttenuationConfig step … when absent, all transcripts elongate normally." | an always-on mechanism becomes off-by-default (restored 3 commits later, then turned off again — §6) | — |
| `09094fe16` | 04-11 | — | Eran (sc) | A | **W!** | none | "Introduces a feature module system for composable simulation configurations." | "Removed 270-line `calculate_superhelical_densities` block"; `DEFAULT_FEATURES=[]` turns **supercoiling and ppGpp regulation, both previously always-on, off by default** | — |
| `3a8add97e` | 04-10 | — | Eran (sc) | A | **M** | vEcoli | "Initialize next_update_time for all partitioned processes (0.0)"; "Benchmark (60s): dry_mass=384.6fg (matches vEcoli 384.5fg)" | — | — |
| `c454a2726` | 04-20 | #25 | eagmon (sc) | P-A | **W!** | crash | PR body: cache fingerprinting + CI only. Commit body: "roll the 10 refreshed TSVs back to the pre-226dcce state. That restores a working ParCa pipeline." | **the model's knowledge base is EcoCyc v29.1, not v29.6**, chosen because v29.6 raised; explicitly deferred as "biology-domain work, not in scope here" | no |

#### B — declared interfaces / wiring

| sha8 | date | PR | login | eff | intent | authority | stated motivation | decision | endorse? |
|---|---|---|---|---|---|---|---|---|---|
| `8cf9a4bc8` | 09-09 | #755 | eagmon (sc) | B | W | team | "`ecoli-metabolism` must stay antibiotic-agnostic — all drug knowledge belongs in the injected layer (sms-ecoli), not in v2ecoli." | — (reverts #753's rate law one day after it landed) | no (2 self-comments, one a self-review) |
| `034fd6f3b` | 09-07 | #737 | eagmon (sc) | B | W | crash | "Root causes taken from the actual `smsvpctest-ray-batch` CloudWatch tracebacks, not inferred." | — | no |
| `91b905a79` | 09-04 | #684 | eagmon (sc) | B | W | none | "v2ecoli's wheel doesn't ship `scripts/` … On the GovCloud pod that's the **sms-ecoli** vendored copy" | fail-loud contract: a registered class that won't import now raises | no |
| `3084a15f9` | 09-03 | #672 | eagmon (sc) | B | W | none | "Two **general, domain-agnostic framework** capabilities … No subsystem-specific (e.g. antibiotic) logic or naming lives here" | — | no |
| `803393d77` | 09-03 | #658 | cplong90 (sc) | B | W | none (type system) | "an injected subsystem that secretes a species the bundle never registered writes into a key nobody created … every downstream reader sees **bit-exact zero**" | `setdefault` not assignment, so a real initial condition can never be reset | no |
| `ca3dc931f` | 09-02 | #655 | eagmon (sc) | B | W | crash | "a native gillespie port's `kf > 0` → `TypeError: '>' not supported between instances of 'str' and 'int'`" | "the fork supplies the calibrated VALUES while the native process supplies the LOGIC" | no |
| `cad6e4598` | 09-02 | #651 | eagmon (sc) | B | W | team | "native==fork is already proven, so the fork-comparison scaffolding is no longer maintained." | retires the fork-comparison arm entirely | no |
| `a407c9a75` | 08-30 | #631 | eagmon (sc) | B | W | team / deployment | "**Why:** unblocks running the native candidate through viva-api with no server change" | — | no |
| `a35cbdd15` | 08-30 | #629 | eagmon (sc) | B | W | team | "Makes the v2ecoli whole-cell engine **drug-agnostic** … the engine holds zero knowledge of mecillinam (or any drug)." | retires `mecillinam`→`cell_geometry` auto-enable; `cell_geometry` becomes a neutral engine feature | no |
| `6107a0f6d` | 08-25 | #594 | cplong90 (sc) | B | **T** | **vEcoli** | "which is the conversion a genuine vEcoli applies to its own exchanges — same units, same sign convention"; test lands at 8.6 vs vEcoli's 9.73 | default `basis` stays `counts`; two declared choices (first observation → 0.0; undefined → 0.0 not NaN) | no |
| `e0c800285` | 08-22 | #575 | eagmon (sc) | B | W | none | "variant-sweep-phenotype studies could emit bulk counts but not listeners" | — | no |
| `47e7c01cc` | 08-19 | #543 | cplong90 (sc) | B | W | crash / intermittency | "**Ordering is established before the injected processes exist**, so they keep the default." Pre-fix a script "failed **4 of 5** runs" | declaration order expresses dependency | self-comment flagging the pattern to eagmon |
| `8f1de5ea6` | 08-18 | #525 | eagmon (sc) | B | W | crash | "surfaces specifically when process-bigraph re-realizes a daughter's structural subtree at cell division — a hard crash mid-simulation" | — | no |
| `56589f5d1` | 08-17 | #522 | eagmon (sc) | B | W | crash | "A store an *earlier* spec in the same `apply()` call had just introduced got wrongly flattened to a generic node" | — | no |
| `6952797a0` | 08-14 | #493 | eagmon (sc) | B | W | crash | "the process read a bare `[]` default and crashed on `bulk['id']`"; "**Metabolism's translated topology is byte-identical to before — no regression.**" | — | no |
| `998bd1551` | 08-13 | #491 | eagmon (sc) | B | **T** | the fork | "the installed class carries a different store layout and crashes at runtime … so the **transferred code never actually runs**" | — | no |
| `6116a8234` | 08-13 | #489 | eagmon (sc) | B | W | vEcoli | "applies a wrapped process's own `initial_state()` to the port defaults (faithful to how vEcoli seeds e.g. antibiotic `reaction_parameters`)" | — | no |
| `029cd6731` | 08-14 | #476 | cplong90 (sc) | P-B | W | team | "The transform is not gone — it **moved to `ecoli-sources`** … Coverage moved and got stronger." | — | routed to eagmon by a self-comment; eagmon's prior judgment on ecoli-sources#12 is the cited gate |
| `3dbb09bb6` | 07-27 | #407 | eagmon (sc) | B | W | crash | "daughters reverted to plain FBA baseline, and the pbg division re-realization then crashed … (`KeyError: 'current_timeline'`)" | — | no |
| `ee74c4c57` | 07-27 | #396 | eagmon (sc) | B | W | crash | "its `next_update_time` applied a tick late → `GlobalClock` returned `full_step=0` → the run hung on tick 2" | — | no |
| `39101963c` | 07-26 | #392 | eagmon (sc) | B | W | none | "every real run built the bare baseline, silently dropped the pack step, and wrote no packs" | — | no |
| `aada8d108` | 07-26 | #384 | eagmon (sc) | B | **S** | none (anatomy asserted) | "Makes the v2ecoli 3D structural model faithful to the baseline sim + gram-negative anatomy." | `envelope` default **True**; changed nucleoid constants — affects the 3D artifact, not WCM state | no |
| `d83777b1a` | 07-25 | #370 | eagmon (sc) | B | W | none | "gives its ports biological types … (inherit `float`; bind to plain-float stores, no wiring change)" | — | no |
| `60af7cb3c` | 07-25 | #361 | eagmon (sc) | B | W | none | "**parity byte-identical** to current main … RNG order preserved" | removes 2 dead input ports; also records that "the repo's June-24 `baseline_parity_signature.json` golden is **stale** relative to today's main" | no |
| `868cf2a36` | 07-24 | #356 | **AlexPatrie (eng)** | B | **W** | crash | "that instance serializes to its `repr` … which is not a parseable bigraph-schema type expression"; "Local-mode behaviour is unchanged (the name resolves to the same registered type)." | **none — clean** | no |
| `010bf7540` | 06-16 | #243 | eagmon (sc) | B | **S** | **citation** | "Adds the **Shape** process (Skalnik et al. 2023, SM §3.1) … Length formula verified == paper." | width 1 µm, density 1.1 g/mL, periplasm fraction 0.2 — read-only deriver, nothing reads `shape` | no |
| `1bca6e82e` | 06-13 | #208 | eagmon (sc) | B | **M** | vEcoli #415 | "Ports the one science improvement from vEcoli `master` since v2ecoli forked (2026-04-10) that is both important and portable" | two declared deviations: `raise`→`warn`; `getattr` fallback | no |
| `ba6769052` | 06-12 | #100 | eagmon (sc) | B | **S** | none | "incrementally turning v2ecoli's hybrid algorithmic whole-cell model into a likelihood-bearing, PDMP-class model" | FBA-bridge hook force-bound but empty (LP identical); PDMP kinetics opt-in, default `"discrete"` | no — 31 self-comments (a sprint log) |
| `693a220c0` | 05-30 | #105 | eagmon (sc) | B | W | none | "Internal math stays in bare fg and is wrapped only at the emit boundary → **parity-preserving** (before/after baseline trajectories coincide, rel 0)" | opt-in `mass_conservation`, default OFF; verdict "the baseline conserves mass to ~1%" | no (2 self-comments) |
| `5e30aa0f3` | 05-13 | #37 | eagmon (sc) | B | W | none | "Adopts `@composite_generator` … as the standard mechanism for declaring v2ecoli's three architectures" | daughter documents now built by calling `baseline()` + overlaying divided state — **not called out as a semantic change** in the body | no |
| `704b8afc7` | 04-12 | — | Eran (sc) | B | **T** | **vEcoli** | "upstream vEcoli auto-wires global_time into every partitioned process's topology (`composites/ecoli_composite.py:461-462`), but v2ecoli converted the process to a plain Step and lost that wiring" | — | — |
| `bff33e036` | 04-11 | — | Eran (sc) | B | **M** | vEcoli | "Moved port_defaults into inputs()/outputs() using `_default` dict syntax." | — | — |
| `967f63891` | 04-10 | — | Eran (sc) | B | **M** | vEcoli | "Replaced `_seed_state_from_ports` with `_seed_state_from_defaults` using `port_defaults.pickle` (full defaults extracted from vEcoli)"; "Benchmark: 384.6fg" | port pre-population now comes from a 713 KB dill pickle keyed by class name | — |
| `9531bbd39` | 04-10 | — | Eran (sc) | B | **M** | vEcoli | "These return the `_default` values from ports_schema, used for initial state seeding."; "Benchmark: 384.6fg, 1.12x — no regression." | — | — |
| `247578781` | 04-10 | — | Eran (sc) | B | **M** | vEcoli | "Generated inputs()/outputs() methods for all 11 PartitionedProcess subclasses **from extracted vEcoli schemas**" | — | — |
| `5263924a3` | 04-10 | — | Eran (sc) | B | **M** | vEcoli | "Use vEcoli-compatible nested request/allocate stores"; "Remaining: List vs Map type resolution conflict" | — | — |
| `a8de7718f` | 04-10 | — | Eran (sc) | B | **M** | vEcoli | "vEcoli's string-based port types … don't parse correctly in current bigraph-schema. Need to replace inputs()/outputs() return values with object-based types" | the declared type surface is re-expressed, not copied | — |
| `339429637` | 04-10 | — | Eran (sc) | B | **M** | vEcoli | "Replace all process files with vEcoli versions (exact config_schema, inputs/outputs, topology, and update logic)" | "Remove defaults dicts"; WIP admission in the same body | — |
| `68e4c12ab` | 04-10 | — | Eran (sc) | port | **M** | vEcoli | "Port of vEcoli's composite branch to pure process-bigraph with no vivarium-core dependency. Partitioned architecture only" | source pinned only as `path = "../vEcoli", editable = true` | — |

---

### 4. The W! list — plumbing PRs that made a modeling decision

**Engineer logins first, per the rubric.**

#### Engineer logins (`AlexPatrie`, `jcschaff`)

**None.** The A/B tables contain exactly one commit under an engineer login — `868cf2a36`
(AlexPatrie, #356, 2026-07-24) — and it is clean `W`. It changes `{"batch": InPlaceDict()}` to
`{"batch": "inplace_dict"}` so the document survives `.pbg` serialization on the remote dispatch
path, and the PR states the invariant: *"Local-mode behaviour is unchanged (the name resolves to
the same registered type)."* No numeric value, no rule, no default, no input/output relationship
changed. **The answer to "did the plumbing PRs make modeling decisions" is, for the engineer
side, no.**

#### Scientist logins (all 12 under `eagmon` / `Eran`; `cplong90` has none)

1. **`c9053136b` (2026-04-12, direct commit) — the largest one, and it is not in the first-pass
   tables.** Subject: *"Collapse unique_update_N declarations behind a FLUSH sentinel"*; body
   opens *"**Lexical cleanup, no behavior change.**"* and asserts *"EXECUTION_LAYERS and FLOW_ORDER
   are identical byte-for-byte."* The diff also contains:
   `-DEFAULT_FEATURES = ['ppgpp_regulation', 'trna_attenuation']  # match original wcEcoli behavior`
   `+DEFAULT_FEATURES = ['ppgpp_regulation']  # trna_attenuation disabled to match v1 default`.
   **tRNA attenuation has been off by default in every v2ecoli run since 2026-04-12 and is still
   off at the tip** (`ecoli_baseline.py:601`). The mechanism is real — per `bd48262f0`, when the
   store is absent *"all transcripts elongate normally."* The new comment cites "v1 default" as
   authority, so this may be a correct `T`; but it was landed inside a commit that declared
   itself behaviour-neutral, with a verification (a dry-mass trajectory) that would not have
   detected it.
2. **`29c4dc262` (#271, 2026-06-24) — three model changes inside a comparison-harness PR.** The
   PR body describes only the harness. The squash contains: (a) `Division.d_period` defaults to
   `True`, so the dry-mass threshold is no longer consulted — this half *does* cite authority, in
   a code comment: *"vEcoli's default (`d_period=True`)"*, *"mirrors vEcoli
   `ecoli/processes/cell_division.py`"*; (b) **a new rate-law form and a new constant** — the hard
   `ppgpp_scale[==0] = 1` switch becomes `b²/(b+K)` with `_PPGPP_SCALE_K = 1e-11`, justified in
   the code as *"the cooperative-threshold biology (a promoter needs a minimum RNAP-recruitment
   competence before a bound TF can act)"* and sized as *"in the empty gap between the numerical
   noise floor (~1e-13) and the smallest real expression (~1e-9)"*; (c) a ParCa ppGpp
   `adjustment = 1` floor. **(b) has no source-model authority — its purpose is to make two
   engines agree** (*"one truly-null gene (TU0-14529) reached ~19% of all transcription on
   carbon-poor media in one engine and ~0 in the other"*). This is a modeling decision taken for
   reproducibility reasons, and it is invisible from the PR.
3. **`c454a2726` (#25, 2026-04-20) — the EcoCyc v29.6 → v29.1 rollback.** Landed under a PR about
   cache fingerprinting. The commit body is honest and explicit, including the deferral: *"Until
   the data inconsistencies are fixed properly (biology-domain work, not in scope here)"*. The
   deferral was never taken up. **The whole-cell model's knowledge base is one minor version
   behind because a build broke.**
4. **`38ee8d22c` (#76, 2026-05-25) — per-process RNG seeds.** The PR's own framing is *"All pure
   infra — **zero biology coupling**"*, which is not true of item 1. The change is defensible as a
   bug fix (multi-seed ensembles were bit-identical), but the *decomposition chosen* —
   `crc32(process_name, master_seed)` — is a modeling choice about the stochastic structure of the
   model, and it silently rebased every trajectory in the repo.
5. **`4c439bd0e` (#128, 2026-06-06) — division trigger changes under a units fix.** The only W!
   whose author flagged it: *"⚠️ **Behavioral change — please review** … Division timing is now
   **mass-gated** … rather than **D-period-gated**"*, firing ~27 s early, and *"anything comparing
   long runs should be re-baselined."* **The PR received zero comments and zero reviews.** The
   request for review is on the record and was not answered.
6. **`bf60df0d4` (#244, 2026-06-16) — an incomplete revert claimed as complete.** The PR says
   *"the execution layers are now **byte-identical to pre-#137** (verified), so main's default
   model is the pre-investigation WCM again"*, and *"Un-wires **all** dnaA mechanisms"*. At
   `origin/main` today: `initial_conditions.py:660` still reads *"Total: 315 sites"* (pre-#137 was
   307), and `transcript_initiation.py:80-84` still carries
   `AUTOREG_STRENGTH = float(os.environ.get("DNAA_AUTOREG_STRENGTH", "0.8"))` with the
   autoregulation applied at `:639`. The claim is about `BASE_EXECUTION_LAYERS` and is true of
   that list; it is not true of "the default model".
7. **`3c5fe1a2c` (#393, 2026-07-26) — the media substitution.** A study-config conformance PR:
   *"`build_generator` strictly rejects unknown params."* The fix replaces `condition:` with
   `media:` across 8 studies, and the PR states the consequence itself: *"Comparison studies now
   run the lightweight `media:` perturbation **(chosen for runnability)**, NOT the calibrated
   per-condition ParCa re-fit."* Trading a calibrated per-condition ParCa cache for an in-cache
   media lever, on runnability grounds, is a modeling decision.
8–12. **The five April port refactors** — `09094fe16`, `bd48262f0`, `1a5c0abe2`, `0e282f535`,
   `0641f9800`. Each is framed as architecture ("composable feature modules", "remove
   partitioning ceremony", "simplify process modules") and each removes or re-scopes a mechanism
   that vEcoli has: supercoiling and ppGpp off by default; tRNA attenuation off by default; seven
   processes out of the allocator on asserted biology; the murein FBA objective adjustment
   deleted as a "testing hack"; Complexation's RNG stream changed. Two of the three feature flips
   were restored the same day by `0223c7078`; **supercoiling never was.**

---

### 5. The S list — for Eran and Chris the people to review

Six rows state a scientific claim or make a modeling choice with no source-model authority. None
carries a human endorsement — the one `APPROVED` review below was posted under a login whose
Claude session also writes PR bodies in this repo.

| sha8 | PR | date | the justification, verbatim | endorsement |
|---|---|---|---|---|
| `268515f0d` | #638 | 09-02 | **"The 60 mM default is ~2× the M9 recipe value (30.272 mM), sized so nitrogen is not the binding constraint at the OD10 working point."** Safety argument: *"any value above 1e-5 mM is behaviourally identical to the previous static one"*, with the qualification *"At exhaustion the pool clamps to `0.0` … a **cliff, not a taper**."* | `eagmon` APPROVED, and the review does check the load-bearing claim (`IMPORT_CONSTRAINT_THRESHOLD = 1e-5`, AMMONIUM not in `carbon_sources`). Still one login reviewing another login. |
| `717b976af` | #137 | 06-15 | *"autoregulation **resolves the V-tension** the dnaa-3 V-sweep proved no constitutive V could — it caps the DnaA peak (1567→635, ~2.5×)"*; *"the **Hill form (n=4, K=0.5)** is correct (lifts the trough)"*; verdict *"supported-with-calibration-pending"*. | The **only** row in the audit with evidence of a named non-Claude scientist: co-authored `@RashmiKaldera`, *"8 feedback rounds (Rashmi/Haochen, through 2026-06-05)"*. But those rounds live as files in the PR, not as GitHub comments, and the PR was **merged from Draft by mistake** (see #244). |
| `5e7f02a00` | #123 | 06-06 | *"Per-reaction `integrate_dt` flag in the equilibrium process + DnaA-ATP hydrolysis modeled as a kinetic equilibrium reaction (the mechanism the `dnaa2-bf8b82e-*` runs depend on)."* | none. ⚠ The `_moleculeRecursiveSearch` guard change (`val != 0` → `val < 0`), which affects **all** multi-product equilibrium reactions, is in the diff but not in the PR body. |
| `aada8d108` | #384 | 07-26 | *"Makes the v2ecoli 3D structural model faithful to the baseline sim + gram-negative anatomy."* `envelope` default `True`, changed nucleoid constants. | none. Effect is the 3D artifact, not WCM state — lowest stakes on this list. |
| `010bf7540` | #243 | 06-16 | *"Adds the **Shape** process (Skalnik et al. 2023, SM §3.1) … Length formula verified == paper."* Width 1 µm, density 1.1 g/mL, periplasm fraction 0.2. | none — but it is the **only row in the entire audit with a literature citation**, and the deriver is read-only (nothing in the model reads `shape`). |
| `ba6769052` | #100 | 06-12 | *"incrementally turning v2ecoli's hybrid algorithmic whole-cell model into a likelihood-bearing, PDMP-class model — one subsystem per phase — while keeping the cell viable."* | none (31 self-comments). Merged surface is inert by default: the FBA-bridge hook is force-bound with an empty `_default`, PDMP kinetics opt-in at `"discrete"`. |

Adjacent, worth reading alongside these (C-rows, so outside the tables but same character):
**#669** — `d_period_cv` stochastic division, *"The model was under-dispersed (CV ~7% vs a
biological 10–30%)"*, default `0.0`; its PR subject also claims a landed ATP-synthase fix that
is not on `main`. **#592** — opt-in carbon-exhaustion arrest, root-caused on the real FBA
(*"objective_value is **unchanged** (3.05204 → 3.05205)"*), and the one PR in this repo where a
second login ran the acceptance and **reported it failing** (*"the arrest never engages once the
cell divides"*), which then produced #623. **#753** — a sulfadiazine DHPS competitive-inhibition
rate law with literal constants, ported from vEcoli-private and **reverted the next day** by #755
for being drug knowledge in the wrong repo.

---

### 6. What I could not determine, and what is uncertain

1. **Who typed any of it.** `eagmon` and `cplong90` are both people and both Claude sessions.
   Every PR body in this set that carries a `🤖 Generated with Claude Code` footer, and every one
   whose commits carry `Co-Authored-By: Claude …`, is at least partly session-written — that is
   most of them. I have recorded *login*, never *person*. The one place a non-session human is
   named is #137 (`@RashmiKaldera`, and Rashmi/Haochen feedback rounds), and even there the
   feedback exists as files rather than as GitHub activity.
2. **No line-level review exists.** 0 inline review comments across all 67 PRs queried. Four
   `APPROVED` reviews exist in the whole set (#638, #648, #293, #590), all by `eagmon`, all on
   `cplong90` PRs. `eagmon`'s own model-changing PRs — including the W! rows — carry **zero
   reviews by anyone**.
3. **The first-pass tables are not exhaustive for W!.** I found `c9053136b` by chasing the
   `DEFAULT_FEATURES` value at the tip, not from the tables — its subject and body both declare
   it behaviour-neutral, so a subject-level or body-level pass cannot catch it. There may be
   others of that shape. A targeted `git log -S` sweep over the ~15 default-bearing constants
   (`DEFAULT_FEATURES`, `BASE_EXECUTION_LAYERS`, threshold literals) would be the way to close it;
   I did that only for `DEFAULT_FEATURES`.
4. **Squash merges hide the boundary between PR body and commit content.** #25 and #30 both carry
   substantive model or store changes that the PR body does not mention but the squashed commit
   body does. Anyone auditing from PR bodies alone would miss both. Conversely #271's three model
   changes *are* described in the individual pre-squash commit messages and are absent from the PR
   body — so neither surface alone is reliable.
5. **The port-era direct commits have no context beyond their own bodies.** For `68e4c12ab`,
   `339429637`, `a8de7718f`, `5263924a3`, `247578781`, `9531bbd39`, `967f63891`, `bff33e036`,
   `3a8add97e`, `704b8afc7`, `09094fe16`, `bd48262f0`, `0223c7078`, `0641f9800`, `1a5c0abe2`,
   `0e282f535`, `c2c95db2e`, `2147fca41`, `c9053136b` — **there is no PR, no thread, and no
   review**. Everything in §2a and the port-era rows of §3 comes from commit bodies, the
   2026-04-11 README/STATUS, and the diffs. I could not establish the source vEcoli commit for
   any of them.
6. **Effect is not re-derived.** Every A/B/P/⚠ code is the first pass's. Where a PR's own claim
   contradicts the first pass (e.g. #244 asserting byte-identical execution layers vs the first
   pass's note that the 315-box initial state survived) I checked the tip and reported both; I did
   not re-audit diffs otherwise.
7. **Two PRs merged with their stated acceptance criterion unmet.** #591 (`cplong90`: *"the
   reactor trajectory is still chunk-dependent in the fed phase, so the acceptance bar is not yet
   met"*, later partly retracted for lacking a repeat-run control) and #592 (validated as *"not a
   problem with the arrest mechanism itself"* but *"the arrest never engages once the cell
   divides"*). Both merged. Whether that was a considered call or an unread thread, I cannot tell.


---

# Appendix D — sms-ecoli intent report (Part 2)

## sms-ecoli — INTENT audit (second pass)

**Repo:** `CovertLabEcoli/sms-ecoli` @ `origin/main`, fetched 2026-09-09. Read-only; nothing posted.
**Input:** the first-pass effect classification (`audit_sms_ecoli.md` §2a, §2b, §3a, §3c) plus the
model-semantic pin bumps named in its §4. **50 rows** classified by INTENT and AUTHORITY from the PR
body, every PR comment and review, and the commit body. Squash-merge repo: one commit = one PR.

**Method note that shapes everything below:** *no PR in this audit carries a single inline review
comment* (`gh api .../pulls/N/comments` returns 0 for all 43 PRs). There are exactly **two formal
`APPROVED` reviews** in the whole set (#297, #183). Every other "review" is a comment posted under
`eagmon` — in five cases on `eagmon`'s own PR. Per the rubric, a comment under a login that is also
a Claude session is not human endorsement, and I have not guessed who typed.

---

### 1. Totals

#### Intent × effect (3 rows carry two intents: #299 M+W, #213 T+S, #199 T+S)

| intent | A (semantics) | B (interfaces) | C (opt-in) | D (mechanical) | E (design) | pin bump | **total** |
|---|---|---|---|---|---|---|---|
| **M** migration | 10 | 3 | 1 | 3 | 0 | 0 | **17** |
| **T** translation correction | 6 | 0 | 0 | 0 | 0 | 0 | **6** |
| **S** scientific refinement | 2 | 0 | 0 | 0 | 2 | 0 | **4** |
| **W** plumbing / debugging | 8 | 4 | 0 | 0 | 2 | 9 | **23** |
| **W!** plumbing that decided model | 2 | 0 | 0 | 0 | 1 | 0 | **3** |
| **total assignments** | 28 | 7 | 1 | 3 | 5 | 9 | **53** |

#### Intent × login class

| intent | scientist logins (eagmon, cplong90 / "Eran Agmon", "Chris Long") | engineer logins (AlexPatrie / "A.P.", jcschaff) |
|---|---|---|
| **M** | 16 | 1 |
| **T** | 6 | 0 |
| **S** | 4 | 0 |
| **W** | 16 | 7 |
| **W!** | **2** | **1** |
| rows | 42 | 8 |

**The headline:** the engineer logins did *not* quietly make the modeling decisions. Of their 8 rows,
7 are clean W and one (#312) is W! only in the narrow sense that a default it repointed selects which
drug mechanisms 36 Run-3 configs carry — and the config it repointed *to* is the one the scientists'
own PRs (#303/#306/#309) designated as Run 3. The two unambiguous W! rows are both under `eagmon`.

---

### 2. The migration of the sms-owned scientific artifacts into the v2 structure

#### The design doc, and its stated motivation

The PRs cite `docs/superpowers/specs/2026-08-26-sms-modules-extension-framework-design.md`
(on `main`). Its §1 states the scientific goal first and the engineering goal second:

> "We want to run the **vEcoli antibiotic/violacein analyses** (the ~20 the configs declare under
> `analysis_options`) on **v2ecoli candidate (`ecoli_baseline`) output**, driven by a **vEcoli-private
> config** the way the comparison harness drives the reference".

The engineering finding that justified the structural move:

> "almost the entire vendored `v2ecoli/` tree IS public v2ecoli — including the model, the comparison
> harness, the analysis framework … The genuinely sms-only *code* is **three helper files**."

A second spec, `2026-08-27-three-arm-vecoli-equivalence-design.md` (PR #138), supplies the *fidelity
programme* the ports were meant to be graded against — three arms of the same biology so that
"Arm1≠Arm2 ⇒ bridge bug; Arm2≠Arm3 ⇒ native-port bug". This is the closest thing in the repo to a
stated scientific acceptance criterion for the migration, and it names a 6-tier porting programme
(N1 pg family → N6 metabolism-redux). **Arms 1 and 2 were never completed**: §0 of that spec records
that Arm 1 "emits NOTHING to parquet" and becomes "REFERENCE-ONLY", so the layered diagnosis the
design promises was not available for any port after #137.

#### #124 — Design + SP1 (`91455d7d`, 2026-08-27, eagmon) — M (container)

Not a scientific-artifact transfer: it creates the `sms_modules` package and declares the dependency.
It ships the design spec above. **Fidelity claim:** none applicable. **Deviation admitted:** the lock
is knowingly out of sync ("`pyproject.toml` and `uv.lock` are intentionally out of sync and the
lock-check CI will fail"). Carries the one substantive scientist comment in the whole migration:
`cplong90` warned that `scripts/` did not follow the package, so "upstream fixes arrive
half-applied", and that the floating `branch = "main"` pin "broke here on its first day".

#### #127 — retire the vendored tree (`f13aca0b`, 2026-08-27, eagmon) — M (container)

The structural migration itself. **Does not say a scientific artifact is being transferred**, and does
not need to — it moves the *container*. **Fidelity claim:** "Suite: 238 passed, 42 skipped, 0 failed"
and an L0–L5 audit gate. **Deviation admitted, and it is the important one:** `v2ecoli` is pinned as
`branch = "main"`, i.e. **floating** — for the first week of the dependency era the model could change
under the repo with no commit here. `cplong90` demonstrated exactly that on #124 the same day.

#### #137 — pg_maturation + pg_shape ports (`d6f90f95`, 2026-08-27, eagmon) — M

**Source:** named precisely, `~/code/vEcoli-private/ecoli/processes/antibiotics/{pg_shape,pg_maturation}.py`
plus `ecoli/library/schema.py:919` (`divide_pg_cellwall`). **Fidelity claim:** the strongest in the
set — "**verbatim physics** from the fork (`diff`-verified byte-identical); adds only a docstring
provenance note + a guarded registration footer", and the SP4 plan instructs "Do NOT re-derive or
'improve' the biophysics." **Admitted deviation:** one, and it is scientific — `pg_shape` gains
"a module-level `DEFAULT_MEDIA_RECIPES` fallback (reconstructed for the `"minimal"` baseline media
from the EcoCyc flat file)", applied only when no `media_recipes` is supplied. That is media data
authored here, not ported. **Says plainly it is a transfer:** yes. **Deferred:** the two live gates —
fork-injection smoke and the 2-generation `divide_pg_cellwall`-at-division test — were explicitly out
of scope, so the ports landed without any run-level fidelity evidence.

#### #142 — MetabolismReduxClassic + violacein new-gene data (`c2360dfd`, 2026-08-28, eagmon) — M

**Source:** the fork's `metabolism_redux_classic`; the violacein new-gene TSVs are described as
"committed construct gene-definition INPUT data" with a rebuild script. **Fidelity claim:** a real
run-level comparison — "`no_metabolism` **PASSES** against genuine vEcoli-private … (t=0 <0.05%,
t≈799 ≤2.4%, mRNA mean ~1%), and metabolic baseline … within ~2%". **Admitted deviation:** the
`with_metabolism` arm needed a config round-trip fix (`quote`-typed params) before the LP would solve
at all, and the PR states plainly "**Model note — `VIOLACEIN[c] = 0` on both** … Genuine vEcoli
behaves identically — correct FBA dead-end behavior, not a native-seam artifact." That is honest
reporting of a null result. **Says plainly it is a transfer:** yes.

#### #148 — the 6-process antibiotic layer + injection topologies (`8d9d2a93`, 2026-08-28, eagmon) — M

The commit that put the antibiotic mechanism in this repo: 2137 lines, six processes, 24 configs.
**Source:** the vEcoli-private antibiotic process family and its 12 configs, with "the 12
vEcoli-private source twins (provenance)" committed alongside. **Fidelity claim: none at the physics
level in this PR** — the evidence offered is CI, an audit gate, and three studies that "✓ ran".
**Admitted deviations, and they are large and honestly stated:** "**Drug delivery is v2ecoli-blocked.**
… no environmental dose is delivered through the runnable seam"; "**Multi-dose MIC needs the variant
sweep**"; one analysis "errors on ragged pg-lattice arrays". So the entire antibiotic layer landed
with the dose inert — the thing it exists to model was untestable at merge. **Says plainly it is a
transfer:** yes.

#### #152 — violacein kinetic ODE (`86375737`, 2026-08-29, eagmon) — M

**Source:** named to the file — the fork's `ecoli/processes/metabolism_redux.py`: "the fork's **S_VIO
pathway ODE** (`forward_step` + all `VIO_*` constants) and the **weight-100 `vio_flux` export-pin**".
**Fidelity claim: the best in the audit** — "the ported numpy RHS matches the fork's jax
`forward_step_jax` to **~1.8e-12** (24 cases)", the kinetics bridge reproduces the fork's unit
handling at "max dev 0.0". **Admitted deviation, stated as a scientific finding:** "the native
violacein titer runs **~2–3× the fork's reference range** … this is a genuine **candidate-vs-reference
divergence**". A 2–3× titer gap declared a finding rather than a defect, with no scientist comment on
the PR. **Says plainly it is a transfer:** yes.

#### #156 — vEcoli reference-parity tests (`d82593bf`, 2026-08-30, eagmon) — M (verification)

The one PR whose whole purpose is fidelity. Turns four processes "from *isolation-tested only* into
*vEcoli-reference-tested*", comparing each to "an **independent reference of the same worked example
the vEcoli source uses**" — pg_shape `rel=1e-6` (actual ~1e-13), pg_maturation `rel=1e-6` (~1e-8),
gillespie against vEcoli's own `test_gillespie.py`, field_timeline against the source's own worked
timeseries. **"No real native-vs-vEcoli divergences found (no xfails)."** Two admitted deviations:
gillespie uses TauLeaping because "the source's SSACSolver needs a C++ toolchain absent in CI", and
the pg_shape test **encoded the source's bugs on purpose** — "Documents the source's
`stress_theta := stress_z` quirk, carried verbatim in the port". That characterization test is what
##203 later had to rewrite.

#### #203 — pg mechanics fixes "from vEcoli-private #93" (`b2088be1`, 2026-09-03, eagmon) — T

**Source:** `CovertLabEcoli/vEcoli-private#93`, plus a literature citation for one value (eLife 72863
supp 2). **What was corrected:** three genuine mechanics bugs (sign of the quadratic coefficient,
`Etheta`→`Ez` axial modulus, `stress_theta = stress_z` copy-paste) and one initialization value
(`prop_crosslinked` 0.20→0.28, stems split 2/3 tetra : 1/3 tri, pentapeptide init 0). **Fidelity
handling is the subtle part:** #156's parity test had been written to *lock in* the bugs, so #203
"Updated to the **corrected** thin-shell physics … while keeping `solve_p_final`'s `beta` on its own
`Etheta`-based `a_z` to mirror the source (the fork fixed `a_z` only in `get_stress_strain`)". So the
port now deliberately carries the source's *remaining* inconsistency. **Caveat:** the authority cited,
vEcoli-private#93, is described as "(draft)" at merge time — sms-ecoli adopted a fork change before
the fork accepted it. The `stress_theta` fix alone doubles the hoop stress the lysis gate reads.

#### #272 — vEcoli-private #93 configs + flat_overrides (`b2676fe2`, 2026-09-07, eagmon) — M

**Source:** named to the commit — `metabolite_concentrations_added.tsv` (#84 `68772795`),
`rna_half_lives_removed.tsv` (#79 `f4e9cc0a`), `protein_half_lives_modified.tsv` (`b3e5a737`),
"Copied verbatim from vEcoli-private master". **Fidelity claim:** verbatim copy + provenance headers;
no numeric verification here (that came in #280's pin bump, which measured pABA = 8e-06 mol/L,
MurD = 1914.725 min against a full chassis build). **Says plainly it is model data:** yes, and
unusually well — "**These change sim_data — they do nothing until a ParCa rebuild passes this
manifest.**" **Admitted deviations:** the Run 3 and Run 4 configs it generates are marked
`_provenance.NEEDS_REVIEW`, and it states its own scale deviation: "`generations=8`/`n_init_sims=1`
chosen for the CD2 8-gen target — **source used 2**." Three open questions were addressed to
`@cplong90 @AlexPatrie`; **neither replied on the PR, which merged 9 minutes after opening.**

#### #299 — the Run 3 dose grid (`1dbff758`, 2026-09-09, AlexPatrie) — M + W

**Source:** "a direct, mechanical port of vEcoli-private's own
`ecoli/variants/antibiotic_cocktail_timeline.py::apply_variant`", verified against
"the real, unmerged source (`origin/antibiotics-cd2`)". **I checked this claim against
vEcoli-private directly.** `configs/antibiotic_cocktail.json` on branch `antibiotics-cd2` carries
mecillinam `[0, 1e-05, 1e-4, 1e-3, 1e-2, 0.1]`, sulfadiazine `[0, 1e-4, 1e-3, 1e-2, 0.1, 1]`,
`times = [[10000]]`, `generations: 20`, `n_init_sims: 4` — **exactly** what #299 hardcodes, scale
included. The claim "nothing here is a new scientific decision" **holds**. **But** `main` also carries
`configs/experiments/antibiotic_cocktail_vecoli_ref.json` (landed by #272, mirroring vEcoli-private
**master**/#93) with a *different* grid: mecillinam `[0, 2.89e-4, 5.78e-4, 1.16e-3, 2.31e-3, 4.62e-3]`
× sulfadiazine `[0, 5.99e-3, 0.024, 0.0959, 0.392]` — a 6×5 near-log dilution series, 30 points.
So two vEcoli-private branches give two different Run-3 dose grids, both present in this repo, and the
one being executed is from the unmerged branch. #299 flagged this itself and did not resolve it:
"which vEcoli-private branch is authoritative for this grid (36 vs a conflicting 9-combo description
in this repo's own `study.yaml`) — raised with the team on #166, not resolved here."

#### #308 — the plain FBA objective from vEcoli MASTER (`c5c4f143`, 2026-09-09, eagmon) — M, opt-in

**Source:** "vEcoli-private MASTER's PLAIN `MetabolismRedux` FBA objective", with the five
differences enumerated in the body. **Fidelity claim: the most rigorous method in the audit** — a
generator script runs "the **FORK's real plain `NetworkFlowModel.solve`** (fork venv)" on a fixture
and dumps the reference; the native path is matched at rtol 1e-6, "**Actual max flux deviation: 0.0**".
**Admitted deviation:** none in the ported path; the *default* stays classic, so this is C, inert.
The eagmon comment records a self-caught methodological error worth noting — a first fixture was
degenerate and "the gate couldn't discriminate", rebuilt with two metabolites. It ends "Held for
Eran's go"; the PR merged 9 minutes later.

#### The common shape

All ten migration PRs **do say plainly that a scientific artifact is being transferred**, and most
name the source to the file or commit. Where fidelity was claimed numerically it was claimed well
(1.8e-12, 0.0, rtol 1e-6, byte-identical). The gap is not honesty — it is that the two ports with the
largest scientific surface, **#148 (the entire antibiotic layer) and #142's `with_metabolism` arm**,
landed with **no physics-level fidelity evidence at all**, and #148 landed with the dose mechanism
inert by its own admission. The "somewhat refactored" that Jim asked about is, concretely: the
`DEFAULT_MEDIA_RECIPES` media fallback (#137), the config-driven `excluded_reactions` that replaced
vEcoli's hardcoded `BAD_RXNS` (#142, reverted by #301), `VIOLACEIN[c]` added to the process's own
exchange set instead of the reconstruction (#155), the `met_map` skip (#175), and the numpy-for-jax
RHS translation (#152).

---

### 3. Full table (most recent first)

Login class: **sci** = eagmon / cplong90 / "Eran Agmon" / "Chris Long"; **eng** = AlexPatrie / "A.P." /
jcschaff. Endorsement column: only a formal `APPROVED` review or a substantive comment under a
*different* login than the author counts; a self-comment is marked as such.

| sha | date | PR | login (class) | effect | intent | authority | stated motivation (quote) | embedded modeling decision (S, W!) | human endorsement seen? |
|---|---|---|---|---|---|---|---|---|---|
| `2a3c3661` | 09-09 | #314 | jcschaff (eng) | A | W | crash | "One tick with a non-integrable state is skipped with a `RuntimeWarning` … and returns an empty update, instead of aborting the whole lineage." | — (see §4 borderline: freezes the wall for one tick, only where the lineage previously died) | eagmon comment (not a review) |
| `50cb3e4e` | 09-09 | #312 | AlexPatrie (eng) | A/E | **W!** | team (#303/#306/#309 config-of-record) | "combos built against the old default would silently omit both drug mechanisms" | **Repoints the sweep generator's default base config, and commits the 36 resolved combos — selecting which drug mechanisms all 36 Run-3 dispatches carry.** | none |
| `f0a9d1b0` | 09-09 | #309 | eagmon (sci) | E | S | team (Eran, reported) | "Eran confirmed the Run 3 antibiotic-cocktail scale: **4 seeds × 20 generations × 36 concentrations**" | Run 3 scale: `generations` 8→20, `n_init_sims` 1→4 | eagmon self-comment; merged 2 min later |
| `c5c4f143` | 09-09 | #308 | eagmon (sci) | C | M | vEcoli-private MASTER | "Ports vEcoli-private MASTER's PLAIN `MetabolismRedux` FBA objective … as a **guarded, config-selectable** path" | — (default unchanged) | eagmon self-comment, "Held for Eran's go" |
| `588bb043` | 09-09 | #306 | eagmon (sci) | A+B | M | vEcoli reference / the reverted v2ecoli#753 block | "Rate law + constants match the vEcoli reference (and the reverted #753 block) exactly" | — (but kcat 0.38, km_paba 7.82e-3, k_i 5.15e-3 carry **no primary citation in this repo**) | eagmon self-review ×2, "Held for Eran's direct go" |
| `6c438e50` | 09-09 | #301 | eagmon (sci) | A | T | vEcoli-private master, run; + team ("Eran's 'follow Robotato/master' directive") | "This restores the source's unconditional behavior: hardcode the canonical `BAD_RXNS` … and apply it on every run" | Selected the plain-redux **51**-reaction list over classic's 48 and the installed package's 5 — a reference-variant choice; residual "solver variant" deviation admitted | none; the Eran directive is cited, not linked |
| `0f7c2216` | 09-09 | #304 | eagmon (sci) | A | T | vEcoli (`nonnegative_accumulate`) | "vEcoli's `local_field` applies the exchange delta with the **`nonnegative_accumulate`** updater, so the field pool never goes below 0" | — | none |
| `3a52c450` | 09-09 | #303 | eagmon (sci) | A+B | M | vEcoli param_store / vEcoli-private master `antibiotic_cocktail.json` | "resolved from the vEcoli param_store in the same unit convention as the existing mecillinam literals … validated by reproducing the existing mecillinam literals exactly" | — | eagmon self-review, "Eran approves" (no record of it) |
| `1dbff758` | 09-09 | #299 | AlexPatrie (eng) | A | M + W | vEcoli-private branch `antibiotics-cd2` | "every dose value is already fully specified upstream, **nothing here is a new scientific decision**" | — (**verified true**; but the source branch is unmerged and conflicts with the in-repo #93 reference grid — §4) | none |
| `cd0d3021` | 09-08 | #297 | jcschaff (eng) | A | W | crash + vEcoli#440 precedent (in review) | "on `SolverError` … or a non-optimal status, retry the same problem on **HIGHS**, then **CLARABEL**" | — (disclosed: "a fallback solver may return a **different optimal vertex**"; §4) | **APPROVED by eagmon** |
| `77248228` | 09-08 | #292 | AlexPatrie (eng) | B | W | crash (`AmbiguousLookupError`) | "the topology's nested `species: {"bulk": ["bulk"]}` wire targets a port this process instance never declares" | — | none |
| `4e7d1d19` | 09-08 | #291 | AlexPatrie (eng) | B | W | crash (`AmbiguousLookupError`) | "The wire is also provably redundant: `update()` … already reads the identical external dose from the `boundary` port independently" | — | none |
| `b2676fe2` | 09-07 | #272 | eagmon (sci) | A+B+E | M | vEcoli-private master #93 (commits named) | "**These change sim_data — they do nothing until a ParCa rebuild passes this manifest.**" | Run 3 scale chosen against the source: "`generations=8`… — source used 2" | asked @cplong90 @AlexPatrie; **no reply; merged in 9 min** |
| `df53f704` | 09-07 | #266 | eagmon (sci) | B | W | team (configs are cplong90's) | "a simulator image built from `main` (simulator 160) can't see the K4 cell-only config because it lives only on the study branch" | — | **cplong90 sign-off comment** (substantive, and adds two safety caveats) |
| `17d67194` | 09-04 | #213 | eagmon (sci) | A | T + S | vEcoli fork dose-response; citation (Brouwers 2020) | "`field_timeline` delivers a decaying environmental source (first-order hydrolysis, k=1.375e-4/s, half-life 1.4 hr, Brouwers 2020) so native external drug drains across the lineage like the fork" | **S:** adds a drug-decay mechanism and its rate constant; **T:** `lineage_time_offset` restores absolute-time dosing. Both default to no-change | none |
| `6ccb5cf1` | 09-03 | #206 | eagmon (sci) | A | W | crash ("chain dispatch: ParCa failed") | "Four violacein configs declare `new_genes` … but **omit `bundle_overrides`** … asserts `This new_genes_data subdirectory is invalid`" | — (changes the reconstruction, but to the strain the config always declared) | none |
| `b2088be1` | 09-03 | #203 | eagmon (sci) | A | T | vEcoli-private#93 (**a draft at merge time**) + eLife 72863 supp 2 | "Ports the peptidoglycan shape/maturation mechanics fixes from **vEcoli-private#93** … which were faithful ports of the fork and carried the same bugs" | `prop_crosslinked` 0.20→0.28 (cited); a parity test was rewritten from characterization to corrected physics | none |
| `279b7bb1` | 09-03 | #199 | eagmon (sci) | A+B | T + S | vEcoli port names (fix 1); **asserted** (fix 2) | "**Fix 2 — pg-shape lyse policy (eagmon-approved dose-response policy)** … records the lysed flag and continues, which is the correct behavior for a dose-response" | **S:** three failure policies `raise_lysis`→`lyse` — the cell now lyses and the run continues where it previously aborted | **the title claims eagmon approval; nothing in the PR records it** |
| `76b73a19` | 09-02 | #183 | cplong90 (sci) | A | M | public `ecoli_sources` gfp set | "the 7 gfp flat TSVs, copied verbatim from the shipped **public** gfp gene set … Verified byte-identical" | The 19-row **composition** (two-cassette arrangement, insertion loci) is authored here, not ported; the PR flags an untested positional-ordering hazard | **APPROVED by eagmon** |
| `fff9091a` | 09-01 | #182 | eagmon (sci) | B | M | vEcoli-private#91 | "**Round-trip verified**: resolving the flat config … `==` the original resolved dict" | — | none |
| `fb1d0250` | 09-01 | #177 | eagmon (sci) | A | M | vEcoli `configs/spatial.json` | "Port vEcoli's `configs/spatial.json` (**byte-identical** to the vEcoli configs installed in this venv)" | — (the spatial field, GLC 1.0 mM, is ported not chosen) | none |
| `677bbe90` | 09-01 | #175 | eagmon (sci) | A | W | crash (`KeyError`) | "Skip exchange metabolites absent from the network's `met_map` … This is a **no-op for the LP and the emitted output**" | — (documented inline "as a native-port divergence from the verbatim source") | none |
| `2dac7051` | 08-31 | #138 | eagmon (sci) | A+B+E | W (+ design spec) | crash (`ZeroDivisionError` misread as a division) | design spec: "Layering makes divergences diagnosable (Arm1≠Arm2 ⇒ bridge bug; Arm2≠Arm3 ⇒ native-port bug)" | — | none |
| `59391f8f` | 08-31 | #167 | eagmon (sci) | B | M | vEcoli-private (verbatim) | "copied **verbatim** from vEcoli-private" … "A config path that 404s **silently falls back to a basal template** (no violacein)" | — | none |
| `9e204009` | 08-30 | #162 | eagmon (sci) | A | **W!** | crash (`ValueError: n < 0` at division) | "Molecule counts are physically ≥ 0, so this is a **general correctness guard**, not vio-specific" | **Adds a hard non-negativity clamp to the homeostatic `dm/dt` on every tick of every redux run — a rule the reference does not have. The PR states the fork avoids the state structurally, by keeping the intermediates in log-space, not by clamping.** | none |
| `0cb3f361` | 08-30 | #157 | eagmon (sci) | B | M | vEcoli-private + a v2ecoli companion PR | "The engine seeds them at **correct submass**, replacing the sms inject layer's zero-mass `extra_bulk_species` append" | — (molar masses 325.426 / 343.426 come with the seam) | none |
| `96e85087` | 08-30 | #155 | eagmon (sci) | A | T | vEcoli fork ParCa (the fork carries the exchange) | "The fix — **in the process, not the ParCa** … Cache-agnostic and permanent" | — but the deviation matters: a secretion reaction is now added to the network **from process code**, so any future cache silently gains it and the reconstruction never records it | none |
| `86375737` | 08-29 | #152 | eagmon (sci) | A | M | the fork's `ecoli/processes/metabolism_redux.py` | "the ported numpy RHS matches the fork's jax `forward_step_jax` to **~1.8e-12** (24 cases)" | — ; admitted: "the native violacein titer runs **~2–3× the fork's reference range** … a genuine candidate-vs-reference divergence" | none |
| `6b213f5b` | 08-29 | #147 | eagmon (sci) | B | W | KPI reads 0.0 | "the KPI leaves … read **0.0** — glucose being 0 on a growing cell means the exchange-flux *lift* + gdcw-basis isn't yet capturing the native candidate's fluxes" | — | none |
| `8d9d2a93` | 08-29 | #148 | eagmon (sci) | A+B | M | vEcoli-private 12 configs + the fork antibiotic processes | "**v2-native antibiotic process layer** — six native processes … injected onto single-cell `ecoli_baseline`" | — ; admitted: "**Drug delivery is v2ecoli-blocked** … no environmental dose is delivered through the runnable seam" | none |
| `c2360dfd` | 08-28 | #142 | eagmon (sci) | A+B | M | the fork's `metabolism_redux_classic` + violacein construct data | "`no_metabolism` **PASSES** against genuine vEcoli-private … within single-seed stochastic tolerance" | — ; admitted: `VIOLACEIN[c] = 0` on both arms, argued correct | none |
| `d6f90f95` | 08-27 | #137 | eagmon (sci) | A | M | vEcoli-private `pg_shape.py` / `pg_maturation.py` / `schema.py:919` | "**verbatim physics** from the fork (`diff`-verified byte-identical); adds only a docstring provenance note + a guarded registration footer" | — ; deviation: a `DEFAULT_MEDIA_RECIPES` minimal-media fallback "reconstructed … from the EcoCyc flat file" | none |
| `f13aca0b` | 08-27 | #127 | eagmon (sci) | D | M (container) | engineering (sync cost) | "sms-ecoli stops **vendoring the entire v2ecoli tree** … and instead **imports `v2ecoli` as a `branch=main` git dependency**" | — ; the floating pin is the deviation | none |
| `91455d7d` | 08-27 | #124 | eagmon (sci) | D | M (container) | design spec | "sms-ecoli becomes a thin private workspace that imports pinned public v2ecoli + private `sms-modules`" | — | **cplong90 comment** — two real design objections (scripts drift; the floating pin "broke here on its first day") |
| `d82593bf` | 08-30 | #156 | eagmon (sci) | D | M (verification) | vEcoli source worked examples | "compare the native process to an **independent reference of the same worked example the vEcoli source uses**" | — ; "**No real native-vs-vEcoli divergences found (no xfails)**"; the pg_shape test deliberately encoded the source's `stress_theta` bug | none |
| **§2b — outside model paths** | | | | | | | | | |
| `0d1bace2` | 09-09 | #313 | cplong90 (sci) | A | W | silent no-op | "`--aeration-schedule` parsed its file, wrote `bird_reactor_config["aeration_schedule"]`, and returned. **Nothing consumed that key.**" | — (adds a units/trigger declaration rule to schedule files) | self-describes a "met-eng lane" review at a named sha |
| `e9e79d0b` | 09-02 | #191 | cplong90 (sci) | A | W | silent wild-type sweep | "23 configs … **nest** that block … For those it returns `None` → `baseline()` builds plain native metabolism → **bit-exact 0.0 product, exit 0, no warning.**" | — (11 configs with a hardcoded `fork_repo` now raise instead of silently running wild-type — a deliberate, narrow refusal) | none |
| **§3c — experiment design** | | | | | | | | | |
| `0651836c` | 09-06 | #230 | eagmon (sci) | E | **W!** | "0 refs" | "Orphan config (0 refs; the other top-level configs have 7-10 refs each): `configs/meteng_vio_gfp_composed_constitutive.json`" | **Deletes the only config that used the composed vio+GFP strain #183 landed 3 days earlier (and eagmon had APPROVED), labelling it "fork-mirror residue from v2ecoli sync" — it was authored in-repo, not mirrored. The overlay + 7 gfp TSVs + guard test survive on `main` with nothing referencing them.** | none |
| `188da919` | 08-31 | #171 | eagmon (sci) | E | S | team (@cplong90's #86 review, elsewhere) | "added by mistake in #167; the tnaA/trpR knockout is **viz-mechanics only** (per @cplong90's #86 review), not a Run 4 config" | Changes which strains Run 4 screens (native_oe in, tnaA/trpR KO out) | cites cplong90 on another PR; nothing on this one |
| `e1ca115a` | 06-27 | — | Eran Agmon (sci) | E | W | commit body only | "each `cond_<name>_1x4.json` inherits the vEcoli-fork condition config and pins `n_init_sims=1/generations=4` (config = source of truth for run shape)" | — | **direct commit, no PR — commit body is the only context** |
| `f4eb0d9c` | 06-27 | — | Eran Agmon (sci) | E | W | commit body only | subject only: "feat(harness): example manifests (5cond 1x4 standard; baseline 4x4 statistical)" | — | **direct commit, no PR, no body** |
| **§4 — model-semantic pin bumps** | | | | | | | | | |
| `4bd7c82a` | 09-09 | #310 | jcschaff (eng) | pin | W | upstream PR ids | "#755 (generic `imposed_flux_bounds` hook; `sim_data.py` back to its pre-#753 bytes, so the `INPUT_FILES` hash matches simulator 182's and every existing ParCa cache verifies)" | — ; **names** that this is the image carrying the DHPS process | none |
| `74ffb930` | 09-09 | #307 | eagmon (sci) | pin | W | upstream PR ids | "removes the drug-specific antibiotic code from the v2ecoli side … and adds the `imposed_flux_bounds` hook … **activating the DHPS growth-inhibition readout end-to-end with no further config change**" | — ; the clearest statement in the audit that a pin bump changes biology | eagmon self-comment |
| `385abec9` | 09-09 | #305 | jcschaff (eng) | pin | W | upstream PR ids | "#751 (gather resource knobs), #752 (one Nextflow gather per variant), **#753 (DHPS inhibition, eagmon)**" | — ; names the model change but not its effect (it baked sulfadiazine-specific logic into v2ecoli metabolism; reverted 37 min later by #307) | none |
| `2e82279b` | 09-08 | #280 | eagmon (sci) | pin | W | upstream PR + integration measurement | "`metabolite_concentrations_added` — pABA + DHPPP become homeostatic targets → **unblocks Run 3 sulfadiazine**"; verified "`conc_dict` pABA = 8e-06 mol/L … MurD half-life = exactly 1914.725 min" | — ; **the model of a good pin bump**: names the biology and measures it | none |
| `4378a057` | 08-24 | #106 | cplong90 (sci) | pin | W | schema resolution | "`vector_slots()` resolved only `VectorObservationSchema`, so … the new per-replicate vector slots would have silently failed to resolve" | — ; **`ecoli-sources` also carries the ParCa flat files and (per #301) a copy of `metabolism_redux.py`; no model delta is enumerated** | none |
| `b9cebabd` | 08-24 | #109 | cplong90 (sci) | pin | W | measurement data | "ships the 18 new per-replicate vector tables (proteome+transcriptome × 9 Ginkgo groups) … **real-sample distributions** for the MMD goodness-of-fit axis, not synthesized" | — (validation data, not model) | none |
| `b40b0a1b` | 08-18 | #70 | cplong90 (sci) | pin | W | missing data | "Pinned to be3c588 …, not the deleted f59a346e48 — that rev carries 10 of 20 cultivation groups … so a verbatim restore would have presented as missing data rather than a bad pin" | — | none |
| `b5f08bd0` | 06-26 | — | Chris Long (sci) | pin | W | commit body | "Repoint the pin from the now-merged feature-branch tip (8348cb5) to the stable main commit … **Content-identical bundle**" | — | direct commit |
| `34bcd16c` | 06-18 | — | Chris Long (sci) | pin | W | commit body + citations | "Picks up the validation-data subsystem's Metabolism and Proteome references: basal__metabolic_fluxes (**Crown 2015 + Toya 2010**) … basal__proteome (**Schmidt 2016 MG1655**)" | — (validation data; well cited) | direct commit |

---

### 4. The W! list — did the plumbing PRs make modeling decisions?

#### Engineer logins first

**`50cb3e4e` #312 — AlexPatrie, 2026-09-09 — W!**
The diff changes one CLI default and commits 36 configs:
```
- base_path = ... else "configs/experiments/antibiotic_cocktail_native_run.json"
+ base_path = ... else "configs/cd2/run3_antibiotic_pg_sulfadiazine.json"
- out_dir   = ... else "out/run3_cocktail_sweep"          # untracked
+ out_dir   = ... else "configs/cd2/run3_sweep"           # committed
```
**The decision embedded:** which model system the entire Run 3 sweep dose. The old base carries no
sulfadiazine transport and no DHPS inhibition; the new one carries both. Every one of the 36
committed combos is therefore a *different biological system* from what #299's generator would have
produced the day before, and this is the commit that made those 36 files the repo's Run-3 corpus.
**Mitigation, and it is real:** the new base is the config that #303, #306 and #309 — all scientist-
login PRs — had just established as Run 3, and the PR says so. This is W! by the letter of the rubric
("changes a default that alters results where it did not previously crash") rather than in spirit.

#### Scientist logins

**`9e204009` #162 — eagmon, 2026-08-30 — W!, and the strongest case in the audit**
Intent is unambiguously plumbing: every native violacein multi-generation run "was **silently stalling
at generation 0**" because a negative bulk count broke `divide_bulk`'s binomial split. The fix:
```python
estimated_homeostatic_dmdt = np.maximum(estimated_homeostatic_dmdt, -homeostatic_metabolite_counts)
```
**The decision embedded:** a hard non-negativity clamp is now applied to the homeostatic `dm/dt` of
**every homeostatic metabolite on every tick of every redux run** — not just the violacein
intermediates that motivated it. It is presented as physically self-evident ("Molecule counts are
physically ≥ 0"), and it is — but the PR's own root-cause paragraph says the reference model avoids
the situation **structurally**, not by clamping: "The **fork never hits this** because it keeps these
intermediates in the pathway ODE's floored log-space state (`VIO_CONC_FLOOR`), never as bulk counts."
So this is a new rule added to the native model to compensate for a structural difference from the
source, with no source authority, no citation, and no review. Every native redux result since
2026-08-30 carries it.

**`0651836c` #230 — eagmon, 2026-09-06 — W!**
A housekeeping PR ("remove fork-mirror residue from v2ecoli sync") deleted
`configs/meteng_vio_gfp_composed_constitutive.json`. Verified against git history: that file was
**added 3 days earlier by cplong90 in #183**, which eagmon had formally APPROVED — it was authored
in-repo, not mirrored from the fork, so the PR's provenance label is factually wrong and its "0 refs"
criterion was true only because the config was new. Its data survives (`composed_overlay.tsv`, the 7
gfp TSVs, `tests/test_composed_overlay.py`) with **nothing on `main` referencing it**: the composed
vio+GFP two-cassette strain is still buildable but no run declares it. A reference-count criterion
applied to a scientific corpus removes exactly the artifacts that are newest.

#### Borderline — the two Jim asked about by name, and my answer

**#297 (jcschaff) — a modeling *consequence*, disclosed and endorsed; not W!.** Yes, choosing
GLOP→HIGHS→CLARABEL embeds a tie-break: on a degenerate norm-1 optimum a different solver returns a
different optimal vertex, so fluxes differ. But it fires **only** where GLOP raised or was non-optimal
— i.e. only on ticks that previously produced no result at all; "Ticks where GLOP is optimal are
byte-for-byte unchanged". And the PR did the right thing with it: a "Caveat (science side,
@cplong90)" section states the vertex risk explicitly, offers to restrict or reorder, and eagmon
formally **APPROVED**. This is the one PR in the debugging era where a modeling-relevant consequence
was written down, addressed to a named scientist, and accepted on the record. It should be the pattern.

**#314 (jcschaff) — a model behaviour choice, but only on a previously fatal path; not W!.**
Choosing "skip the tick, carry `pg_cellwall` unchanged, warn" over "abort" *is* a statement about the
model — for one timestep no peptidoglycan maturation chemistry happens. But the alternative was a dead
lineage, and the PR is explicit that it does not fix the cause: "It does not fix why the daughter's
first-tick mass is not finite … it makes the symptom survivable and *visible*." The real risk it
creates is governance, not physics: a lineage can now complete with N skipped ticks and nothing grades
N. The `RuntimeWarning` is the only signal, and no analysis reads it.

**#299 (AlexPatrie) — M, and the fidelity claim checks out.** I verified the grid, the 10,000 s onset,
`generations: 20` and `n_init_sims: 4` against `CovertLabEcoli/vEcoli-private` branch
`antibiotics-cd2`'s `configs/antibiotic_cocktail.json`: identical. "Nothing here is a new scientific
decision" is true. What is *not* settled is which upstream branch is authoritative — see finding 1.

#### Pin bumps

Intent of all nine is W. **None silently changed biology in a way its body concealed** — #307 and
##280 state the biological effect explicitly and #280 measures it; #305 and #310 name the upstream PR
that carries it. The systemic risk is one level down and is not visible in any bump body: the
`ecoli-sources` pin was last moved 2026-08-24 for a *schema* reason (#106), and #301 later discovered
that the same package "is a **stale snapshot** of `metabolism_redux.py`" carrying 5 of the 51
`BAD_RXNS` — a model process frozen inside a data-package pin nobody was tracking as a model input.

---

### 5. The S list — for Eran and Chris the people to review

Four scientific choices were made in this repo with no source-model authority. None carries a formal
review; two are recorded only as a claim about an approval that happened elsewhere.

1. **`279b7bb1` #199 — pg-shape failure policy `raise_lysis` → `lyse` (×3).** Justification:
   *"records the lysed flag and continues, which is the correct behavior for a dose-response and is
   what the downstream analyses read."* The PR title calls it an "eagmon-approved dose-response
   policy"; **nothing in the PR thread records that approval.** The change was bundled into a PR
   whose headline item is a topology-key crash fix. Effect: a drug-induced lysis now yields a
   completed, plotted run instead of an aborted one — which is what a dose-response needs, and also
   what makes a lysing arm indistinguishable from a surviving one unless the flag is read.
   *(Later partial corroboration: #272 records that vEcoli-private#93's own
   `mecillinam_shape_vecoli_ref.json` uses the `lyse` policy — but that landed four days after #199.)*

2. **`17d67194` #213 — drug decay as a delivered mechanism.** Justification: *"delivers a decaying
   environmental source (first-order hydrolysis, k=1.375e-4/s, half-life 1.4 hr, Brouwers 2020) so
   native external drug drains across the lineage like the fork."* Cited to a paper, defaults to
   no-change, and validated against the fork (native IC50 0.20–0.26 µM vs fork 0.175–0.28). The
   decision to review is whether first-order hydrolysis at that rate is the right model of mecillinam
   loss in this environment, and whether it should be on by default for Run 3.

3. **`f0a9d1b0` #309 — Run 3 scale, `generations` 8 → 20, `n_init_sims` 1 → 4.** Justification:
   *"Eran confirmed the Run 3 antibiotic-cocktail scale: 4 seeds × 20 generations × 36
   concentrations."* Reported, not linked. (It agrees with the `antibiotics-cd2` source config, so
   the value is independently corroborated — but the PR did not know that; it merged 2 minutes after
   its own review comment.)

4. **`188da919` #171 — Run 4 screens native_oe, not the tnaA/trpR knockout.** Justification: *"the
   tnaA/trpR knockout is viz-mechanics only (per @cplong90's #86 review), not a Run 4 config."* One
   config added, one deleted; the cited review is on a different PR.

**Two adjacent items that are not S but belong in front of a scientist:**
- **#306's DHPS kinetics** — kcat 0.38, km_paba 7.82e-3 mM, k_i 5.15e-3 mM. The PR's authority is
  "match the vEcoli reference (and the reverted #753 block) exactly"; **no primary citation for the
  three numbers appears anywhere in this repo.**
- **#152's 2–3× violacein titer divergence**, declared "a finding, not a bug" with a bit-faithful ODE.
  No scientist commented.

---

### 6. What I could not determine

- **Whether any `ecoli-sources` / `ecoli-sources-private` pin bump changed reconstruction or model
  code.** Their bodies name only schema and validation-data reasons; the package also ships the ParCa
  flat files and (per #301) at least one model process file. Answering this needs a diff of the
  package between `2dfabd52`, `840bc973`, and their June predecessors — outside this repo.
- **Who actually typed any of it.** Every login in this audit posts as both a person and a Claude
  session; five PRs (#303, #306, #308, #309, #307) carry a review comment posted under `eagmon` on
  `eagmon`'s own PR, and four of those say the merge is "held for Eran's go" while the PR merged 2–20
  minutes later with no recorded go. I have reported that as a fact about the record, not as an
  inference about who read what.
- **The two June direct commits** (`e1ca115a`, `f4eb0d9c`) have no PR; `f4eb0d9c` has no commit body
  at all, so its subject line is the entire available context.
- **Whether `vEcoli-private` branch `antibiotics-cd2` or `master`/#93 is the authoritative Run 3 dose
  grid.** Both are present in this repo. #299 raised it on sms-ecoli#166 and it is unresolved there;
  I did not read that issue thread as it is outside the commit list.
- **Whether the #199 "eagmon-approved" and #301 "Eran's follow-Robotato/master directive" claims are
  real.** Both are asserted in PR bodies and neither is linked to anything.


---

# Appendix E — Part 2 rubric

## Intent audit rubric (second pass over the 2026-09-09 model-change audit)

Context from Jim (the user), verbatim in substance:
- The models were MIGRATED from another repo with the v1 vEcoli structure (vEcoli / vEcoli-private /
  the "fork"), and had to be INJECTED into the v2ecoli composition and somewhat refactored. A migration
  PR is the transfer of a scientific artifact; its description should make that clear, and we want to
  extract the scientific justification and motivation of the entire PR (what was ported, from where,
  what fidelity was claimed or verified, what was knowingly changed).
- More recently the team has been DEBUGGING THE COMPOSITION under the v2ecoli structure. Some of those
  fixes may have corrected mistakes in the original translation. Those are software fixes whose
  authority is "what vEcoli does".
- Most recently Alex Patrie and Jim Schaff (via their Claude sessions, posting as @AlexPatrie /
  @jcschaff) have been changing things to get the PLUMBING to work. Even where those PRs were written
  with a scientific-sounding rationale, the intent is NOT to make modeling decisions. We need to know
  whether any of them did anyway.

The first pass classified EFFECT (A semantics / B interfaces / C opt-in / P parca / E design). This pass
classifies INTENT and AUTHORITY, from the PR description, the PR thread, and the commit message —
i.e. by the CONTEXT the change was made in. Do not re-derive effect; take it from the first pass.

### Intent codes (exactly one per commit; add a second only if the PR itself is two things)
- **M  Migration** — ports model code or model data from a named source (vEcoli, vEcoli-private, the
  fork, vivarium-ecoli, a paper's supplement). Record: the source (repo/branch/file if named), the
  fidelity claim (e.g. "reference-parity tests", "rtol 1e-6", "byte-identical", none), and any
  deviation from the source the PR admits (refactor, dropped feature, changed default).
- **T  Translation correction** — the PR's stated reason is that v2ecoli/sms-ecoli behaved differently
  from the source model and this restores the source behaviour. Authority cited = the source model.
  Record the cited reference behaviour.
- **S  Scientific refinement / modeling decision** — the stated reason is a scientific claim or a
  choice with no source-model authority: a new mechanism, a parameter value with a citation or none,
  a media/condition definition, enabling/disabling a mechanism by default, a dose grid, a division
  rule. Record the justification VERBATIM (short quote) and whether a human-looking comment from
  eagmon or cplong90 endorses it (a PR body written by a Claude session is not endorsement).
- **W  Plumbing / software debugging** — the stated reason is software: a crash, a config not
  reaching its target, a store type, ordering, threading a knob, a dispatcher need. No claim about
  what the biology should be.
- **W!** — a W-intent PR whose diff nonetheless makes a modeling decision (chooses a numeric value,
  adds or removes a rule, changes a default that alters results where it did not previously crash,
  changes a declared input/output relationship between processes for a reason other than restoring the
  source). This is the category Jim most wants to see. Say exactly what decision was embedded.

### Authority column
What the PR appeals to: `vEcoli` (names the reference behaviour), `citation` (paper/database),
`none` (asserts), `crash` (the only justification is that it no longer crashes), `team` (a decision
recorded in an issue/thread by a person — link it).

### Login classes (logins are Claude sessions much of the time; say so, do not guess who typed)
scientist logins: eagmon, cplong90 (and git authors "Eran", "Eran Agmon", "Chris Long").
engineer logins: AlexPatrie / "A.P.", jcschaff / "Jim Schaff".

### Method
- For every commit in the first-pass A, B (and P-A, and the "outside model paths" A) tables: read the
  PR body and ALL comments/reviews (`gh pr view N -R <repo> --json title,body,author,comments,reviews`
  or `gh api repos/<repo>/pulls/N/comments`), and the commit body (`git show -s --format=%B <sha>`).
  For direct commits with no PR, the commit body is the only context; say so.
- Quote, do not paraphrase, the sentence(s) that state the motivation. ≤ 40 words per quote.
- Read-only. Do not post, comment, push, or check anything out. Do not run simulations.
- Timezone: GitHub gives UTC; keep it.

### Output (markdown file; the path is given in your task)
1. Totals: intent × effect cross-tab; intent × login-class cross-tab.
2. The migration PRs, each with a paragraph: source, what was ported, fidelity claim, admitted
   deviations, whether the description says it is a scientific artifact transfer.
3. The full table, most recent first: sha | date | PR | login (class) | effect | intent | authority |
   stated motivation (quote) | embedded modeling decision (for S and W!) | human endorsement seen?
4. The W! list on its own, engineer logins first — these are the answer to "did the plumbing PRs make
   modeling decisions".
5. The S list on its own with the justifications, for Eran and Chris the people to review.
6. What you could not determine (missing PR body, squash with no thread, etc.).

