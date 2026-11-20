#!/usr/bin/env python3
"""Add a guarded, board-level F.SilkS overlay to the v5 routed PCB (KiCad 10)."""
import argparse
import importlib.util
from pathlib import Path

import pcbnew as pcb

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("board_ops", HERE.parent / "placement-trial" / "board_ops.py")
ops = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ops)

# Pin order and positions are part of the artwork's meaning. Fail closed if a
# future candidate moves a connector or changes its electrical assignments.
CONNECTORS = {
    "J2": (15, 9.7, 180, ["GND", "LOCAL_5V"]),
    "J12": (39, 9.7, 180, ["GND", "SONY_5V_SENSE"]),
    "J3": (9.8, 32, -90, ["GND", "/FLGDATA", "/FLGCLK", "/FLCLEAR"]),
    "J4": (9.8, 51, -90, ["/FLSTB", "/FLSDATA", "/FLSCLK"]),
    "J5": (9.8, 70, -90, ["GND", "/OUT0", "/OUT1", "/OUT2"]),
    "J6": (9.8, 89, -90, ["/IN0", "/IN1", "/IN2", "/IN3"]),
    "J7": (9.8, 121, -90, ["/IN4", "/IN5", "/IN6", "/IN7"]),
    "J8": (9.8, 140, -90, ["/OUT3", "/OUT4", "/OUT5"]),
    "J9": (9.8, 180, -90, ["GND", "/A.MUTE", "/D.MUTE", "/RELAY"]),
    "J10": (9.8, 218, -90, ["GND", "/ATT", "/SHIFT", "/LATCH", "/INIT"]),
    "J11": (9.8, 240, -90, ["GND", "/BCKI", "/DATA", "/LRCK"]),
    "JP1": (59, 95, 0, ["LOCAL_5V", "ESP_CTRL_5V"]),
    "JP2": (59, 255, 0, ["LOCAL_5V", "ESP_AUDIO_5V"]),
}

