import argparse
import contextlib
import json
import os
import socket
import struct
import subprocess
import sys

ALLOW = {"squeue", "sbatch", "scancel", "sinfo", "sacct", "scontrol"}
IS_LINUX = sys.platform.startswith("linux")


def is_safe_arg(arg: str) -> bool:
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789./-_=:@")
    return isinstance(arg, str) and all(c in allowed for c in arg)


def validate_request(req_json: str) -> tuple[str, list[str]]:
    req = json.loads(req_json)
    # check that req should be a dictionary with only "cmd" and "args"
    if not isinstance(req, dict):
        raise TypeError("Invalid request: must be a dictionary")
    if "cmd" not in req or "args" not in req:
        raise ValueError("Invalid request: must contain 'cmd' and 'args' keys")
    if len(req) != 2:
        raise ValueError("Invalid request: must contain only 'cmd' and 'args' keys")

    cmd = req.get("cmd")
    if not isinstance(cmd, str):
        raise TypeError("Invalid 'cmd': must be a string")
    if cmd not in ALLOW:
        raise ValueError(f"Invalid cmd: {cmd!r} not allowed")

    cmd_args = req.get("args", [])
    if not isinstance(cmd_args, list):
        raise TypeError("Invalid args: must be a list")
    if not all(is_safe_arg(str(a)) for a in cmd_args):
        raise ValueError("Invalid args: unsafe argument detected")
    return cmd, cmd_args


parser = argparse.ArgumentParser(description="slurm-proxy UNIX socket server")
parser.add_argument("--sock", default=os.path.expanduser("~/.slurm-proxy/slurm.sock"), help="Path to the UNIX socket")
example = '"{\\"cmd\\": \\"squeue\\", \\"args\\": [\\"-j\\", 1201]}"'
parser.add_argument(
    "--test",
    help=f"Optional JSON string to validate for command and args (e.g. --test {example})",
    type=str,
    default='{"cmd": "squeue", "args": []}',
)
args = parser.parse_args()

if args.test:
    try:
        cmd, cmd_args = validate_request(args.test)
        print(f"Valid command JSON, cmd={[cmd, *cmd_args]}")
        sys.exit(0)
    except Exception as e:
        print(f"Invalid command JSON: {e}", file=sys.stderr)
        sys.exit(1)

SOCK = args.sock

with contextlib.suppress(FileNotFoundError):
    os.unlink(SOCK)
os.makedirs(os.path.dirname(SOCK), exist_ok=True)

s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
os.chmod(os.path.dirname(SOCK), 0o700)
try:
    s.bind(SOCK)
except OSError as e:
    print(f"Error binding to socket {SOCK}: {e}", file=sys.stderr)
    sys.exit(1)
os.chmod(SOCK, 0o600)
s.listen(8)
USER = os.environ.get("USER", "unknown")
print(f"Listening for validated SLURM commands from uid={os.getuid()} on local UNIX socket {SOCK}")


def is_same_uid(conn: socket.socket) -> bool:
    if IS_LINUX:
        ucred = conn.getsockopt(socket.SOL_SOCKET, 17, struct.calcsize("3i"))  # 17 = SO_PEERCRED
        _, peer_uid, _ = struct.unpack("3i", ucred)
        return int(peer_uid) == os.getuid()
    else:
        print("WARNING: UID check is skipped on non-Linux platforms.", file=sys.stderr)
        return True


def send_response(conn: socket.socket, returncode: int, stdout: str = "", stderr: str = "") -> None:
    resp = {"returncode": returncode, "stdout": stdout, "stderr": stderr}
    conn.sendall((json.dumps(resp) + "\n").encode())


while True:
    conn, _ = s.accept()
    with conn:
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
            cmd, cmd_args = validate_request(req)
            env = {k: v for k, v in os.environ.items() if not (k.startswith("LD_") or k.startswith("SLURM_"))}
            p = subprocess.run(  # noqa: S603  mark as safe
                [f"/usr/bin/{cmd}", *map(str, cmd_args)],
                capture_output=True,
                text=True,
                env=env,
                cwd=os.path.expanduser("~"),
                timeout=300,
            )
            send_response(conn=conn, returncode=p.returncode, stdout=p.stdout, stderr=p.stderr)
        except Exception as e:
            send_response(conn=conn, returncode=127, stderr=f"{type(e).__name__}: {e}")
