import pickle

import pytest


@pytest.mark.asyncio
async def test_get_analysis() -> None:
    from libsms import Client
    from libsms.api.data_v_ecoli import download_analysis_output_data
    from libsms.types import Response
    from sms_api.config import get_settings
    env = get_settings()
    base_url = env.dev_base_url
    client = Client(base_url=base_url)
    async with client as client:
        # my_data: MyDataModel = await get_my_data_model.asyncio(client=client)
        experiment_id = "sms_single"
        filename = "mass_fraction_summary.html"
        response = await download_analysis_output_data.asyncio_detailed(client=client, experiment_id=experiment_id, filename=filename)
        assert response.status_code == 200
        assert isinstance(response.content, bytes)
