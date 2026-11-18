#!/usr/bin/env python3
"""Verify that the graphics-only derivative preserves routed copper."""
from pathlib import Path
import pcbnew as pcb

here = Path(__file__).resolve().parent
old = pcb.LoadBoard(str(here.parent / "esp-edge-candidate/result.kicad_pcb"))
new = pcb.LoadBoard(str(here / "result.kicad_pcb"))


def tracks(board):
    return sorted((t.m_Uuid.AsString(), t.GetClass(), t.GetNetname(), t.GetLayer(),
                   t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y,
                   t.GetWidth(pcb.F_Cu) if isinstance(t, pcb.PCB_VIA) else t.GetWidth(),
                   t.GetDrillValue() if isinstance(t, pcb.PCB_VIA) else 0)
                  for t in board.GetTracks())


if tracks(old) != tracks(new):
    raise ValueError("Source tracks or vias changed")
print("Source tracks and vias unchanged.")
