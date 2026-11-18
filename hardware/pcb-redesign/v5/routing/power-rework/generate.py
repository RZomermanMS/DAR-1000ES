#!/usr/bin/env python3
"""Generate a power-rework candidate from the preserved decoupling trial."""
from pathlib import Path
import json
import pcbnew as pcb

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "decoupling-trial" / "result.kicad_pcb"
OUTPUT = HERE / "result.kicad_pcb"


def main():
    board = pcb.LoadBoard(str(SOURCE))
    if len(list(board.Zones())) != 2 or any(not z.GetIsRuleArea() for z in board.Zones()):
        raise ValueError("unexpected source zones")
    ground = board.FindNet("GND")
    bridge = pcb.PCB_TRACK(board)
    bridge.SetStart(pcb.VECTOR2I(pcb.FromMM(50.24), pcb.FromMM(210)))
    bridge.SetEnd(pcb.VECTOR2I(pcb.FromMM(50.24), pcb.FromMM(212)))
    bridge.SetLayer(pcb.B_Cu)
    bridge.SetWidth(pcb.FromMM(0.3))
    bridge.SetNetCode(ground.GetNetCode())
    board.Add(bridge)
    footprints = {f.GetReference(): f for f in board.GetFootprints()}
    for route in json.loads((HERE / "supply-branches.json").read_text()):
        ref, pin = route["target"].split(".")
        source = next(p for p in footprints[route["cap"]].Pads() if p.GetNetname() != "GND")
        target = next(p for p in footprints[ref].Pads() if p.GetNumber() == pin)
        if source.GetNetname() != target.GetNetname():
            raise ValueError(f"wrong supply net for {route['cap']}")
        points = [pcb.VECTOR2I(pcb.FromMM(x), pcb.FromMM(y)) for x, y in route["points_mm"]]
        if points[0] != source.GetPosition() or points[-1] != target.GetPosition():
            raise ValueError(f"branch endpoints differ for {route['cap']}")
        for start, end in zip(points, points[1:]):
            track = pcb.PCB_TRACK(board)
            track.SetStart(start)
            track.SetEnd(end)
            track.SetLayer(board.GetLayerID(route["layer"]))
            track.SetWidth(pcb.FromMM(0.3))
            track.SetNetCode(source.GetNetCode())
            board.Add(track)
    for layer in (pcb.F_Cu, pcb.B_Cu):
        zone = pcb.ZONE(board)
        zone.SetLayer(layer)
        zone.SetNetCode(ground.GetNetCode())
        zone.SetLocalClearance(pcb.FromMM(0.25))
        zone.SetPadConnection(pcb.ZONE_CONNECTION_THERMAL)
        zone.SetThermalReliefGap(pcb.FromMM(0.25))
        zone.SetThermalReliefSpokeWidth(pcb.FromMM(0.25))
        zone.SetIslandRemovalMode(pcb.ISLAND_REMOVAL_MODE_ALWAYS)
        outline = zone.Outline()
        outline.NewOutline()
        for x, y in ((0.5, 0.5), (99.5, 0.5), (99.5, 299.5), (0.5, 299.5)):
            outline.Append(pcb.FromMM(x), pcb.FromMM(y))
        board.Add(zone)
    if not pcb.SaveBoard(str(OUTPUT), board):
        raise RuntimeError("could not save board")


if __name__ == "__main__":
    main()
