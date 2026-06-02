"""Tests for Path B1: decouple ``n_tp`` from the SLURM run.

Covers:
- ``RequestPayload.hash()`` is independent of ``n_tp``.
- ``PtoolsAnalysisConfig`` validates ``n_tp`` against the supported divisor set.
- ``reaggregate_ptools_columns`` produces correct mean/sum re-binned TSVs.
- ``ptools_aggregation_mode`` reports per-module modes.
"""

import io

import pandas as pd
import pytest

from sms_api.analysis.analysis_service import (
    RequestPayload,
    ptools_aggregation_mode,
    reaggregate_ptools_columns,
)
from sms_api.analysis.models import (
    PTOOLS_CANONICAL_N_TP,
    PTOOLS_SUPPORTED_N_TP,
    ExperimentAnalysisRequest,
    PtoolsAnalysisConfig,
    PtoolsAnalysisType,
)


def _request_with_n_tp(n_tp: int) -> dict[str, object]:
    return ExperimentAnalysisRequest(
        experiment_id="exp1",
        single=[
            PtoolsAnalysisConfig(name=PtoolsAnalysisType.RNA.value, n_tp=n_tp),
            PtoolsAnalysisConfig(name=PtoolsAnalysisType.PROTEINS.value, n_tp=n_tp),
        ],
    ).model_dump()


def test_supported_n_tp_includes_divisors_of_canonical() -> None:
    for n in PTOOLS_SUPPORTED_N_TP:
        assert PTOOLS_CANONICAL_N_TP % n == 0
    # canonical itself is in the supported set
    assert PTOOLS_CANONICAL_N_TP in PTOOLS_SUPPORTED_N_TP


def test_request_payload_hash_is_independent_of_n_tp() -> None:
    h_a = RequestPayload(data=_request_with_n_tp(8)).hash()
    h_b = RequestPayload(data=_request_with_n_tp(60)).hash()
    h_c = RequestPayload(data=_request_with_n_tp(PTOOLS_CANONICAL_N_TP)).hash()
    assert h_a == h_b == h_c


def test_request_payload_hash_differs_when_module_set_differs() -> None:
    req_rna_only = ExperimentAnalysisRequest(
        experiment_id="exp1",
        single=[PtoolsAnalysisConfig(name=PtoolsAnalysisType.RNA.value, n_tp=8)],
    ).model_dump()
    req_both = _request_with_n_tp(8)
    assert RequestPayload(data=req_rna_only).hash() != RequestPayload(data=req_both).hash()


def test_request_payload_hash_differs_when_filters_differ() -> None:
    a = ExperimentAnalysisRequest(
        experiment_id="exp1",
        seeds=[0],
        single=[PtoolsAnalysisConfig(name=PtoolsAnalysisType.RNA.value, n_tp=8)],
    ).model_dump()
    b = ExperimentAnalysisRequest(
        experiment_id="exp1",
        seeds=[0, 1],
        single=[PtoolsAnalysisConfig(name=PtoolsAnalysisType.RNA.value, n_tp=8)],
    ).model_dump()
    assert RequestPayload(data=a).hash() != RequestPayload(data=b).hash()


def test_ptools_config_rejects_non_divisor_n_tp() -> None:
    with pytest.raises(ValueError, match="must be a divisor"):
        PtoolsAnalysisConfig(name=PtoolsAnalysisType.RNA.value, n_tp=7)


def test_ptools_config_accepts_default_n_tp() -> None:
    cfg = PtoolsAnalysisConfig(name=PtoolsAnalysisType.RNA.value)
    assert cfg.n_tp == 8
    assert 8 in PTOOLS_SUPPORTED_N_TP


def test_ptools_aggregation_mode_defaults_to_mean() -> None:
    assert ptools_aggregation_mode("ptools_rna") == "mean"
    assert ptools_aggregation_mode("ptools_proteins") == "mean"
    assert ptools_aggregation_mode("ptools_rxns") == "mean"
    assert ptools_aggregation_mode("unknown_module") == "mean"


