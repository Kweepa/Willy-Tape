#!/usr/bin/env python3
"""Tests for canonical UDG pool selection."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from udg_pool import (  # noqa: E402
    pairwise_spread_score,
    select_diverse_canonicals,
    udg_distance,
)


def test_pairwise_beats_random_triplet() -> None:
    a = bytes([0xFF, 0x00, 0xFF, 0x00, 0xFF, 0x00, 0xFF, 0x00])
    b = bytes([0x00, 0xFF, 0x00, 0xFF, 0x00, 0xFF, 0x00, 0xFF])
    c = bytes([0xAA, 0x55, 0xAA, 0x55, 0xAA, 0x55, 0xAA, 0x55])
    d = bytes(a)  # duplicate of a

    picked, _sources = select_diverse_canonicals(
        [(0, a), (1, b), (2, c), (3, d)], 3
    )
    score = pairwise_spread_score(picked)
    # Should pick a,b,c not a,a,c
    assert len(set(picked[:3])) == 3
    assert score > pairwise_spread_score([a, a, c])


def test_greedy_beats_all_same() -> None:
    chunks = [
        bytes([0x80, 0, 0, 0, 0, 0, 0, 0]),
        bytes([0, 0x80, 0, 0, 0, 0, 0, 0]),
        bytes([0, 0, 0, 0x80, 0, 0, 0, 0]),
        bytes([0, 0, 0, 0, 0x80, 0, 0, 0]),
    ]
    picked, _sources = select_diverse_canonicals(
        [(i, c) for i, c in enumerate(chunks)], 3
    )
    assert pairwise_spread_score(picked[:3]) >= udg_distance(chunks[0], chunks[1]) + udg_distance(
        chunks[0], chunks[2]
    )


if __name__ == "__main__":
    test_pairwise_beats_random_triplet()
    test_greedy_beats_all_same()
    print("ok")
