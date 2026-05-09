"""
Stateful process-bigraph runtime — mirrors the paradigm from rest-process.

Manages a per-pod in-memory registry of instantiated process/step instances,
keyed by UUID. Instances are lost on pod restart; callers should treat process
IDs as ephemeral within a session.
"""

from __future__ import annotations

import uuid
from typing import Any

from bigraph_schema import Edge
from process_bigraph import allocate_core

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
# Internal helpers
# ---------------------------------------------------------------------------


def _require_instance(process_id: str) -> Any:
    instance = _instances.get(process_id)
    if instance is None:
        raise KeyError(f"Process instance '{process_id}' not found")
    return instance
