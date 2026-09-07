"""Shared Batch analysis-DAG-node submitter.

The post-simulation analysis step -- run the ported cd1_*/ptools_* analyses over a
finished sweep -- is one Batch DAG node (``dependsOn`` the job(s) it reads output
from). This module holds the parts of that node that are backend-agnostic: the
``v2ecoli-analyze`` config-JSON + argv builder, and the submit-then-record
orchestration. Today only the study Batch/Ray path (``SimulationServiceRay``)
calls it; a compose backend follows in a later task, reusing the SAME node
unmodified rather than re-deriving its own argv.

REAL CLI SURFACE (confirmed against v2ecoli@main, console-script target
``v2ecoli.workflow.analysis_runner:main``): EXACTLY one positional ``sweep_dir``
and one ``--config <path>`` flag. Nothing else -- no ``--out-uri``/``--n-seeds``/
``--n-generations``/``--modules``/``--analysis-name``, no ``--experiment-id``/
``--out-dir``. Those flags never existed on this CLI; a job emitting any of them
gets ``argparse`` exit code 2. The old (stale) flags this module replaces don't
disappear -- they fold into the ``--config`` JSON instead:

  * ``--out-uri``                    -> ``config["out_dir"]`` (the analysis's own
    write location -- callers pass the already-resolved ``.../analyses/<name>``
    path, since the new CLI has no ``--analysis-name`` to derive it from itself).
  * ``--modules`` / ``--analysis-name`` -> ``config["analysis_options"]`` (which
    analyses to run; ``--analysis-name`` no longer needs a CLI flag once
    ``out_dir`` is pre-resolved by the caller).
  * ``--n-seeds`` / ``--n-generations`` -> DROPPED. v2ecoli infers both from the
    sweep's own hive partitions; nothing replaces them in the config.

``sim_data`` is threaded through BOTH the (already-proven, see
``analysis_runner.resolve_sim_data``'s ``$V2ECOLI_SIM_DATA`` fallback)
environment variable AND ``config["sim_data_path"]``, always derived from the
CALLER-GIVEN cache/commit reference -- never a hardcoded or default per-commit
path (viva-api#448: a stock cache silently standing in for a real one is exactly
the failure class that bit Dispatch 339/340).

The config JSON's shape (a top-level ``analysis_options`` key) mirrors what the
SLURM ``--config`` caller already writes (``AnalysisServiceSlurm`` /
``viva_api/analysis/analysis_service.py``'s ``generate_slurm_script``, which
``echo``'s a JSON blob to a temp file and passes ``--config "$tmp_config"`` to
``runscripts/analysis.py``) -- the one other place in this repo that already
speaks a working ``--config`` contract.
"""

from __future__ import annotations

import json
import logging
import shlex
from typing import TYPE_CHECKING, Any, Protocol

from viva_api.simulation.tables_orm import AnalysisStatusDB

if TYPE_CHECKING:
    from viva_api.simulation.database_service import DatabaseService

logger = logging.getLogger(__name__)


class SubmitContainerFn(Protocol):
    """Shape of ``SimulationServiceRay._submit_container`` (the subset this
    module actually calls) -- lets any Batch-capable service inject its own
    submission mechanics without this module depending on boto3/settings."""

    def __call__(
        self,
        *,
        job_name: str,
        job_definition: str,
        job_cmd: str,
        out_s3: str,
        out_dir: str,
        depends_on: list[str] | None = None,
        depends_type: str | None = "SEQUENTIAL",
        tags: dict[str, str] | None = None,
    ) -> str: ...


def build_analysis_config(
    *,
    analysis_options: dict[str, Any] | str,
    out_dir: str,
    sim_data_path: str,
) -> dict[str, Any]:
    """Build the ``v2ecoli-analyze --config`` JSON payload.

    ``analysis_options`` rides through unchanged -- either a ``{scale: {name:
    params}}`` mapping or the ``"applicable"`` keyword, exactly as the old
    ``--modules`` flag accepted. ``out_dir`` is the analysis's own pre-resolved
    write location (see module docstring). ``sim_data_path`` must always be the
    caller's real cache pointer, never a default.
    """
    return {
        "analysis_options": analysis_options,
        "out_dir": out_dir,
        "sim_data_path": sim_data_path,
    }


