import pytest

from sms_api.analysis.analysis_service import AnalysisServiceSlurm, RequestPayload
from sms_api.analysis.models import (
    AnalysisConfig,
    ExperimentAnalysisRequest,
    PtoolsAnalysisConfig,
    PtoolsAnalysisType,
)
from sms_api.api import request_examples
from sms_api.config import get_settings

ENV = get_settings()
GENERATE_ARTIFACTS = True

# Test simulator hash - used for unit tests only
TEST_SIMULATOR_HASH = "test123abc"


@pytest.mark.asyncio
async def test_generate_slurm_script(
    analysis_service: AnalysisServiceSlurm,
    analysis_request_config: AnalysisConfig,
) -> None:
    request = request_examples.analysis_ptools
    simulator_hash = TEST_SIMULATOR_HASH
    name = "test_generate_slurm_script"
    analysis_config = request.to_config(analysis_name=name, env=ENV)

    slurmjob_name, slurm_log_file = analysis_service._collect_slurm_parameters(
        request=request, simulator_hash=simulator_hash, analysis_name=name
    )

    slurm_script = analysis_service._generate_slurm_script(
        slurm_log_file=slurm_log_file,
        slurm_job_name=slurmjob_name,
        latest_hash=simulator_hash,
        config=analysis_config,
        analysis_name=name,
    )

    assert isinstance(slurm_script, str)


@pytest.mark.asyncio
async def test_normalize() -> None:
    from sms_api.api.request_examples import analysis_request_base

    origin = analysis_request_base.model_dump()
    payload1 = RequestPayload(data=origin)
    h1 = payload1.hash()
    assert h1 == RequestPayload(data=origin).hash()


# -- generation/seed filtering tests --


class TestPtoolsAnalysisConfigFiltering:
    """Tests for generation_start, generation_end, and seeds filtering params."""

    def test_to_dict_no_filters(self) -> None:
        config = PtoolsAnalysisConfig(name=PtoolsAnalysisType.REACTIONS, n_tp=10)
        result = config.to_dict()
        assert result == {"ptools_rxns": {"n_tp": 10}}

    def test_to_dict_generation_start(self) -> None:
        config = PtoolsAnalysisConfig(name=PtoolsAnalysisType.RNA, n_tp=8, generation_start=3)
        result = config.to_dict()
        assert result == {"ptools_rna": {"n_tp": 8, "generation_lower_bound": 3}}

    def test_to_dict_generation_end(self) -> None:
        config = PtoolsAnalysisConfig(name=PtoolsAnalysisType.PROTEINS, n_tp=5, generation_end=7)
        result = config.to_dict()
        assert result == {"ptools_proteins": {"n_tp": 5, "generation_upper_bound": 7}}

    def test_to_dict_generation_range(self) -> None:
        config = PtoolsAnalysisConfig(name=PtoolsAnalysisType.REACTIONS, n_tp=8, generation_start=2, generation_end=8)
        result = config.to_dict()
        assert result == {"ptools_rxns": {"n_tp": 8, "generation_lower_bound": 2, "generation_upper_bound": 8}}

    def test_to_dict_seeds(self) -> None:
        config = PtoolsAnalysisConfig(name=PtoolsAnalysisType.RNA, n_tp=8, seeds=[0, 3, 5])
        result = config.to_dict()
        assert result == {"ptools_rna": {"n_tp": 8, "lineage_seeds": [0, 3, 5]}}

    def test_to_dict_all_filters(self) -> None:
        config = PtoolsAnalysisConfig(
            name=PtoolsAnalysisType.REACTIONS, n_tp=10, generation_start=2, generation_end=9, seeds=[1, 2]
        )
        result = config.to_dict()
        assert result == {
            "ptools_rxns": {
                "n_tp": 10,
                "generation_lower_bound": 2,
                "generation_upper_bound": 9,
                "lineage_seeds": [1, 2],
            }
        }

    def test_request_to_config_preserves_filters(self) -> None:
        request = ExperimentAnalysisRequest(
            experiment_id="test-exp",
            multiseed=[
                PtoolsAnalysisConfig(name=PtoolsAnalysisType.REACTIONS, n_tp=8, generation_start=5),
                PtoolsAnalysisConfig(name=PtoolsAnalysisType.RNA, n_tp=8, seeds=[0, 1]),
            ],
        )
        config = request.to_config(analysis_name="test-analysis", env=ENV)
        multiseed = config.analysis_options.multiseed  # type: ignore[attr-defined]
        assert multiseed["ptools_rxns"]["generation_lower_bound"] == 5
        assert multiseed["ptools_rna"]["lineage_seeds"] == [0, 1]

    def test_request_serialization_roundtrip(self) -> None:
        config = PtoolsAnalysisConfig(name=PtoolsAnalysisType.REACTIONS, n_tp=8, generation_start=3, generation_end=8)
        request = ExperimentAnalysisRequest(
            experiment_id="test-exp",
            multiseed=[config],
        )
        dumped = request.model_dump()
        restored = ExperimentAnalysisRequest(**dumped)
        assert restored.multiseed is not None
        item = restored.multiseed[0]
        assert isinstance(item, PtoolsAnalysisConfig)
        assert item.generation_start == 3
        assert item.generation_end == 8
