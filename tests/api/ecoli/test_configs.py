from pathlib import Path

import pytest

from sms_api.config import get_settings
from sms_api.data.models import AnalysisConfig
from sms_api.simulation.models import SimulationConfig


@pytest.mark.asyncio
async def test_analysis_config() -> None:
    conf_path = Path("assets/sms_multigen_analysis.json")
    conf = AnalysisConfig.from_file(fp=conf_path)
    assert conf.analysis_options.experiment_id is not None
    assert len(conf.emitter_arg["out_dir"])


@pytest.mark.skipif(len(get_settings().slurm_base_path) == 0, reason="slurm base path not supplied")
@pytest.mark.asyncio
def test_load_simulation_config() -> None:
    config = SimulationConfig.from_file(fp=Path("assets/sms_base_simulation_config.json"))
    expected_dump = {
        "experiment_id": "<PLACEHOLDER>",
        "sim_data_path": "/home/FCAM/svc_vivarium/workspace/kb/simData.cPickle",
        "suffix_time": True,
        "parca_options": {
            "cpus": 2,
            "outdir": "",
            "operons": True,
            "ribosome_fitting": True,
            "rnapoly_fitting": True,
            "remove_rrna_operons": False,
            "remove_rrff": False,
            "stable_rrna": False,
            "new_genes": "off",
            "debug_parca": False,
            "load_intermediate": None,
            "save_intermediates": False,
            "intermediates_directory": "",
            "variable_elongation_transcription": True,
            "variable_elongation_translation": False,
        },
        "generations": 1,
        "n_init_sims": 1,
        "max_duration": 10800.0,
        "initial_global_time": 0.0,
        "time_step": 1.0,
        "single_daughters": True,
        "emitter": "parquet",
        "emitter_arg": {"out_dir": ""},
        "analysis_options": {
            "single": {
                "mass_fraction_summary": {},
                "ptools_rxns": {"n_tp": 8},
                "ptools_rna": {"n_tp": 8},
                "ptools_proteins": {"n_tp": 8},
            }
        },
        "agent_id": "0",
        "parallel": False,
        "divide": True,
        "d_period": True,
        "division_threshold": True,
        "division_variable": ["divide"],
        "chromosome_path": ["unique", "full_chromosome"],
        "spatial_environment": False,
        "fixed_media": "minimal",
        "condition": "basal",
        "save": False,
        "profile": False,
        "processes": [
            "post-division-mass-listener",
            "bulk-timeline",
            "media_update",
            "exchange_data",
            "ecoli-tf-unbinding",
            "ecoli-equilibrium",
            "ecoli-two-component-system",
            "ecoli-rna-maturation",
            "ecoli-tf-binding",
            "ecoli-transcript-initiation",
            "ecoli-polypeptide-initiation",
            "ecoli-chromosome-replication",
            "ecoli-protein-degradation",
            "ecoli-rna-degradation",
            "ecoli-complexation",
            "ecoli-transcript-elongation",
            "ecoli-polypeptide-elongation",
            "ecoli-chromosome-structure",
            "ecoli-metabolism",
            "ecoli-mass-listener",
            "RNA_counts_listener",
            "rna_synth_prob_listener",
            "monomer_counts_listener",
            "dna_supercoiling_listener",
            "replication_data_listener",
            "rnap_data_listener",
            "unique_molecule_counts",
            "ribosome_data_listener",
            "global_clock",
        ],
        "process_configs": {"global_clock": {}, "replication_data_listener": {"time_step": 1}},
        "topology": {
            "bulk-timeline": {"bulk": ["bulk"], "global": ["timeline"], "media_id": ["environment", "media_id"]},
            "global_clock": {"global_time": ["global_time"], "next_update_time": ["next_update_time"]},
        },
        "engine_process_reports": [["listeners"]],
        "progress_bar": True,
        "emit_topology": False,
        "emit_processes": False,
        "emit_config": False,
        "emit_unique": False,
        "log_updates": False,
        "raw_output": True,
        "description": "",
        "seed": 0,
        "mar_regulon": False,
        "amp_lysis": False,
        "initial_state_file": "",
        "skip_baseline": False,
        "daughter_outdir": "",
        "lineage_seed": 0,
        "fail_at_max_duration": False,
        "flow": {
            "post-division-mass-listener": [],
            "media_update": [["post-division-mass-listener"]],
            "exchange_data": [["media_update"]],
            "ecoli-tf-unbinding": [["media_update"]],
            "ecoli-equilibrium": [["ecoli-tf-unbinding"]],
            "ecoli-two-component-system": [["ecoli-tf-unbinding"]],
            "ecoli-rna-maturation": [["ecoli-tf-unbinding"]],
            "ecoli-tf-binding": [["ecoli-equilibrium"]],
            "ecoli-transcript-initiation": [["ecoli-tf-binding"]],
            "ecoli-polypeptide-initiation": [["ecoli-tf-binding"]],
            "ecoli-chromosome-replication": [["ecoli-tf-binding"]],
            "ecoli-protein-degradation": [["ecoli-tf-binding"]],
            "ecoli-rna-degradation": [["ecoli-tf-binding"]],
            "ecoli-complexation": [["ecoli-tf-binding"]],
            "ecoli-transcript-elongation": [["ecoli-complexation"]],
            "ecoli-polypeptide-elongation": [["ecoli-complexation"]],
            "ecoli-chromosome-structure": [["ecoli-polypeptide-elongation"]],
            "ecoli-metabolism": [["ecoli-chromosome-structure"]],
            "ecoli-mass-listener": [["ecoli-metabolism"]],
            "RNA_counts_listener": [["ecoli-metabolism"]],
            "rna_synth_prob_listener": [["ecoli-metabolism"]],
            "monomer_counts_listener": [["ecoli-metabolism"]],
            "dna_supercoiling_listener": [["ecoli-metabolism"]],
            "replication_data_listener": [["ecoli-metabolism"]],
            "rnap_data_listener": [["ecoli-metabolism"]],
            "unique_molecule_counts": [["ecoli-metabolism"]],
            "ribosome_data_listener": [["ecoli-metabolism"]],
        },
    }
    assert config.model_dump() == expected_dump
