import marimo

__generated_with = "0.14.16"
app = marimo.App(width="medium")


@app.function
async def upload_ptools_files(local_analysis_dirpath=None):
    import pandas as pd
    import numpy as np
    from pathlib import Path
    from sms_api.common.ssh.ssh_service import get_ssh_service

    analysis_dirpath = local_analysis_dirpath or Path(
        "/Users/alexanderpatrie/sms/vEcoli/out/sms_single/analyses/variant=0/lineage_seed=0/generation=1/agent_id=0/plots"
    )
    anal_files = [fp for fp in analysis_dirpath.iterdir() if "ptools" in str(fp)]
    ssh = get_ssh_service()

    remote_anal_dir = Path(
        "/home/FCAM/svc_vivarium/prod/sims/sms_single/analyses/variant=0/lineage_seed=0/generation=1/agent_id=0/plots"
    )
    for local_path in anal_files:
        remote_path = remote_anal_dir / local_path.parts[-1]
        await ssh.scp_upload(local_file=local_path, remote_path=remote_path)


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
