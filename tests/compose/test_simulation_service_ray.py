"""ComposeSimulationServiceRay unit tests (no AWS): command shape + backend flags."""

import types

import pytest

from sms_api.common.models import JobBackend
from sms_api.compose import simulation_service_ray as mod
from sms_api.compose.simulation_service_ray import ComposeSimulationServiceRay


def _settings(**overrides: object) -> types.SimpleNamespace:
    base: dict[str, object] = {
        "compose_ray_image_tag": "abc123",
        "compose_parca_cache_dir": "",
        "compose_pbg_core_builder": "",
        "ecr_account_id": "111122223333",
        "batch_region": "us-gov-west-1",
        "ray_ecr_repository": "v2ecoli",
    }
    base.update(overrides)
    return types.SimpleNamespace(**base)


def test_backend_flags() -> None:
    svc = ComposeSimulationServiceRay()
    assert svc.backend == JobBackend.RAY
    assert svc.requires_container_build is False


def test_compose_command_embeds_runner_and_stages_doc() -> None:
    svc = ComposeSimulationServiceRay()
    cmd = svc._compose_command("s3://bucket/exp/input.pbg", steps=7)
    # downloads the doc, embeds the runner via heredoc, runs it with -n steps
    assert "aws s3 cp s3://bucket/exp/input.pbg" in cmd
    assert "PBG_RUNNER_EOF" in cmd
    assert "-n 7" in cmd
    assert mod.COMPOSE_OUT_DIR in cmd


# --- B1: an unset image tag must fail at SUBMIT, not as an opaque Batch pull error ---


def test_image_uri_raises_when_tag_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    """The ECR repo is populated per-commit and has no "latest", so an unset tag can
    only ever resolve to a nonexistent image. Fail here, naming the setting."""
    monkeypatch.setattr(mod, "get_settings", lambda: _settings(compose_ray_image_tag=""))
    with pytest.raises(RuntimeError, match="compose_ray_image_tag"):
        ComposeSimulationServiceRay()._image_uri()


def test_image_uri_builds_the_commit_pinned_uri(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mod, "get_settings", lambda: _settings(compose_ray_image_tag="a08e20bd"))
    uri = ComposeSimulationServiceRay()._image_uri()
    assert uri == "111122223333.dkr.ecr.us-gov-west-1.amazonaws.com/v2ecoli:a08e20bd"


# --- B2: the driver swap must not drop the ensemble path's ParCa cache staging ---


def test_parca_staging_disabled_when_no_cache_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    """Generic default: a composite that needs no prebuilt cache stages nothing."""
    monkeypatch.setattr(mod, "get_settings", lambda: _settings(compose_parca_cache_dir=""))
    assert ComposeSimulationServiceRay()._parca_staging() == (None, None)


def test_parca_staging_is_keyed_by_the_image_tag_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression: the compose path called _submit_mnp WITHOUT stage_s3/stage_dir, so
    a composite whose cache_dir expects a populated ParCa bundle (v2ecoli baseline)
    started against an empty directory. The cache is commit-addressed and the image
    tag IS the commit."""
    monkeypatch.setattr(
        mod,
        "get_settings",
        lambda: _settings(compose_ray_image_tag="a08e20bd", compose_parca_cache_dir="/app/v2ecoli/out/cache"),
    )
    stage_s3, stage_dir = ComposeSimulationServiceRay()._parca_staging()
    assert stage_dir == "/app/v2ecoli/out/cache"
    assert stage_s3 is not None
    assert stage_s3.endswith("ray-parca-cache/a08e20bd/")


# --- B3: name the workspace's own core builder so its registered TYPES resolve ---


def _exec_suffix(cmd: str) -> str:
    """The command AFTER the embedded runner source.

    The heredoc inlines all of run_pbg.py, whose own source mentions
    ``PBG_CORE_BUILDER`` (it reads that env var and logs it), so a substring check
    over the whole command can never be negative. Only the tail is the real
    invocation.
    """
    return cmd.rsplit("PBG_RUNNER_EOF", 1)[-1]


def test_compose_command_passes_core_builder_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mod, "get_settings", lambda: _settings(compose_pbg_core_builder="v2ecoli.core:build_core"))
    cmd = ComposeSimulationServiceRay()._compose_command("s3://b/i.pbg", steps=3)
    assert "PBG_CORE_BUILDER=v2ecoli.core:build_core" in _exec_suffix(cmd)


def test_compose_command_omits_core_builder_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mod, "get_settings", lambda: _settings(compose_pbg_core_builder=""))
    cmd = ComposeSimulationServiceRay()._compose_command("s3://b/i.pbg", steps=3)
    assert "PBG_CORE_BUILDER" not in _exec_suffix(cmd)
