import json
import pathlib

import numpy as np
import pandas as pd
import requests
import xmltodict

from sms_api.data.models import BiocycData


def login_biocyc() -> requests.Session:
    s = requests.Session()  # create session
    # email = os.getenv("BIOCYC_EMAIL")
    # pw = os.getenv("BIOCYC_PASSWORD")
    resp = s.post(
        "https://websvc.biocyc.org/credentials/login/",
        data={"email": "cellulararchitect@protonmail.com", "password": "Cellman0451"},
    )
    resp.raise_for_status()
    return s


def get_biocyc_data(session: requests.Session, orgid: str, objid: str) -> BiocycData:
    url = f"https://websvc.biocyc.org/getxml?id={orgid.upper()}:{objid}&detail=low&fmt=json"
    r = session.get(url, headers={"Accept": "application/json"})
    r.raise_for_status()
    xml = r.text
    # Convert XML to dict
    data_dict = xmltodict.parse(xml)

    # Convert dict to JSON string
    json_data = json.loads(json.dumps(data_dict, indent=2))

    request_data = {"url": url, "headers": {"Accept": "application/json"}}
    return BiocycData(obj_id=objid, org_id=orgid, data=json_data, request=request_data)


def write_biocyc_batch(session: requests.Session, objids: np.ndarray) -> int:
    # data = {}
    dest_fp = pathlib.Path("assets/biocyc")
    for m_id in objids:
        orgid = "ECOLI"
        m_fp = dest_fp / f"{m_id}.json"
        if not m_fp.exists():
            data_i = get_biocyc_data(session=session, objid=m_id, orgid=orgid)
            data_i.export()
        else:
            print(f"There is already data for: {m_id} at {m_fp}")
        # data[m_id] = data_i
    return 0


def load_flat(csv_filename: str) -> pd.DataFrame:
    return pd.read_csv(
        pathlib.Path(f"/Users/alexanderpatrie/sms/vEcoli/reconstruction/ecoli/flat/{csv_filename}.tsv"),
        sep="\t",
        comment="#",
    )


def get_metabolite_ids() -> list[str]:
    met = load_flat("metabolites")
    return met[["id"]].to_numpy().flatten().tolist()
