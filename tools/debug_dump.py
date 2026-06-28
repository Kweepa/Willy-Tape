#!/usr/bin/env python3
"""One-shot read of collision ZP snapshot from VICE remote monitor.

VICE halts the CPU while the monitor is active; do NOT poll in a loop.
Play the game normally, then run this once after Willy dies (or pauses).
Sends 'g' to resume emulation after reading.
"""

import json
import re
import socket
import sys
import time
from pathlib import Path

DBG_PX = 0x89
DBG_PY = 0x8A
DBG_ITEMS = 0x8B
DBG_CHR = 0x8C
DBG_CELL = 0x8D
DBG_TOUCH = 0x8E
DBG_KILLED = 0x8F
DEAD = 0x17

LOG_PATH = Path(__file__).resolve().parent.parent / "debug-5b8a3a.log"
SESSION_ID = "5b8a3a"
HOST = "127.0.0.1"
PORT = 6510


def monitor_read(sock: socket.socket, start: int, end: int) -> list[int]:
    cmd = f"m {start:04x} {end - 1:04x}\n"
    sock.sendall(cmd.encode())
    time.sleep(0.08)
    data = b""
    sock.settimeout(1.0)
    try:
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
            if b"\n." in data or data.rstrip().endswith(b"."):
                break
    except socket.timeout:
        pass
    out: list[int] = []
    text = data.decode("latin-1", errors="replace")
    # VICE may embed the dump in a status line: "(C:$1653) >C:0089  d0 60 ..."
    for m in re.finditer(
        r"C:([0-9a-fA-F]+)\s+((?:[0-9a-fA-F]{2}\s*)+)", text
    ):
        for tok in m.group(2).split():
            out.append(int(tok, 16))
    return out


def classify(chr_val: int, items_left: int) -> str:
    if chr_val == 15:
        return "B" if items_left == 0 else "A"
    if chr_val >= 22:
        return "A"
    if chr_val == 19:
        return "E"
    if chr_val == 18:
        return "D"
    return "C"


def main() -> int:
    run_id = sys.argv[1] if len(sys.argv) > 1 else "post-fix"
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))
        sock.sendall(b"\n")
        time.sleep(0.1)
        dbg = monitor_read(sock, DBG_PX, DBG_KILLED + 1)
        dead_raw = monitor_read(sock, DEAD, DEAD + 1)
        sock.sendall(b"g\n")
    if len(dbg) < 7:
        print("Could not read debug snapshot from VICE. Is -remotemonitor enabled?")
        return 1
    snap = {
        "px": dbg[0],
        "py": dbg[1],
        "items_left": dbg[2],
        "chr": dbg[3],
        "cell": dbg[4],
        "touch": dbg[5],
        "killed_flag": dbg[6],
        "dead": dead_raw[0] if dead_raw else 0,
    }
    entry = {
        "sessionId": SESSION_ID,
        "runId": run_id,
        "hypothesisId": classify(snap["chr"], snap["items_left"]),
        "location": "debug_dump.py",
        "message": "willy_died" if snap["dead"] else "collision_snapshot",
        "data": snap,
        "timestamp": int(time.time() * 1000),
    }
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    print(json.dumps(snap, indent=2))
    print(f"Logged to {LOG_PATH}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ConnectionRefusedError:
        print("Cannot connect. Start xvic with -remotemonitor -remotemonitoraddress 127.0.0.1:6510")
        raise SystemExit(1)
