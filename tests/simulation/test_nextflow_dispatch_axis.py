"""The nextflow_dispatch axis: a third dispatch path chosen per request.

Deliberately NOT a new ComputeBackend. `compute_backend_for_repo` maps repo ->
backend, so a NEXTFLOW member would either reroute every v2ecoli request or be
dead configuration. This is the same axis `multi_node_dispatch` already uses to
pick pbg-native over chain-dispatch: same repo, same image, one config field.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.simulation.test_ray_backend import _ray_settings, _v2ecoli_simulator
from viva_api.simulation.simulation_service_ray import SimulationServiceRay


def _sim(**extras: Any) -> MagicMock:
    sim = MagicMock()
    cfg = MagicMock()
    cfg.experiment_id = "exp-nf"
    cfg.generations = 1
    # getattr(config, name, None) must miss for anything not explicitly given
    for name in ("nextflow_dispatch", "multi_node_dispatch", "composite", "mbp_dispatch"):
        setattr(cfg, name, extras.get(name))
    sim.config = cfg
    sim.simulator_id = 133
    return sim


def _db() -> MagicMock:
    db = MagicMock()
    db.get_simulator = AsyncMock(return_value=_v2ecoli_simulator())
    return db


@pytest.mark.asyncio
async def test_nextflow_dispatch_is_chosen_before_multi_node() -> None:
    """Order is load-bearing. A Nextflow request carries a composite_id too, so a
    later check would claim it first and the run would execute on the WRONG
    mechanism while looking like it worked -- the same misrouting the MNP check
    was placed ahead of chain-dispatch to avoid."""
    service = SimulationServiceRay()
    sim = _sim(
        nextflow_dispatch={"composite_id": "v2ecoli.composites.workflow_nf"},
        multi_node_dispatch={"composite_id": "v2ecoli.composites.lineage_ray_batch"},
    )
    with (
        patch.object(service, "_submit_nextflow_dispatch", new=AsyncMock(return_value="nf")) as nf,
        patch.object(service, "_submit_multi_node_composite", new=AsyncMock(return_value="mnp")) as mnp,
    ):
        await service.submit_ecoli_simulation_job(sim, _db(), correlation_id="c")
    assert nf.await_count == 1
    assert mnp.await_count == 0


@pytest.mark.asyncio
async def test_absent_axis_leaves_every_other_route_untouched() -> None:
    """A request that does not ask for Nextflow must dispatch exactly as before."""
    service = SimulationServiceRay()
    sim = _sim(multi_node_dispatch={"composite_id": "x"})
    with (
        patch.object(service, "_submit_nextflow_dispatch", new=AsyncMock()) as nf,
        patch.object(service, "_submit_multi_node_composite", new=AsyncMock(return_value="mnp")) as mnp,
    ):
        await service.submit_ecoli_simulation_job(sim, _db(), correlation_id="c")
    assert nf.await_count == 0
    assert mnp.await_count == 1


@pytest.mark.asyncio
async def test_missing_composite_id_fails_rather_than_guessing() -> None:
    service = SimulationServiceRay()
    with (
        patch("viva_api.simulation.simulation_service_ray.get_settings", _ray_settings),
        pytest.raises(ValueError, match="composite_id is required"),
    ):
        await service._submit_nextflow_dispatch(_sim(), _db(), {})


# --- the command that actually runs in the container ------------------------


def _command(**dispatch: Any) -> str:
    service = SimulationServiceRay()
    with patch("viva_api.simulation.simulation_service_ray.get_settings", _ray_settings):
        return service._render_nf_command(
            runner_s3_uri="s3://b/exp/render_nf.py",
            composite_id="v2ecoli.composites.workflow_nf",
            params=dispatch.get("params"),
            executor=dispatch.get("executor", "local"),
            launch=dispatch.get("launch", False),
            outdir="/app/v2ecoli/nf-render",
            pbg_runner_s3_uri="s3://b/exp/run_pbg.py",
            nf_params=dispatch.get("nf_params"),
            resources=dispatch.get("resources"),
            work_dir=dispatch.get("work_dir"),
            resume=dispatch.get("resume", False),
            stage_out_s3=dispatch.get("stage_out_s3"),
            session_s3=dispatch.get("session_s3"),
        )


def test_command_stages_the_compiler_rather_than_inlining_it() -> None:
    """Batch caps a container override command at 8192 bytes, which is why the
    script travels through S3 -- the same reason run_pbg is staged."""
    cmd = _command()
    assert "aws s3 cp s3://b/exp/render_nf.py /tmp/render_nf.py" in cmd
    assert "python /tmp/render_nf.py" in cmd


def test_command_defaults_to_render_only_on_the_local_executor() -> None:
    """Phase 3 verifies executor=local INSIDE the real image before Phase 4
    introduces awsbatch, so a failure has one candidate cause, not two."""
    cmd = _command()
    assert "--executor local" in cmd
    assert "--launch" not in cmd
    assert "--resume" not in cmd


def test_command_always_writes_a_trace() -> None:
    """A reused task reports CACHED in the trace CSV and nowhere else, so without
    it there is no way to tell a resumed run from a repeated one (go/no-go 3)."""
    assert "--trace /app/v2ecoli/nf-render/trace.csv" in _command()


def test_launch_resume_and_workdir_reach_the_command() -> None:
    cmd = _command(launch=True, resume=True, work_dir="s3://bucket/work", executor="awsbatch")
    assert "--launch" in cmd and "--resume" in cmd
    assert "--work-dir s3://bucket/work" in cmd
    assert "--executor awsbatch" in cmd


def test_params_are_shell_quoted_json() -> None:
    """Generator params carry arbitrary nested values; an unquoted blob would be
    split by the shell and silently truncate the campaign shape."""
    cmd = _command(params={"n_seeds": 4, "variants": [{"variant_name": "a b"}]})
    assert "--overrides" in cmd
    payload = cmd.split("--overrides ", 1)[1].split(" --")[0]
    assert json.loads(payload.strip("'")) == {"n_seeds": 4, "variants": [{"variant_name": "a b"}]}


def test_head_image_is_the_submit_tag_not_the_task_image() -> None:
    """Only the process running `nextflow run` needs a JVM. The task image has no
    Java, so dispatching Nextflow against it would fail inside the container
    rather than at submit time."""
    service = SimulationServiceRay()
    with patch("viva_api.simulation.simulation_service_ray.get_settings", _ray_settings):
        assert service._submit_image_uri("abc1234").endswith("/v2ecoli:abc1234-submit")


# --- Phase 4: the awsbatch profile's inputs ---------------------------------

# The contract with process-bigraph's `_awsbatch_profile`, spelled out rather
# than imported: process_bigraph is not a declared dependency here, so an
# `importorskip` cross-check would simply skip in CI and prove nothing. A
# mismatch (`containerImage` for `container_image`, say) renders a profile full
# of nulls that Nextflow accepts and that fails minutes later inside Batch.
# Upstream constant: process_bigraph.nextflow_deploy.AWSBATCH_REQUIRED_PARAMS
# (process-bigraph#204).
AWSBATCH_PARAM_NAMES = {
    "container_image",
    "queue",
    "aws_region",
    "s3_endpoint",
    "container_env",
    "work_dir",
}


def _nf_params(**overrides: Any) -> dict[str, Any]:
    service = SimulationServiceRay()
    settings = _ray_settings()
    for key, value in overrides.items():
        setattr(settings, key, value)
    with patch("viva_api.simulation.simulation_service_ray.get_settings", lambda: settings):
        return service._awsbatch_nf_params("abc1234", "exp-nf")


def test_awsbatch_params_are_derived_from_settings_not_from_the_request() -> None:
    """Queue, registry and work bucket name the DEPLOYMENT, so a caller does not
    get to supply them."""
    params = _nf_params()
    assert set(params) == AWSBATCH_PARAM_NAMES
    assert params["queue"] == "smscdk-vecoli-task-amd64"
    assert params["aws_region"] == "us-gov-west-1"
    assert params["s3_endpoint"] == "https://s3.us-gov-west-1.amazonaws.com"
    assert params["work_dir"] == "s3://mybucket/nextflow/work/exp-nf/work"


def test_task_container_is_the_plain_image_not_the_submit_head() -> None:
    """Only the head needs a JVM. Handing tasks the `-submit` tag would work --
    and quietly run every task on a fatter image built for a different job."""
    assert _nf_params()["container_image"].endswith("/v2ecoli:abc1234")
    assert "-submit" not in _nf_params()["container_image"]


def test_pythonpath_is_always_emitted() -> None:
    """`PYTHONPATH` is not optional under Nextflow: the task's cwd is not
    /app/v2ecoli, and v2ecoli bare-imports `scripts.*` throughout. viva-api#359
    fixed this via PBG_RUNNER_ENV, which an emitted process block never sees.

    It rides in `container_env` because it describes THIS image, not AWS Batch."""
    assert _nf_params()["container_env"] == {
        "PYTHONPATH": "/app/v2ecoli",
        # The checkout root, for artefacts that ship in the repo and not the
        # wheel -- v2ecoli resolves scripts/build_cache.py against it.
        "V2E_ROOT": "/app/v2ecoli",
    }


@pytest.mark.parametrize("missing", ["batch_amd64_queue", "s3_work_bucket", "ecr_account_id"])
def test_unconfigured_deployment_raises_at_dispatch_not_inside_batch(missing: str) -> None:
    with pytest.raises(ValueError, match=missing):
        _nf_params(**{missing: ""})


def test_nf_params_reach_the_command_as_quoted_json() -> None:
    cmd = _command(executor="awsbatch", nf_params=_nf_params())
    assert "--nf-params" in cmd
    payload = cmd.split("--nf-params ", 1)[1].split(" --")[0]
    assert json.loads(payload.strip("'")) == _nf_params()
    # Distinct flag from --overrides, which parameterizes the composite generator.
    assert "--overrides" not in cmd


def test_local_executor_carries_no_aws_params() -> None:
    """Phase 3's local check must stay independent of any AWS configuration."""
    assert "--nf-params" not in _command()


