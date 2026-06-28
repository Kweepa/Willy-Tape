#!/usr/bin/env python3
"""Zero-page layout audit for JSW (zp.asm + optional ASM indexed-writer scan)."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Explicit symbol sizes (bytes). Unlisted symbols default to 1.
SIZE_OVERRIDES: dict[str, int] = {
    "arr": 2,
    "arr2": 2,
    "arr3": 2,
    "scr_ptr": 2,
    "col_ptr": 2,
    "map_ptr": 2,
    "udg_ptr": 2,
    "play_udg": 2,
    "hx": 10,  # hx..guard_axis guardian scratch ($20-$29)
    "rope_scr": 2,
    "rope_udg_mem": 2,
    "rope_old_screen_pos": 32,
    "player_overlap": 6,
    "player_touch": 48,
    "cell_off_2x3": 6,
    "lr_touch_a": 6,
    "lr_touch_b": 6,
    "lr_touch_c": 6,
    "draw_vguard_chrs": 6,
    "draw_player_offsets": 6,
    "draw_player_chrs": 6,
    "ingame_tune_pitch": 9,
}

# Aliases / sub-fields — skip duplicate overlap reports.
SKIP_OVERLAP = {
    "stream_ptr_hi",  # $53 = high byte of stream_ptr ($52-$53)
    "hy",
    "hl",
    "hr",
    "hd",
    "g_frame",
    "ht",
    "g_fctl",
    "hc",
    "guard_axis",  # $21-$28 via hx,y base at $20
    "lr_touch_b",
    "lr_touch_c",
    "cell_off_2x3",
    "lr_touch_a",
    "draw_vguard_chrs",
    "player_overlap",
    "player_touch",
}

# Intentional multi-byte writes (symbol, extent bytes, reason)
INTENTIONAL_WRITES: dict[str, tuple[int, str]] = {
    "player_overlap": (54, "DrawPlayer clears overlap+touch via player_overlap,x"),
    "cell_off_2x3": (18, "WarmStart copies boot_zp_pack room tables to $DC-$ED"),
    "draw_player_offsets": (6, "WarmStart RelocateDrawPlayerTables"),
    "draw_player_chrs": (6, "WarmStart RelocateDrawPlayerTables"),
}

# Stack-page symbols (not low ZP) — skip in ZP asm scan
STACK_PAGE_SYMBOLS = {"x24rowtab", "jumptab", "jumpnotes", "pickup_got", "pickup_got_last"}

VIRTUAL_REGIONS: list[tuple[str, int, int]] = [
    ("DrawPlayer_clear", 0xA0, 54),
    ("boot_zp_room_pack", 0xDC, 18),
]

KERNAL_RESERVE = [
    (0x90, 0x93, "LOAD serial/status"),
    (0xAE, 0xAF, "LOAD address ptr"),
    (0xB7, 0xC4, "SETNAM/SETLFS/LOAD setup"),
]

STACK_PAGE_REGIONS: list[tuple[str, int, int]] = [
    ("pickup_got", 0x100, 0x3E),  # $100-$13D inclusive
    ("x24rowtab", 0x140, 36),
    ("jumptab", 0x164, 54),
    ("jumpnotes", 0x19A, 27),
]

CLEAR_ZONE = (0xA0, 0xD5)
CLEAR_ZONE_OK = {"player_overlap", "player_touch", "DrawPlayer_clear"}
BOOT_PACK_END = 0xEF

EQUATE_RE = re.compile(
    r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\$([0-9A-Fa-f]+)",
    re.MULTILINE,
)

WRITE_RE = re.compile(
    r"^\s*(sta|inc|dec)\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s*([,\+\-])\s*([xy]))?",
    re.IGNORECASE | re.MULTILINE,
)

PLUS1_WRITE_RE = re.compile(
    r"^\s*(sta|inc|dec)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\+\s*1",
    re.IGNORECASE | re.MULTILINE,
)

LDX_IMM_RE = re.compile(r"ldx\s+#([^;\n]+)", re.IGNORECASE)
LDY_IMM_RE = re.compile(r"ldy\s+#([^;\n]+)", re.IGNORECASE)


@dataclass
class Region:
    name: str
    start: int
    size: int
    virtual: bool = False

    @property
    def end(self) -> int:
        return self.start + self.size - 1

    def overlaps(self, other: Region) -> bool:
        return self.start <= other.end and other.start <= self.end


def parse_zp(zp_path: Path) -> dict[str, int]:
    text = zp_path.read_text(encoding="utf-8", errors="replace")
    symbols: dict[str, int] = {}
    for name, addr in EQUATE_RE.findall(text):
        symbols[name] = int(addr, 16)
    return symbols


def build_regions(symbols: dict[str, int]) -> list[Region]:
    regions: list[Region] = []
    for name, addr in sorted(symbols.items(), key=lambda kv: kv[1]):
        if name in SKIP_OVERLAP:
            continue
        size = SIZE_OVERRIDES.get(name, 1)
        regions.append(Region(name, addr, size))
    for name, start, size in VIRTUAL_REGIONS:
        regions.append(Region(name, start, size, virtual=True))
    return sorted(regions, key=lambda r: r.start)


def fmt_addr(addr: int) -> str:
    return f"${addr:02X}"


def print_map(regions: list[Region]) -> None:
    print("Zero-page map ($00-$FF):")
    print(f"{'Start':>6} {'End':>6} {'Size':>4}  Symbol")
    print("-" * 52)
    prev_end = 0x01
    for r in regions:
        if r.start > 0xFF:
            continue
        if r.start > prev_end + 1 and prev_end >= 0x02:
            gap = r.start - prev_end - 1
            print(f"{fmt_addr(prev_end + 1):>6} {fmt_addr(r.start - 1):>6} {gap:4}  (gap)")
        end = min(r.end, 0xFF)
        size = end - r.start + 1
        tag = " [virtual]" if r.virtual else ""
        print(f"{fmt_addr(r.start):>6} {fmt_addr(end):>6} {size:4}  {r.name}{tag}")
        prev_end = max(prev_end, end)
    if prev_end < 0xFF:
        print(f"{fmt_addr(prev_end + 1):>6} {fmt_addr(0xFF):>6} {0xFF - prev_end:4}  (gap)")
    print()


def _inside_pack(region: Region, pack: Region) -> bool:
    return region.start >= pack.start and region.end <= pack.end


def check_overlaps(regions: list[Region]) -> list[str]:
    errors: list[str] = []
    zp_regions = [r for r in regions if r.start <= 0xFF and not r.virtual]
    pack = next((r for r in regions if r.name == "boot_zp_pack"), None)
    clear = next((r for r in regions if r.name == "DrawPlayer_clear"), None)
    for i, a in enumerate(zp_regions):
        for b in zp_regions[i + 1 :]:
            if not a.overlaps(b):
                continue
            if pack and (_inside_pack(a, pack) or _inside_pack(b, pack)):
                continue
            if clear and a.name == "cell_off_2x3":
                continue  # clear zone ends $D5; pack starts $DC
            errors.append(
                f"overlap: {a.name} {fmt_addr(a.start)}-{fmt_addr(a.end)} "
                f"vs {b.name} {fmt_addr(b.start)}-{fmt_addr(b.end)}"
            )
    return errors


def check_clear_zone(regions: list[Region]) -> list[str]:
    errors: list[str] = []
    cz_lo, cz_hi = CLEAR_ZONE
    cz = Region("DrawPlayer_clear", cz_lo, cz_hi - cz_lo + 1, virtual=True)
    for r in regions:
        if r.name in CLEAR_ZONE_OK or r.virtual or r.name in SKIP_OVERLAP:
            continue
        if r.start > 0xFF:
            continue
        if r.overlaps(cz):
            errors.append(
                f"clear-zone: {r.name} {fmt_addr(r.start)}-{fmt_addr(r.end)} "
                f"intersects DrawPlayer clear {fmt_addr(cz_lo)}-{fmt_addr(cz_hi)}"
            )
    return errors


def check_boot_boundary(regions: list[Region]) -> list[str]:
    errors: list[str] = []
    for r in regions:
        if r.virtual or r.name == "boot_zp_room_pack":
            continue
        if r.name in ("ingame_tune_pitch",):
            continue
        if r.start <= BOOT_PACK_END and r.end > BOOT_PACK_END and r.start >= 0xDC:
            errors.append(
                f"boot-pack spill: {r.name} ends at {fmt_addr(r.end)} (room pack ends {fmt_addr(BOOT_PACK_END)})"
            )
    return errors


def check_kernal(regions: list[Region]) -> list[str]:
    warnings: list[str] = []
    for r in regions:
        if r.virtual or r.start > 0xFF:
            continue
        for lo, hi, desc in KERNAL_RESERVE:
            k = Region("KERNAL", lo, hi - lo + 1, virtual=True)
            if r.overlaps(k):
                warnings.append(
                    f"KERNAL reserve: {r.name} {fmt_addr(r.start)}-{fmt_addr(r.end)} "
                    f"in {fmt_addr(lo)}-{fmt_addr(hi)} ({desc})"
                )
    return warnings


def check_stack_page(symbols: dict[str, int]) -> list[str]:
    errors: list[str] = []
    regions = [Region(n, s, sz) for n, s, sz in STACK_PAGE_REGIONS]
    if "pickup_got_last" in symbols:
        got = symbols["pickup_got"]
        last = symbols["pickup_got_last"]
        regions[0] = Region("pickup_got", got, last - got + 1)
    for i, a in enumerate(regions):
        for b in regions[i + 1 :]:
            if a.overlaps(b):
                errors.append(
                    f"stack-page overlap: {a.name} {fmt_addr(a.start)}-{fmt_addr(a.end)} "
                    f"vs {b.name} {fmt_addr(b.start)}-{fmt_addr(b.end)}"
                )
    prev_end = 0xFF
    for r in regions:
        if r.start > prev_end + 1:
            gap = r.start - prev_end - 1
            print(f"  stack-page gap: {fmt_addr(prev_end + 1)}-{fmt_addr(r.start - 1)} ({gap} B)")
        prev_end = max(prev_end, r.end)
    return errors


def eval_imm(expr: str, constants: dict[str, int]) -> int | None:
    expr = expr.strip().split(";")[0].strip()
    if not expr:
        return None
    # Simple cases: decimal, hex, symbol, symbol-1, (48+6-1)
    expr = expr.replace("(", "").replace(")", "")
    if re.fullmatch(r"[0-9]+", expr):
        return int(expr)
    if re.fullmatch(r"\$[0-9A-Fa-f]+", expr, re.I):
        return int(expr[1:], 16)
    m = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)\s*-\s*([0-9]+)", expr)
    if m and m.group(1) in constants:
        return constants[m.group(1)] - int(m.group(2))
    if expr in constants:
        return constants[expr]
    # arithmetic like 48+6-1
    if re.fullmatch(r"[0-9+\-]+", expr):
        try:
            return eval(expr, {"__builtins__": {}}, {})
        except Exception:
            return None
    return None


def load_asm_constants() -> dict[str, int]:
    consts: dict[str, int] = {
        "boot_zp_size": 32,
        "stack_page_size": 117,
        "ROPE_UDG_BYTES": 128,
    }
    for path in (ROOT / "defines.asm", ROOT / "runtime_const.asm", ROOT / "header.asm"):
        if not path.exists():
            continue
        for name, addr in EQUATE_RE.findall(path.read_text(encoding="utf-8", errors="replace")):
            consts[name] = int(addr, 16)
    return consts


def symbol_owning(addr: int, symbols: dict[str, int]) -> str | None:
    """Return the ZP symbol that owns addr, or None if unassigned gap."""
    owner: str | None = None
    for name, start in symbols.items():
        if name in SKIP_OVERLAP:
            continue
        size = SIZE_OVERRIDES.get(name, 1)
        if start <= addr < start + size:
            if owner is not None:
                return owner  # first match; overlaps reported elsewhere
            owner = name
    return owner


def scan_plus1_clashes(symbols: dict[str, int], asm_dir: Path) -> list[str]:
    """Flag sta/inc/dec sym+1 where high byte is a different live ZP symbol."""
    errors: list[str] = []
    zp_names = set(symbols)
    for path in sorted(asm_dir.glob("*.asm")):
        if path.name == "rope_test.asm":
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            stripped = line.split(";")[0]
            m = PLUS1_WRITE_RE.search(stripped)
            if not m:
                continue
            op, sym = m.group(1).lower(), m.group(2)
            if sym not in zp_names or sym in STACK_PAGE_SYMBOLS:
                continue
            if sym not in symbols:
                continue
            sym_size = SIZE_OVERRIDES.get(sym, 1)
            if sym_size >= 2:
                continue  # intentional high byte of a 2+ byte field
            hi_addr = symbols[sym] + 1
            if hi_addr > 0xFF:
                continue
            hi_owner = symbol_owning(hi_addr, symbols)
            if hi_owner is None:
                continue
            if hi_owner != sym:
                errors.append(
                    f"+1 clash: {path.name}:{lineno} {op} {sym}+1 "
                    f"({fmt_addr(hi_addr)} is {hi_owner}, not high byte of {sym})"
                )
    return errors


def scan_asm_writes(symbols: dict[str, int], asm_dir: Path) -> list[str]:
    errors: list[str] = []
    consts = load_asm_constants()
    zp_names = set(symbols)

    for path in sorted(asm_dir.glob("*.asm")):
        if path.name == "rope_test.asm":
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        pending_x: int | None = None
        pending_y: int | None = None

        for lineno, line in enumerate(lines, 1):
            stripped = line.split(";")[0]
            m_ldx = LDX_IMM_RE.search(stripped)
            if m_ldx:
                pending_x = eval_imm(m_ldx.group(1), consts)
            m_ldy = LDY_IMM_RE.search(stripped)
            if m_ldy:
                pending_y = eval_imm(m_ldy.group(1), consts)

            m = WRITE_RE.search(stripped)
            if not m:
                continue
            op, sym, op2, reg = m.group(1).lower(), m.group(2), m.group(3), m.group(4)
            if sym not in zp_names or sym in STACK_PAGE_SYMBOLS:
                continue
            base_size = SIZE_OVERRIDES.get(sym, 1)
            loc = f"{path.name}:{lineno}"

            if sym in INTENTIONAL_WRITES:
                allowed, _ = INTENTIONAL_WRITES[sym]
                if op == "sta" and op2 and reg:
                    max_idx = pending_x if reg.lower() == "x" else pending_y
                    if max_idx is not None and max_idx + 1 <= allowed:
                        continue

            if op2 and reg:
                idx_reg = reg.lower()
                max_idx = pending_x if idx_reg == "x" else pending_y
                if max_idx is None:
                    continue
                # inc/dec with index still touch one byte at base+index
                extent = max_idx + 1
                if op == "sta" and "+1" in stripped and f"{sym}+1" in stripped.replace(" ", ""):
                    extent = max_idx + 2
                if "+1" in stripped and sym in stripped:
                    # e.g. sta rope_old_screen_pos+1,x
                    if re.search(rf"{re.escape(sym)}\s*\+\s*1\s*,\s*{idx_reg}", stripped, re.I):
                        extent = max_idx + 2
                if extent > base_size:
                    errors.append(
                        f"indexed spill: {loc} {op} {sym},{idx_reg} "
                        f"(max index {max_idx} -> {extent} B, declared {base_size} B)"
                    )
            elif op in ("inc", "dec"):
                pass  # single-byte by definition
            elif op == "sta" and re.search(rf"{re.escape(sym)}\s*\+\s*1", stripped, re.I):
                if 2 > base_size:
                    errors.append(
                        f"spill: {loc} sta {sym}+1 (2 B, declared {base_size} B)"
                    )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit JSW zero-page layout")
    parser.add_argument("--zp", type=Path, default=ROOT / "zp.asm")
    parser.add_argument("--asm", action="store_true", help="scan ASM for indexed ZP writes")
    parser.add_argument("--page100", action="store_true", default=True)
    parser.add_argument("--no-page100", action="store_true")
    args = parser.parse_args()

    symbols = parse_zp(args.zp)
    if not symbols:
        print(f"error: no equates in {args.zp}", file=sys.stderr)
        return 1

    regions = build_regions(symbols)
    print_map(regions)

    all_errors: list[str] = []
    all_warnings: list[str] = []

    all_errors.extend(check_overlaps(regions))
    all_errors.extend(check_clear_zone(regions))
    all_errors.extend(check_boot_boundary(regions))
    all_warnings.extend(check_kernal(regions))

    if not args.no_page100:
        print("Stack page tables:")
        all_errors.extend(check_stack_page(symbols))
        print()

    if args.asm:
        print("ASM symbol+1 clash scan:")
        plus1_errors = scan_plus1_clashes(symbols, ROOT)
        for e in plus1_errors:
            print(f"  {e}")
        all_errors.extend(plus1_errors)
        print()

        print("ASM indexed-writer scan:")
        asm_errors = scan_asm_writes(symbols, ROOT)
        for e in asm_errors:
            print(f"  {e}")
        all_errors.extend(asm_errors)
        print()

    if all_warnings:
        print("Warnings:")
        for w in all_warnings:
            print(f"  {w}")
        print()

    if all_errors:
        print(f"FAILED ({len(all_errors)} issue(s)):")
        for e in all_errors:
            print(f"  {e}")
        return 1

    print("OK - no ZP overlaps, clear-zone conflicts, or ASM spills reported")
    return 0


if __name__ == "__main__":
    sys.exit(main())
