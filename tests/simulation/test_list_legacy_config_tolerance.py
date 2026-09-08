"""A legacy stored config must not 500 the whole simulation list.

`ParcaOptions` is intentionally `extra="forbid"` (catch unknown parca_options on
creation), but older rows carry fields the current schema now rejects (e.g.
`parca_options.rnaseq_manifest_path`). The list path deserializes every stored
config, so one bad row used to raise `ValidationError` and 500 the entire
response — hiding every run from every client. `_build_simulations` now degrades
that single record (strips the extra-forbidden keys, re-parses strictly) instead
of failing the list. Creation + the per-id detail path stay strict.
"""
from types import SimpleNamespace

from viva_api.simulation.database_service import DatabaseServiceSQL
from viva_api.simulation.models import ParcaOptions, SimulationConfig


def _orm(sim_id: int, config: dict) -> SimpleNamespace:
    # _build_simulations only reads attributes off the ORM row, so a stub is enough.
    return SimpleNamespace(
        id=sim_id,
        config=config,
        config_filename="default.json",
        experiment_id=config["experiment_id"],
        simulator_id=1,
        parca_dataset_id=1,
        tags=[],
    )


def test_parca_options_still_forbids_extra_on_creation():
    """Guard the intent: ParcaOptions stays strict so creation catches typos."""
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ParcaOptions(outdir="/x", rnaseq_manifest_path="$ECOLI_SOURCES/data/manifest.tsv")


def test_list_tolerates_a_legacy_config_and_still_enumerates_it():
    legacy = _orm(1, {
        "experiment_id": "legacy-run",
        "parca_options": {"outdir": "/x", "rnaseq_manifest_path": "m", "rnaseq_source": "experimental"},
    })
    ok = _orm(2, {"experiment_id": "clean-run", "parca_options": {"outdir": "/y"}})

    # The whole point: this does NOT raise even though row 1 fails strict validation.
    sims = DatabaseServiceSQL._build_simulations([legacy, ok])

    assert [s.experiment_id for s in sims] == ["legacy-run", "clean-run"]
    # The legacy record still lists, with the offending key dropped from the view
    # and a valid, type-correct ParcaOptions (no serialization surprises).
    assert isinstance(sims[0].config, SimulationConfig)
    assert isinstance(sims[0].config.parca_options, ParcaOptions)
    assert "rnaseq_manifest_path" not in sims[0].config.parca_options.model_dump()
    assert sims[0].config.parca_options.outdir == "/x"
    # A clean record is unaffected.
    assert sims[1].config.parca_options.outdir == "/y"
