"""The CD2 -> Nextflow translator: the team's workflow configs become one campaign each."""

from __future__ import annotations

import importlib.util
import json
import shlex
import sys
from pathlib import Path
from typing import Any

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "cd2_nextflow_dispatches.py"
_spec = importlib.util.spec_from_file_location("cd2_nextflow_dispatches", _SCRIPT)
assert _spec is not None and _spec.loader is not None
t: Any = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = t  # @dataclass resolves the module through sys.modules
_spec.loader.exec_module(t)

FLAT = {  # Runs 1/2/4 shape
    "swap_processes": {"ecoli-metabolism": "ecoli-metabolism-redux"},
    "exclude_processes": ["exchange_data"],
    "generations": 10,
    "n_init_sims": 1,
    "emitter": "parquet",
    "analysis_options": {"multiseed": {"cd1_exchange_fluxes": {"generation_lower_bound": 5}}, "single": {}},
}
NESTED = {  # Run 3 shape
    "generations": 8,
    "n_init_sims": 1,
    "injected_processes": {
        "add_processes": ["permeability", "gillespie"],
        "fork_repo": "",
        "process_configs": {"gillespie": {"bulk_species": True}},
        "seed_bulk_species": [{"id": "mecillinam[p]", "molar_mass_g_per_mol": 325.4}],
        "time_step": 1.0,
    },
    "analysis_options": {"multivariant": {"antibiotic_mic": {"skip_n_gens": 1}}},
}
MAPPING = {"k4_cell_only": {"rows": [{"seed": s, "cache_s3_uri": f"s3://b/founder-seed{s}"} for s in range(3)]}}


def test_flat_config_becomes_variants_carrying_the_apis_own_injection_block() -> None:
    plan = t.plan_campaign(
        run="1",
        cfg=FLAT,
        label="k4",
        simulator_id=181,
        simulation_config="c.json",
        variants=t.founder_variants(MAPPING, "k4_cell_only", "run1"),
    )
    v = plan.params["variants"]
    assert [x["variant_name"] for x in v] == ["run1_seed0", "run1_seed1", "run1_seed2"]
    assert all(x["cache_uri"] == f"s3://b/founder-seed{i}" for i, x in enumerate(v))
    inj = v[0]["injected_processes"]
    assert inj["swap_processes"] == {"ecoli-metabolism": "ecoli-metabolism-redux"}
    assert inj["exclude_processes"] == ["exchange_data"] and inj["fork_repo"] == ""
    # the product axis is a dispatch decision on Runs 1/2/4, top-level knobs since v2ecoli#746
    assert plan.params["exchange_fluxes"] == t.VIOLACEIN_EXCHANGE_FLUXES
    assert plan.params["exchange_flux_basis"] == "gdcw"
    assert plan.n_seeds == 1 and plan.n_generations == 10
    # only real, non-empty analysis scales survive
    assert plan.analysis_options == {"multiseed": {"cd1_exchange_fluxes": {"generation_lower_bound": 5}}}


def test_nested_run3_block_is_carried_whole_and_has_no_exchange_fluxes() -> None:
    plan = t.plan_campaign(
        run="3",
        cfg=NESTED,
        label="mec",
        simulator_id=181,
        simulation_config="c.json",
        variants=[
            {"variant_name": "dose_0", "config_overrides": {"dose": 0}},
            {"variant_name": "dose_1", "config_overrides": {"dose": 1}},
        ],
    )
    v = plan.params["variants"]
    assert [x["variant_name"] for x in v] == ["dose_0", "dose_1"]
    inj = v[1]["injected_processes"]
    assert inj["add_processes"] == ["permeability", "gillespie"]
    assert inj["process_configs"] == {"gillespie": {"bulk_species": True}}
    assert inj["seed_bulk_species"][0]["id"] == "mecillinam[p]"
    assert v[1]["config_overrides"] == {"dose": 1}
    assert "exchange_fluxes" not in plan.params
    assert plan.analysis_options == {"multivariant": {"antibiotic_mic": {"skip_n_gens": 1}}}


def test_command_is_the_proven_cli_shape_from_sim_683() -> None:
    plan = t.plan_campaign(
        run="2",
        cfg=FLAT,
        label="j3",
        simulator_id=181,
        simulation_config="c.json",
        n_seeds=10,
        cache_uri="s3://b/chassis",
        independent_founders=True,
        media=None,
    )
    args = plan.cli_args()
    assert args[:7] == ["uv", "run", "atlantis", "composite", "nextflow", "j3", "181"]
    assert "--executor" in args and args[args.index("--executor") + 1] == "awsbatch"
    assert "--independent-founders" in args and "--include-analysis" in args
    assert args[args.index("--cache-uri") + 1] == "s3://b/chassis"
    params = json.loads(args[args.index("--params") + 1])
    assert params["variants"][0]["variant_name"] == "run2" and params["exchange_fluxes"]
    # round-trips through the shell
    assert shlex.split(plan.command()) == args


