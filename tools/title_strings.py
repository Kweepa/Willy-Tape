"""Load title screen lines from title_strings.txt (repo root)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TITLE_STRINGS_PATH = ROOT / "title_strings.txt"


def load_title_lines(path: Path | None = None) -> list[str]:
    src = path or TITLE_STRINGS_PATH
    if not src.is_file():
        raise SystemExit(f"missing {src}")
    out: list[str] = []
    for raw in src.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            out.append(line)
    if not out:
        raise SystemExit(f"no title lines in {src}")
    return out
