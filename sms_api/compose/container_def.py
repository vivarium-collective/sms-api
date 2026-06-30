"""Containerization DTOs and the generic process-bigraph singularity def builder.

This module inlines the small ``ContainerizationFileRepr`` / ``ContainerizationEngine``
DTOs (previously imported from ``pbest``) and owns ``build_pbg_def`` — a
deterministic Singularity/apptainer definition that installs process-bigraph and
embeds the generic ``run_pbg.py`` runner. This removes sms-api's dependency on
``pbest`` for the generic compose path.
"""

from enum import Enum

from pydantic import BaseModel


class ContainerizationEngine(Enum):
    """The container engine a definition targets."""

    NONE = 0
    DOCKER = 1
    APPTAINER = 2
    BOTH = 3


class ContainerizationFileRepr(BaseModel):
    """A textual container-definition file (e.g. a Singularity/apptainer def)."""

    representation: str
    containerization_engine: ContainerizationEngine = ContainerizationEngine.APPTAINER
