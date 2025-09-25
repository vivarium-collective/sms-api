"""
API for funcs in this module:

Names: <ROUTER_NAME>_<ENDPOINT_NAME/PATHS>()

For example:

For the endpoint: /core/simulation/workflow: core_simulation_workflow
For the endpoint: /core/simulator/versions: core_simulator_versions

Then, add that func to the list within the examples dict comprehension below!
"""

from sms_api.common.utils import unique_id
from sms_api.data.models import ExperimentAnalysisRequest
from sms_api.simulation.models import ExperimentRequest, SimulationConfiguration

DEFAULT_SIMULATION_CONFIG = SimulationConfiguration.from_base()


base_analysis = ExperimentAnalysisRequest(
    experiment_id="sms_multigeneration",
    analysis_name=unique_id(scope="ptools_analysis"),
    single={
        "mass_fraction_summary": {},
        "ptools_rxns": {"n_tp": 8},
        "ptools_rna": {"n_tp": 8},
        "ptools_proteins": {"n_tp": 8},
    },
    multigeneration={
        "replication": {},
        "ribosome_components": {},
        "ribosome_crowding": {},
        "ribosome_production": {},
        "ribosome_usage": {},
        "rna_decay_03_high": {},
        "ptools_rxns": {"n_tp": 8},
        "ptools_rna": {"n_tp": 8},
        "ptools_proteins": {"n_tp": 8},
    },
    multiseed={
        "protein_counts_validation": {},
        "ribosome_spacing": {},
        "subgenerational_expression_table": {},
        "ptools_rxns": {"n_tp": 8},
        "ptools_rna": {"n_tp": 8},
        "ptools_proteins": {"n_tp": 8},
    },
    multivariant={
        "average_monomer_counts": {},
        "cell_mass": {},
        "doubling_time_hist": {"skip_n_gens": 1},
        "doubling_time_line": {},
    },
)

ptools_analysis = ExperimentAnalysisRequest(
    experiment_id="sms_multigeneration",
    analysis_name=unique_id(scope="ptools_analysis"),
    single={"ptools_rxns": {"n_tp": 8}, "ptools_rna": {"n_tp": 8}, "ptools_proteins": {"n_tp": 8}},
    multigeneration={
        "ptools_rxns": {"n_tp": 8},
        "ptools_rna": {"n_tp": 8},
        "ptools_proteins": {"n_tp": 8},
    },
    multiseed={
        "ptools_rxns": {"n_tp": 8},
        "ptools_rna": {"n_tp": 8},
        "ptools_proteins": {"n_tp": 8},
    },
    multivariant={},
)


base_simulation = (lambda expid: ExperimentRequest(experiment_id=expid, simulation_name=expid))(unique_id("sms_single"))
