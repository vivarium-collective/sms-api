"""Tests for K8s backend: K8sJobService, SimulationServiceK8s, config backend selection."""

from unittest.mock import MagicMock, patch

import pytest

from sms_api.common.hpc.k8s_job_service import K8sJobService, _job_to_status
from sms_api.common.models import JobBackend, JobId, JobStatus


class TestJobToStatus:
    """Test K8s Job condition → JobStatus mapping."""

    def test_completed_job(self) -> None:
        job = MagicMock()
        job.status.conditions = [MagicMock(type="Complete", status="True")]
        job.status.active = 0
        job.status.ready = 0
        assert _job_to_status(job) == JobStatus.COMPLETED

    def test_failed_job(self) -> None:
        job = MagicMock()
        job.status.conditions = [MagicMock(type="Failed", status="True")]
        job.status.active = 0
        assert _job_to_status(job) == JobStatus.FAILED

    def test_running_job(self) -> None:
        job = MagicMock()
        job.status.conditions = None
        job.status.active = 1
        job.status.ready = 0
        assert _job_to_status(job) == JobStatus.RUNNING

    def test_pending_job(self) -> None:
        job = MagicMock()
        job.status.conditions = None
        job.status.active = 0
        job.status.ready = 0
        assert _job_to_status(job) == JobStatus.PENDING

    def test_no_status(self) -> None:
        job = MagicMock()
        job.status = None
        assert _job_to_status(job) == JobStatus.UNKNOWN

    def test_condition_not_true(self) -> None:
        job = MagicMock()
        job.status.conditions = [MagicMock(type="Complete", status="False")]
        job.status.active = 1
        job.status.ready = 0
        assert _job_to_status(job) == JobStatus.RUNNING


class TestGetJobBackend:
    def test_slurm_for_rke(self) -> None:
        from sms_api.config import get_job_backend

        with patch("sms_api.config.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(deployment_namespace="sms-api-rke")
            assert get_job_backend() == "slurm"

    def test_k8s_for_stanford(self) -> None:
        from sms_api.config import get_job_backend

        with patch("sms_api.config.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(deployment_namespace="sms-api-stanford")
            assert get_job_backend() == "k8s"

    def test_k8s_for_stanford_test(self) -> None:
        from sms_api.config import get_job_backend

        with patch("sms_api.config.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(deployment_namespace="sms-api-stanford-test")
            assert get_job_backend() == "k8s"

    def test_slurm_for_empty_namespace(self) -> None:
        from sms_api.config import get_job_backend

        with patch("sms_api.config.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(deployment_namespace="")
            assert get_job_backend() == "slurm"


class TestK8sJobService:
    def test_get_job_status_not_found(self) -> None:
        from kubernetes.client.rest import ApiException

        service = MagicMock(spec=K8sJobService)
        service._namespace = "test-ns"

        # Simulate the real behavior: 404 returns None
        mock_batch_api = MagicMock()
        mock_batch_api.read_namespaced_job_status.side_effect = ApiException(status=404)

        with patch.object(K8sJobService, "__init__", lambda self, namespace: None):
            svc = K8sJobService.__new__(K8sJobService)
            svc._namespace = "test-ns"
            svc._batch_api = mock_batch_api
            svc._core_api = MagicMock()

            result = svc.get_job_status("nonexistent-job")
            assert result is None

    def test_get_job_status_running(self) -> None:
        mock_job = MagicMock()
        mock_job.status.conditions = None
        mock_job.status.active = 1
        mock_job.status.ready = 0
        mock_job.status.start_time = None
        mock_job.status.completion_time = None

        mock_batch_api = MagicMock()
        mock_batch_api.read_namespaced_job_status.return_value = mock_job

        with patch.object(K8sJobService, "__init__", lambda self, namespace: None):
            svc = K8sJobService.__new__(K8sJobService)
            svc._namespace = "test-ns"
            svc._batch_api = mock_batch_api
            svc._core_api = MagicMock()

            result = svc.get_job_status("my-job")
            assert result is not None
            assert result.status == JobStatus.RUNNING
            assert result.job_id == "my-job"


class TestJobId:
    def test_slurm_factory(self) -> None:
        job_id = JobId.slurm(12345)
        assert job_id.value == "12345"
        assert job_id.backend == JobBackend.SLURM
        assert job_id.as_slurm_int == 12345
        assert str(job_id) == "12345"

    def test_k8s_factory(self) -> None:
        job_id = JobId.k8s("nf-sim-abc")
        assert job_id.value == "nf-sim-abc"
        assert job_id.backend == JobBackend.K8S
        assert str(job_id) == "nf-sim-abc"

    def test_slurm_int_raises_for_k8s(self) -> None:
        job_id = JobId.k8s("nf-sim-abc")
        with pytest.raises(TypeError, match="Not a SLURM job ID"):
            _ = job_id.as_slurm_int

    def test_equality(self) -> None:
        assert JobId.slurm(123) == JobId.slurm(123)
        assert JobId.slurm(123) != JobId.slurm(456)
        assert JobId.slurm(123) != JobId.k8s("123")
        assert JobId.k8s("abc") == JobId.k8s("abc")

    def test_frozen(self) -> None:
        job_id = JobId.slurm(123)
        with pytest.raises(AttributeError):
            job_id.value = "456"  # type: ignore[misc]
