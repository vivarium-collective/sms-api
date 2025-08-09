# ~/.slurm-proxy/proxy.py
import argparse
import contextlib
import json
import os
import socket
import struct
import subprocess
import sys

parser = argparse.ArgumentParser(description="slurm-proxy UNIX socket server")
parser.add_argument("--sock", default=os.path.expanduser("~/.slurm-proxy/slurm.sock"), help="Path to the UNIX socket")
args = parser.parse_args()

SOCK = args.sock
ALLOW = {"squeue", "sbatch", "scancel", "sinfo", "sacct", "scontrol"}
IS_LINUX = sys.platform.startswith("linux")


with contextlib.suppress(FileNotFoundError):
    os.unlink(SOCK)
# create the directory if it does not exist
os.makedirs(os.path.dirname(SOCK), exist_ok=True)

s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
os.chmod(os.path.dirname(SOCK), 0o700)
s.bind(SOCK)
os.chmod(SOCK, 0o600)
s.listen(8)


def is_safe_arg(arg: str) -> bool:
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789./-_=:@")
    return isinstance(arg, str) and all(c in allowed for c in arg)


def is_same_uid(conn: socket.socket) -> bool:
    """Check if the peer UID matches the current process UID."""
    if IS_LINUX:
        ucred = conn.getsockopt(socket.SOL_SOCKET, 17, struct.calcsize("3i"))  # 17 = SO_PEERCRED
        _, peer_uid, _ = struct.unpack("3i", ucred)
        return int(peer_uid) == os.getuid()
    else:
        # On non-Linux systems, we skip the UID check for simplicity
        print("WARNING: UID check is skipped on non-Linux platforms.", file=sys.stderr)
        return True

def send_response(conn: socket.socket, returncode: int, stdout: str = "", stderr: str = "") -> None:
    resp = {"returncode": returncode, "stdout": stdout, "stderr": stderr}
    conn.sendall((json.dumps(resp) + "\n").encode())


while True:
    conn, _ = s.accept()
    with conn:
        # Check peer UID
        if not is_same_uid(conn):
            send_response(conn=conn, returncode=127, stderr="ERROR: UID mismatch")
            continue

        data = b""
        while True:
            chunk = conn.recv(65536)
            if not chunk:
                break
            data += chunk
            if b"\n" in data:
                break
        try:
            req = json.loads(data.decode().strip())
            cmd = req.get("cmd")
            args = req.get("args", [])
            if cmd not in ALLOW:
                send_response(conn=conn, returncode=127, stderr="command not allowed")
                continue
            # sanitize the args
            if not all(is_safe_arg(str(a)) for a in args):
                send_response(conn=conn, returncode=127, stderr="unsafe argument detected")
                continue
            # sanitize env
            env = {k: v for k, v in os.environ.items() if not (k.startswith("LD_") or k.startswith("SLURM_"))}
            p = subprocess.run(  # noqa: S603  mark as safe
                [f"/usr/bin/{cmd}", *map(str, args)],
                capture_output=True,
                text=True,
                env=env,
                cwd=os.path.expanduser("~"),
                timeout=300,
            )
            send_response(conn=conn, returncode=p.returncode, stdout=p.stdout, stderr=p.stderr)
        except Exception as e:
            send_response(conn=conn, returncode=127, stderr=f"{type(e).__name__}: {e}")
