"""
API for funcs in this module:

Names: <ROUTER_NAME>_<ENDPOINT_NAME/PATHS>()

For example:

For the endpoint: /core/simulation/workflow: core_simulation_workflow
For the endpoint: /core/simulator/versions: core_simulator_versions

Then, add that func to the list within the examples dict comprehension below!
"""

from sms_api.common.utils import unique_id
from sms_api.data.models import ExperimentAnalysisRequest, PtoolsAnalysisConfig, PtoolsAnalysisType
from sms_api.simulation.models import ExperimentRequest

ptools_analysis = ExperimentAnalysisRequest(
    experiment_id="sms_multiseed_0-2794dfa74b9cf37c_1759844363435",
    multiseed=[
        PtoolsAnalysisConfig(
            name=PtoolsAnalysisType.REACTIONS,
            n_tp=8,
        ),
        PtoolsAnalysisConfig(name=PtoolsAnalysisType.PROTEINS, n_tp=8),
        PtoolsAnalysisConfig(name=PtoolsAnalysisType.RNA, n_tp=8),
    ],
)


base_simulation = (lambda expid: ExperimentRequest(experiment_id=expid, simulation_name=expid))(unique_id("sms_single"))

base_observables = ["bulk"]
