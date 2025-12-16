"""
API for funcs in this module:

Names: <ROUTER_NAME>_<ENDPOINT_NAME/PATHS>()

For example:

For the endpoint: /core/simulation/workflow: core_simulation_workflow
For the endpoint: /core/simulator/versions: core_simulator_versions

Then, add that func to the list within the examples dict comprehension below!
"""

from sms_api.analysis.models import AnalysisDomain, ExperimentAnalysisRequest, PtoolsAnalysisConfig, PtoolsAnalysisType
from sms_api.common.gateway.utils import generate_analysis_request
from sms_api.common.utils import unique_id
from sms_api.simulation.models import ExperimentRequest

DEFAULT_NUM_SEEDS = 30
DEFAULT_NUM_GENERATIONS = 4


def get_analysis_multiseed_multigen() -> ExperimentAnalysisRequest:
    request = ExperimentAnalysisRequest(
        analysis_name="ANALYSIS_TEST",
        experiment_id="publication_multiseed_multigen-a7ae0b4e093e20e6_1762830572273",
        # experiment_id="sms_multiseed_0-2794dfa74b9cf37c_1759844363435",
        multiseed=[
            PtoolsAnalysisConfig(
                name=PtoolsAnalysisType.REACTIONS,
                n_tp=5,
            ),
            PtoolsAnalysisConfig(name=PtoolsAnalysisType.RNA, n_tp=5),
        ],
        multigeneration=[
            PtoolsAnalysisConfig(
                name=PtoolsAnalysisType.REACTIONS,
                n_tp=5,
            ),
            PtoolsAnalysisConfig(name=PtoolsAnalysisType.RNA, n_tp=5),
        ],
        experiment_index=False,
    )

    return request


def get_analysis_ptools() -> ExperimentAnalysisRequest:
    return ExperimentAnalysisRequest(
        experiment_id="sms_multiseed_0-2794dfa74b9cf37c_1759844363435",
        multiseed=[
            PtoolsAnalysisConfig(
                name=PtoolsAnalysisType.REACTIONS,
                n_tp=8,
            ),
            PtoolsAnalysisConfig(name=PtoolsAnalysisType.PROTEINS, n_tp=10),
            PtoolsAnalysisConfig(name=PtoolsAnalysisType.RNA, n_tp=10),
        ],
    )


def get_analysis_ptools2() -> ExperimentAnalysisRequest:
    requested_configs = AnalysisDomain.to_list()
    expid = "publication_multiseed_multigen-a7ae0b4e093e20e6_1762830572273"
    request = generate_analysis_request(experiment_id=expid, requested_configs=requested_configs)
    return request


def get_analysis_wcecoli_setD4() -> ExperimentAnalysisRequest:
    # _n_init_sims_wcecoli_setD4 = 30
    #     generations_wcecoli_setD4 = 4
    experiment_id_wcecoli_setD4 = """ \
        wcecoli_fig2_setD4_scaled-c6263425684df8c0_1763578699104-449b7de3d0de10a5_1763578788396
    """.strip()
    return ExperimentAnalysisRequest(
        experiment_id=experiment_id_wcecoli_setD4,
        multiseed=[
            PtoolsAnalysisConfig(
                name=PtoolsAnalysisType.REACTIONS,
                n_tp=8,
            ),
            PtoolsAnalysisConfig(name=PtoolsAnalysisType.PROTEINS, n_tp=8),
            PtoolsAnalysisConfig(name=PtoolsAnalysisType.RNA, n_tp=8),
        ],
    )


def get_analysis_api_multiseed() -> ExperimentAnalysisRequest:
    expid = "api_multiseed"
    return ExperimentAnalysisRequest(
        experiment_id=expid,
        multiseed=[
            PtoolsAnalysisConfig(
                name=PtoolsAnalysisType.REACTIONS,
                n_tp=8,
            ),
            PtoolsAnalysisConfig(name=PtoolsAnalysisType.PROTEINS, n_tp=8),
            PtoolsAnalysisConfig(name=PtoolsAnalysisType.RNA, n_tp=8),
        ],
    )


def get_simulation_request(sim_id: str, gens: int, seeds: int) -> ExperimentRequest:
    sim_id = unique_id("sms_experiment")
    return ExperimentRequest(
        experiment_id=sim_id,
        simulation_name=sim_id,
        generations=gens,
        n_init_sims=seeds,
    )


def get_simulation_base() -> ExperimentRequest:
    sim_id = unique_id("sms_experiment")
    return get_simulation_request(sim_id=sim_id, gens=DEFAULT_NUM_GENERATIONS, seeds=DEFAULT_NUM_SEEDS)


# example analyses
analysis_ptools = get_analysis_ptools()
analysis_wcecoli_setD4 = get_analysis_wcecoli_setD4()
analysis_api_multiseed = get_analysis_api_multiseed()
analysis_multiseed_multigen = get_analysis_multiseed_multigen()
analysis_request_base = generate_analysis_request(
    # experiment_id="publication_multiseed_multigen-a7ae0b4e093e20e6_1762830572273",
    experiment_id="sms_multigeneration",
    requested_configs=[AnalysisDomain.MULTIGENERATION, AnalysisDomain.MULTISEED],
)

# example simulations
base_simulation = (lambda expid: ExperimentRequest(experiment_id=expid, simulation_name=expid))(unique_id("sms_single"))
base_observables = ["bulk"]
