#!/usr/bin/env python3
"""Build title-screen Moonlight Sonata -> VIC-20 appendix F.

84 notes (28 triplets) + 255 — loop ends after m7 (cut before m8/m9).

Arrangements (set TITLE_ARRANGEMENT env or --arrangement):
  dual         — LH on $900a + RH on $900b via compressed triplet LUTs (default)
  rh_arpeggios — RH triplet arpeggios from score (Kobayashi / mfiles)
  lh_bass      — LH octave roots from score
  jsw          — original ZX Spectrum $85FB pitch classes

VIC poke is monotonic: lower value = lower pitch; semitone/octave up = larger value.
"""

from __future__ import annotations

import argparse
import os

TITLE_NOTE_COUNT = 84
TITLE_BAR_COUNT = TITLE_NOTE_COUNT // 3

CHROMATIC = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

ARRANGEMENT_SOURCES: dict[str, list[str]] = {
    "dual": [
        "https://hp.hisashikobayashi.com/wp-content/uploads/2019/06/"
        "AnAnalysisoftheArpeggios-RevisedinJune_20_2019.pdf",
        "https://www.mfiles.co.uk/scores/moonlight-movement1.pdf",
    ],
    "rh_arpeggios": [
        "https://hp.hisashikobayashi.com/wp-content/uploads/2019/06/"
        "AnAnalysisoftheArpeggios-RevisedinJune_20_2019.pdf",
        "https://www.mfiles.co.uk/scores/moonlight-movement1.pdf",
        "https://instrumentalfx.co/moonlight-sonata-sheet-music/",
    ],
    "lh_bass": [
        "https://hp.hisashikobayashi.com/wp-content/uploads/2019/06/"
        "AnAnalysisoftheArpeggios-RevisedinJune_20_2019.pdf",
        "https://www.mfiles.co.uk/scores/moonlight-movement1.pdf",
        "https://instrumentalfx.co/moonlight-sonata-sheet-music/",
    ],
    "jsw": [
        "https://skoolkit.ca/disassemblies/jet_set_willy/asm/34299.html",
        "http://jswremakes.emuunlim.com/Mmt/A%20Miner%20Triad.htm",
    ],
}

# Original ZX Spectrum Jet Set Willy title tune @ $85FB (trimmed to 84 bytes / B28).
JSW_SPEC_TUNE: list[int] = [
    0x51, 0x3C, 0x33, 0x51, 0x3C, 0x33, 0x51, 0x3C, 0x33, 0x51, 0x3C, 0x33,
    0x51, 0x3C, 0x33, 0x51, 0x3C, 0x33, 0x51, 0x3C, 0x33, 0x51, 0x3C, 0x33,
    0x4C, 0x3C, 0x33, 0x4C, 0x3C, 0x33, 0x4C, 0x39, 0x2D, 0x4C, 0x39, 0x2D,
    0x51, 0x40, 0x2D, 0x51, 0x3C, 0x33, 0x51, 0x3C, 0x36, 0x5B, 0x40, 0x36,
    0x66, 0x51, 0x3C, 0x51, 0x3C, 0x33, 0x51, 0x3C, 0x33, 0x28, 0x3C, 0x28,
    0x28, 0x36, 0x2D, 0x51, 0x36, 0x2D, 0x51, 0x36, 0x2D, 0x28, 0x36, 0x28,
    0x28, 0x3C, 0x33, 0x51, 0x3C, 0x33, 0x26, 0x3C, 0x2D, 0x4C, 0x3C, 0x2D,
]

# Richard Hallas tone chart (value, label); '#' = semitone between naturals.
CHART_ROWS: list[tuple[int, str]] = [
    (16, "C"),
    (17, "B"),
    (18, "#"),
    (19, "A"),
    (20, "#"),
    (22, "G"),
    (23, "#"),
    (24, "F"),
    (25, "E"),
    (27, "#"),
    (29, "D"),
    (31, "#"),
    (32, "C"),
    (34, "B"),
    (36, "#"),
    (38, "A"),
    (40, "#"),
    (43, "G"),
    (45, "#"),
    (48, "F"),
    (51, "E"),
    (54, "#"),
    (57, "D"),
    (60, "#"),
    (64, "C"),
    (68, "B"),
    (72, "#"),
    (76, "A"),
    (81, "#"),
    (86, "G"),
    (91, "#"),
    (96, "F"),
    (102, "E"),
    (108, "#"),
    (115, "D"),
    (121, "#"),
    (128, "C"),
]

