"""
API for funcs in this module:

Names: <ROUTER_NAME>_<ENDPOINT_NAME/PATHS>()

For example:

For the endpoint: /core/simulation/workflow: core_simulation_workflow
For the endpoint: /core/simulator/versions: core_simulator_versions

Then, add that func to the list within the examples dict comprehension below!
"""

from sms_api.common.utils import unique_id
from sms_api.data.models import ExperimentAnalysisRequest, OutputFileMetadata, PtoolsAnalysisConfig
from sms_api.simulation.models import ExperimentRequest

ptools_analysis = ExperimentAnalysisRequest(
    experiment_id="sms_multigeneration_0",
    analysis_name=unique_id(scope="ptools_analysis"),
    multiseed=[
        PtoolsAnalysisConfig(
            name="ptools_rxns",
            n_tp=8,
            files=[OutputFileMetadata(filename="ptools_rxns_multiseed.txt", variant=0, generation=1)],
        )
    ],
)


base_simulation = (lambda expid: ExperimentRequest(experiment_id=expid, simulation_name=expid))(unique_id("sms_single"))

base_observables = ["bulk"]