# (text, centre x/y, angle, character height/width). All dimensions mm.
TEXTS = [
    ("CONTROLLER", 50, 145, 0, 1.8),
    ("AUDIO", 50, 155, 0, 1.8),
    ("LOCAL 5V", 14, 16, 0, 1.0),
    ("SONY 5V SENSE", 39, 16, 0, 1.0),
    ("1 GND", 18.2, 32, 0, 0.8),
    ("2 FLGDATA", 18.2, 34.5, 0, 0.8),
    ("3 FLGCLK", 18.2, 37, 0, 0.8),
    ("4 FLCLEAR", 18.2, 39.5, 0, 0.8),
    ("1 FLSTB", 18.2, 51, 0, 0.8),
    ("2 FLSDATA", 18.2, 53.5, 0, 0.8),
    ("3 FLSCLK", 18.2, 56, 0, 0.8),
    ("1 GND", 18.2, 70, 0, 0.8),
    ("2 OUT0", 18.2, 72.5, 0, 0.8),
    ("3 OUT1", 18.2, 75, 0, 0.8),
    ("4 OUT2", 18.2, 77.5, 0, 0.8),
    ("1 IN0", 18.2, 89, 0, 0.8),
    ("2 IN1", 18.2, 91.5, 0, 0.8),
    ("3 IN2", 18.2, 94, 0, 0.8),
    ("4 IN3", 18.2, 96.5, 0, 0.8),
    ("1 IN4", 16.65, 122, 0, 0.8),
    ("2 IN5", 16.65, 123.75, 0, 0.8),
    ("3 IN6", 16.65, 126, 0, 0.8),
    ("4 IN7", 16.65, 128.5, 0, 0.8),
    ("1 OUT3", 17.4, 140, 0, 0.8),
    ("2 OUT4", 17.4, 142.5, 0, 0.8),
    ("3 OUT5", 17.4, 145, 0, 0.8),
    ("1 GND", 18.2, 180, 0, 0.8),
    ("2 A.MUTE", 18.2, 182.5, 0, 0.8),
    ("3 D.MUTE", 18.2, 185, 0, 0.8),
    ("4 RELAY", 18.2, 187.5, 0, 0.8),
    ("1 GND", 18.2, 218, 0, 0.8),
    ("2 ATT", 18.2, 220.5, 0, 0.8),
    ("3 SHIFT", 18.2, 223, 0, 0.8),
    ("4 LATCH", 18.2, 225.5, 0, 0.8),
    ("5 INIT", 18.2, 228, 0, 0.8),
    ("1 GND", 18.2, 240, 0, 0.8),
    ("2 BCKI", 18.2, 242.5, 0, 0.8),
    ("3 DATA", 18.2, 245, 0, 0.8),
    ("4 LRCK", 18.2, 247.5, 0, 0.8),
    ("1 GND", 21.3, 9.7, 0, 0.8),
    ("1 GND", 45.3, 9.7, 0, 0.8),
    ("2 5V", 6.5, 9.7, 0, 0.8),
    ("2 SENSE", 29.5, 9.7, 0, 0.8),
    ("1 LOCAL", 65, 95, 0, 0.8),
    ("2 CTRL", 65, 97.54, 0, 0.8),
    ("1 LOCAL", 65, 255, 0, 0.8),
    ("2 AUDIO", 65, 257.54, 0, 0.8),
    ("J2  1 GND  2 LOCAL_5V", 25, 286, 0, 1.0),
    ("J12  1 GND  2 SONY_5V_SENSE", 25, 287.9, 0, 1.0),
    ("J3  1 GND  2 FLGDATA  3 FLGCLK  4 FLCLEAR", 25, 289.8, 0, 1.0),
    ("J4  1 FLSTB  2 FLSDATA  3 FLSCLK", 25, 291.7, 0, 1.0),
    ("J5  1 GND  2 OUT0  3 OUT1  4 OUT2", 25, 293.6, 0, 1.0),
    ("J6  1 IN0  2 IN1  3 IN2  4 IN3", 25, 295.5, 0, 1.0),
    ("J7  1 IN4  2 IN5  3 IN6  4 IN7", 25, 297.4, 0, 1.0),
    ("J8  1 OUT3  2 OUT4  3 OUT5", 75, 286, 0, 1.0),
    ("J9  1 GND  2 A.MUTE  3 D.MUTE  4 RELAY", 75, 287.9, 0, 1.0),
    ("J10  1 GND  2 ATT  3 SHIFT  4 LATCH  5 INIT", 75, 289.8, 0, 1.0),
    ("J11  1 GND  2 BCKI  3 DATA  4 LRCK", 75, 291.7, 0, 1.0),
    ("JP1  1 LOCAL_5V  2 ESP_CTRL_5V", 75, 293.6, 0, 1.0),
    ("JP2  1 LOCAL_5V  2 ESP_AUDIO_5V", 75, 295.5, 0, 1.0),
]


def point(x, y):
    return pcb.VECTOR2I(pcb.FromMM(x), pcb.FromMM(y))


def check_connectors(board):
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    for ref, (x, y, angle, nets) in CONNECTORS.items():
        fp = fps[ref]
        if (fp.GetPosition() != point(x, y) or
                abs((fp.GetOrientationDegrees() - angle + 180) % 360 - 180) > 0.001):
            raise ValueError(f"{ref} has moved or rotated; redesign overlay")
        pads = {p.GetNumber(): p.GetNetname() for p in fp.Pads()}
        if pads != {str(i + 1): net for i, net in enumerate(nets)}:
            raise ValueError(f"{ref} pin map changed: {pads}")
        for pad in fp.Pads():
            index = int(pad.GetNumber()) - 1
            expected = (point(x - 2.5 * index, y) if ref in ("J2", "J12")
                        else point(x, y + (2.54 if ref.startswith("JP") else 2.5) * index))
            if pad.GetPosition() != expected:
                raise ValueError(f"{ref}.{pad.GetNumber()} pad moved; redesign overlay")


