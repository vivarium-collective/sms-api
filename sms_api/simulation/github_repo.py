"""Shared GitHub-API helpers for simulator repo introspection (no SSH).

Used by both the K8s/Batch (`SimulationServiceK8s`) and Ray
(`SimulationServiceRay`) backends to read the latest commit, fetch config
templates, and discover configs/analysis modules without an SSH login node.
"""

import json
import logging

import httpx
from fastapi import HTTPException

from sms_api.simulation.models import RepoDiscovery, SimulatorVersion

logger = logging.getLogger(__name__)

# Embedded config template used when the target vEcoli repo does not ship
# an api_simulation_default.json (e.g. the public CovertLab/vEcoli repo).
# Mirrors vEcoli-private/configs/api_simulation_default.json with the same
# placeholders that the handler's replacement logic expects.
_DEFAULT_CONFIG_TEMPLATE: dict[str, object] = {
    "experiment_id": "EXPERIMENT_ID_PLACEHOLDER",
    "parca_options": {
        "cpus": 6,
        "outdir": "HPC_SIM_BASE_PATH_PLACEHOLDER",
        "operons": True,
        "ribosome_fitting": True,
        "remove_rrna_operons": False,
        "remove_rrff": False,
        "stable_rrna": False,
        "new_genes": "off",
        "debug_parca": False,
        "save_intermediates": False,
        "intermediates_directory": "",
        "variable_elongation_transcription": True,
        "variable_elongation_translation": False,
    },
    "sim_data_path": None,
    "suffix_time": False,
    "generations": 8,
    "n_init_sims": 3,
    "max_duration": 10800.0,
    "initial_global_time": 0.0,
    "time_step": 1.0,
    "single_daughters": True,
    "emitter": "parquet",
    "emitter_arg": {"out_dir": "HPC_SIM_BASE_PATH_PLACEHOLDER"},
    "analysis_options": {"multiseed": {}},
    "aws_cdk": {
        "build_image": False,
        "container_image": "SIMULATOR_IMAGE_PATH_PLACEHOLDER",
    },
}

_ANALYSIS_CATEGORIES = ["single", "multiseed", "multigeneration", "multidaughter", "multivariant"]


def _github_api_url(repo_url: str) -> str:
    """Convert a GitHub HTTPS URL to the API equivalent.

    https://github.com/org/repo -> https://api.github.com/repos/org/repo
    """
    api_url = repo_url.replace("https://github.com/", "https://api.github.com/repos/")
    if api_url.endswith(".git"):
        api_url = api_url[:-4]
    return api_url


def _github_headers(token: str | None = None) -> dict[str, str]:
    headers: dict[str, str] = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


async def fetch_latest_commit_hash(git_repo_url: str, git_branch: str, token: str | None) -> str:
    """Return the first 7 chars of the latest commit hash via the GitHub API."""
    api_url = f"{_github_api_url(git_repo_url)}/commits/{git_branch}"
    headers = _github_headers(token)
    async with httpx.AsyncClient() as client:
        response = await client.get(api_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return str(data["sha"])[:7]


async def fetch_config_template(
    simulator_version: SimulatorVersion,
    config_filename: str,
    token: str | None,
    allow_default_fallback: bool = False,
) -> str:
    """Read a vEcoli config template from the GitHub repo via the Contents API.

    Raises HTTPException(404) if the config file does not exist in the repo at
    the requested commit. Set ``allow_default_fallback=True`` to silently
    substitute the embedded ``_DEFAULT_CONFIG_TEMPLATE`` instead.
    """
    if config_filename.startswith("configs/"):
        raise HTTPException(
            status_code=400,
            detail=(
                f"config_filename {config_filename!r} starts with 'configs/' — "
                "drop the prefix. The path is resolved relative to the repo's "
                "configs/ directory, so e.g. pass 'campaigns/pilot_mixed.json' "
                "instead of 'configs/campaigns/pilot_mixed.json'."
            ),
        )

    base = _github_api_url(simulator_version.git_repo_url)
    api_url = f"{base}/contents/configs/{config_filename}?ref={simulator_version.git_commit_hash}"
    headers: dict[str, str] = {"Accept": "application/vnd.github.v3.raw"}
    if token:
        headers["Authorization"] = f"token {token}"
    async with httpx.AsyncClient() as client:
        response = await client.get(api_url, headers=headers)
        if response.status_code == 404:
            if allow_default_fallback:
                logger.warning(
                    "Config %s not found in %s@%s — using embedded default template (allow_default_fallback=True)",
                    config_filename,
                    simulator_version.git_repo_url,
                    simulator_version.git_commit_hash,
                )
                return json.dumps(_DEFAULT_CONFIG_TEMPLATE)
            logger.error(
                "Config %s not found in %s@%s (URL=%s)",
                config_filename,
                simulator_version.git_repo_url,
                simulator_version.git_commit_hash,
                api_url,
            )
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Config file {config_filename!r} not found in "
                    f"{simulator_version.git_repo_url} at commit "
                    f"{simulator_version.git_commit_hash}. "
                    f"Use GET /api/v1/simulations/discovery?simulator_id=... "
                    f"to list available configs."
                ),
            )
        response.raise_for_status()
        return response.text


async def fetch_repo_discovery(simulator_version: SimulatorVersion, token: str | None) -> RepoDiscovery:
    """Discover available configs and analysis modules via the GitHub Contents API."""
    base = _github_api_url(simulator_version.git_repo_url)
    headers = _github_headers(token)
    ref = simulator_version.git_commit_hash

    async with httpx.AsyncClient() as client:
        # List config files
        config_filenames: list[str] = []
        resp = await client.get(f"{base}/contents/configs?ref={ref}", headers=headers)
        if resp.status_code == 200:
            for item in resp.json():
                name = item.get("name", "")
                if name.endswith(".json"):
                    config_filenames.append(name)

        # List analysis modules per category
        analysis_modules: dict[str, list[str]] = {}
        for category in _ANALYSIS_CATEGORIES:
            resp = await client.get(f"{base}/contents/ecoli/analysis/{category}?ref={ref}", headers=headers)
            if resp.status_code == 200:
                modules = [
                    item["name"].removesuffix(".py")
                    for item in resp.json()
                    if item.get("name", "").endswith(".py") and not item["name"].startswith("__")
                ]
                if modules:
                    analysis_modules[category] = sorted(modules)

    return RepoDiscovery(
        simulator_id=simulator_version.database_id,
        git_repo_url=simulator_version.git_repo_url,
        git_commit_hash=simulator_version.git_commit_hash,
        config_filenames=sorted(config_filenames),
        analysis_modules=analysis_modules,
    )
