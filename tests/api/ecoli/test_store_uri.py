import pytest

from sms_api.api.routers.sms import _build_store_uri
from sms_api.config import get_settings


def test_build_store_uri(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "s3_work_bucket", "my-bucket")
    monkeypatch.setattr(settings, "s3_output_prefix", "vecoli-output")
    uri = _build_store_uri("exp-abc", 0)
    assert uri == "s3://my-bucket/vecoli-output/exp-abc/seed_00/store.zarr"
