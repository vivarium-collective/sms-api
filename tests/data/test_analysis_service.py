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


class TestAnalysisDataFiltering:
    """Tests for top-level generation_start, generation_end, and seeds filtering.

    These map to vEcoli's ``build_duckdb_filter`` which applies DuckDB WHERE
    clauses to the simulation dataset *before* any analysis module runs.
    """

    def test_to_dict_passes_n_tp(self) -> None:
        config = PtoolsAnalysisConfig(name=PtoolsAnalysisType.REACTIONS, n_tp=10)
        result = config.to_dict()
        assert result == {"ptools_rxns": {"n_tp": 10}}

    def test_request_generation_start_sets_generation_range(self) -> None:
        request = ExperimentAnalysisRequest(
            experiment_id="test-exp",
            generation_start=3,
            multiseed=[PtoolsAnalysisConfig(name=PtoolsAnalysisType.REACTIONS, n_tp=8)],
        )
        config = request.to_config(analysis_name="test-analysis", env=ENV)
        # generation_range is [start, end) exclusive — so start=3, end=1000 (no upper bound)
        # Filters live inside analysis_options (where vEcoli reads them)
        assert config.analysis_options.generation_range == [3, 1000]  # type: ignore[attr-defined]

    def test_request_generation_end_sets_generation_range(self) -> None:
        request = ExperimentAnalysisRequest(
            experiment_id="test-exp",
            generation_end=7,
            multiseed=[PtoolsAnalysisConfig(name=PtoolsAnalysisType.REACTIONS, n_tp=8)],
        )
        config = request.to_config(analysis_name="test-analysis", env=ENV)
        # generation_end=7 → range [0, 8) to include generation 7
        assert config.analysis_options.generation_range == [0, 8]  # type: ignore[attr-defined]

    def test_request_generation_range_both_bounds(self) -> None:
        request = ExperimentAnalysisRequest(
            experiment_id="test-exp",
            generation_start=2,
            generation_end=8,
            multiseed=[PtoolsAnalysisConfig(name=PtoolsAnalysisType.REACTIONS, n_tp=8)],
        )
        config = request.to_config(analysis_name="test-analysis", env=ENV)
        assert config.analysis_options.generation_range == [2, 9]  # type: ignore[attr-defined]

    def test_request_seeds_sets_lineage_seed(self) -> None:
        request = ExperimentAnalysisRequest(
            experiment_id="test-exp",
            seeds=[0, 3, 5],
            multiseed=[PtoolsAnalysisConfig(name=PtoolsAnalysisType.RNA, n_tp=8)],
        )
        config = request.to_config(analysis_name="test-analysis", env=ENV)
        assert config.analysis_options.lineage_seed == [0, 3, 5]  # type: ignore[attr-defined]

    def test_request_all_filters(self) -> None:
        request = ExperimentAnalysisRequest(
            experiment_id="test-exp",
            generation_start=2,
            generation_end=9,
            seeds=[1, 2],
            multiseed=[PtoolsAnalysisConfig(name=PtoolsAnalysisType.REACTIONS, n_tp=10)],
        )
        config = request.to_config(analysis_name="test-analysis", env=ENV)
        assert config.analysis_options.generation_range == [2, 10]  # type: ignore[attr-defined]
        assert config.analysis_options.lineage_seed == [1, 2]  # type: ignore[attr-defined]
        # Module params are still preserved
        multiseed = config.analysis_options.multiseed  # type: ignore[attr-defined]
        assert multiseed["ptools_rxns"]["n_tp"] == 10

    def test_request_no_filters_omits_keys(self) -> None:
        request = ExperimentAnalysisRequest(
            experiment_id="test-exp",
            multiseed=[PtoolsAnalysisConfig(name=PtoolsAnalysisType.REACTIONS, n_tp=8)],
        )
        config = request.to_config(analysis_name="test-analysis", env=ENV)
        assert not hasattr(config.analysis_options, "generation_range")
        assert not hasattr(config.analysis_options, "lineage_seed")

    def test_request_serialization_roundtrip(self) -> None:
        request = ExperimentAnalysisRequest(
            experiment_id="test-exp",
            generation_start=3,
            generation_end=8,
            seeds=[0, 1],
            multiseed=[PtoolsAnalysisConfig(name=PtoolsAnalysisType.REACTIONS, n_tp=8)],
        )
        dumped = request.model_dump()
        restored = ExperimentAnalysisRequest(**dumped)
        assert restored.generation_start == 3
        assert restored.generation_end == 8
        assert restored.seeds == [0, 1]