# --- the head runs as a K8s Job, and that is a permission fact ---------------


def _svc_with_k8s() -> tuple[Any, MagicMock]:
    k8s = MagicMock()
    return SimulationServiceRay(k8s_job_service=k8s), k8s


async def _dispatch(**dispatch: Any) -> tuple[Any, MagicMock]:
    service, k8s = _svc_with_k8s()
    sim = _sim()
    with (
        patch("viva_api.simulation.simulation_service_ray.get_settings", _ray_settings),
        patch.object(service, "stage_render_nf", new=AsyncMock(return_value="s3://b/e/render_nf.py")),
        patch.object(service, "stage_runner", new=AsyncMock(return_value="s3://b/e/run_pbg.py")),
    ):
        job_id = await service._submit_nextflow_dispatch(
            sim, _db(), {"composite_id": "v2ecoli.composites.workflow_nf", **dispatch}
        )
    return job_id, k8s


@pytest.mark.asyncio
async def test_head_job_uses_the_batch_submit_service_account() -> None:
    """The entire reason the head is a K8s Job rather than a Batch job.

    A Batch-hosted head runs as `ray-mnp-job`, which has S3 and no `batch:*` at
    all, so it would pull, parse its config, start, and only then fail at the
    first task submission. `batch-submit` carries the IRSA identity that may
    submit -- the same one vEcoli's Nextflow head has always used.
    """
    _, k8s = await _dispatch()
    assert k8s.create_job.call_count == 1
    job = k8s.create_job.call_args[0][0]
    assert job.spec.template.spec.service_account_name == "batch-submit"


