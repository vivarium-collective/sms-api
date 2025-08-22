import pytest
import requests

from sms_api.data.biocyc_service import get_biocyc_data, load_flat


@pytest.mark.asyncio
async def test_get_biocyc_data(session: requests.Session) -> None:
    orgid = "ECOLI"
    objid = "6PFRUCTPHOS-RXN"
    data = get_biocyc_data(session, orgid, objid)
    assert data is not None
    print(data)


@pytest.mark.asyncio
async def test_load_flat() -> None:
    metabolits = load_flat("metabolites")
    metabolite_ids = metabolits[["id"]].to_numpy().flatten()
    assert len(metabolite_ids)