BAR_LABELS: list[str] = [
    *["m1"] * 4,
    *["m2"] * 4,
    *["m3"] * 4,
    *["m4"] * 4,
    *["m5"] * 4,
    *["m6"] * 4,
    *["m7"] * 4,
]

# VIC-20 Programmer's Reference Guide, appendix F (rows low -> high pitch).
VIC_ROWS: list[dict[str, int]] = [
    {
        "C": 135,
        "C#": 143,
        "D": 147,
        "D#": 151,
        "E": 159,
        "F": 163,
        "F#": 167,
        "G": 175,
        "G#": 179,
        "A": 183,
        "A#": 187,
        "B": 191,
    },
    {
        "C": 195,
        "C#": 199,
        "D": 201,
        "D#": 203,
        "E": 207,
        "F": 209,
        "F#": 212,
        "G": 215,
        "G#": 217,
        "A": 219,
        "A#": 221,
        "B": 223,
    },
    {
        "C": 225,
        "C#": 227,
        "D": 228,
        "D#": 229,
        "E": 231,
        "F": 232,
        "F#": 233,
        "G": 235,
        "G#": 236,
        "A": 237,
        "A#": 238,
        "B": 239,
    },
]

OCTAVE_TO_ROW: dict[int, int] = {3: 0, 4: 1, 5: 2}

# Sustained root across three beats; oct 4/5/5 sits in voice-A row band ($900a).
LH_BASS_OCTAVES = [4, 5, 5]

# LH sustained octave roots per triplet beat (4 beats/measure, mm.1-9).
# Sources: Kobayashi Part A; instrumentalfx LH bass progression.
LH_BASS_TRIPLETS: list[tuple[str, str, list[int]]] = [
  # m1  LH C#-8ve
    *[( "m1", "C#", LH_BASS_OCTAVES)] * 4,
  # m2  LH B passing
    *[( "m2", "B",  LH_BASS_OCTAVES)] * 4,
  # m3  LH A then F# (RH VI -> D/F#)
    *(("m3", "A",  LH_BASS_OCTAVES),) * 2,
    *(("m3", "F#", LH_BASS_OCTAVES),) * 2,
  # m4  LH G#
    *(("m4", "G#", LH_BASS_OCTAVES),) * 4,
  # m5  LH C#-G#-C# (beat 4 G# from score)
    *(("m5", "C#", LH_BASS_OCTAVES),) * 3,
    ( "m5", "G#", LH_BASS_OCTAVES),
  # m6  LH B#-G#-B# alternation (B# = C on VIC; was B, sounded wrong at B21)
    ( "m6", "C",  LH_BASS_OCTAVES),
    ( "m6", "G#", LH_BASS_OCTAVES),
    ( "m6", "C",  LH_BASS_OCTAVES),
    ( "m6", "G#", LH_BASS_OCTAVES),
  # m7  LH C# then F# (RH return / F#m) — loop ends after B28
    *(("m7", "C#", LH_BASS_OCTAVES),) * 2,
    *(("m7", "F#", LH_BASS_OCTAVES),) * 2,
]

# RH triplet arpeggios mm.1-9 (low -> high within each triplet).
# Sources: Kobayashi Part A; mfiles score.
RH_ARPEGGIO_TRIPLETS: list[tuple[str, list[str], list[int]]] = [
    *[(f"m{1 if i < 4 else 2}", ["G#", "C#", "E"], [4, 5, 5]) for i in range(8)],
    ("m3", ["A", "C#", "E"], [4, 5, 5]),
    ("m3", ["A", "C#", "E"], [4, 5, 5]),
    ("m3", ["A", "D", "F#"], [4, 5, 5]),
    ("m3", ["A", "D", "F#"], [4, 5, 5]),
    ("m4", ["G#", "C", "F#"], [4, 4, 4]),
    ("m4", ["G#", "C#", "E"], [4, 5, 5]),
    ("m4", ["G#", "C#", "D#"], [4, 5, 5]),
    ("m4", ["G#", "C", "D#"], [4, 5, 5]),
    ("m5", ["E", "G#", "C#"], [4, 4, 5]),
    ("m5", ["G#", "C#", "E"], [4, 5, 5]),
    ("m5", ["G#", "C#", "E"], [4, 5, 5]),
    ("m5", ["G#", "C#", "E"], [4, 5, 5]),
    ("m6", ["G#", "D#", "F#"], [4, 5, 5]),
    ("m6", ["G#", "D#", "F#"], [4, 5, 5]),
    ("m6", ["G#", "D#", "F#"], [4, 5, 5]),
    ("m6", ["G#", "D#", "F#"], [4, 5, 5]),
    ("m7", ["G#", "C#", "E"], [4, 5, 5]),
    ("m7", ["G#", "C#", "E"], [4, 5, 5]),
    ("m7", ["A", "C#", "F#"], [4, 5, 5]),
    ("m7", ["A", "C#", "F#"], [4, 5, 5]),
]

