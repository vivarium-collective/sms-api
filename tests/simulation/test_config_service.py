import pytest

from sms_api.config import get_settings
from sms_api.simulation.config_service import ConfigServiceHpc


@pytest.mark.asyncio
async def test_get_default_config() -> None:
    env = get_settings()
    config_service = ConfigServiceHpc(env)
    config_dir = config_service.config_dir()
    _ = config_service.new_genes_dir().remote_path.parent
    _ = config_service.variants_dir()

    assert str(config_dir.remote_path.parent) == str(config_service.vecoli_root_dir().remote_path)
