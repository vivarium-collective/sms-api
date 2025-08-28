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
async def _():
    from pathlib import Path
    import polars as pl

    from sms_api.common.ssh.ssh_service import get_ssh_service

    parquet_dirpath = Path(
        "/Users/alexanderpatrie/sms/sms-api/home/FCAM/svc_vivarium/prod/sims/sms_single/history/experiment_id=sms_single/variant=0/lineage_seed=0/generation=1/agent_id=0"
    )

    local_metadata_filepath = Path(
        "/Users/alexanderpatrie/sms/sms-api/home/FCAM/svc_vivarium/prod/sims/sms_single/analyses/variant=0/lineage_seed=0/generation=1/agent_id=0/plots/metadata.json"
    )
    remote_metdata_filepath = Path(
        "/home/FCAM/svc_vivarium/prod/sims/sms_single/analyses/variant=0/lineage_seed=0/generation=1/agent_id=0/plots/metadata.json"
    )

    ssh = get_ssh_service()

    await ssh.scp_upload(local_file=local_metadata_filepath, remote_path=remote_metdata_filepath)
    return local_metadata_filepath, parquet_dirpath, pl


@app.cell
def _(local_metadata_filepath):
    local_metadata_filepath.exists()
    return


@app.cell
def _(parquet_dirpath, pl):
    times = pl.scan_parquet(parquet_dirpath).select("time").collect()
    return (times,)


@app.cell
def _(times):
    dir(times)
    return


@app.cell
def _(times):
    times.to_numpy().max()
    return


@app.function
async def upload_files(local_analysis_dirpath=None):
    import pandas as pd
    import numpy as np
    from pathlib import Path
    from sms_api.common.ssh.ssh_service import get_ssh_service

    analysis_dirpath = local_analysis_dirpath or Path(
        "/Users/alexanderpatrie/sms/sms-api/home/FCAM/svc_vivarium/prod/sims/sms_perturb_growth_10800/analyses"
    )
    anal_files = []
    for root, _, files in analysis_dirpath.walk():
        for f in files:
            filepath = root / f
            if not filepath.parts[-1].startswith("."):
                anal_files.append(filepath)
    ssh = get_ssh_service()

    remote_anal_dir = Path("/home/FCAM/svc_vivarium/prod/sims/sms_perturb_growth_10800/analyses")
    # await ssh.scp_upload(local_file=analysis_dirpath, remote_path=remote_anal_dir)
    for i, local_path in enumerate(anal_files):
        try:
            remote_path = (
                Path(
                    f"/home/FCAM/svc_vivarium/prod/sims/sms_perturb_growth_10800/analyses/variant={i}/lineage_seed=0/generation=1/agent_id=0/plots"
                )
                / local_path.parts[-1]
            )
            await ssh.scp_upload(local_file=local_path, remote_path=remote_path)
            print(f"Uploaded path!: {remote_path}")
        except:
            print(f"Couldnt upload {local_path}")


@app.cell
def _():
    # await upload_files()
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
