#!/usr/bin/env python3
"""Fail-closed ADR-0023 merge gate: upstream-map, 18 shelf pins, ADR evidence & manifests."""

from __future__ import annotations

import importlib
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SHELF_CANDIDATES = (
    ROOT.parent / "sota-upstream-shelf-lock" / "src",
    pathlib.Path("C:/sota-workstation/sota-upstream-shelf-lock/src"),
)
for cand in SHELF_CANDIDATES:
    if cand.is_dir() and str(cand) not in sys.path:
        sys.path.insert(0, str(cand))
        break


def main() -> int:
    try:
        mod = importlib.import_module("shelf_lock.hard_upstream_rule")
    except ModuleNotFoundError as exc:
        print(f"[MERGE-GATE FAIL] Missing sota-upstream-shelf-lock: {exc}", file=sys.stderr)
        return 1

    problems = [
        *mod.verify_upstream_map(ROOT),
        *mod.verify_adrs_have_evidence(ROOT),
        *mod.verify_sealed_manifests(ROOT),
        *mod.verify_shelf_pins_on_disk(),
    ]
    if problems:
        for p in problems:
            print(f"[MERGE-GATE FAIL] {p}", file=sys.stderr)
        return 1
    print(f"[MERGE-GATE PASS] {ROOT.name}: ADR-0023 upstream-map, shelf pins & ADRs verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