@pytest.mark.asyncio
async def test_head_job_id_is_neither_ray_nor_plain_k8s() -> None:
    """`ray` would send a Job NAME to describe_jobs. `k8s` would poll fine and
    then serve vEcoli's output layout for a v2ecoli run."""
    from viva_api.common.models import JobBackend

    job_id, _ = await _dispatch()
    assert job_id.backend == JobBackend.K8S_NEXTFLOW
    assert job_id.backend not in (JobBackend.RAY, JobBackend.K8S)


@pytest.mark.asyncio
async def test_head_job_name_is_a_valid_dns_label() -> None:
    """K8s rejects the underscores and uppercase that experiment ids carry, and
    it rejects them at create time -- on a dispatch that otherwise worked."""
    import re as _re

    service, k8s = _svc_with_k8s()
    sim = _sim()
    sim.config.experiment_id = "Test_Experiment_NF_2026"
    with (
        patch("viva_api.simulation.simulation_service_ray.get_settings", _ray_settings),
        patch.object(service, "stage_render_nf", new=AsyncMock(return_value="s3://b/e/r.py")),
        patch.object(service, "stage_runner", new=AsyncMock(return_value="s3://b/e/run_pbg.py")),
    ):
        job_id = await service._submit_nextflow_dispatch(sim, _db(), {"composite_id": "v2ecoli.composites.workflow_nf"})
    assert _re.fullmatch(r"[a-z0-9]([-a-z0-9]*[a-z0-9])?", job_id.value), job_id.value
    assert len(job_id.value) <= 63
    assert k8s.create_job.call_args[0][0].metadata.name == job_id.value


