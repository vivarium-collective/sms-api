"""
API for funcs in this module:

Names: <ROUTER_NAME>_<ENDPOINT_NAME/PATHS>()

For example:

For the endpoint: /core/simulation/workflow: core_simulation_workflow
For the endpoint: /core/simulator/versions: core_simulator_versions

Then, add that func to the list within the examples dict comprehension below!
"""
import json

from sms_api.common.utils import unique_id
from sms_api.data.models import ExperimentAnalysisRequest, PtoolsAnalysisConfig
from sms_api.simulation.models import ExperimentRequest, ObservablesRequest

ptools_analysis = ExperimentAnalysisRequest(
    experiment_id="sms_multiseed_0-2794dfa74b9cf37c_1759844363435",
    multiseed=[
        PtoolsAnalysisConfig(
            name="ptools_rxns",
            n_tp=8,
        ),
        PtoolsAnalysisConfig(name="ptools_proteins", n_tp=8),
        PtoolsAnalysisConfig(name="ptools_rna", n_tp=8),
    ],
)


base_simulation = (lambda expid: ExperimentRequest(experiment_id=expid, simulation_name=expid))(
    unique_id("sms_experiment")
)

# base_observables = ["bulk", "genes"]
base_observables = ObservablesRequest(
    bulk=[
        "--TRANS-ACENAPHTHENE-12-DIOL",
        "ACETOLACTSYNI-CPLX",
        "CPD-3729"
    ],
    genes=[
        "deoC",
        "deoD",
        "fucU"
    ]
)

with open("/Users/alexanderpatrie/sms/sms-api/assets/wcecoli_figure2_setD4.json", "r") as fp:
    experiment_conf = json.load(fp)
wcecoli_fig2_setD4 = ExperimentRequest(simulation_name="wcecoli_figure2_setD4", **experiment_conf)

