"""ComposeSimulationServiceRay unit tests (no AWS): command shape + backend flags."""

from sms_api.common.models import JobBackend
from sms_api.compose import simulation_service_ray as mod
from sms_api.compose.simulation_service_ray import ComposeSimulationServiceRay


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
