import pytest

from sms_api.data.analysis_service import AnalysisService


@pytest.mark.asyncio
def test_get_file_paths() -> None:
    svc = AnalysisService()
    expid = "sms_single"
    paths = svc.get_file_paths(experiment_id=expid)
    print(paths)
    assert len(paths)


@pytest.mark.asyncio
def test_get_file_path() -> None:
    svc = AnalysisService()
    expid = "sms_single"
    filename = "ptools_rna.txt"
    fp = svc.get_file_path(expid, filename)
    print(fp)
    assert fp.exists()