DEFAULT_ARRANGEMENT = os.environ.get("TITLE_ARRANGEMENT", "dual")


def _build_hallas() -> dict[int, str]:
    out: dict[int, str] = {}
    for i, (val, label) in enumerate(CHART_ROWS):
        if label != "#":
            out[val] = label
            continue
        hi_name = None
        for j in range(i + 1, len(CHART_ROWS)):
            if CHART_ROWS[j][1] != "#":
                hi_name = CHART_ROWS[j][1]
                break
        if hi_name is None:
            raise ValueError(f"unresolved # at chart value {val}")
        out[val] = CHROMATIC[(CHROMATIC.index(hi_name) + 1) % 12]
    return out


HALLAS = _build_hallas()


def _nearest_spec(v: int) -> int:
    if v in HALLAS:
        return v
    return min(HALLAS, key=lambda k: abs(k - v))


def pitch_from_spec(v: int) -> str:
    return HALLAS[_nearest_spec(v)]


def midi_note(pitch: str, octave: int) -> int:
    return (octave + 1) * 12 + CHROMATIC.index(pitch)


def assign_octaves_jsw(pitches: list[str], spec_vals: list[int]) -> list[int]:
    octaves: list[int] = []
    prev_midi = -1
    for v, pitch in zip(spec_vals, pitches):
        if not octaves:
            octave = 4 if v >= 64 else 3
        else:
            octave = octaves[-1]
        midi = midi_note(pitch, octave)
        while midi <= prev_midi:
            octave += 1
            midi = midi_note(pitch, octave)
        if octave > 5:
            raise ValueError(f"voicing out of range: {list(zip(pitches, spec_vals))}")
        octaves.append(octave)
        prev_midi = midi
    return octaves


