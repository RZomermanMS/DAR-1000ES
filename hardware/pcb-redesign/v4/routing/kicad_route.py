#!/usr/bin/env python3
"""Export KiCad routing geometry or build a candidate from routing records.

Run with KiCad 10's Python. The input project is never overwritten.
"""

import argparse
from collections import Counter
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pcbnew as pcb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import verify


def mm(values):
    return tuple(value / verify.IU for value in values)


def point(x, y):
    return pcb.VECTOR2I(round(x * verify.IU), round(y * verify.IU))


def emit(kind, *values):
    print(kind, *(f"{value:.6f}".rstrip("0").rstrip(".") for value in values))


def routing_nets(footprints):
    """IDs depend on schematic pad names, not KiCad's load-order net codes."""
    counts = Counter(pad.GetNetname() for fp in footprints for pad in fp.Pads())
    return {name: index for index, name in enumerate(
        sorted(name for name, count in counts.items() if name and count > 1), 1)}


def obstacles(board, parts):
    bodies = {}
    for ref, footprint in parts.items():
        if verify.HOLE_RE.fullmatch(ref):
            x, y = verify.xy(footprint.GetPosition())
            r = verify.SCREW_RADIUS
            bodies[ref] = x - r, y - r, x + r, y + r
        else:
            bodies[ref] = verify.body_envelope(pcb, footprint)
    insertion = verify.verify_connectors(pcb, parts, bodies)
    # Planning envelopes, not dimensional approval: provide antenna and USB
    # access beyond the horizontal socket ends. No wire may cross them.
    module_access = [b for ref in verify.ESP_REFS for b in verify.module_access(parts[ref])]
    return [*bodies.values(), *insertion.values(), *module_access,
            *(bounds for _, bounds in verify.top_silk(pcb, board, parts))]


def export(board, fresh, channels=False):
    footprints = {fp.GetReference(): fp for fp in board.GetFootprints()}
    parts = {ref: fp for ref, fp in footprints.items() if not verify.LINK_RE.fullmatch(ref)}
    nets = routing_nets(parts.values())
    for name, net in nets.items():
        emit("width", net, 0.8 if name in POWER else 0.3)
    if channels:
        pins = {(ref, p.GetNumber()): p.GetNetname()
                for ref, fp in parts.items() for p in fp.Pads()}
        for name, channel in verify.functional_channels(pcb, parts, pins).items():
            if name in nets:
                emit("channel", nets[name], *mm(channel))
    for ref in sorted(parts):
        for pad in sorted(parts[ref].Pads(), key=lambda p: p.GetNumber()):
            x1, y1, x2, y2 = mm(verify.bounds(pad.GetBoundingBox()))
            emit("pad", nets.get(pad.GetNetname(), 0),
                 *mm(verify.xy(pad.GetPosition())), (x2-x1)/2, (y2-y1)/2)
    for box in obstacles(board, parts):
        emit("block", *mm(box))
    if fresh:
        return
    for track in board.GetTracks():
        if type(track) is not pcb.PCB_TRACK or track.GetLayer() != pcb.B_Cu:
            raise ValueError("Expected only B.Cu line segments")
        emit("segment", nets[track.GetNetname()], *mm(verify.xy(track.GetStart())),
             *mm(verify.xy(track.GetEnd())))
    for ref in sorted(footprints):
        if verify.LINK_RE.fullmatch(ref):
            a, b = sorted(footprints[ref].Pads(), key=lambda p: p.GetPosition().y)
            emit("bridge", nets[a.GetNetname()], *mm(verify.xy(a.GetPosition())),
                 *mm(verify.xy(b.GetPosition())))


POWER = {"LOCAL_5V", "GND", "ESP_CTRL_5V", "ESP_AUDIO_5V"}


def read_routes(routes):
    tracks, links = [], []
    for number, line in enumerate(routes.read_text().splitlines(), 1):
        fields = line.partition("#")[0].split()
        if not fields:
            continue
        kind, net, x, y, x2, y2 = fields
        a, b = point(float(x), float(y)), point(float(x2), float(y2))
        if kind == "segment" and a != b:
            tracks.append((int(net), a, b))
        elif kind == "bridge" and a.x == b.x and 2_540_000 <= abs(a.y-b.y) <= verify.BRIDGE_MAX:
            links.append((int(net), *sorted((a, b), key=lambda p: p.y)))
        else:
            raise ValueError(f"{routes}:{number}: invalid route record {line!r}")
    return tracks, sorted(links, key=lambda row: (row[1].y, row[1].x, row[2].y, row[0]))


