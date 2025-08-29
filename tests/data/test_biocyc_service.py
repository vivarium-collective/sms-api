import pytest

from sms_api.data.biocyc_service import BiocycService


@pytest.mark.asyncio
async def test_get_biocyc_data(biocyc_service: BiocycService) -> None:
    # orgid = "ECOLI"
    # objid = "6PFRUCTPHOS-RXN"
    # data = biocyc_service.get_data(obj_id=objid, org_id=orgid)
    # assert data is not None
    # print(data)
    print(biocyc_service)
