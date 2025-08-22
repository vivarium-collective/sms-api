from enum import StrEnum
from pathlib import Path

from sms_api.common.gateway.models import Namespace
from sms_api.common.ssh.ssh_service import get_ssh_service


class HpcDirectory(StrEnum):
    LOGS = "htclogs"
    IMAGES = "images"
    PARCA = "parca"
    REPOS = "repos"
    SIMS = "sims"


async def upload_to_hpc(
    local: Path,
    remote: Path | None = None,
    remote_dest: HpcDirectory | None = None,
    namespace: Namespace | None = None,
    **kwargs: bool | str,
) -> None:
    if not remote:
        ns = namespace or Namespace.PRODUCTION
        filename = local.parts[-1]
        remote = Path(f"/home/FCAM/svc_vivarium/{ns}/{remote_dest}") / filename
    ssh = get_ssh_service()
    try:
        await ssh.scp_upload(local, remote, **kwargs)
    except Exception as e:
        print(e)