def unroute(source, dest):
    """Keep the saved component placement but discard copper and old wires.

    KiCad's top-level blocks have exactly one tab of indentation. Recognize
    only these blocks; this also avoids removing SWIG-owned footprints.
    """
    text = source.read_text()
    chunks = re.split(r"(?m)(?=^\t\([a-z_]+(?:\s|\)))", text)
    chunks = [
        chunk for chunk in chunks
        if not chunk.startswith(("\t(segment", "\t(arc", "\t(via"))
        and not (chunk.startswith("\t(footprint")
                 and re.search(r'\(property\s+"Reference"\s+"JW[1-9][0-9]*"', chunk))
    ]
    dest.write_text("".join(chunks))
    board = verify.load_board(pcb, dest)
    if list(board.GetTracks()) or any(verify.LINK_RE.fullmatch(fp.GetReference())
                                     for fp in board.GetFootprints()):
        raise ValueError("Failed to remove old routes")
    return board


def build(source, routes, output, placement):
    tracks, links = read_routes(routes)
    output.mkdir()
    for child in source.parent.iterdir():
        if child.name in {"fp-lib-table", "sym-lib-table", "DAR1000ES.kicad_sym"} or child.suffix in {
            ".kicad_pro", ".kicad_sch", ".kicad_dru"
        }:
            shutil.copyfile(child, output / child.name)
    library = output / "DAR1000ES.pretty"
    shutil.copytree(source.parent / library.name, library, ignore=shutil.ignore_patterns("Vertical_Wire_*"))
    dest = output / source.name
    board = unroute(source, dest)
    if placement:
        place(board, placement)
        if any(line.partition("#")[0].strip() == "nand-reallocation"
               for line in placement.read_text().splitlines()):
            shutil.copyfile(Path(__file__).with_name("separated-interlock.kicad_sch"),
                            output / f"{source.stem}-interlock.kicad_sch")
    parts = {fp.GetReference(): fp for fp in board.GetFootprints()}
    blocked = obstacles(board, parts)
    nets = {i: board.FindNet(name) for name, i in routing_nets(parts.values()).items()}
    for net, a, b in tracks:
        track = pcb.PCB_TRACK(board)
        track.SetStart(a)
        track.SetEnd(b)
        track.SetLayer(pcb.B_Cu)
        track.SetWidth(800_000 if nets[net].GetNetname() in POWER else 300_000)
        track.SetNet(nets[net])
        board.Add(track)
    link_boxes = [(a.x-850_000, a.y-850_000, a.x+850_000, b.y+850_000) for _, a, b in links]
    schedule = ["Ref     X (mm)     Y1 (mm)    Y2 (mm)   Pitch (mm)  Net"]
    for i, (net, a, b) in enumerate(links, 1):
        pitch = (b.y-a.y)/verify.IU
        name = f"Vertical_Wire_{pitch:.6f}".rstrip("0").rstrip(".").replace(".", "p")+"mm"
        footprint_file = library / (name+".kicad_mod")
        if not footprint_file.exists():
            footprint_file.write_text(bridge_footprint(name, pitch))
        fp = pcb.FootprintLoad(str(library), name)
        fp.SetFPID(pcb.LIB_ID(library.stem, name))
        ref = f"JW{i}"
        fp.SetReference(ref)
        fp.SetPosition(a)
        board.Add(fp)
        for pad in fp.Pads():
            pad.SetNet(nets[net])
        label = fp.Reference()
        x, y, y2 = a.x/verify.IU, a.y/verify.IU, b.y/verify.IU
        positions = [(x+sign*dx, yy) for dx in (2.3, 2.9, 3.6, 4.5, 6)
                     for yy in ((y+y2)/2, y, y2) for sign in (1, -1)]
        for xx, yy in positions:
            label.SetPosition(point(xx, yy))
            box = verify.bounds(label.GetBoundingBox())
            if (500_000 < box[0] and 500_000 < box[1] and box[2] < 99_500_000
                    and box[3] < 299_500_000
                    and not any(verify.overlaps(box, ob) for ob in blocked+link_boxes)):
                blocked.append(box)
                break
        else:
            label.SetLayer(pcb.Dwgs_User)
            label.SetPosition(point(*positions[0]))
        schedule.append(f"{ref:<6} {x:9.4f}  {y:9.4f}  {y2:9.4f}  {pitch:9.4f}  {nets[net].GetNetname()}")
    if not pcb.SaveBoard(str(dest), board):
        raise RuntimeError(f"Unable to save {dest}")
    (output / "Wire-schedule.txt").write_text("\n".join(schedule)+"\n")


def trim_dangling(path):
    """Trim native-reported dead ends in a newly built candidate only."""
    with TemporaryDirectory(prefix="dar-drc-") as directory:
        report = Path(directory) / "drc.json"
        for _ in range(20):
            subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json",
                            "-o", str(report), str(path)], check=True)
            findings = json.loads(report.read_text())["violations"]
            if not findings:
                return
            if any(finding["type"] != "track_dangling" for finding in findings):
                raise ValueError(f"{path}: non-dangling DRC findings; inspect the candidate")
            uuids = {item["uuid"] for finding in findings for item in finding["items"]}
            board = pcb.LoadBoard(str(path))
            tracks = [t for t in board.GetTracks()
                      if type(t) is pcb.PCB_TRACK and t.m_Uuid.AsString() in uuids]
            if not tracks or len(tracks) != len(uuids):
                raise ValueError(f"{path}: not all reported items identified as track segments")
            for track in tracks:
                board.Remove(track)
            if not pcb.SaveBoard(str(path), board):
                raise RuntimeError(f"Unable to save {path}")
        raise ValueError(f"{path}: dangling track cleanup did not converge")


