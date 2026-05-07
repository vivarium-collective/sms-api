"""Unit tests for compose ORM tables and enum mappers."""

import pytest

from sms_api.compose.models import (
    BiGraphComputeType,
    ComposeJobStatus,
    ComposeJobType,
    PackageType,
)
from sms_api.compose.tables_orm import (
    BiGraphComputeTypeDB,
    ComposeJobStatusDB,
    ComposeJobTypeDB,
    PackageTypeDB,
)


class TestEnumMappers:
    def test_job_status_roundtrip(self) -> None:
        for status in ComposeJobStatus:
            db_status = ComposeJobStatusDB(status.value)
            assert db_status.to_job_status() == status

    def test_job_type_roundtrip(self) -> None:
        for jt in ComposeJobType:
            db_jt = ComposeJobTypeDB.from_job_type(jt)
            assert db_jt.to_job_type() == jt

    def test_package_type_roundtrip(self) -> None:
        for pt in PackageType:
            db_pt = PackageTypeDB.from_package_type(pt)
            assert db_pt.to_package_type() == pt

    def test_compute_type_roundtrip(self) -> None:
        for ct in BiGraphComputeType:
            db_ct = BiGraphComputeTypeDB.from_compute_type(ct)
            assert db_ct.to_compute_type() == ct

    def test_compute_type_none_raises(self) -> None:
        with pytest.raises(ValueError, match="No compute type specified"):
            BiGraphComputeTypeDB.from_compute_type(None)


class TestComposeTableNames:
    """Verify all compose tables use the compose_ prefix to avoid collisions."""

    def test_table_prefixes(self) -> None:
        from sms_api.compose.tables_orm import (
            ORMComposeAllowList,
            ORMComposeBiGraphCompute,
            ORMComposeHpcRun,
            ORMComposePackage,
            ORMComposeSimulation,
            ORMComposeSimulator,
            ORMComposeSimulatorToPackage,
            ORMComposeWorkerEvent,
        )

        tables = [
            ORMComposeSimulator,
            ORMComposeSimulatorToPackage,
            ORMComposeSimulation,
            ORMComposeHpcRun,
            ORMComposeWorkerEvent,
            ORMComposePackage,
            ORMComposeBiGraphCompute,
            ORMComposeAllowList,
        ]
        for table in tables:
            assert table.__tablename__.startswith("compose_"), (
                f"{table.__name__} table '{table.__tablename__}' does not have compose_ prefix"
            )
