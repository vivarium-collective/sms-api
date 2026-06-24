import pytest

from sms_api.api.routers.sms import _build_store_uri
from sms_api.config import get_settings


def test_build_store_uri(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "s3_work_bucket", "my-bucket")
    monkeypatch.setattr(settings, "s3_output_prefix", "vecoli-output")
    uri = _build_store_uri("exp-abc", 0)
    assert uri == "s3://my-bucket/vecoli-output/exp-abc/v2ecoli_seed00.zarr"


def test_build_store_uri_zero_pads_seed(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "s3_work_bucket", "b")
    monkeypatch.setattr(settings, "s3_output_prefix", "p")
    assert _build_store_uri("exp", 7).endswith("/exp/v2ecoli_seed07.zarr")