def test_media_reaches_the_campaign_for_run4_arms() -> None:
    plan = t.plan_campaign(
        run="4",
        cfg=FLAT,
        label="fss",
        simulator_id=181,
        simulation_config="c.json",
        variants=[{"variant_name": "g7", "new_genes": "fss_g7", "cache_uri": "s3://b/g7"}],
        media="minimal",
    )
    assert plan.params["media"] == "minimal"
    assert plan.params["variants"][0]["new_genes"] == "fss_g7"


def test_refusals() -> None:
    with pytest.raises(t.TranslationError, match="experiment_id"):
        t.plan_campaign(run="1", cfg={**FLAT, "experiment_id": "x"}, label="k4", simulator_id=1, simulation_config="c")
    with pytest.raises(t.TranslationError, match="share one founder"):
        t.plan_campaign(
            run="1",
            cfg=FLAT,
            label="k4",
            simulator_id=1,
            simulation_config="c",
            n_seeds=4,
            variants=[{"variant_name": "a", "cache_uri": "s3://a"}, {"variant_name": "b", "cache_uri": "s3://b"}],
        )
    with pytest.raises(t.TranslationError, match="PENDING"):
        t.founder_variants({"k4_cell_only": {"rows": [{"seed": 0, "cache_s3_uri": "PENDING"}]}}, "k4_cell_only", "r")
    with pytest.raises(t.TranslationError, match="duplicate"):
        t.variant_specs([{"variant_name": "a"}, {"variant_name": "a"}], None)


