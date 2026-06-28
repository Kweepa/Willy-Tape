#!/usr/bin/env python3
"""Audit dual title tune LH/RH harmony and register clashes."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.title_tune_convert import (  # noqa: E402
    BAR_LABELS,
    CHROMATIC,
    TITLE_BAR_COUNT,
    build_dual_tables,
    build_triplets_jsw,
    build_triplets_lh_bass,
    build_triplets_rh_arpeggios,
)


def pc(name: str) -> int:
    return CHROMATIC.index(name)


def fmt_notes(pitches: list[str], octaves: list[int]) -> str:
    return "-".join(f"{p}{o}" for p, o in zip(pitches, octaves))


def analyze_bar(
    lh_pitch: str,
    lh_o: list[int],
    rh_p: list[str],
    rh_o: list[int],
    lh_v: tuple[int, int, int],
    rh_v: tuple[int, int, int],
) -> list[str]:
    issues: list[str] = []
    bass = lh_pitch

    for p, o in zip(rh_p, rh_o):
        iv = (pc(p) - pc(bass)) % 12
        if iv in (1, 6):
            issues.append(
                f"RH {p}{o} is +{iv} semitones from LH {bass} (m2 or tritone)"
            )

    if bass == "B" and "G#" in rh_p and "D#" in rh_p:
        issues.append("LH B natural under G#-D#-F# (score uses B#/C for G#7)")

    # G#7 RH with B natural as the third (score: G#-B#-F# or G#-B#-D#)
    if "G#" in rh_p and "B" in rh_p and "F#" in rh_p:
        b_idx = rh_p.index("B")
        if rh_p.index("G#") < b_idx:
            issues.append(
                "RH G#-B-F# uses B natural (score: B# / C for G#7)"
            )

    # G#7 beat without F# (Kobayashi m4 beat 4): should not lead with F#
    if rh_p[0] == "F#" and "B" in rh_p and "D#" in rh_p and bass == "G#":
        issues.append(
            "RH F#-B-D# over G# bass (score m4 beat 4: G#-B#-D#, F# omitted)"
        )

    if min(rh_v) < lh_v[0] - 5:
        issues.append(
            f"register: RH low poke {min(rh_v)} below LH root poke {lh_v[0]}"
        )

    if rh_o == [4, 4, 4] and lh_o == [4, 5, 5]:
        if max(rh_v) < lh_v[1] - 3:
            issues.append(
                f"RH [4,4,4] top {max(rh_v)} under LH mid {lh_v[1]}"
            )

    return issues


def main() -> None:
    lh_lut, lh_ids, rh_lut, rh_ids, _ = build_dual_tables()
    lh_t = build_triplets_lh_bass()
    rh_t = build_triplets_rh_arpeggios()
    jsw = build_triplets_jsw()

    print("=== BAR-BY-BAR AUDIT ===\n")
    flagged: list[int] = []
    for bi in range(TITLE_BAR_COUNT):
        lh_pitch = lh_t[bi][1][0]
        lh_o = lh_t[bi][2]
        rh_p, rh_o = rh_t[bi][1], rh_t[bi][2]
        lv = lh_lut[lh_ids[bi]]
        rv = rh_lut[rh_ids[bi]]
        issues = analyze_bar(lh_pitch, lh_o, rh_p, rh_o, lv, rv)
        if issues:
            flagged.append(bi + 1)
            print(
                f"B{bi + 1:02d} {BAR_LABELS[bi]}  "
                f"LH {lh_pitch}{lh_o[0]}  RH {fmt_notes(rh_p, rh_o)}"
            )
            for msg in issues:
                print(f"    ! {msg}")
            print(f"    LH{lh_ids[bi]}={lv}  RH{rh_ids[bi]}={rv}")
            jsw_p, jsw_o = jsw[bi][1], jsw[bi][2]
            print(f"    JSW ref: {fmt_notes(jsw_p, jsw_o)}")
            print()

    print(f"Flagged {len(flagged)}/{TITLE_BAR_COUNT} bars: {flagged}\n")

    print("=== ALL UNIQUE LH/RH PAIRINGS ===")
    pairs: dict[tuple[int, int], list[int]] = {}
    for bi in range(TITLE_BAR_COUNT):
        key = (lh_ids[bi], rh_ids[bi])
        pairs.setdefault(key, []).append(bi + 1)
    for (lh, rh), bars in sorted(pairs.items()):
        bi = bars[0] - 1
        lp = lh_t[bi][1][0]
        rh_p = rh_t[bi][1]
        iss = analyze_bar(
            lp,
            lh_t[bi][2],
            rh_p,
            rh_t[bi][2],
            lh_lut[lh],
            rh_lut[rh],
        )
        mark = " ***" if iss else ""
        print(
            f"  LH{lh} RH{rh}  bars {bars}  "
            f"{lp} + {fmt_notes(rh_p, rh_t[bi][2])}{mark}"
        )
        for msg in iss:
            print(f"      ! {msg}")

    print("\n=== RH [4,4,4] VOICINGS ===")
    for bi in range(TITLE_BAR_COUNT):
        if rh_t[bi][2] == [4, 4, 4]:
            print(
                f"  B{bi + 1:02d} {BAR_LABELS[bi]}  "
                f"LH {lh_t[bi][1][0]}  RH {fmt_notes(rh_t[bi][1], rh_t[bi][2])}  "
                f"vic {rh_lut[rh_ids[bi]]}"
            )


if __name__ == "__main__":
    main()
