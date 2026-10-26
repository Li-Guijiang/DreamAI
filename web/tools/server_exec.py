"""Minimal remote helper over SSH (Paramiko).

Usage:
    set DREAMAI_SSH_PASSWORD=...
    python tools/server_exec.py exec  <local-script.sh>
    python tools/server_exec.py put   <local-file> <remote-path>
    python tools/server_exec.py get   <remote-path> <local-file>
    python tools/server_exec.py shell "<command>"

The password is read from the environment and never stored on disk.
"""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

import paramiko

HOST = os.environ.get("DREAMAI_SSH_HOST", "8.156.85.180")
USER = os.environ.get("DREAMAI_SSH_USER", "root")
PASSWORD = os.environ.get("DREAMAI_SSH_PASSWORD", "")


def connect() -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        HOST,
        port=22,
        username=USER,
        password=PASSWORD,
        timeout=20,
        banner_timeout=20,
        auth_timeout=20,
        look_for_keys=False,
        allow_agent=False,
    )
    return client


def run(client: paramiko.SSHClient, command: str) -> int:
    stdin, stdout, stderr = client.exec_command(command, timeout=600, get_pty=True)
    stdin.close()
    channel = stdout.channel
    while True:
        if channel.recv_ready():
            sys.stdout.write(channel.recv(65536).decode("utf-8", "replace"))
            sys.stdout.flush()
        if channel.recv_stderr_ready():
            sys.stderr.write(channel.recv_stderr(65536).decode("utf-8", "replace"))
            sys.stderr.flush()
        if channel.exit_status_ready() and not channel.recv_ready() and not channel.recv_stderr_ready():
            break
    code = channel.recv_exit_status()
    print(f"\n[exit {code}]")
    return code


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    action = sys.argv[1]
    client = connect()
    try:
        if action == "exec":
            script = Path(sys.argv[2]).read_text(encoding="utf-8")
            client.exec_command("mkdir -p /root/.dreamai")[1].channel.recv_exit_status()
            sftp = client.open_sftp()
            remote = "/root/.dreamai/script.sh"
            with sftp.open(remote, "w") as handle:
                handle.write(script)
            sftp.chmod(remote, stat.S_IRWXU)
            sftp.close()
            return run(client, f"bash {remote}")
        if action == "shell":
            return run(client, sys.argv[2])
        if action == "put":
            sftp = client.open_sftp()
            sftp.put(sys.argv[2], sys.argv[3])
            sftp.close()
            print(f"uploaded {sys.argv[2]} -> {sys.argv[3]}")
            return 0
        if action == "get":
            sftp = client.open_sftp()
            sftp.get(sys.argv[2], sys.argv[3])
            sftp.close()
            print(f"downloaded {sys.argv[2]} -> {sys.argv[3]}")
            return 0
        print(__doc__)
        return 2
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
