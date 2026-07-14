"""Unit tests for the pure classification logic in db_reconcile.

These cover the state machine without touching a database. End-to-end
stamp/upgrade behavior is exercised against a real Postgres by the migration
Job in deployment; here we lock down the decision logic that drives it.

The fingerprint vectors below are length-4, matching LEGACY_FINGERPRINTS:
    [baseline, hpcrun-k8s, cancelled-enum, simulation.tags]
"""

from sms_api.simulation.db_reconcile import DbState, classify

HEAD = "c1a2b3d4e5f6"
# Mirrors LEGACY_FINGERPRINTS ordering.
REVS = ["fb7621a73e24", "0f991fad32ba", "a1c3e5f7b9d2", "c1a2b3d4e5f6"]


def test_managed_database_takes_upgrade_path() -> None:
    diag = classify(alembic_revision="0f991fad32ba", fingerprint=[True, True, False, False], head_revision=HEAD)
    assert diag.state is DbState.MANAGED
    assert diag.current_revision == "0f991fad32ba"
    assert diag.matched_revision is None
    assert diag.needs_stamp is False
    assert diag.can_upgrade is True


def test_managed_takes_precedence_even_with_odd_fingerprint() -> None:
    # If alembic_version exists, we trust it regardless of fingerprint probes.
    diag = classify(alembic_revision=HEAD, fingerprint=[False, False, False, False], head_revision=HEAD)
    assert diag.state is DbState.MANAGED


def test_fresh_database_when_no_tables_and_no_version() -> None:
    diag = classify(alembic_revision=None, fingerprint=[False, False, False, False], head_revision=HEAD)
    assert diag.state is DbState.FRESH
    assert diag.matched_revision is None
    assert diag.needs_stamp is False
    assert diag.can_upgrade is True


def test_legacy_matches_baseline_only() -> None:
    diag = classify(alembic_revision=None, fingerprint=[True, False, False, False], head_revision=HEAD)
    assert diag.state is DbState.LEGACY
    assert diag.matched_revision == "fb7621a73e24"
    assert diag.needs_stamp is True


def test_legacy_matches_middle_revision() -> None:
    # The pre-0.9.19 stanford-test state: baseline + hpcrun-k8s, but enum missing 'cancelled'.
    diag = classify(alembic_revision=None, fingerprint=[True, True, False, False], head_revision=HEAD)
    assert diag.state is DbState.LEGACY
    assert diag.matched_revision == "0f991fad32ba"
    assert diag.needs_stamp is True


def test_legacy_matches_cancelled_revision() -> None:
    # A create_all DB with the enum fixed but no tags column yet (no alembic_version).
    diag = classify(alembic_revision=None, fingerprint=[True, True, True, False], head_revision=HEAD)
    assert diag.state is DbState.LEGACY
    assert diag.matched_revision == "a1c3e5f7b9d2"


def test_legacy_matches_head_when_all_markers_present() -> None:
    diag = classify(alembic_revision=None, fingerprint=[True, True, True, True], head_revision=HEAD)
    assert diag.state is DbState.LEGACY
    assert diag.matched_revision == "c1a2b3d4e5f6"


def test_inconsistent_when_later_marker_present_but_earlier_missing() -> None:
    # A gap (True after False) means the schema matches no single revision.
    diag = classify(alembic_revision=None, fingerprint=[True, False, True, False], head_revision=HEAD)
    assert diag.state is DbState.INCONSISTENT
    assert diag.matched_revision is None
    assert diag.can_upgrade is False


def test_inconsistent_when_baseline_missing_but_later_present() -> None:
    # baseline table absent while later markers (also created by baseline) are
    # present is impossible for a clean create_all DB => a gap => inconsistent.
    diag = classify(alembic_revision=None, fingerprint=[False, True, True, True], head_revision=HEAD)
    assert diag.state is DbState.INCONSISTENT
    assert diag.can_upgrade is False


def test_markers_are_reported_with_labels() -> None:
    diag = classify(alembic_revision=None, fingerprint=[True, True, False, False], head_revision=HEAD)
    labels = [label for label, _ in diag.markers]
    presence = [present for _, present in diag.markers]
    assert presence == [True, True, False, False]
    assert any("simulation" in label for label in labels)
    assert any("tags" in label for label in labels)
