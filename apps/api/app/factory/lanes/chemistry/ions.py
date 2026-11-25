"""Ionic formulas from charges, two independent ways (criss-cross and search)."""

from __future__ import annotations

import math

from app.factory.lanes.chemistry import tables as T


def group(sym: str, count: int) -> str:
    """A symbol or a polyatomic group with its subscript, bracketed when it repeats."""
    if count == 1:
        return sym
    if sym in T.POLYATOMIC:
        return f"({sym}){count}"
    return f"{sym}{count}"


def formula_from_counts(cation: str, m: int, anion: str, n: int) -> str:
    return group(cation, m) + group(anion, n)


def crisscross(qc: int, qa: int) -> tuple[int, int]:
    """Swap the charge numbers, then divide both by their greatest common divisor."""
    g = math.gcd(qc, qa)
    return qa // g, qc // g


def search_smallest(qc: int, qa: int) -> tuple[int, int]:
    """The first (m, n) in order of m + n with m * qc == n * qa: no swapping used."""
    for total in range(2, 40):
        for m in range(1, total):
            n = total - m
            if m * qc == n * qa:
                return m, n
    raise ValueError("no neutral combination")


def exists(cation: str, qc: int, anion: str) -> bool:
    """Combinations kept out of the lane because the compound is not a school example."""
    if cation == "NH4" and anion in {"O", "S", "N", "PO4", "OH"}:
        return False
    if anion == "N":
        return cation in {"Mg", "Ca", "Al"}
    if cation == "Al" and anion in {"CO3", "S"}:
        return False
    if cation == "Fe" and qc == 3 and anion in {"CO3", "S"}:
        return False
    return not (cation == "Ag" and anion == "OH")
