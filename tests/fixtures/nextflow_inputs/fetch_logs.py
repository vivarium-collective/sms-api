#!/usr/bin/env python
"""
Fetch Nextflow job logs from the HPC cluster.

Usage:
    uv run python tests/fixtures/nextflow_inputs/fetch_logs.py <job_uuid>

Example:
    uv run python tests/fixtures/nextflow_inputs/fetch_logs.py 49316d48ad7f4254a1a8f49791ea390f
"""

import asyncio
import sys
from pathlib import Path

from sms_api.common.ssh.ssh_service import SSHSessionService
from sms_api.config import get_settings


async def fetch_logs(job_uuid: str, tail_lines: int = 100) -> None:
    """Fetch and print logs for a given job UUID."""
    settings = get_settings()
    ssh_service = SSHSessionService(
        hostname=settings.slurm_submit_host,
        username=settings.slurm_submit_user,
        key_path=Path(settings.slurm_submit_key_path),
        known_hosts=Path(settings.slurm_submit_known_hosts) if settings.slurm_submit_known_hosts else None,
    )

    base_path = f"/projects/SMS/sms_api/alex/htclogs/sms_ccam_{job_uuid}"

    async with ssh_service.session() as ssh:
        # Check output log
        retcode, stdout, stderr = await ssh.run_command(
            f"cat {base_path}.out 2>&1 | tail -{tail_lines}"
        )
        print("=== OUTPUT LOG ===")
        print(stdout)

        # Check error log
        retcode, stdout, stderr = await ssh.run_command(
            f"cat {base_path}.err 2>&1 | tail -{tail_lines}"
        )
        print("\n=== ERROR LOG ===")
        print(stdout)


async def list_recent_jobs(limit: int = 10) -> None:
    """List recent SMS CCAM job files on the HPC."""
    settings = get_settings()
    ssh_service = SSHSessionService(
        hostname=settings.slurm_submit_host,
        username=settings.slurm_submit_user,
        key_path=Path(settings.slurm_submit_key_path),
        known_hosts=Path(settings.slurm_submit_known_hosts) if settings.slurm_submit_known_hosts else None,
    )

    async with ssh_service.session() as ssh:
        retcode, stdout, stderr = await ssh.run_command(
            f"ls -lt /projects/SMS/sms_api/alex/htclogs/sms_ccam_*.out 2>/dev/null | head -{limit}"
        )
        print("=== RECENT SMS CCAM JOBS ===")
        print(stdout if stdout else "No jobs found")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fetch_logs.py <job_uuid> [tail_lines]")
        print("       python fetch_logs.py --list")
        print("\nExamples:")
        print("  python fetch_logs.py 49316d48ad7f4254a1a8f49791ea390f")
        print("  python fetch_logs.py 49316d48ad7f4254a1a8f49791ea390f 50")
        print("  python fetch_logs.py --list")
        sys.exit(1)

    if sys.argv[1] == "--list":
        asyncio.run(list_recent_jobs())
    else:
        job_uuid = sys.argv[1]
        tail_lines = int(sys.argv[2]) if len(sys.argv) > 2 else 100
        asyncio.run(fetch_logs(job_uuid, tail_lines))
