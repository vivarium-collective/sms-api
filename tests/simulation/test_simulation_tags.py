from sms_api.simulation.simulation_tags import SIMULATION_TAGS, resolve_tag


def test_resolve_known_tag() -> None:
    experiment_ids = resolve_tag("cd1")
    assert isinstance(experiment_ids, list)
    assert len(experiment_ids) == 3
    assert "sim31-baseline-60bb" in experiment_ids
    assert "sim33-violacien-seeds1000-generations10-9617" in experiment_ids
    assert "sim33-mecillinam-seeds84-generations10-036f" in experiment_ids


def test_resolve_unknown_tag_raises() -> None:
    try:
        resolve_tag("nonexistent")
    except ValueError as e:
        assert "nonexistent" in str(e)
        assert "cd1" in str(e)
    else:
        raise AssertionError("Expected ValueError for unknown tag")


def test_tags_dict_structure() -> None:
    assert isinstance(SIMULATION_TAGS, dict)
    for tag_name, experiment_ids in SIMULATION_TAGS.items():
        assert isinstance(tag_name, str)
        assert isinstance(experiment_ids, list)
        assert len(experiment_ids) > 0
        for eid in experiment_ids:
            assert isinstance(eid, str)
            assert eid  # non-empty
