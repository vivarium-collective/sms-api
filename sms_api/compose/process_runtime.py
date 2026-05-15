"""
Stateful process-bigraph runtime — mirrors the paradigm from rest-process.

Manages a per-pod in-memory registry of instantiated process/step instances,
keyed by UUID. Instances are lost on pod restart; callers should treat process
IDs as ephemeral within a session.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from bigraph_schema import Edge
from process_bigraph import Process, Step, allocate_core

from sms_api.compose.models import BiGraphComputeType, BiGraphProcess, BiGraphStep

# ---------------------------------------------------------------------------
# Core singleton (lazy-initialised once on first use)
# ---------------------------------------------------------------------------

_core: Any = None


def get_core() -> Any:
    global _core
    if _core is None:
        _core = allocate_core()
    return _core


# ---------------------------------------------------------------------------
# In-memory instance store
# ---------------------------------------------------------------------------

_instances: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Public API — mirrors rest-process server.py
# ---------------------------------------------------------------------------


def list_types() -> list[str]:
    """Return all registered type names from the bigraph-schema type registry."""
    return list(get_core().registry.keys())


def list_processes() -> list[str]:
    """Return all registered process/step names from the link registry."""
    return list(get_core().link_registry.keys())


def get_config_schema(process_name: str) -> dict[str, Any]:
    """Return the config_schema for a named process class, or {} if not found."""
    core = get_core()
    process_class = core.link_registry.get(process_name, Edge)
    if process_class is None:
        return {}
    schema = getattr(process_class, "config_schema", {})
    return schema


def initialize_process(process_name: str, config: dict[str, Any]) -> str:
    """Instantiate a process with the given config; return a UUID instance ID."""
    core = get_core()
    process_class = core.link_registry.get(process_name)
    if process_class is None:
        raise KeyError(f"Process '{process_name}' not found in registry")
    process_id = str(uuid.uuid4())
    instance = process_class(config, core=core)
    _instances[process_id] = instance
    return process_id


def get_inputs(process_id: str) -> dict[str, Any]:
    """Return the inputs schema for an active process instance."""
    instance = _require_instance(process_id)
    return instance.inputs()  # type: ignore[no-any-return]


def get_outputs(process_id: str) -> dict[str, Any]:
    """Return the outputs schema for an active process instance."""
    instance = _require_instance(process_id)
    return instance.outputs()  # type: ignore[no-any-return]


def update_process(process_id: str, state: dict[str, Any], interval: float) -> Any:
    """Run one update step on an active process instance."""
    instance = _require_instance(process_id)
    return instance.update(state, interval)


def end_process(process_id: str) -> None:
    """Terminate an active process instance and release its memory."""
    if process_id not in _instances:
        raise KeyError(f"Process instance '{process_id}' not found")
    del _instances[process_id]


# ---------------------------------------------------------------------------
# Introspection helper — core.link_registry → typed pydantic objects
# ---------------------------------------------------------------------------


def introspect_core() -> tuple[list[BiGraphProcess], list[BiGraphStep]]:
    """Query the live core.link_registry and split entries into Process vs Step.

    Returns (processes, steps) as typed pydantic objects with module path,
    class name, compute type, and config_schema serialised to JSON.
    """
    core = get_core()
    processes: list[BiGraphProcess] = []
    steps: list[BiGraphStep] = []

    for name, cls in core.link_registry.items():
        if not isinstance(cls, type):
            continue
        module = getattr(cls, "__module__", "") or ""
        config_schema = getattr(cls, "config_schema", {})
        schema_json = json.dumps(config_schema) if isinstance(config_schema, dict) else "{}"

        if issubclass(cls, Process):
            processes.append(
                BiGraphProcess(
                    database_id=0,
                    module=module,
                    name=name,
                    compute_type=BiGraphComputeType.PROCESS,
                    inputs=schema_json,
                    outputs=schema_json,
                )
            )
        elif issubclass(cls, Step):
            steps.append(
                BiGraphStep(
                    database_id=0,
                    module=module,
                    name=name,
                    compute_type=BiGraphComputeType.STEP,
                    inputs=schema_json,
                    outputs=schema_json,
                )
            )

    return processes, steps


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _require_instance(process_id: str) -> Any:
    instance = _instances.get(process_id)
    if instance is None:
        raise KeyError(f"Process instance '{process_id}' not found")
    return instance
