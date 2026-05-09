"""Tests verifying that mutating process runtime routes mirror state to the DB."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from sms_api.compose.models import ProcessInstanceRecord, ProcessInstanceStatus, ProcessUpdateRecord

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_instance_record(process_id: str = "test-uuid", process_name: str = "TestStep") -> ProcessInstanceRecord:
    return ProcessInstanceRecord(
        database_id=1,
        process_id=process_id,
        process_name=process_name,
        config={},
        status=ProcessInstanceStatus.ACTIVE,
        created_at="2025-01-01T00:00:00",
    )


def _make_update_record(process_instance_id: int = 1) -> ProcessUpdateRecord:
    return ProcessUpdateRecord(
        database_id=1,
        process_instance_id=process_instance_id,
        interval=1.0,
        state={},
        result={"output": 1.0},
        called_at="2025-01-01T00:00:01",
    )


def _make_mock_db(
    insert_instance_return: ProcessInstanceRecord | None = None,
    end_instance_return: ProcessInstanceRecord | None = None,
    insert_update_return: ProcessUpdateRecord | None = None,
    list_instances_return: list[ProcessInstanceRecord] | None = None,
    list_updates_return: list[ProcessUpdateRecord] | None = None,
) -> MagicMock:
    registry_db = MagicMock()
    registry_db.insert_process_instance = AsyncMock(return_value=insert_instance_return or _make_instance_record())
    registry_db.end_process_instance = AsyncMock(return_value=end_instance_return or _make_instance_record())
    registry_db.insert_process_update = AsyncMock(return_value=insert_update_return or _make_update_record())
    registry_db.list_process_instances = AsyncMock(return_value=list_instances_return or [])
    registry_db.list_process_updates = AsyncMock(return_value=list_updates_return or [])

    db = MagicMock()
    db.get_process_registry_db.return_value = registry_db
    return db


@pytest.fixture()
def compose_client_with_db(monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, MagicMock]:
    """TestClient with compose router + injected mock DB."""
    monkeypatch.setenv("COMPUTE_BACKEND", "slurm")
    monkeypatch.setenv("PUBLIC_MODE", "true")

    from sms_api.api.routers import compose as compose_module

    mock_db = _make_mock_db()
    monkeypatch.setattr(compose_module, "_compose_db_service", mock_db)

    app = FastAPI()
    app.include_router(compose_module.router, prefix="/compose/v1")
    return TestClient(app), mock_db


# ---------------------------------------------------------------------------
# DB mirror tests
# ---------------------------------------------------------------------------


STEP_NAME = "TestStep"


class TestInitializeMirrorsToDb:
    def test_initialize_mirrors_to_db(
        self, compose_client_with_db: tuple[TestClient, MagicMock], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        client, mock_db = compose_client_with_db
        process_id = "injected-uuid"

        monkeypatch.setattr(
            "sms_api.compose.process_runtime.initialize_process",
            lambda name, config: process_id,
        )

        resp = client.post(f"/compose/v1/process/{STEP_NAME}/initialize", json={"config": {"key": "val"}})
        assert resp.status_code == 200
        data = resp.json()
        assert data["process_id"] == process_id

        registry_db = mock_db.get_process_registry_db()
        registry_db.insert_process_instance.assert_awaited_once_with(process_id, STEP_NAME, {"key": "val"})

    def test_initialize_unknown_no_db_write(
        self, compose_client_with_db: tuple[TestClient, MagicMock], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        client, mock_db = compose_client_with_db

        def _raise(name: str, config: Any) -> str:
            raise KeyError(f"Process '{name}' not found in registry")

        monkeypatch.setattr("sms_api.compose.process_runtime.initialize_process", _raise)

        resp = client.post("/compose/v1/process/unknown_xyz/initialize", json={"config": {}})
        assert resp.status_code == 404

        registry_db = mock_db.get_process_registry_db()
        registry_db.insert_process_instance.assert_not_awaited()


class TestEndMirrorsToDb:
    def test_end_mirrors_to_db(
        self, compose_client_with_db: tuple[TestClient, MagicMock], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        client, mock_db = compose_client_with_db
        process_id = "end-uuid"

        monkeypatch.setattr("sms_api.compose.process_runtime.end_process", lambda pid: None)

        resp = client.post(f"/compose/v1/process/{STEP_NAME}/end/{process_id}")
        assert resp.status_code == 200

        registry_db = mock_db.get_process_registry_db()
        registry_db.end_process_instance.assert_awaited_once_with(process_id)

    def test_end_not_found_no_db_write(
        self, compose_client_with_db: tuple[TestClient, MagicMock], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        client, mock_db = compose_client_with_db

        def _raise(pid: str) -> None:
            raise KeyError(f"Process instance '{pid}' not found")

        monkeypatch.setattr("sms_api.compose.process_runtime.end_process", _raise)

        resp = client.post(f"/compose/v1/process/{STEP_NAME}/end/does-not-exist")
        assert resp.status_code == 404

        registry_db = mock_db.get_process_registry_db()
        registry_db.end_process_instance.assert_not_awaited()


class TestUpdateLogsToDb:
    def test_update_logs_to_db(
        self, compose_client_with_db: tuple[TestClient, MagicMock], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        client, mock_db = compose_client_with_db
        process_id = "update-uuid"
        expected_result = {"output": 99.0}

        monkeypatch.setattr(
            "sms_api.compose.process_runtime.update_process",
            lambda pid, state, interval: expected_result,
        )

        resp = client.post(
            f"/compose/v1/process/{STEP_NAME}/update/{process_id}",
            json={"state": {"x": 1}, "interval": 0.5},
        )
        assert resp.status_code == 200

        registry_db = mock_db.get_process_registry_db()
        registry_db.insert_process_update.assert_awaited_once_with(process_id, {"x": 1}, 0.5, expected_result)


class TestReadOnlyRegistryEndpoints:
    def test_list_instances_empty(self, compose_client_with_db: tuple[TestClient, MagicMock]) -> None:
        client, _ = compose_client_with_db
        resp = client.get("/compose/v1/process/instances")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_instances_with_status_filter(self, compose_client_with_db: tuple[TestClient, MagicMock]) -> None:
        client, mock_db = compose_client_with_db
        mock_db.get_process_registry_db().list_process_instances = AsyncMock(
            return_value=[_make_instance_record("pid-1"), _make_instance_record("pid-2")]
        )

        resp = client.get("/compose/v1/process/instances?status=active")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_get_instance_history_empty(self, compose_client_with_db: tuple[TestClient, MagicMock]) -> None:
        client, _ = compose_client_with_db
        resp = client.get("/compose/v1/process/instances/some-uuid/history")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_instance_history_not_found(self, compose_client_with_db: tuple[TestClient, MagicMock]) -> None:
        client, mock_db = compose_client_with_db
        mock_db.get_process_registry_db().list_process_updates = AsyncMock(
            side_effect=LookupError("Process instance 'bad-uuid' not found")
        )

        resp = client.get("/compose/v1/process/instances/bad-uuid/history")
        assert resp.status_code == 404