def build_triplets_jsw() -> list[tuple[str, list[str], list[int]]]:
    if len(JSW_SPEC_TUNE) != TITLE_NOTE_COUNT:
        raise ValueError(f"expected {TITLE_NOTE_COUNT} spec bytes, got {len(JSW_SPEC_TUNE)}")
    triplets: list[tuple[str, list[str], list[int]]] = []
    for t in range(TITLE_NOTE_COUNT // 3):
        spec = JSW_SPEC_TUNE[t * 3 : t * 3 + 3]
        pitches = [pitch_from_spec(v) for v in spec]
        octaves = assign_octaves_jsw(pitches, spec)
        triplets.append((BAR_LABELS[t], pitches, octaves))
    return triplets


def build_triplets_lh_bass() -> list[tuple[str, list[str], list[int]]]:
    if len(LH_BASS_TRIPLETS) != TITLE_NOTE_COUNT // 3:
        raise ValueError(
            f"expected {TITLE_NOTE_COUNT // 3} LH triplets, got {len(LH_BASS_TRIPLETS)}"
        )
    triplets: list[tuple[str, list[str], list[int]]] = []
    for bar, pitch, octaves in LH_BASS_TRIPLETS:
        triplets.append((bar, [pitch, pitch, pitch], octaves))
    return triplets


def build_triplets_rh_arpeggios() -> list[tuple[str, list[str], list[int]]]:
    if len(RH_ARPEGGIO_TRIPLETS) != TITLE_NOTE_COUNT // 3:
        raise ValueError(
            f"expected {TITLE_NOTE_COUNT // 3} RH triplets, "
            f"got {len(RH_ARPEGGIO_TRIPLETS)}"
        )
    return list(RH_ARPEGGIO_TRIPLETS)


def triplet_vic_bytes(
    triplets: list[tuple[str, list[str], list[int]]],
) -> list[tuple[int, int, int]]:
    out: list[tuple[int, int, int]] = []
    for _bar, pitches, octaves in triplets:
        regs = tuple(vic_for(p, o) for p, o in zip(pitches, octaves))
        out.append(regs)  # type: ignore[arg-type]
    return out


def dedupe_triplets(
    vic_triplets: list[tuple[int, int, int]],
) -> tuple[list[tuple[int, int, int]], list[int]]:
    """Return unique triplet LUT and per-bar indices into it."""
    lut: list[tuple[int, int, int]] = []
    rev: dict[tuple[int, int, int], int] = {}
    ids: list[int] = []
    for triplet in vic_triplets:
        if triplet not in rev:
            rev[triplet] = len(lut)
            lut.append(triplet)
        ids.append(rev[triplet])
    return lut, ids


def build_dual_tables() -> tuple[
    list[tuple[int, int, int]],
    list[int],
    list[tuple[int, int, int]],
    list[int],
    list[int],
]:
    lh_triplets = build_triplets_lh_bass()
    rh_triplets = build_triplets_rh_arpeggios()
    lh_vic = triplet_vic_bytes(lh_triplets)
    rh_vic = triplet_vic_bytes(rh_triplets)
    lh_lut, lh_ids = dedupe_triplets(lh_vic)
    rh_lut, rh_ids = dedupe_triplets(rh_vic)
    if len(lh_ids) != TITLE_BAR_COUNT or len(rh_ids) != TITLE_BAR_COUNT:
        raise ValueError("dual bar sequence length mismatch")
    bar_seq = [lh | (rh << 3) for lh, rh in zip(lh_ids, rh_ids)]
    return lh_lut, lh_ids, rh_lut, rh_ids, bar_seq


def build_triplets(arrangement: str) -> list[tuple[str, list[str], list[int]]]:
    if arrangement == "jsw":
        return build_triplets_jsw()
    if arrangement == "lh_bass":
        return build_triplets_lh_bass()
    if arrangement == "rh_arpeggios":
        return build_triplets_rh_arpeggios()
    if arrangement == "dual":
        return build_triplets_rh_arpeggios()
    raise ValueError(
        f"unknown arrangement: {arrangement!r} "
        "(use dual, rh_arpeggios, lh_bass, or jsw)"
    )


def active_arrangement() -> str:
    return DEFAULT_ARRANGEMENT


MOONLIGHT_TRIPLETS = build_triplets(active_arrangement())


def vic_for(pitch: str, octave: int) -> int:
    return VIC_ROWS[OCTAVE_TO_ROW[octave]][pitch]


def build_vic_tune(
    arrangement: str | None = None,
) -> list[int]:
    triplets = (
        MOONLIGHT_TRIPLETS
        if arrangement is None
        else build_triplets(arrangement)
    )
    out: list[int] = []
    for _bar, triplet, octaves in triplets:
        for pitch, octave in zip(triplet, octaves):
            out.append(vic_for(pitch, octave))
    out.append(255)
    return out


def triplet_table(
    arrangement: str | None = None,
) -> list[tuple[int, str, list[str], list[int], list[int]]]:
    triplets = (
        MOONLIGHT_TRIPLETS
        if arrangement is None
        else build_triplets(arrangement)
    )
    rows: list[tuple[int, str, list[str], list[int], list[int]]] = []
    for t, (bar, pitches, octaves) in enumerate(triplets, 1):
        regs = [vic_for(p, o) for p, o in zip(pitches, octaves)]
        rows.append((t, bar, pitches, octaves, regs))
    return rows


def title_triplet_ofs_entries(max_rh_voice: int) -> list[int]:
    """Shared index×3 table for LH (voices 0–6) and RH (voices 0–max)."""
    return [i * 3 for i in range(max_rh_voice + 1)]


def asm_dual_lines() -> list[str]:
    lh_lut, lh_ids, rh_lut, rh_ids, bar_seq = build_dual_tables()
    lh_triplets = build_triplets_lh_bass()
    rh_triplets = build_triplets_rh_arpeggios()
    max_rh_voice = max(rh_ids)
    ofs = title_triplet_ofs_entries(max_rh_voice)

    lines = [
        f"; Moonlight dual: LH->$900a RH->$900b, {len(lh_lut)}+{len(rh_lut)} unique triplets, "
        f"{TITLE_BAR_COUNT}-bar seq.",
        "title_bar_seq",
    ]
    for i, (_packed, lh, rh) in enumerate(zip(bar_seq, lh_ids, rh_ids)):
        bar = BAR_LABELS[i]
        lines.append(f"    !byte ({rh}<<3)+{lh}      ; B{i+1:02d} {bar}")
    lines.append("")
    lines.append("title_lh_triplets")
    for i, (a, b, c) in enumerate(lh_lut):
        bar, pitch, octaves = lh_triplets[next(j for j, lid in enumerate(lh_ids) if lid == i)]
        score = ",".join(f"{pitch}{o}" for o in octaves)
        lines.append(f"    !byte {a},{b},{c}       ; LH{i} {score}")
    lines.append("")
    lines.append("title_rh_triplets")
    for i, (a, b, c) in enumerate(rh_lut):
        bar, pitches, octaves = rh_triplets[next(j for j, rid in enumerate(rh_ids) if rid == i)]
        score = ",".join(f"{p}{o}" for p, o in zip(pitches, octaves))
        lines.append(f"    !byte {a},{b},{c}      ; RH{i} {score}")
    lines.append("")
    lines.append("title_rh_ofs")
    lines.append("    !byte " + ",".join(str(b) for b in ofs))
    return lines


def asm_triplet_lines(arrangement: str | None = None) -> list[str]:
    arr = arrangement or active_arrangement()
    if arr == "dual":
        return asm_dual_lines()
    tag = "LH" if arr == "lh_bass" else "RH"
    lines = ["title_tune_notes"]
    for t, bar, pitches, octaves, regs in triplet_table(arrangement):
        score = ",".join(f"{p}{o}" for p, o in zip(pitches, octaves))
        decs = ",".join(str(b) for b in regs)
        lines.append(f"    !byte {decs}      ; T{t:02d} {bar:3s}  {tag} {score}")
    lines.append("    !byte 255                ; END")
    return lines


def check_scale_monotonic() -> list[str]:
    bad: list[str] = []
    for row_idx, row in enumerate(VIC_ROWS):
        prev_midi = prev_vic = None
        for pitch in CHROMATIC:
            midi = midi_note(pitch, 3 + row_idx)
            vic = row[pitch]
            if prev_midi is not None and midi > prev_midi and vic <= prev_vic:
                bad.append(f"row {row_idx}: {pitch} vic {vic} <= {prev_vic}")
            prev_midi, prev_vic = midi, vic
    for pitch in CHROMATIC:
        for oct in (3, 4):
            v0 = vic_for(pitch, oct)
            v1 = vic_for(pitch, oct + 1)
            if v1 <= v0:
                bad.append(f"{pitch}{oct}->{oct + 1}: vic {v0}->{v1}")
    return bad


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate title-screen Moonlight tune")
    parser.add_argument(
        "--arrangement",
        choices=("dual", "rh_arpeggios", "lh_bass", "jsw"),
        default=active_arrangement(),
        help="dual | rh_arpeggios | lh_bass | jsw (default: TITLE_ARRANGEMENT env or dual)",
    )
    args = parser.parse_args()
    arrangement = args.arrangement

    titles = {
        "dual": "Moonlight title tune — dual LH+$900a RH+$900b (compressed)",
        "rh_arpeggios": "Moonlight title tune — RH score arpeggios",
        "lh_bass": "Moonlight title tune — LH bass octaves (score)",
        "jsw": "Moonlight title tune — JSW $85FB RH arpeggios",
    }
    print(titles[arrangement])
    print("VIC rule: lower poke = lower pitch; semitone/octave up = larger poke.")
    print("Sources:")
    for url in ARRANGEMENT_SOURCES.get(arrangement, ARRANGEMENT_SOURCES["dual"]):
        print(f"  {url}")
    bad = check_scale_monotonic()
    if bad:
        print("\nSCALE ERRORS:")
        for line in bad:
            print(f"  {line}")
    else:
        print("\nScale monotonicity OK")
    if arrangement == "dual":
        lh_lut, lh_ids, rh_lut, rh_ids, bar_seq = build_dual_tables()
        print()
        print(f"LH unique triplets: {len(lh_lut)}  RH unique triplets: {len(rh_lut)}")
        print(
            f"Data: {len(bar_seq)} + {len(lh_lut)*3} + {len(rh_lut)*3} = "
            f"{len(bar_seq) + len(lh_lut)*3 + len(rh_lut)*3} bytes"
        )
        print()
        for line in asm_dual_lines():
            print(line)
        return
    print()
    print(f"{'T':>3}  {'Score':^22}  {'VIC':^16}  Bar")
    print("-" * 56)
    for t, bar, pitches, octaves, regs in triplet_table(arrangement):
        score = "-".join(f"{p}{o}" for p, o in zip(pitches, octaves))
        decs = ",".join(f"{r:3d}" for r in regs)
        print(f"{t:3d}  {score:22s}  {decs:16s}  {bar}")
    print()
    for line in asm_triplet_lines(arrangement):
        print(line)


if __name__ == "__main__":
    main()