def analysis_dag_command(
    *,
    v2ecoli_dir: str,
    sweep_dir: str,
    sim_data_uri: str,
    config: dict[str, Any],
) -> str:
    """Build the analysis DAG node's shell command: ``v2ecoli-analyze <sweep_dir>
    --config <config.json>``, the whole real CLI surface (see module docstring).

    The config JSON is written to a temp file first -- the same pattern
    ``AnalysisServiceSlurm.generate_slurm_script`` already uses for its own
    working ``--config`` caller (``tmp_config=$(mktemp); echo '...' >
    "$tmp_config"; ... --config "$tmp_config"``). ``V2ECOLI_SIM_DATA`` is set via
    its own ``export`` statement (not a ``KEY=value cmd`` prefix) so the final
    ``&&``-segment is a clean, directly ``shlex.split()``-able argv -- exactly
    what a contract test parsing against the real argparse parser needs.
    """
    config_json = json.dumps(config)
    return (
        f"cd {v2ecoli_dir}"
        f" && tmp_config=$(mktemp)"
        f' && echo {shlex.quote(config_json)} > "$tmp_config"'
        f" && export V2ECOLI_SIM_DATA={shlex.quote(sim_data_uri)}"
        f' && v2ecoli-analyze {shlex.quote(sweep_dir)} --config "$tmp_config"'
    )


async def submit_analysis_dag_node(
    *,
    sweep_dir: str,
    analysis_options: dict[str, Any] | str,
    sim_data_uri: str,
    result_out_dir: str,
    v2ecoli_dir: str,
    submit_container: SubmitContainerFn,
    job_definition: str,
    job_name: str,
    out_s3: str,
    container_out_dir: str,
    depends_on_job_id: str | None,
    depends_type: str | None,
    tags: dict[str, str],
    database_service: DatabaseService,
    experiment_id: str,
    analysis_name: str,
    simulation_id: int | None,
    backend: str,
    db_config: dict[str, Any],
    result_uri: str | None,
) -> str | None:
    """Build the analysis config + command, submit the Batch job, and record it.

    Best-effort by design, but never SILENT: whatever this depends on is already
    submitted (and possibly running) by the time this is reached, so raising
    would orphan real, expensive jobs. A submission failure is logged AND
    written to the ``analyses`` table as a FAILED row -- "the analysis never
    ran" is a visible state, not an absence. Mirrors
    ``SimulationServiceRay._submit_analysis_job``'s existing contract exactly
    (that method is now a thin wrapper around this function).

    ``db_config`` is opaque to this module -- callers own the DB record's exact
    shape (this module only decides the ARGV/config-JSON the container sees, not
    what a caller chooses to persist about the submission).
    """
    config = build_analysis_config(
        analysis_options=analysis_options,
        out_dir=result_out_dir,
        sim_data_path=sim_data_uri,
    )
    cmd = analysis_dag_command(
        v2ecoli_dir=v2ecoli_dir,
        sweep_dir=sweep_dir,
        sim_data_uri=sim_data_uri,
        config=config,
    )
    try:
        job_id = submit_container(
            job_name=job_name,
            job_definition=job_definition,
            job_cmd=cmd,
            out_s3=out_s3,
            out_dir=container_out_dir,
            depends_on=[depends_on_job_id] if depends_on_job_id else None,
            depends_type=depends_type,
            tags=tags,
        )
    except Exception as e:
        logger.exception("Analysis DAG node submission failed for %s", experiment_id)
        await database_service.record_analysis(
            experiment_id=experiment_id,
            n_tp=None,
            status=AnalysisStatusDB.FAILED,
            config=db_config,
            name=analysis_name,
            simulation_id=simulation_id,
            backend=backend,
            result_uri=result_uri,
            error_message=f"analysis job submission failed: {type(e).__name__}: {e}",
        )
        return None
    await database_service.record_analysis(
        experiment_id=experiment_id,
        n_tp=None,
        status=AnalysisStatusDB.COMPUTING,
        config=db_config,
        name=analysis_name,
        simulation_id=simulation_id,
        backend=backend,
        job_id_ext=str(job_id),
        result_uri=result_uri,
    )
    return job_id
