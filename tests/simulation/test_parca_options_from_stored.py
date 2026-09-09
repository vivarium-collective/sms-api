"""GET /simulation/parca/versions must not 500 because one stored row carries keys
this build's ParcaOptions forbids (smsvpctest 2026-09-09: rnaseq_* keys from a branch build)."""

from __future__ import annotations

import logging

import pytest
from pydantic import ValidationError

from viva_api.simulation.database_service import parca_options_from_stored
from viva_api.simulation.models import ParcaOptions


def test_stored_row_with_foreign_keys_parses_with_them_dropped(caplog: pytest.LogCaptureFixture) -> None:
    row = {
        "new_genes": "on",
        "rnaseq_manifest_path": "x.tsv",
        "rnaseq_basal_dataset_id": 7,
        "rnaseq_fill_missing_genes_from_ref": True,
    }
    with caplog.at_level(logging.WARNING, logger="viva_api.simulation.database_service"):
        opts = parca_options_from_stored(row)
    assert opts.new_genes == "on"
    assert not hasattr(opts, "rnaseq_manifest_path")
    assert "rnaseq_basal_dataset_id" in caplog.text and "rnaseq_manifest_path" in caplog.text


def test_clean_row_is_parsed_strictly_and_silently(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="viva_api.simulation.database_service"):
        assert parca_options_from_stored({"new_genes": "off"}).new_genes == "off"
    assert "ignoring" not in caplog.text


def test_a_real_validation_error_still_raises() -> None:
    with pytest.raises(ValidationError):
        parca_options_from_stored({"cpus": "not-an-int"})


def test_new_requests_still_forbid_extras() -> None:
    with pytest.raises(ValidationError):
        ParcaOptions(rnaseq_manifest_path="x.tsv")  # type: ignore[call-arg]
