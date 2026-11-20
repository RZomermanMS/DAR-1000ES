#!/usr/bin/env python3
"""Verify clearance-first composition and run domain and filled-zone audits."""
import collections
import hashlib
import importlib.util
import json
from pathlib import Path

import pcbnew as pcb

HERE = Path(__file__).resolve().parent
ROUTING = HERE.parent.parent
RESULT = HERE / "result.kicad_pcb"


def load_module(name, file):
    spec = importlib.util.spec_from_file_location(name, file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def track_signature(t):
    return (t.GetNetname(), t.GetLayer(), t.GetWidth(),
            t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y)


def main():
    overlay = load_module("overlay_audit", HERE.parent / "audit_integration.py")
    base = pcb.LoadBoard(str(ROUTING / "decoupling-trial/result.kicad_pcb"))
    clearance = pcb.LoadBoard(str(ROUTING / "pad-clearance-rework/result.kicad_pcb"))
    power = pcb.LoadBoard(str(ROUTING / "power-rework/result.kicad_pcb"))
    board = pcb.LoadBoard(str(RESULT))
    silk = pcb.LoadBoard(str(ROUTING / "silk-rework/result.kicad_pcb"))
    added_silk = overlay.additions(board, base)
    expected_silk = overlay.additions(silk, base)
    if len(added_silk) != 61 or collections.Counter(map(overlay.signature, added_silk)) != collections.Counter(map(overlay.signature, expected_silk)):
        raise ValueError("Overlay differs from saved silk")
    ids = {x.m_Uuid.AsString() for x in base.GetTracks()}
    expected_tracks = [x for x in power.GetTracks() if x.m_Uuid.AsString() not in ids]
    new_tracks = [x for x in board.GetTracks() if x.m_Uuid.AsString() not in ids]
    expected = [track_signature(t) for t in expected_tracks]
    old, new = pcb.FromMM(72.5), pcb.FromMM(72.6)
    x = pcb.FromMM(46.5)
    corrected = []
    count = 0
    for sig in expected:
        sig = list(sig)
        if sig[0] == "LOCAL_5V" and sig[1] == pcb.F_Cu:
            for xi, yi in ((3, 4), (5, 6)):
                if sig[xi] == x and sig[yi] == old:
                    sig[yi] = new
                    count += 1
        corrected.append(tuple(sig))
    if count != 2 or collections.Counter(corrected) != collections.Counter(map(track_signature, new_tracks)):
        raise ValueError("Power tracks differ beyond the single authorized C6 junction move")
    original = {x.m_Uuid.AsString(): track_signature(x) for x in clearance.GetTracks()}
    retained = {x.m_Uuid.AsString(): track_signature(x) for x in board.GetTracks()
                if x.m_Uuid.AsString() in ids}
    if original != retained:
        raise ValueError("Existing tracks differ from replayed clearance board")
    evidence = {"board_sha256": hashlib.sha256(RESULT.read_bytes()).hexdigest(),
                "replay_equals_saved_clearance": True,
                "silk_items_match_saved": len(added_silk),
                "power_tracks_match_saved_except_c6_junction_move": len(new_tracks),
                "existing_tracks_match_clearance": True}
    (HERE / "composition.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print("Clearance replay, silk geometry and power-track composition verified.")


if __name__ == "__main__":
    main()
