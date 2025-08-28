## Candidate parameters for perturbation:

- ### ``growth_rate_parameters``
    Why: Directly controls growth kinetics; affects many observables.

    Perturbation: ±10–50% (log-uniform if multiplicative).

    Sampling: 1-factor-at-a-time (OAT) for screening, then Sobol/Morris for global sensitivity.

- ### ``doubling_time`` (or parameters mapping in ``condition_to_doubling_time``)

    Why: Directly sets timescales for growth — high leverage on outputs.

    Perturbation: ±10–50% (or sample between plausible min/max doubling times).

    Note: If doubling_time and growth_rate_parameters both exist, perturb consistently.

- ### ``translation_supply_rate``

    Why: Affects protein synthesis throughput — important for proteome-level predictions.

    Perturbation: scale by 0.5–2× (log-uniform).

    Effect to watch: global protein abundance, resource allocation.

- ### ``tf_to_fold_change`` and ``pPromoterBound`` (TF / promoter strength maps)

    Why: Controls transcription regulation strength; perturbing these probes regulatory sensitivity.

    Perturbation: multiplicative factors (e.g., ×[0.5, 2.0]) or ±1–2 orders of magnitude for exploratory runs.

    Sampling: targeted (per-TF / per-promoter) then group-level.

- ### ``basal_expression_condition`` and ``adjust_final_expression`` / ``adjust_new_gene_final_expression``

    Why: Basal expression and final-expression adjustments move absolute expression levels (useful to test expression noise / detection).

    Perturbation: add/subtract absolute small amounts or multiply by 0.5–2×.

- ### ``translation_supply_rate`` (repeat intentionally — high impact on dynamics)

    Why: (See above) — critical if you simulate resource-limited behavior.

- ### ``expectedDryMassIncreaseDict``

    Why: Affects mass growth dynamics; changes cell size/timing.

    Perturbation: ±10–30% or multiplicative scaling.

- ### ``constants`` (physical/kinetic constants, if they are numeric model parameters)

    Why: Fundamental to dynamics; useful for sensitivity checks on specific constants.

    Perturbation: small ±1–20% (be careful: some constants must remain physically realistic).

- ### ``variants`` (if variants parameterize meaningful biological changes)

    Why: Simulates genotypic/phenotypic perturbations.

    Perturbation: toggle on/off or change values to represent mutant phenotypes.

- ### ``process_configs`` (per-process rate constants or config dictionaries)

    Why: Directly modifies per-process behavior (e.g., enzymatic rates).

    Perturbation: per-parameter ±10–100% depending on uncertainty.


## Perturbation Types

| Parameter | Perturbation Type | Notes / Reasoning |
|-----------|-----------------|-----------------|
| growth_rate_parameters | Multiplicative | Controls growth kinetics; relative scaling makes sense. ±10–50% multiplicative. |
| doubling_time / condition_to_doubling_time | Multiplicative | Timescale parameter; scaling is more natural than absolute offset. ±10–50% multiplicative. |
| translation_supply_rate | Multiplicative | Affects protein synthesis globally; scale 0.5–2×. |
| tf_to_fold_change | Multiplicative | TF regulation strength is inherently relative; scale 0.5–2× or orders of magnitude. |
| pPromoterBound | Multiplicative | Promoter binding effects are relative; scaling makes sense. |
| basal_expression_condition | Additive or Multiplicative | Can be either: small absolute changes (additive) or scale by 0.5–2× (multiplicative) depending on experiment. |
| adjust_final_expression / adjust_new_gene_final_expression | Additive or Multiplicative | Same reasoning as above: absolute adjustment vs fold-change. |
| expectedDryMassIncreaseDict | Multiplicative | Mass growth dynamics scale naturally; ±10–30% multiplicative. |
| constants | Additive or Multiplicative | Small ±1–20% perturbation; keep physically realistic. Multiplicative usually safer for rates. |
| variants | Additive / Discrete | Toggle or modify absolute values representing mutant phenotypes. |
| process_configs | Multiplicative | Rate constants / process parameters scale naturally; ±10–100% multiplicative. |

## Perturbation Strategies

### A — Where to Start (Priority List)

Start with the **scalar parameters** that have direct, large effects on transcription/translation/growth:

- **ribosomeElongationRate (amino_acid/s)** — high impact on translation throughput.
- **rnaPolymeraseElongationRate (nucleotide/s)** — high impact on transcription speed.
- **RNAP_per_cell** — cellular RNAP count; scales transcription capacity.
- **fractionActiveRibosome / fractionActiveRnap / fractionActiveRnapSynthesizingStableRna** — active fractions strongly affect effective capacity.
- **ppGpp_conc** — regulatory metabolite; influences transcription/translation indirectly.
- **expectedDryMassIncreaseDict / per_dry_mass_to_per_volume / ratioRProteinToTotalProtein** — mass/stoichiometry quantities affecting growth scaling.
- **distanceBetweenRibosomesOnMRna** — influences ribosome density/translation initiation; less obvious but useful to probe.
- **stableRnaPerTotalRnaSynthesized** — affects fraction of stable rRNA synthesized; can change resource allocation.

Then, after scanning scalars, probe the **spline-based parameters** (see special handling below):

- `RNAP_active_fraction_params`
- `RNAP_elongation_rate_params`
- `ribosome_active_fraction_params`
- `ribosome_elongation_rate_params`

These are functions that map growth condition (or time) → rate/fraction.

---

### B — Perturbation Type & Suggested Ranges (Concrete)

General rule: **rates and fold-effects → multiplicative**, **counts sometimes multiplicative**; **fractions must remain in [0,1]**.

| Parameter | Type | Suggested Perturbation |
|-----------|------|--------------------------|
| ribosomeElongationRate | multiplicative | ±10–30% (start: ±10%, ±30%) |
| rnaPolymeraseElongationRate | multiplicative | ±10–30% |
| RNAP_per_cell | multiplicative (or integer additive) | ×[0.8, 1.2] (±20%) or ±200–1000 RNAP for exploratory |
| fractionActiveRibosome / fractionActiveRnap / fractionActiveRnapSynthesizingStableRna | multiplicative/clamped | multiply by (1 + δ) with δ in [-0.2,0.2], then clamp to [0,1] |
| ppGpp_conc | multiplicative | ×[0.5, 2.0] (log-uniform if broad) |
| per_dry_mass_to_per_volume | multiplicative (phys constant) | ±5–10% (be conservative) |
| ratioRProteinToTotalProtein | multiplicative | ±10–30% |
| distanceBetweenRibosomesOnMRna | additive or multiplicative | small absolute ±5–20 nt, or ×[0.9,1.1] |
| stableRnaPerTotalRnaSynthesized | multiplicative (fraction) | scale ±10–30% then clamp to [0,1] |

**Start small** (±10% / ×[0.9,1.1]) for initial screening (OAT).
Use wider ranges (×0.5–2.0) only for exploratory or when you expect large uncertainty.

---

### C — Special Handling for Spline / Function Objects

Your interpolate objects (`CubicSpline` instances inside the `*_params` dicts) are function objects — **don’t rewrite their knot arrays** unless you know what you’re doing.
Safer approaches:

---

#### **Option 1 — Scale the Function Output**

Wrap the original function with a multiplicative factor:

```python
orig_fn = params['function']   # CubicSpline
factor = 1.2  # e.g. +20%
new_fn = lambda x, _orig=orig_fn, _f=factor: _orig(x) * _f
# replace the function pointer where the model expects it
params['function'] = new_fn