def _build_canonical_tsv(n_features: int = 3, n_tp: int = PTOOLS_CANONICAL_N_TP) -> str:
    """Synthesise a vEcoli-like TSV with ``n_tp`` time columns named '0', '1', ..., '<n_tp-1>'."""
    columns = ["$", *[str(i) for i in range(n_tp)]]
    rows: list[list[float | str]] = []
    for f in range(n_features):
        row: list[float | str] = [f"feature_{f}"]
        # value = feature_idx * 100 + time_idx so each cell is unique and predictable
        row.extend(float(f * 100 + i) for i in range(n_tp))
        rows.append(row)
    df = pd.DataFrame(rows, columns=columns)
    return df.to_csv(sep="\t", index=False)


def test_reaggregate_mean_matches_block_means() -> None:
    canonical = _build_canonical_tsv(n_features=2, n_tp=PTOOLS_CANONICAL_N_TP)
    coarsened = reaggregate_ptools_columns(canonical, target_n_tp=8, source_n_tp=PTOOLS_CANONICAL_N_TP, mode="mean")
    df = pd.read_csv(io.StringIO(coarsened), sep="\t")
    # 1 index col + 8 time cols
    assert df.shape == (2, 9)
    group_size = PTOOLS_CANONICAL_N_TP // 8  # 15
    # First group of feature_0: mean of values [0, 1, ..., 14] = 7.0
    assert df.iloc[0, 1] == pytest.approx(sum(range(group_size)) / group_size)
    # First group of feature_1: mean of values [100, 101, ..., 114] = 107.0
    assert df.iloc[1, 1] == pytest.approx(100 + sum(range(group_size)) / group_size)
    # Last group of feature_0: mean of values [105, 106, ..., 119]
    last_group_first = PTOOLS_CANONICAL_N_TP - group_size
    expected_last = sum(range(last_group_first, PTOOLS_CANONICAL_N_TP)) / group_size
    assert df.iloc[0, 8] == pytest.approx(expected_last)
    # Output column names = first source-column name of each group
    expected_names = ["$"] + [str(g * group_size) for g in range(8)]
    assert list(df.columns) == expected_names


def test_reaggregate_sum_matches_block_sums() -> None:
    canonical = _build_canonical_tsv(n_features=1, n_tp=PTOOLS_CANONICAL_N_TP)
    coarsened = reaggregate_ptools_columns(canonical, target_n_tp=4, source_n_tp=PTOOLS_CANONICAL_N_TP, mode="sum")
    df = pd.read_csv(io.StringIO(coarsened), sep="\t")
    group_size = PTOOLS_CANONICAL_N_TP // 4  # 30
    # First group sum = sum(0..29) = 30*29/2 = 435
    assert df.iloc[0, 1] == pytest.approx(sum(range(group_size)))
    # Second group sum = sum(30..59)
    assert df.iloc[0, 2] == pytest.approx(sum(range(group_size, 2 * group_size)))


def test_reaggregate_target_equals_source_is_passthrough() -> None:
    canonical = _build_canonical_tsv(n_features=1, n_tp=PTOOLS_CANONICAL_N_TP)
    same = reaggregate_ptools_columns(canonical, target_n_tp=PTOOLS_CANONICAL_N_TP, source_n_tp=PTOOLS_CANONICAL_N_TP)
    assert same == canonical


def test_reaggregate_non_divisor_raises() -> None:
    canonical = _build_canonical_tsv(n_features=1, n_tp=PTOOLS_CANONICAL_N_TP)
    with pytest.raises(ValueError, match="must divide"):
        reaggregate_ptools_columns(canonical, target_n_tp=7, source_n_tp=PTOOLS_CANONICAL_N_TP)


def test_reaggregate_mismatched_column_count_returns_input_unchanged() -> None:
    # TSV claims 8 time columns but caller says source_n_tp=120 → bail out, return input.
    short = _build_canonical_tsv(n_features=1, n_tp=8)
    result = reaggregate_ptools_columns(short, target_n_tp=4, source_n_tp=PTOOLS_CANONICAL_N_TP)
    assert result == short