@pytest.mark.asyncio
async def test_head_job_is_not_retried_by_kubernetes() -> None:
    """A half-finished Nextflow run is not safely restartable from scratch --
    a retried head would resubmit every task. Recovery is `-resume` on a new
    dispatch, which reuses the cached successful ones."""
    _, k8s = await _dispatch()
    assert k8s.create_job.call_args[0][0].spec.backoff_limit == 0


@pytest.mark.asyncio
async def test_dispatch_without_a_cluster_fails_loudly() -> None:
    service = SimulationServiceRay()  # no K8sJobService
    with (
        patch("viva_api.simulation.simulation_service_ray.get_settings", _ray_settings),
        pytest.raises(RuntimeError, match="k8s_job_namespace"),
    ):
        await service._submit_nextflow_dispatch(_sim(), _db(), {"composite_id": "v2ecoli.composites.workflow_nf"})


@pytest.mark.asyncio
async def test_status_of_a_k8s_head_does_not_go_to_describe_jobs() -> None:
    """The value is a Job NAME. describe_jobs would return an empty list, and
    this would report None -- a running campaign that looks like a lost one."""
    from viva_api.common.models import JobId

    service, k8s = _svc_with_k8s()
    with patch.object(service, "_batch") as batch:
        await service.get_job_status(JobId.k8s_nextflow("nf-exp-abc"))
    assert batch.call_count == 0
    k8s.get_job_status.assert_called_once_with("nf-exp-abc")


def test_command_preserves_the_exit_code_before_staging_out() -> None:
    """On the Batch path an entrypoint synced out_dir -> S3. A pod has none, so
    the command stages its own -- and a trailing copy that succeeded would
    otherwise report a failed render as a success."""
    cmd = _command(nf_params=_nf_params(), stage_out_s3="s3://bucket/out/")
    assert "NF_EXIT=$?" in cmd
    assert cmd.strip().endswith("exit $NF_EXIT")
    assert cmd.index("NF_EXIT=$?") < cmd.index("aws s3 cp --recursive")


def test_default_command_stages_nothing() -> None:
    assert "NF_EXIT" not in _command()


def test_command_stages_run_pbg_beside_render_nf() -> None:
    """render_nf imports run_pbg's resolver, and the simulator image has no
    `viva_api`. Fetching only render_nf fails at import -- after a successful
    5.8 GB pull and a clean start."""
    cmd = _command()
    assert "aws s3 cp s3://b/exp/render_nf.py /tmp/render_nf.py" in cmd
    staged_runner = "/tmp/run_pbg.py"  # noqa: S108  (a path in a container, not a local temp file)
    assert f"aws s3 cp s3://b/exp/run_pbg.py {staged_runner}" in cmd
    # Same directory: the fallback import resolves from render_nf's own dir.
    assert cmd.index(staged_runner) < cmd.index("python /tmp/render_nf.py")


@pytest.mark.asyncio
async def test_head_job_carries_the_workspace_core_builder_and_import_root() -> None:
    """The head RESOLVES the composite, so it needs what PBG_RUNNER_ENV carries.

    The generic core registers only process-bigraph's base types. A document with
    a nested Composite then fails to realize with
    `no link found at address: {'protocol': 'local', 'data': 'composite'}` --
    which is every sub-workflow this dispatch path exists to emit.

    #359 put these in PBG_RUNNER_ENV for the chain/Ray paths. A K8s Job never
    sees that string; §Phase 0 of the plan predicted this for PYTHONPATH, and it
    generalises to PBG_CORE_BUILDER.
    """
    _, k8s = await _dispatch()
    env = {e.name: e.value for e in k8s.create_job.call_args[0][0].spec.template.spec.containers[0].env}
    assert env["PBG_CORE_BUILDER"] == "v2ecoli.core:build_core"
    assert env["PYTHONPATH"] == "/app/v2ecoli"
    assert env["AWS_DEFAULT_REGION"] == "us-gov-west-1"


# --- resources are not optional in practice --------------------------------


def test_a_dispatch_with_no_resources_still_gets_them() -> None:
    """Measured on simulation 355: no `resources` means no `withLabel` block,
    so nf-amazon's auto-registered job definition took ITS defaults (~1 GB, no
    timeout) and ParCa was killed with exit 137 before doing anything."""
    from viva_api.simulation.simulation_service_ray import _merge_nf_resources

    res = _merge_nf_resources(None)
    assert set(res) == {"parca", "lineage", "analysis"}
    for label, spec in res.items():
        assert "memory" in spec, label
        assert "time" in spec, label  # the only bound on a runaway task


