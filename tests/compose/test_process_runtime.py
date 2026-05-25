"""Tests for the rest-process runtime endpoints and process_runtime module."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# process_runtime unit tests
# ---------------------------------------------------------------------------


class TestProcessRuntime:
    """Unit tests for sms_api.compose.process_runtime (no HTTP)."""

    def test_list_types_returns_list(self) -> None:
        from sms_api.compose.process_runtime import list_types

        types = list_types()
        assert isinstance(types, list)
        assert len(types) > 0
        assert all(isinstance(t, str) for t in types)

    def test_list_processes_returns_list(self) -> None:
        from sms_api.compose.process_runtime import list_processes

        processes = list_processes()
        assert isinstance(processes, list)
        assert len(processes) > 0

    def test_get_config_schema_known_process(self) -> None:
        from sms_api.compose.process_runtime import get_config_schema, list_processes

        procs = list_processes()
        # Pick the first real process (not 'edge')
        name = next(p for p in procs if p != "edge")
        schema = get_config_schema(name)
        assert isinstance(schema, dict)

    def test_get_config_schema_unknown_returns_empty(self) -> None:
        from sms_api.compose.process_runtime import get_config_schema

        schema = get_config_schema("nonexistent_process_xyz")
        assert schema == {}

    def test_initialize_and_end_process(self) -> None:
        from sms_api.compose.process_runtime import _instances, end_process, initialize_process, list_processes

        # Use a known step class that doesn't require heavy config
        procs = list_processes()
        # CopasiUTCStep or any real step
        step_name = next((p for p in procs if "Step" in p and "." not in p), None)
        if step_name is None:
            pytest.skip("No simple Step found in registry")

        process_id = initialize_process(step_name, {})
        assert process_id in _instances

        end_process(process_id)
        assert process_id not in _instances

    def test_end_unknown_process_raises(self) -> None:
        from sms_api.compose.process_runtime import end_process

        with pytest.raises(KeyError):
            end_process("does-not-exist-uuid")

    def test_get_inputs_unknown_raises(self) -> None:
        from sms_api.compose.process_runtime import get_inputs

        with pytest.raises(KeyError):
            get_inputs("does-not-exist-uuid")

    def test_get_outputs_unknown_raises(self) -> None:
        from sms_api.compose.process_runtime import get_outputs

        with pytest.raises(KeyError):
            get_outputs("does-not-exist-uuid")

    def test_core_singleton(self) -> None:
        from sms_api.compose.process_runtime import get_core

        core1 = get_core()
        core2 = get_core()
        assert core1 is core2


# ---------------------------------------------------------------------------
# REST endpoint tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def compose_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """TestClient with compose router mounted, compose services mocked."""
    from unittest.mock import AsyncMock, MagicMock

    monkeypatch.setenv("COMPUTE_BACKEND", "slurm")
    monkeypatch.setenv("PUBLIC_MODE", "true")

    from fastapi import FastAPI

    from sms_api.api.routers import compose as compose_module

    # Inject a mock DB so that mutating process runtime handlers don't 500.
    registry_db = MagicMock()
    registry_db.insert_process_instance = AsyncMock(return_value=None)
    registry_db.end_process_instance = AsyncMock(return_value=None)
    registry_db.insert_process_update = AsyncMock(return_value=None)
    mock_db = MagicMock()
    mock_db.get_process_registry_db.return_value = registry_db
    monkeypatch.setattr(compose_module, "_compose_db_service", mock_db)

    app = FastAPI()
    app.include_router(compose_module.router, prefix="/compose/v1")
    return TestClient(app)


class TestProcessRuntimeRoutes:
    """HTTP-level tests for the rest-process runtime endpoints."""

    def test_list_types(self, compose_client: TestClient) -> None:
        resp = compose_client.get("/compose/v1/types")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_config_schema_known(self, compose_client: TestClient) -> None:
        from sms_api.compose.process_runtime import list_processes

        procs = list_processes()
        name = next(p for p in procs if p != "edge")
        resp = compose_client.get(f"/compose/v1/process/{name}/config-schema")
        assert resp.status_code == 200
        assert isinstance(resp.json(), dict)

    def test_config_schema_unknown_returns_empty(self, compose_client: TestClient) -> None:
        resp = compose_client.get("/compose/v1/process/nonexistent_xyz/config-schema")
        assert resp.status_code == 200
        assert resp.json() == {}

    def test_initialize_unknown_process_returns_404(self, compose_client: TestClient) -> None:
        resp = compose_client.post(
            "/compose/v1/process/nonexistent_xyz/initialize",
            json={"config": {}},
        )
        assert resp.status_code == 404

    def test_initialize_and_end_roundtrip(self, compose_client: TestClient) -> None:
        from sms_api.compose.process_runtime import list_processes

        procs = list_processes()
        step_name = next((p for p in procs if "Step" in p and "." not in p), None)
        if step_name is None:
            pytest.skip("No simple Step in registry")

        # initialize
        resp = compose_client.post(
            f"/compose/v1/process/{step_name}/initialize",
            json={"config": {}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "process_id" in data
        process_id = data["process_id"]

        # inputs
        resp = compose_client.get(f"/compose/v1/process/{step_name}/inputs/{process_id}")
        assert resp.status_code == 200

        # outputs
        resp = compose_client.get(f"/compose/v1/process/{step_name}/outputs/{process_id}")
        assert resp.status_code == 200

        # end
        resp = compose_client.post(f"/compose/v1/process/{step_name}/end/{process_id}")
        assert resp.status_code == 200

    def test_inputs_unknown_instance_returns_404(self, compose_client: TestClient) -> None:
        resp = compose_client.get("/compose/v1/process/Step/inputs/does-not-exist")
        assert resp.status_code == 404

    def test_outputs_unknown_instance_returns_404(self, compose_client: TestClient) -> None:
        resp = compose_client.get("/compose/v1/process/Step/outputs/does-not-exist")
        assert resp.status_code == 404

    def test_end_unknown_instance_returns_404(self, compose_client: TestClient) -> None:
        resp = compose_client.post("/compose/v1/process/Step/end/does-not-exist")
        assert resp.status_code == 404

    def test_update_unknown_instance_returns_404(self, compose_client: TestClient) -> None:
        resp = compose_client.post(
            "/compose/v1/process/Step/update/does-not-exist",
            json={"state": {}, "interval": 1.0},
        )
        assert resp.status_code == 404
