"""Tests for AWS Batch backend, JobStatusService abstraction, and get_job_backend()."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sms_api.common.hpc.batch_service import AwsBatchService
from sms_api.common.hpc.job_service import JobStatusInfo
from sms_api.common.hpc.slurm_service import _slurm_job_to_status_info
from sms_api.common.models import JobBackend, JobStatus
from sms_api.simulation.simulation_service_batch import SimulationServiceBatch


class TestJobBackend:
    def test_job_backend_values(self) -> None:
        assert JobBackend.SLURM.value == "slurm"
        assert JobBackend.BATCH.value == "batch"


class TestJobStatusFromBatchState:
    @pytest.mark.parametrize(
        "batch_state,expected",
        [
            ("SUBMITTED", JobStatus.PENDING),
            ("PENDING", JobStatus.PENDING),
            ("RUNNABLE", JobStatus.QUEUED),
            ("STARTING", JobStatus.RUNNING),
            ("RUNNING", JobStatus.RUNNING),
            ("SUCCEEDED", JobStatus.COMPLETED),
            ("FAILED", JobStatus.FAILED),
            ("UNKNOWN_STATE", JobStatus.UNKNOWN),
        ],
    )
    def test_from_batch_state(self, batch_state: str, expected: JobStatus) -> None:
        assert JobStatus.from_batch_state(batch_state) == expected


class TestGetJobBackend:
    def test_slurm_for_rke(self) -> None:
        from sms_api.config import get_job_backend

        with patch("sms_api.config.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(deployment_namespace="sms-api-rke")
            assert get_job_backend() == "slurm"

    def test_slurm_for_rke_dev(self) -> None:
        from sms_api.config import get_job_backend

        with patch("sms_api.config.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(deployment_namespace="sms-api-rke-dev")
            assert get_job_backend() == "slurm"

    def test_batch_for_stanford(self) -> None:
        from sms_api.config import get_job_backend

        with patch("sms_api.config.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(deployment_namespace="sms-api-stanford")
            assert get_job_backend() == "batch"

    def test_batch_for_stanford_test(self) -> None:
        from sms_api.config import get_job_backend

        with patch("sms_api.config.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(deployment_namespace="sms-api-stanford-test")
            assert get_job_backend() == "batch"

    def test_slurm_for_empty_namespace(self) -> None:
        from sms_api.config import get_job_backend

        with patch("sms_api.config.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(deployment_namespace="")
            assert get_job_backend() == "slurm"


class TestSlurmJobToStatusInfo:
    def test_running_job(self) -> None:
        from sms_api.common.hpc.models import SlurmJob

        slurm_job = SlurmJob(
            job_id=12345,
            name="sim-abc1234-1",
            account="acct",
            user_name="user",
            job_state="RUNNING",
            start_time="2024-01-15T10:30:00",
        )
        info = _slurm_job_to_status_info(slurm_job)
        assert info.job_id == "12345"
        assert info.status == JobStatus.RUNNING
        assert info.start_time == "2024-01-15T10:30:00"
        assert info.error_message is None

    def test_failed_job(self) -> None:
        from sms_api.common.hpc.models import SlurmJob

        slurm_job = SlurmJob(
            job_id=12345,
            name="sim-abc1234-1",
            account="acct",
            user_name="user",
            job_state="FAILED",
            exit_code="1:0",
            reason="NonZeroExitCode",
        )
        info = _slurm_job_to_status_info(slurm_job)
        assert info.status == JobStatus.FAILED
        assert "SLURM state: FAILED" in info.error_message  # type: ignore[operator]
        assert "reason: NonZeroExitCode" in info.error_message  # type: ignore[operator]


@pytest.mark.asyncio
class TestAwsBatchService:
    async def test_submit_job(self) -> None:
        service = AwsBatchService(region="us-east-1")
        mock_client = AsyncMock()
        mock_client.submit_job.return_value = {"jobId": "test-uuid-123"}
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch.object(service._session, "client", return_value=mock_client):
            job_id = await service.submit_job(
                job_name="test-job",
                job_definition="test-def",
                job_queue="test-queue",
            )
        assert job_id == "test-uuid-123"

    async def test_get_job_statuses(self) -> None:
        service = AwsBatchService(region="us-east-1")
        mock_client = AsyncMock()
        mock_client.describe_jobs.return_value = {
            "jobs": [
                {
                    "jobId": "uuid-1",
                    "status": "RUNNING",
                    "startedAt": 1700000000,
                    "container": {},
                },
                {
                    "jobId": "uuid-2",
                    "status": "FAILED",
                    "startedAt": 1700000000,
                    "stoppedAt": 1700001000,
                    "statusReason": "OutOfMemory",
                    "container": {"exitCode": 137, "reason": "OOMKilled"},
                },
            ]
        }
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch.object(service._session, "client", return_value=mock_client):
            statuses = await service.get_job_statuses(["uuid-1", "uuid-2"])

        assert len(statuses) == 2
        assert statuses[0].job_id == "uuid-1"
        assert statuses[0].status == JobStatus.RUNNING
        assert statuses[1].job_id == "uuid-2"
        assert statuses[1].status == JobStatus.FAILED
        assert statuses[1].error_message == "OOMKilled"
        assert statuses[1].exit_code == "137"

    async def test_get_job_statuses_empty(self) -> None:
        service = AwsBatchService(region="us-east-1")
        result = await service.get_job_statuses([])
        assert result == []


@pytest.mark.asyncio
class TestSimulationServiceBatch:
    async def test_implements_all_abstract_methods(self) -> None:
        """Verify SimulationServiceBatch can be instantiated (all abstract methods implemented)."""
        batch_service = AwsBatchService(region="us-east-1")
        service = SimulationServiceBatch(batch_service=batch_service)
        assert service is not None

    async def test_get_job_status_delegates_to_batch(self) -> None:
        batch_service = AwsBatchService(region="us-east-1")
        service = SimulationServiceBatch(batch_service=batch_service)
        expected = JobStatusInfo(job_id="uuid-1", status=JobStatus.RUNNING)
        with patch.object(batch_service, "get_job_statuses", return_value=[expected]):
            result = await service.get_job_status("uuid-1")
        assert result == expected

    async def test_get_job_status_returns_none_when_not_found(self) -> None:
        batch_service = AwsBatchService(region="us-east-1")
        service = SimulationServiceBatch(batch_service=batch_service)
        with patch.object(batch_service, "get_job_statuses", return_value=[]):
            result = await service.get_job_status("nonexistent")
        assert result is None