def rect(box, margin=0):
    m = pcb.FromMM(margin)
    return (box.GetX() - m, box.GetY() - m, box.GetRight() + m, box.GetBottom() + m)


def overlaps(a, b):
    return a[0] <= b[2] and a[2] >= b[0] and a[1] <= b[3] and a[3] >= b[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("netlist", type=Path)
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve() or args.output.exists():
        raise ValueError("Output must be a new file, distinct from input")
    board = pcb.LoadBoard(str(args.input))
    ops.verify_netlist(board, str(args.netlist))
    ops.verify_uart(str(args.netlist))
    ops.audit_sections(board, 150, "lower")
    ops.audit_component_envelopes(board, 150, "lower")
    check_connectors(board)
    existing = {g.GetText() for g in board.GetDrawings() if isinstance(g, pcb.PCB_TEXT)}
    if existing.intersection(t[0] for t in TEXTS):
        raise ValueError("Overlay labels already present")
    additions = []
    for text, x, y, angle, size in TEXTS:
        item = pcb.PCB_TEXT(board)
        item.SetLayer(pcb.F_SilkS)
        item.SetText(text)
        item.SetPosition(point(x, y))
        item.SetTextSize(point(size, size))
        item.SetTextThickness(pcb.FromMM(0.12 if size == 0.8 else (0.15 if size == 1.0 else 0.25)))
        item.SetTextAngle(pcb.EDA_ANGLE(angle, pcb.DEGREES_T))
        additions.append(item)
    line = pcb.PCB_SHAPE(board)
    line.SetShape(pcb.SHAPE_T_SEGMENT)
    line.SetStart(point(1, 150))
    line.SetEnd(point(99, 150))
    line.SetWidth(pcb.FromMM(0.2))
    line.SetLayer(pcb.F_SilkS)
    additions.append(line)
    courts = [(f.GetReference(), rect(f.GetCourtyard(pcb.F_CrtYd).BBox(), 0.2))
              for f in board.GetFootprints()]
    pads = [(f"{f.GetReference()}.{p.GetNumber()}", rect(p.GetBoundingBox(), 0.3))
            for f in board.GetFootprints() for p in f.Pads()]
    references = [(f.GetReference(), rect(f.Reference().GetBoundingBox()))
                  for f in board.GetFootprints()
                  if f.Reference().IsVisible() and f.Reference().GetLayer() == pcb.F_SilkS]
    # Conservative bounding boxes avoid both courtyard interiors and pad masks;
    # native DRC additionally checks the actual silk against mask and silk.
    for i, item in enumerate(additions):
        box = rect(item.GetBoundingBox())
        if box[0] < pcb.FromMM(0.2) or box[1] < pcb.FromMM(0.2) or box[2] > pcb.FromMM(99.8) or box[3] > pcb.FromMM(299.8):
            raise ValueError(f"Overlay item {i} is too close to the board edge")
        for ref, court in courts:
            if overlaps(box, court):
                raise ValueError(f"Overlay item {i} overlaps {ref} courtyard + 0.2 mm")
        for ref, pad in pads:
            if overlaps(box, pad):
                raise ValueError(f"Overlay item {i} overlaps {ref} pad + 0.3 mm")
        for ref, reference in references:
            if overlaps(box, reference):
                raise ValueError(f"Overlay item {i} overlaps {ref} reference")
        for other in additions[:i]:
            if overlaps(box, rect(other.GetBoundingBox(), 0.2)):
                raise ValueError(f"Overlay items overlap: {i}")
    for item in additions:
        board.Add(item)
    pcb.SaveBoard(str(args.output), board)
    print(f"Added {len(TEXTS)} labels and boundary; checked {len(courts)} courtyards.")


if __name__ == "__main__":
    main()
