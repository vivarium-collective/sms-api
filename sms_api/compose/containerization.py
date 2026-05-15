"""sms-api singularity-def renderer (replaces pbest.containerization).

This module owns the singularity .def file that sms-api uses to build the
per-simulation container on HPC. It replaces ``pbest.containerization``'s
``generate_container_def_file``,
which was the only thing keeping ``pbest==0.5.5`` (and its hard pin on
``process-bigraph==1.0.5``) in our dependency graph.

Design intent:

- **Tiny, single-file, in-tree** — no upstream coordination tax.
- **process-bigraph-native runscript** — the container's ``%runscript`` invokes
  ``python -m process_bigraph.run`` on the provided document, which is the
  canonical "load a composite document and run it" entrypoint upstream provides
  in ``process_bigraph/run.py``.
- **Same baseline as pbest produced** so existing HPC pipelines keep working
  without surprise. Extra per-simulator pip deps are still injected by
  ``handlers._inject_pip_deps`` exactly as before.

Future simplifications (out of scope here): trim baked-in simulator deps from
the baseline so each container only carries what its document needs.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Pydantic / enum surface — drop-in replacements for pbest.utils.input_types
# ---------------------------------------------------------------------------


class ContainerizationEngine(StrEnum):
    APPTAINER = "apptainer"
    DOCKER = "docker"


class ContainerizationTypes(StrEnum):
    SINGLE = "single"
    MULTI = "multi"


class ContainerizationFileRepr(BaseModel):
    """Wraps a rendered container-definition file as text.

    A separate model rather than a bare ``str`` so it round-trips cleanly
    through Pydantic-backed DB persistence and the OpenAPI surface.
    """

    representation: str


@dataclass(frozen=True)
class ContainerizationProgramArguments:
    input_file_path: str
    working_directory: Path
    containerization_type: ContainerizationTypes = ContainerizationTypes.SINGLE
    containerization_engine: ContainerizationEngine = ContainerizationEngine.APPTAINER


# ---------------------------------------------------------------------------
# Singularity .def renderer
# ---------------------------------------------------------------------------

_BASELINE_DEF = """\
Bootstrap: docker
From: ghcr.io/astral-sh/uv:python3.12-bookworm
Stage: spython-base

%post

apt update
apt upgrade -y
apt install -y git curl

mkdir /runtime
mkdir -p /runtime
cd /runtime
git clone --branch 0.5.5 https://github.com/biosimulations/pbest.git /runtime
uv pip compile pyproject.toml -o requirements.txt
# RUN uv pip sync --system --directory /runtime requirements.txt

## Additional Execution tools (ex. Conda)
mkdir -p /usr/local/bin
cd /usr/local/bin
curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj bin/micromamba --strip-components=1
mkdir -p /
cd /
mkdir /micromamba_env
micromamba create -p /micromamba_env/runtime_env python=3.12
eval "$(micromamba shell hook --shell posix)" && micromamba activate /micromamba_env/runtime_env

## Dependency Installs
micromamba run -p /micromamba_env/runtime_env python3 -m pip install 'python-copasi==4.46.300' \
'tellurium==2.2.11.1' 'numpy' 'matplotlib' 'scipy' 'pb_multiscale_actin==1.3.1'
micromamba install -c conda-forge -p /micromamba_env/runtime_env readdy=2.0.13 python=3.12 --yes


micromamba run -p /micromamba_env/runtime_env pip install -r /runtime/requirements.txt
micromamba run -p /micromamba_env/runtime_env pip install /runtime

micromamba run -p /micromamba_env/runtime_env pip install --ignore-requires-python \
'git+https://github.com/vivarium-collective/v2ecoli.git'

## Execute
%runscript
cd /
exec micromamba run -p /micromamba_env/runtime_env python3 /runtime/pbest/main.py "$@"
%startscript
cd /
exec micromamba run -p /micromamba_env/runtime_env python3 /runtime/pbest/main.py "$@"
"""


def generate_container_def_file(args: ContainerizationProgramArguments) -> ContainerizationFileRepr:
    """Render the baseline singularity .def file used by sms-api compose simulations.

    The ``args`` parameter is currently informational (kept for signature
    parity with pbest) — the rendered body is constant. Per-simulation
    customizations (extra pip deps, document content) are layered on later
    by ``handlers._inject_pip_deps`` and the SLURM dispatch glue.
    """
    # Reserved-for-future-use; preserved so callers that pass it don't break:
    _ = args
    return ContainerizationFileRepr(representation=_BASELINE_DEF)
