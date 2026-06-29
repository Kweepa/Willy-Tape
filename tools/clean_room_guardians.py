#!/usr/bin/env python3
"""Remove @guardiansprites blocks and f= from @guardians lines in room files."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

F_RE = re.compile(r"\s+f=\S+")


def clean_room_text(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().lower() == "@guardiansprites":
            i += 1
            while i < len(lines) and not lines[i].startswith("@"):
                i += 1
            continue
        if line.strip() == "@guardians":
            out.append(line)
            i += 1
            while i < len(lines) and not lines[i].startswith("@"):
                raw = lines[i]
                stripped = raw.strip()
                if stripped and not stripped.startswith(";") and not stripped.startswith("#"):
                    body = F_RE.sub("", raw.split("#", 1)[0].rstrip())
                    comment = ""
                    if "#" in raw:
                        comment = " #" + raw.split("#", 1)[1]
                    elif ";" in raw and not raw.strip().startswith(";"):
                        parts = raw.split(";", 1)
                        body = F_RE.sub("", parts[0].rstrip())
                        comment = " ;" + parts[1]
                    out.append(body + comment)
                else:
                    out.append(raw)
                i += 1
            continue
        out.append(line)
        i += 1
    return "\n".join(out).rstrip() + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rooms", type=Path, default=ROOT / "rooms")
    args = ap.parse_args()
    n = 0
    for path in sorted(args.rooms.glob("room*.txt")):
        new = clean_room_text(path.read_text(encoding="utf-8"))
        old = path.read_text(encoding="utf-8")
        if new != old:
            path.write_text(new, encoding="utf-8")
            n += 1
            print(f"cleaned {path.name}")
    print(f"Updated {n} room files")


if __name__ == "__main__":
    main()