def test_memory_scales_on_137_and_only_on_137() -> None:
    """Retrying an OOM at the same size is three identical failures -- which is
    exactly what happened. Scaling on EVERY failure would instead multiply
    memory for faults that have nothing to do with it."""
    from viva_api.simulation.simulation_service_ray import _merge_nf_resources

    mem = _merge_nf_resources(None)["parca"]["memory"]
    assert mem.lstrip().startswith("{"), "must be a Groovy closure, not a quoted string"
    assert "task.exitStatus == 137" in mem
    assert "task.attempt" in mem


def test_overriding_one_key_does_not_drop_the_others() -> None:
    """Replacing wholesale would let `{'lineage': {'time': ...}}` silently take
    the run back to nf-amazon's ~1 GB."""
    from viva_api.simulation.simulation_service_ray import _merge_nf_resources

    merged = _merge_nf_resources({"lineage": {"time": "24 h"}})
    assert merged["lineage"]["time"] == "24 h"
    assert "137" in merged["lineage"]["memory"]
    assert merged["lineage"]["cpus"] == 4
    assert "137" in merged["parca"]["memory"]


def test_an_unknown_label_is_additive() -> None:
    from viva_api.simulation.simulation_service_ray import _merge_nf_resources

    merged = _merge_nf_resources({"custom": {"cpus": 2}})
    assert merged["custom"] == {"cpus": 2}
    assert "parca" in merged


@pytest.mark.asyncio
async def test_resources_reach_the_rendered_command() -> None:
    """The defaults are useless if the dispatcher does not pass them."""
    service, k8s = _svc_with_k8s()
    with (
        patch("viva_api.simulation.simulation_service_ray.get_settings", _ray_settings),
        patch.object(service, "stage_render_nf", new=AsyncMock(return_value="s3://b/e/r.py")),
        patch.object(service, "stage_runner", new=AsyncMock(return_value="s3://b/e/run_pbg.py")),
    ):
        await service._submit_nextflow_dispatch(
            _sim(), _db(), {"composite_id": "v2ecoli.composites.workflow_nf.workflow_nf", "executor": "awsbatch"}
        )
    cmd = k8s.create_job.call_args[0][0].spec.template.spec.containers[0].command[2]
    assert "--resources" in cmd
    payload = cmd.split("--resources ", 1)[1].split(" --")[0]
    assert "task.exitStatus == 137" in payload


# --- the session cache is what makes -resume mean anything ------------------


def test_the_session_is_restored_before_the_run_and_saved_after() -> None:
    """`-resume` needs a durable SESSION, not just a durable work dir.

    Nextflow keeps .nextflow/history and its cache DB in the LAUNCH directory --
    an ephemeral pod here -- so without this a second dispatch reports, verbatim:

        WARN: It appears you have never run this project before
              -- Option `-resume` is ignored

    and re-runs a ParCa whose output is sitting complete in the work dir.
    Measured on simulation 359.
    """
    cmd = _command(stage_out_s3="s3://b/out/", session_s3="s3://b/sess/")
    assert "aws s3 cp --recursive s3://b/sess/" in cmd  # restored
    assert "/.nextflow s3://b/sess/" in cmd  # and saved
    assert cmd.index("s3://b/sess/") < cmd.index("render_nf.py")  # before the run


def test_the_session_is_saved_even_when_the_run_fails() -> None:
    """A FAILED run's session is exactly the one a `-resume` needs, so guarding
    the save on success would defeat the purpose."""
    cmd = _command(stage_out_s3="s3://b/out/", session_s3="s3://b/sess/")
    assert cmd.index("NF_EXIT=$?") < cmd.index("/.nextflow s3://b/sess/")
    assert cmd.strip().endswith("exit $NF_EXIT")


def test_session_and_work_dir_are_keyed_the_same() -> None:
    """They are only useful together: -resume matches a task by hash in the
    SESSION, then reuses outputs in the WORK DIR. Either alone resumes nothing."""
    service = SimulationServiceRay()
    with patch("viva_api.simulation.simulation_service_ray.get_settings", _ray_settings):
        session = service._nf_session_s3_uri("exp-nf")
        work = service._awsbatch_nf_params("abc1234", "exp-nf")["work_dir"]
    assert session.rsplit("/", 1)[0] == work.rsplit("/", 1)[0]