def bridge_footprint(name, pitch):
    points = [(-.35,-.85), (.35,-.85), (.85,-.35), (.85,.35),
              (.525,.68), (.525,pitch-.68), (.85,pitch-.35), (.85,pitch+.35),
              (.35,pitch+.85), (-.35,pitch+.85), (-.85,pitch+.35), (-.85,pitch-.35),
              (-.525,pitch-.68), (-.525,.68), (-.85,.35), (-.85,-.35)]
    polygon = " ".join(f"(xy {x:.6f} {y:.6f})" for x, y in points)
    return f'''(footprint "{name}"
 (version 20260206) (generator "pcbnew") (layer "F.Cu")
 (descr "Straight insulated component-side wire with two plated terminals")
 (property "Reference" "JW**" (at 2.8 {pitch/2:.6f}) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))
 (property "Value" "Insulated wire link" (at 0 0) (layer "F.Fab") (hide yes) (effects (font (size 1 1))))
 (attr through_hole board_only exclude_from_pos_files)
 (duplicate_pad_numbers_are_jumpers yes)
 (pad "1" thru_hole circle (at 0 0) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))
 (pad "1" thru_hole circle (at 0 {pitch:.6f}) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))
 (fp_poly (pts {polygon}) (stroke (width 0.05) (type solid)) (fill no) (layer "F.CrtYd"))
 (fp_line (start 0 0) (end 0 {pitch:.6f}) (stroke (width 0.23) (type solid)) (layer "Dwgs.User"))
 (fp_circle (center 0 0) (end 0.65 0) (stroke (width 0.18) (type solid)) (fill no) (layer "Dwgs.User"))
 (fp_circle (center 0 {pitch:.6f}) (end 0.65 {pitch:.6f}) (stroke (width 0.18) (type solid)) (fill no) (layer "Dwgs.User"))
)
'''


def place(board, placement):
    parts = {fp.GetReference(): fp for fp in board.GetFootprints()}
    for line in placement.read_text().splitlines():
        fields = line.partition("#")[0].split()
        if not fields:
            continue
        if fields == ["nand-reallocation"]:
            for (ref, number), name in verify.NAND_REALLOCATION.items():
                net = board.FindNet(name)
                if net is None:
                    net = pcb.NETINFO_ITEM(board, name)
                    board.Add(net)
                next(p for p in parts[ref].Pads() if p.GetNumber() == number).SetNet(net)
            continue
        if fields[0] == "label":
            _, x, y, text = line.split(maxsplit=3)
            label = next(d for d in board.GetDrawings()
                         if isinstance(d, pcb.PCB_TEXT) and d.GetText() == text)
            label.SetPosition(point(float(x), float(y)))
            continue
        ref, x, y, angle = fields
        if ref not in parts or verify.LINK_RE.fullmatch(ref):
            raise ValueError(f"Unknown placement reference {ref}")
        fp = parts[ref]
        fp.SetOrientationDegrees(float(angle))
        fp.SetPosition(point(float(x), float(y)))
    for ref, fp in parts.items():
        if not verify.HOLE_RE.fullmatch(ref):
            fp.BuildCourtyardCaches()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("board", type=Path)
    parser.add_argument("--fresh", action="store_true", help="Export only coarse and physical obstacles, no existing routes")
    parser.add_argument("--channels", action="store_true", help="Keep local nets out of the opposite functional block")
    parser.add_argument("--placement", type=Path, help="Override placement using ref x y angle records")
    parser.add_argument("--routes", type=Path, help="Build a candidate from these routing records")
    parser.add_argument("--output", type=Path, help="New candidate project directory")
    parser.add_argument("--trim-dangling", action="store_true", help="Trim native DRC dead-end segments in the candidate")
    args = parser.parse_args()
    if args.routes:
        if not args.output:
            parser.error("--routes requires --output")
        build(args.board, args.routes, args.output, args.placement)
        if args.trim_dangling:
            trim_dangling(args.output / args.board.name)
    else:
        if args.trim_dangling:
            parser.error("--trim-dangling requires --routes")
        if args.placement and not args.fresh:
            parser.error("--placement requires --fresh when exporting")
        board = verify.load_board(pcb, args.board)
        if args.placement:
            place(board, args.placement)
        export(board, args.fresh, args.channels)


if __name__ == "__main__":
    main()
