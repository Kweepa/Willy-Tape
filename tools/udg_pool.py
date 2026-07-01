"""Canonical tile UDG pools with per-room index assignment."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from mkroom import tile_types_in_tilemap  # noqa: E402

# tileudg indices in mkroom room dict
TILE_FLOOR = 1
TILE_WALL = 2
TILE_NASTY = 3
TILE_RAMP = 4
TILE_BELT = 5
TILE_PICKUP = 6

# Default catalogue pool sizes (overrides may raise per type).
UDG_POOL_LIMITS: dict[int, int] = {
    TILE_FLOOR: 16,
    TILE_WALL: 16,
    TILE_NASTY: 16,
    TILE_RAMP: 8,
    TILE_BELT: 8,
    TILE_PICKUP: 32,
}

UDG_POOL_ORDER = (
    TILE_FLOOR,
    TILE_WALL,
    TILE_NASTY,
    TILE_RAMP,
    TILE_BELT,
    TILE_PICKUP,
)

UDG_INDEX_ORDER = (TILE_FLOOR, TILE_WALL, TILE_NASTY, TILE_RAMP, TILE_BELT, TILE_PICKUP)

UDG_INDEX_BYTES = 6  # per-room canonical indices (fixed)

SKIP_ROOM_IDS = frozenset({47})
REDIRECT_ROOM_PTR: dict[int, int] = {47: 0}

TYPE_NAMES = {
    TILE_FLOOR: "floor",
    TILE_WALL: "wall",
    TILE_NASTY: "nasty",
    TILE_RAMP: "ramp",
    TILE_BELT: "conveyor",
    TILE_PICKUP: "pickup",
}


def _pixel(data: bytes, row: int, col: int) -> int:
    if row < 0 or row > 7 or col < 0 or col > 7:
        return 0
    return (data[row] >> (7 - col)) & 1


def _ink_positions(data: bytes) -> list[tuple[int, int]]:
    return [(r, c) for r in range(8) for c in range(8) if _pixel(data, r, c)]


def udg_distance(a: bytes, b: bytes) -> int:
    """Lower is closer. Count mismatches; B-only ink penalised by dist to nearest A ink."""
    a = bytes(a[:8].ljust(8, b"\x00"))
    b = bytes(b[:8].ljust(8, b"\x00"))
    a_ink = _ink_positions(a)
    mismatches = 0
    missing_penalty = 0
    for r in range(8):
        for c in range(8):
            pa, pb = _pixel(a, r, c), _pixel(b, r, c)
            if pa == pb:
                continue
            mismatches += 1
            if pb and not pa:
                if a_ink:
                    missing_penalty += min(
                        abs(r - ar) + abs(c - ac) for ar, ac in a_ink
                    )
                else:
                    missing_penalty += 8
    return mismatches * 10 + missing_penalty


def pairwise_spread_score(chunks: list[bytes]) -> int:
    """Sum of udg_distance over every pair — higher means more visually distinct set."""
    total = 0
    for i in range(len(chunks)):
        for j in range(i + 1, len(chunks)):
            total += udg_distance(chunks[i], chunks[j])
    return total


def _normalise_chunk(chunk: bytes) -> bytes:
    return bytes(chunk[:8].ljust(8, b"\x00"))


def _unique_room_chunks(candidates: list[tuple[int, bytes]]) -> list[tuple[int, bytes]]:
    """First room id seen for each distinct byte pattern."""
    unique: list[tuple[int, bytes]] = []
    seen: set[bytes] = set()
    for rid, raw in candidates:
        chunk = _normalise_chunk(raw)
        if chunk not in seen:
            seen.add(chunk)
            unique.append((rid, chunk))
    return unique


def select_diverse_canonicals(
    candidates: list[tuple[int, bytes]], cap: int
) -> tuple[list[bytes], list[int]]:
    """Pick up to cap canonical UDGs maximising total pairwise spread.

    Returns (pool chunks, source room id per slot).
    """
    unique = _unique_room_chunks(candidates)
    if not unique:
        return [b"\x00" * 8] * cap, [-1] * cap

    chunks = [c for _rid, c in unique]
    k = min(cap, len(unique))
    if k == 1:
        selected_idx = [0]
    else:
        best_i, best_j, best_d = 0, 1, -1
        for i in range(len(chunks)):
            for j in range(i + 1, len(chunks)):
                d = udg_distance(chunks[i], chunks[j])
                if d > best_d:
                    best_i, best_j, best_d = i, j, d

        selected_idx = [best_i, best_j]
        while len(selected_idx) < k:
            best_c = -1
            best_gain = -1
            for c in range(len(chunks)):
                if c in selected_idx:
                    continue
                gain = sum(udg_distance(chunks[c], chunks[s]) for s in selected_idx)
                if gain > best_gain:
                    best_gain = gain
                    best_c = c
            selected_idx.append(best_c)

    chosen = [chunks[i] for i in selected_idx]
    sources = [unique[i][0] for i in selected_idx]
    while len(chosen) < cap:
        chosen.append(b"\x00" * 8)
        sources.append(-1)
    return chosen[:cap], sources[:cap]


def room_tile_types_used(room: dict) -> set[int]:
    """Tile type indices 1-6 present in gameplay tilemap (matches tileudg indices)."""
    return tile_types_in_tilemap(room["tilemap"])


def udg_defined(room: dict, tile_type: int) -> bool:
    if tile_type == TILE_PICKUP:
        return bool(room.get("itemudg_defined"))
    return bool(any(room["tileudg"][tile_type]))


def audit_unused_udg_definitions(rooms: list[dict]) -> list[str]:
    """Rooms with a UDG tag set for a tile type that does not appear in the tilemap."""
    labels = {
        TILE_FLOOR: "floor",
        TILE_WALL: "wall",
        TILE_NASTY: "nasty",
        TILE_RAMP: "ramp",
        TILE_BELT: "belt",
        TILE_PICKUP: "pickup",
    }
    lines: list[str] = []
    for room in rooms:
        rid = room["id"]
        if rid in SKIP_ROOM_IDS:
            continue
        used = room_tile_types_used(room)
        for tile_type, name in labels.items():
            if udg_defined(room, tile_type) and tile_type not in used:
                lines.append(f"room {rid}: @{name}udg defined but no {name} in tilemap")
    return lines


def load_canonical_overrides(path: Path | None) -> dict[int, dict[str, object]]:
    """Optional JSON: per tile-type count, include_rooms, exclude_rooms."""
    if path is None or not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    tag_to_type = {
        "floor": TILE_FLOOR,
        "wall": TILE_WALL,
        "nasty": TILE_NASTY,
        "ramp": TILE_RAMP,
        "belt": TILE_BELT,
        "conveyor": TILE_BELT,
        "pickup": TILE_PICKUP,
    }
    out: dict[int, dict[str, object]] = {}
    for key, spec in data.items():
        if key.startswith("_"):
            continue
        tile_type = tag_to_type.get(key.lower())
        if tile_type is None or not isinstance(spec, dict):
            continue
        entry: dict[str, object] = {}
        if "count" in spec:
            entry["count"] = int(spec["count"])
        for field in ("include_rooms", "exclude_rooms"):
            raw = spec.get(field, [])
            if isinstance(raw, list):
                entry[field] = [int(x) for x in raw]
        if entry:
            out[tile_type] = entry
    return out


def selection_limit_for(
    tile_type: int,
    overrides: dict[int, dict[str, object]],
    *,
    warnings: list[str] | None = None,
) -> int:
    """How many canonical UDGs to pick for a tile type (overrides may exceed defaults)."""
    default = UDG_POOL_LIMITS[tile_type]
    spec = overrides.get(tile_type, {})
    raw = spec.get("count")
    if raw is None:
        return default
    count = int(raw)
    if count < 1:
        if warnings is not None:
            warnings.append(f"{TYPE_NAMES[tile_type]}: count {count} < 1 — using 1")
        return 1
    return count


def pool_limit_for(tile_type: int, selection_limit: int) -> int:
    """Catalogue blob slots for a type (at least default, grows with override count)."""
    return max(UDG_POOL_LIMITS[tile_type], selection_limit)


def nearest_canonical_index(chunk: bytes, pool: list[bytes]) -> int:
    chunk = _normalise_chunk(chunk)
    return min(range(len(pool)), key=lambda i: udg_distance(chunk, pool[i]))


@dataclass
class UdgPool:
    limits: dict[int, int] = field(default_factory=lambda: dict(UDG_POOL_LIMITS))
    selection_limits: dict[int, int] = field(
        default_factory=lambda: dict(UDG_POOL_LIMITS)
    )
    canonical: dict[int, list[bytes]] = field(default_factory=dict)
    # tile_type -> source room id per canonical slot (-1 = padding)
    canonical_source: dict[int, list[int]] = field(default_factory=dict)
    # tile_type -> pool index -> room ids assigned to that slot
    rooms_by_index: dict[int, dict[int, list[int]]] = field(default_factory=dict)
    # (room_id, tile_type) -> pool index
    assignment: dict[tuple[int, int], int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    overrides: dict[int, dict[str, object]] = field(default_factory=dict)

    def selection_limit(self, tile_type: int) -> int:
        return self.selection_limits.get(tile_type, UDG_POOL_LIMITS[tile_type])

    def pool_limit(self, tile_type: int) -> int:
        return self.limits.get(tile_type, UDG_POOL_LIMITS[tile_type])

    def build(
        self,
        rooms: list[dict],
        *,
        flags_by_rid: dict[int, int],
        overrides_path: Path | None = None,
    ) -> None:
        self.canonical = {t: [] for t in self.limits}
        self.canonical_source = {t: [] for t in self.limits}
        self.rooms_by_index = {t: {} for t in self.limits}
        self.assignment = {}
        self.warnings = []
        self.overrides = load_canonical_overrides(overrides_path)
        self.selection_limits = {
            t: selection_limit_for(t, self.overrides, warnings=self.warnings)
            for t in UDG_POOL_ORDER
        }
        self.limits = {
            t: pool_limit_for(t, self.selection_limits[t]) for t in UDG_POOL_ORDER
        }
        for tile_type in UDG_POOL_ORDER:
            self._build_type(tile_type, rooms, flags_by_rid)
        self._rebuild_rooms_by_index()

    def _room_chunk(
        self, room: dict, tile_type: int, flags: int
    ) -> bytes | None:
        rid = room["id"]
        if rid in SKIP_ROOM_IDS:
            return None
        if tile_type not in room_tile_types_used(room):
            return None
        chunk = bytes(room["tileudg"][tile_type][:8])
        if not any(chunk):
            return None
        return chunk

    def _build_type(
        self, tile_type: int, rooms: list[dict], flags_by_rid: dict[int, int]
    ) -> None:
        cap = self.selection_limit(tile_type)
        needs: list[tuple[int, bytes]] = []
        for room in rooms:
            rid = room["id"]
            flags = flags_by_rid.get(rid, 0)
            chunk = self._room_chunk(room, tile_type, flags)
            if chunk is None:
                continue
            needs.append((rid, chunk))

        type_over = self.overrides.get(tile_type, {})
        exclude_rooms = set(type_over.get("exclude_rooms", []) or [])

        forced: list[tuple[int, bytes]] = []
        for rid in type_over.get("include_rooms", []) or []:
            match = next(((r, c) for r, c in needs if r == rid), None)
            if match is None:
                self.warnings.append(
                    f"include_rooms: room {rid} has no {tile_type} UDG — skipped"
                )
                continue
            chunk = _normalise_chunk(match[1])
            if not any(c == chunk for _r, c in forced):
                forced.append((rid, chunk))

        auto_candidates = [
            (rid, chunk)
            for rid, chunk in needs
            if rid not in exclude_rooms
            and not any(c == _normalise_chunk(chunk) for _r, c in forced)
        ]
        auto_cap = max(0, cap - len(forced))
        auto_pool, auto_sources = select_diverse_canonicals(auto_candidates, auto_cap)
        pool: list[bytes] = []
        sources: list[int] = []
        for rid, chunk in forced:
            if len(pool) >= cap:
                break
            pool.append(chunk)
            sources.append(rid)
        for chunk, src in zip(auto_pool, auto_sources):
            if len(pool) >= cap:
                break
            if chunk == b"\x00" * 8:
                continue
            if any(c == chunk for c in pool):
                continue
            pool.append(chunk)
            sources.append(src)

        while pool and pool[-1] == b"\x00" * 8 and len(pool) > 1:
            pool.pop()
            sources.pop()

        self.canonical[tile_type] = pool
        self.canonical_source[tile_type] = sources
        for rid, chunk in needs:
            self.assignment[(rid, tile_type)] = nearest_canonical_index(chunk, pool)

    def _rebuild_rooms_by_index(self) -> None:
        for tile_type in self.limits:
            self.rooms_by_index[tile_type] = {}
        for (rid, tile_type), idx in self.assignment.items():
            self.rooms_by_index[tile_type].setdefault(idx, []).append(rid)
        for tile_type in self.limits:
            for idx in self.rooms_by_index[tile_type]:
                self.rooms_by_index[tile_type][idx].sort()

    def index(self, rid: int, tile_type: int, *, flags: int = 0) -> int:
        if rid in SKIP_ROOM_IDS:
            return 0
        if self._room_chunk({"id": rid, "tileudg": {}}, tile_type, flags) is None:
            if tile_type in (TILE_FLOOR, TILE_WALL, TILE_PICKUP):
                return self.assignment.get((rid, tile_type), 0)
            return 0
        return self.assignment.get((rid, tile_type), 0)

    def pack_room_indices(self, rid: int, flags: int) -> bytes:
        out = bytearray()
        for tile_type in UDG_INDEX_ORDER:
            if tile_type in (TILE_NASTY, TILE_RAMP, TILE_BELT):
                if tile_type == TILE_NASTY and not (flags & 0x04):
                    out.append(0)
                    continue
                if tile_type == TILE_RAMP and not (flags & 0x08):
                    out.append(0)
                    continue
                if tile_type == TILE_BELT and not (flags & 0x10):
                    out.append(0)
                    continue
            out.append(self.assignment.get((rid, tile_type), 0) & 0xFF)
        return bytes(out)

    def pool_used(self, tile_type: int) -> int:
        return len(self.canonical.get(tile_type, []))

    def pool_blob(self) -> bytes:
        parts: list[bytes] = []
        for tile_type in UDG_POOL_ORDER:
            for chunk in self.canonical.get(tile_type, []):
                parts.append(chunk)
        return b"".join(parts)

    def pool_offsets(self) -> dict[int, int]:
        """Byte offset of each tile type within pool_blob (actual used slots only)."""
        offsets: dict[int, int] = {}
        pos = 0
        for tile_type in UDG_POOL_ORDER:
            offsets[tile_type] = pos
            pos += len(self.canonical.get(tile_type, [])) * 8
        return offsets

    def pool_bytes(self) -> int:
        return len(self.pool_blob())

    def stats(self) -> dict[str, int | float]:
        used = sum(len(v) for v in self.canonical.values())
        return {
            "pool_bytes": self.pool_bytes(),
            "canonical_used": used,
            "index_bytes": 6,  # per room
        }


def format_assignment_report(pool: UdgPool) -> str:
    lines: list[str] = [
        "Canonical UDG pool — room assignments",
        "(UDG bytes include ; invert from room files via parse_udg_bytes)",
        "",
    ]
    for tile_type in UDG_POOL_ORDER:
        default = UDG_POOL_LIMITS[tile_type]
        pool_cap = pool.pool_limit(tile_type)
        chosen = pool.selection_limit(tile_type)
        name = TYPE_NAMES[tile_type]
        cap_note = f"{chosen} chosen"
        if pool_cap > default:
            cap_note += f", pool {pool_cap} (default {default})"
        else:
            cap_note += f", pool {pool_cap}"
        lines.append(f"=== {name} ({cap_note}) ===")
        chunks = pool.canonical.get(tile_type, [])
        sources = pool.canonical_source.get(tile_type, [])
        by_idx = pool.rooms_by_index.get(tile_type, {})
        for i in range(chosen):
            if i >= len(chunks):
                lines.append(f"  [{i}] (unused slot)")
                continue
            src = sources[i] if i < len(sources) else -1
            rooms = by_idx.get(i, [])
            src_s = f"room {src}" if src >= 0 else "padding"
            if rooms:
                room_s = ", ".join(str(r) for r in rooms)
            else:
                room_s = "(none)"
            lines.append(f"  [{i}] from {src_s}  ->  rooms: {room_s}")
        lines.append("")
    if pool.warnings:
        lines.append("Warnings:")
        lines.extend(f"  - {w}" for w in pool.warnings)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
