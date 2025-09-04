import asyncio
import os
import socket
import struct
import sys
from asyncio import StreamReader, StreamWriter

IS_LINUX = sys.platform.startswith("linux")
if IS_LINUX:
    SO_PEERCRED = 17  # Linux only


ALLOWED_COMMANDS = {
    "sbatch": [os.environ.get("FAKE_SBATCH", "/usr/bin/sbatch")],
    "squeue": ["/usr/bin/squeue"],
    "scancel": ["/usr/bin/scancel"],
}


async def handle_client(reader: StreamReader, writer: StreamWriter) -> None:
    try:
        if IS_LINUX:
            sock = writer.get_extra_info("socket")
            ucred = sock.getsockopt(socket.SOL_SOCKET, SO_PEERCRED, struct.calcsize("3i"))
            pid, peer_uid, gid = struct.unpack("3i", ucred)
            if peer_uid != os.getuid():
                writer.write(b"ERROR: UID mismatch\n")
                await writer.drain()
                writer.close()
                return
        else:
            # On macOS, skip UID check (not secure!)
            print("WARNING: UID check is skipped on non-Linux platforms.", file=sys.stderr)

        data = await reader.readline()
        if not data:
            writer.close()
            return
        parts = data.decode().strip().split()
        if not parts or parts[0] not in ALLOWED_COMMANDS:
            writer.write(b"ERROR: Command not allowed\n")
            await writer.drain()
            writer.close()
            return
        cmd = ALLOWED_COMMANDS[parts[0]] + parts[1:]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        writer.write(stdout)
        if stderr:
            writer.write(b"\nERROR:\n" + stderr)
        await writer.drain()
    except Exception as e:
        writer.write(f"ERROR: {e}\n".encode())
        await writer.drain()
    finally:
        writer.close()


async def main(socket_path: str) -> None:
    if os.path.exists(socket_path):
        os.remove(socket_path)
    server = await asyncio.start_unix_server(handle_client, path=socket_path)
    os.chmod(socket_path, 0o700)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        print(f"Usage: {sys.argv[0]} SOCKET_PATH")
        sys.exit(1)
    socket_path = sys.argv[1]
    try:
        asyncio.run(main(socket_path))
    except KeyboardInterrupt:
        print("Broker stopped.")