def test_cli_main_against_the_real_sms_ecoli_configs(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = Path("/Users/jimschaff/Documents/workspace/sms-ecoli")
    if not (repo / "configs/cd2/run3_antibiotic_pg_sulfadiazine.json").exists():
        pytest.skip("sms-ecoli checkout not available")
    rc = t.main([
        "--run",
        "3",
        "--sms-ecoli",
        str(repo),
        "--simulator",
        "181",
        "--label",
        "mec-pilot",
        "--variants-json",
        '[{"variant_name":"dose_a"}]',
        "--generations",
        "1",
        "--emit",
        "json",
    ])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    inj = out["params"]["variants"][0]["injected_processes"]
    assert "permeability" in inj["add_processes"] and "process_configs" in inj
    assert out["n_generations"] == 1 and "multivariant" in out["analysis_options"]


def test_run4_genotypes_are_one_variant_per_cache_and_one_campaign_per_medium() -> None:
    names = t.expand_template("cd2-run4-carina-genotype{n}", 1, 3)
    variants = t.cache_variants(names, "6299ba5", "run4")
    assert variants[2] == {
        "variant_name": "run4_cd2-run4-carina-genotype3",
        "cache_uri": "s3://smsvpctest-shared-sharedbucket60d199d6-abfvwv0day91/ray-parca-cache/6299ba5/cd2-run4-carina-genotype3/",
    }
    minimal = t.plan_campaign(
        run="4",
        cfg=FLAT,
        label="fss-min",
        simulator_id=181,
        simulation_config="c",
        variants=variants,
        media="minimal",
        n_seeds=1,
        n_generations=8,
    )
    trp = t.plan_campaign(
        run="4",
        cfg=FLAT,
        label="fss-trp",
        simulator_id=181,
        simulation_config="c",
        variants=variants,
        media="minimal_plus_tryptophan",
        n_seeds=1,
        n_generations=8,
    )
    assert len(minimal.params["variants"]) == 3 and minimal.params["media"] == "minimal"
    assert trp.params["media"] == "minimal_plus_tryptophan"
    assert all("new_genes" not in v for v in minimal.params["variants"])  # the strain IS the cache
    with pytest.raises(t.TranslationError, match="cache-commit"):
        t.cache_variants(names, "", "run4")


def test_run3_dose_sweep_is_a_per_variant_patch_over_the_configs_injection_block() -> None:
    doses = [
        {
            "variant_name": f"mec_{d}",
            "injected_processes_patch": {"process_configs": {"field_timeline": {"timeline": [[0, {"mecillinam": d}]]}}},
        }
        for d in (0.0, 0.5)
    ]
    plan = t.plan_campaign(run="3", cfg=NESTED, label="mec", simulator_id=181, simulation_config="c", variants=doses)
    v0, v1 = plan.params["variants"]
    assert v1["injected_processes"]["process_configs"]["field_timeline"]["timeline"] == [[0, {"mecillinam": 0.5}]]
    assert v1["injected_processes"]["process_configs"]["gillespie"] == {"bulk_species": True}  # rest intact
    assert v1["injected_processes"]["add_processes"] == ["permeability", "gillespie"]
    assert "injected_processes_patch" not in v1
    assert v0["injected_processes"]["process_configs"]["field_timeline"]["timeline"][0][1] == {"mecillinam": 0.0}
    with pytest.raises(t.TranslationError, match="no block to patch"):
        t.variant_specs([{"variant_name": "x", "injected_processes_patch": {"a": 1}}], None)


def test_deep_merge_replaces_leaves_and_merges_dicts() -> None:
    assert t.deep_merge({"a": {"b": 1, "c": 2}, "d": [1]}, {"a": {"c": 3}, "d": [2]}) == {
        "a": {"b": 1, "c": 3},
        "d": [2],
    }


def test_exchange_fluxes_ride_in_the_injection_block_too_for_pre_746_images() -> None:
    plan = t.plan_campaign(
        run="1",
        cfg=FLAT,
        label="k4",
        simulator_id=173,
        simulation_config="c",
        variants=[{"variant_name": "s0", "cache_uri": "s3://b/s0"}],
    )
    inj = plan.params["variants"][0]["injected_processes"]
    assert inj["exchange_fluxes"] == t.VIOLACEIN_EXCHANGE_FLUXES and inj["exchange_flux_basis"] == "gdcw"
    assert inj["swap_processes"] == {"ecoli-metabolism": "ecoli-metabolism-redux"}  # the config's block survives
    assert plan.params["exchange_fluxes"] == t.VIOLACEIN_EXCHANGE_FLUXES  # and the #746 knob is still set
    run3 = t.plan_campaign(run="3", cfg=NESTED, label="mec", simulator_id=181, simulation_config="c")
    assert "exchange_fluxes" not in run3.params["variants"][0]["injected_processes"]


def test_legacy_image_emits_no_top_level_knobs_but_keeps_fluxes_in_the_injection_block() -> None:
    """sim 732 on simulator 173: to_document raised KeyError on the #746 knobs."""
    plan = t.plan_campaign(
        run="1",
        cfg={**FLAT, "time_step": 1.0},
        label="k4",
        simulator_id=173,
        simulation_config="c",
        variants=[{"variant_name": "s0", "cache_uri": "s3://b/s0"}],
        legacy_image=True,
    )
    assert set(plan.params) == {"variants"}
    inj = plan.params["variants"][0]["injected_processes"]
    assert inj["exchange_fluxes"] == t.VIOLACEIN_EXCHANGE_FLUXES
    with pytest.raises(t.TranslationError, match="media needs a #746 image"):
        t.plan_campaign(
            run="4", cfg=FLAT, label="x", simulator_id=166, simulation_config="c", media="minimal", legacy_image=True
        )


def test_run3_sweep_is_one_variant_per_dose_combo_with_its_own_resolved_timeline() -> None:
    repo = Path("/Users/jimschaff/Documents/workspace/sms-ecoli")
    if not (repo / "sms_modules/bridge/antibiotic_cocktail_sweep.py").exists():
        pytest.skip("sms-ecoli >= #299 not available")
    base = {**NESTED, "generations": 1, "n_init_sims": 1}
    base["injected_processes"] = {
        **NESTED["injected_processes"],
        "process_configs": {"gillespie": {"bulk_species": True}, "field_timeline": {"bins": [1, 1], "timeline": []}},
    }
    variants, seeds, gens = t.run3_sweep_variants(base, repo, "mec-sweep")
    assert len(variants) == 36 and (seeds, gens) == (4, 20)
    names = [v["variant_name"] for v in variants]
    assert names[0] == "combo00_mec0_sulf0" and names[-1] == "combo35_mec0.1_sulf1" and len(set(names)) == 36
    tl = variants[7]["injected_processes"]["process_configs"]["field_timeline"]["timeline"]
    assert tl == [[10000.0, {"mecillinam": 1e-05}], [10000.0, {"sulfadiazine": 0.0001}]]
    assert variants[7]["injected_processes"]["add_processes"] == ["permeability", "gillespie"]
    assert all("experiment_id" not in v for v in variants)
    plan = t.plan_campaign(
        run="3",
        cfg=base,
        label="mec-sweep",
        simulator_id=181,
        simulation_config="c",
        variants=variants,
        n_seeds=seeds,
        n_generations=gens,
    )
    assert plan.n_seeds == 4 and plan.n_generations == 20 and len(plan.params["variants"]) == 36
    assert "exchange_fluxes" not in plan.params
