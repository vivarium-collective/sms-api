import pytest
import requests

from sms_api.data.biocyc_service import get_biocyc_data


@pytest.mark.asyncio
async def test_get_biocyc_data(session: requests.Session) -> None:
    orgid = "ECOLI"
    objid = "6PFRUCTPHOS-RXN"
    data = get_biocyc_data(session, orgid, objid)
    assert data is not None
    print(data)
