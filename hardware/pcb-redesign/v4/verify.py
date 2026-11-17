#!/usr/bin/env python3
"""Validate the saved DAR-1000ES v4 design without modifying the project.

Run with KiCad 10's Python (pcbnew) and kicad-cli on PATH:
    /usr/bin/python3 hardware/pcb-redesign/v4/verify.py --reports v4-validation

For example, in a repository checkout on Linux:
    mkdir -p v4-validation-work
    docker run --rm --user "$(id -u):$(id -g)" -e HOME=/output \
      -v "$PWD:/workspace:ro" -v "$PWD/v4-validation-work:/output" \
      -w /workspace --entrypoint /usr/bin/python3 kicad/kicad:10.0.2 \
      hardware/pcb-redesign/v4/verify.py --reports /output/reports

Reports require a new directory. The mechanical checks use 2-D conservative
envelopes; they do not qualify the harness, RF/USB access, enclosure fit,
decoupling impedance, or hardware operation.
"""

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET


STEM = "DAR-1000ES-v4"
HERE = Path(__file__).resolve().parent
REFERENCE = HERE.parent / "reference"
BASELINE = HERE.parent / "baseline-v3"
IU = 1_000_000  # KiCad PCB integer units per mm
WIDTH, LENGTH, EXTENSION = 100 * IU, 300 * IU, 210 * IU
EDGE_REACH = 2 * IU  # maximum JST courtyard setback from its mating edge
BRIDGE_MAX = 15_240_000  # v4 checker policy, not a user-specified dimension
WIRE_RADIUS = 500_000  # assumed 1 mm insulated wire diameter
SCREW_RADIUS = 3 * IU  # assumed 6 mm M3 screwhead envelope
LINK_RE = re.compile(r"JW([1-9][0-9]*)")
HOLE_RE = re.compile(r"H[1-9][0-9]*")
CONNECTORS = tuple(f"J{n}" for n in range(2, 13))
CONTROL_CONNECTORS = tuple(f"J{n}" for n in range(3, 10))
AUDIO_CONNECTORS = ("J10", "J11")
ESP_REFS = ("U1-CONTROLLER1", "U6-AUDIO1")


class ValidationError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def json_file(path):
    return json.loads(path.read_text(encoding="utf-8"))


def cli(*args):
    command = ["kicad-cli", *(str(arg) for arg in args)]
    proc = subprocess.run(command, capture_output=True, text=True, timeout=300)
    require(proc.returncode == 0, f"{' '.join(command)} exited {proc.returncode}:\n"
            f"{proc.stdout}{proc.stderr}")
    return proc.stdout.strip()


def unique(records, label):
    result = {}
    for key, value in records:
        require(key not in result, f"Duplicate {label}: {key}")
        result[key] = value
    return result


def compare(actual, expected, label):
    if actual == expected:
        return
    missing = sorted(expected.keys() - actual.keys())
    extra = sorted(actual.keys() - expected.keys())
    changed = [(k, expected[k], actual[k]) for k in sorted(actual.keys() & expected.keys())
               if actual[k] != expected[k]]
    raise ValidationError(f"{label}: missing {len(missing)} {missing[:8]}, "
                          f"extra {len(extra)} {extra[:8]}, "
                          f"changed {len(changed)} (key, expected, actual) {changed[:8]}")


def read_netlist(path):
    root = ET.parse(path).getroot()
    components = unique(
        ((c.attrib["ref"], (c.findtext("value"), c.findtext("footprint")))
         for c in root.findall("./components/comp")), "schematic reference"
    )
    nets = unique(
        ((net.attrib["name"], net.findall("node")) for net in root.findall("./nets/net")),
        "net name",
    )
    pins = unique(
        (((node.attrib["ref"], node.attrib["pin"]), (name, node.get("pinfunction")))
         for name, nodes in nets.items() for node in nodes), "schematic pin"
    )
    require(components and pins, f"{path}: XML netlist is empty")
    require(all(ref in components for ref, _ in pins), f"{path}: unknown component on a net")
    return components, pins


def verify_power(pins):
    power = {
        ("J2", "1"): "GND", ("J2", "2"): "LOCAL_5V",
        ("J12", "1"): "GND", ("J12", "2"): "SONY_5V_SENSE",
        ("U10", "2"): "SONY_5V_SENSE", ("C8", "1"): "SONY_5V_SENSE", ("C8", "2"): "GND",
        ("JP1", "1"): "LOCAL_5V", ("JP1", "2"): "ESP_CTRL_5V",
        ("JP2", "1"): "LOCAL_5V", ("JP2", "2"): "ESP_AUDIO_5V",
        (ESP_REFS[0], "J1.21"): "ESP_CTRL_5V",
        (ESP_REFS[1], "J1.21"): "ESP_AUDIO_5V",
    }
    for ref, rail in (("C9", "LOCAL_5V"), ("C10", "ESP_CTRL_5V"), ("C11", "ESP_CTRL_5V"),
                      ("C12", "ESP_AUDIO_5V"), ("C13", "ESP_AUDIO_5V")):
        power[ref, "1"], power[ref, "2"] = rail, "GND"
    for pin, net in power.items():
        require(pins.get(pin) == net, f"{pin}: expected {net}, got {pins.get(pin)}")
    require({pin for pin, net in pins.items() if net == "SONY_5V_SENSE"} ==
            {("J12", "2"), ("U10", "2"), ("C8", "1")}, "Unexpected load on Sony 5 V sense")


def erc_signature(report):
    return Counter((v["type"], v["severity"])
                   for sheet in report["sheets"] for v in sheet["violations"])


def ignored(report):
    return {entry["key"] for entry in report["ignored_checks"]}


def same_checks(report, baseline, label):
    require(ignored(report) <= ignored(baseline),
            f"{label}: newly ignored checks: {sorted(ignored(report) - ignored(baseline))}")
    require(set(report["included_severities"]) >= {"error", "warning", "exclusion"},
            f"{label}: native report omitted one or more severity classes")


def verify_schematic(project, reports):
    sch = project / f"{STEM}.kicad_sch"
    netlist = reports / f"{STEM}-netlist.xml"
    erc_path = reports / f"{STEM}-ERC.json"
    cli("sch", "export", "netlist", "--format", "kicadxml", "-o", netlist, sch)
    cli("sch", "erc", "--format", "json", "--severity-all", "-o", erc_path, sch)
    expected_parts, expected_pins = read_netlist(REFERENCE / "pcb-v3-netlist.xml")
    parts, nodes = read_netlist(netlist)
    compare(parts, expected_parts, "Schematic refs/values/footprints vs golden v3")
    compare(nodes, expected_pins, "Schematic pins/nets/functions vs golden v3")
    pins = {pin: net for pin, (net, _) in nodes.items()}
    verify_power(pins)
    erc = json_file(erc_path)
    baseline = json_file(BASELINE / "DAR-1000ES-v3-ERC.json")
    same_checks(erc, baseline, "ERC")
    signature = erc_signature(erc)
    compare(signature, erc_signature(baseline), "ERC type/severity counts vs baseline")
    counts = Counter()
    for (kind, _), count in signature.items():
        counts[kind] += count
    return parts, pins, dict(sorted(counts.items()))


def xy(vector):
    return vector.x, vector.y


def bounds(box):
    return box.GetLeft(), box.GetTop(), box.GetRight(), box.GetBottom()


def union(boxes):
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


def overlaps(a, b):
    return a[0] <= b[2] and a[2] >= b[0] and a[1] <= b[3] and a[3] >= b[1]


def axis_gap(a, b):
    return max(b[0] - a[2], a[0] - b[2], b[1] - a[3], a[1] - b[3])


def box_mm(box):
    return tuple(round(v / IU, 4) for v in box)


def verify_outline(pcbnew, board):
    edge = pcbnew.Edge_Cuts
    shapes = [d for d in board.GetDrawings() if d.GetLayer() == edge]
    require(not any(g.GetLayer() == edge for f in board.GetFootprints()
                    for g in f.GraphicalItems()), "Footprint geometry on Edge.Cuts")
    require(all(isinstance(d, pcbnew.PCB_SHAPE) for d in shapes),
            "Unexpected non-shape Edge.Cuts geometry")
    corners = [(0, 0), (WIDTH, 0), (WIDTH, LENGTH), (0, LENGTH)]
    if len(shapes) == 1 and shapes[0].GetShape() == pcbnew.SHAPE_T_RECT:
        (x1, y1), (x2, y2) = xy(shapes[0].GetStart()), xy(shapes[0].GetEnd())
        require((min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)) ==
                (0, 0, WIDTH, LENGTH), f"Wrong Edge.Cuts rectangle: {box_mm((x1, y1, x2, y2))}")
        return
    expected = {frozenset((a, b)) for a, b in zip(corners, corners[1:] + corners[:1])}
    require(len(shapes) == 4 and all(d.GetShape() == pcbnew.SHAPE_T_SEGMENT for d in shapes)
            and {frozenset((xy(d.GetStart()), xy(d.GetEnd()))) for d in shapes} == expected,
            "Edge.Cuts must be one exact (0,0)–(100,300) mm rectangle, without extra cuts")


def load_board(pcbnew, path):
    # SWIG exposes the explicit jumper-group container only as an opaque
    # pointer. Check these syntax tokens outside quoted strings before loading.
    tokens = re.compile(r'"(?:[^"\\]|\\.)*"|\(\s*(?:jumper_pad_groups|net_tie_pad_groups)(?=[\s)])')
    require(not any(m[0].startswith("(") for m in tokens.finditer(path.read_text(encoding="utf-8"))),
            "Explicit jumper or net-tie groups are not permitted")
    board = pcbnew.LoadBoard(str(path))
    require(board is not None, "pcbnew failed to load v4 board")
    return board


def is_plated(pcbnew, pad):
    return (pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH and pad.HasDrilledHole()
            and pad.IsOnLayer(pcbnew.F_Cu) and pad.IsOnLayer(pcbnew.B_Cu))


def pad_map(pcbnew, footprints, parts, pins):
    actual = {}
    for ref, (value, footprint) in sorted(parts.items()):
        fp = footprints[ref]
        fpid = fp.GetFPID()
        require(fp.GetValue() == value, f"{ref}: board value {fp.GetValue()!r} != {value!r}")
        require(f"{fpid.GetLibNickname()}:{fpid.GetLibItemName()}" == footprint,
                f"{ref}: board footprint differs from schematic {footprint}")
        require(fp.GetLayer() == pcbnew.F_Cu and not fp.GetAttributes() & pcbnew.FP_BOARD_ONLY,
                f"{ref}: expected a top-mounted schematic footprint")
        require(not fp.GetDuplicatePadNumbersAreJumpers(), f"{ref}: unexpected board jumper equivalence")
        for pad in fp.Pads():
            require(is_plated(pcbnew, pad), f"{ref}.{pad.GetNumber()}: expected a plated THT pad")
            key = ref, pad.GetNumber()
            require(key not in actual, f"Duplicate schematic footprint pad {key}")
            actual[key] = pad.GetNetname()
    compare(actual, pins, "Board pads vs freshly exported schematic nets")


def body_envelope(pcbnew, fp):
    courtyard = fp.GetCourtyard(pcbnew.F_CrtYd)
    boxes = []
    for i in range(courtyard.OutlineCount()):
        outline = courtyard.Outline(i)
        points = [xy(outline.CPoint(j)) for j in range(outline.PointCount())]
        # KiCad's courtyard BBox includes the line stroke. Its centerline
        # polygon, rather than the display stroke, defines the envelope.
        boxes.extend((x, y, x, y) for x, y in points)
    # Include fab body shapes (the ESP footprints have separate socket courtyards)
    # and pad bounds, but do not use fab text as physical geometry.
    boxes += [bounds(g.GetBoundingBox()) for g in fp.GraphicalItems()
              if isinstance(g, pcbnew.PCB_SHAPE) and g.GetLayer() == pcbnew.F_Fab]
    boxes += [bounds(p.GetBoundingBox()) for p in fp.Pads()]
    require(boxes, f"{fp.GetReference()}: no measurable component envelope")
    return union(boxes)


def verify_connectors(pcbnew, footprints, bodies):
    regions = {}
    for ref in CONNECTORS:
        fp = footprints[ref]
        require(fp.GetCourtyard(pcbnew.F_CrtYd).OutlineCount(), f"{ref}: missing JST courtyard")
        x1, y1, x2, y2 = bodies[ref]
        require(0 <= x1 < x2 <= WIDTH and EXTENSION <= y1 < y2 <= LENGTH,
                f"{ref}: connector envelope {box_mm(bodies[ref])} outside the extension")
        # The preserved JST-XH horizontal footprint mates along local +Y.
        angle = fp.GetOrientationDegrees() % 360
        if angle == 0 and LENGTH - y2 <= EDGE_REACH:
            path = (x1, y2, x2, LENGTH)
            direction = (1, 0)
        elif angle == 90 and WIDTH - x2 <= EDGE_REACH:
            path = (x2, y1, WIDTH, y2)
            direction = (0, -1)
        elif angle == 270 and x1 <= EDGE_REACH:
            path = (0, y1, x1, y2)
            direction = (0, 1)
        else:
            raise ValidationError(f"{ref}: JST mouth not facing a nearby exterior edge "
                                  f"(angle={angle:g}°, envelope={box_mm(bodies[ref])})")
        positions = {pad.GetNumber(): xy(pad.GetPosition()) for pad in fp.Pads()}
        start = positions["1"]
        for n in range(1, len(positions) + 1):
            offset = (n - 1) * 2_500_000
            require(positions.get(str(n)) == (start[0] + direction[0] * offset,
                                             start[1] + direction[1] * offset),
                    f"{ref}: nonstandard JST-XH pitch or physical pin order")
        for other, body in bodies.items():
            if other != ref:
                require(not overlaps(path, body), f"{ref}: mating path obstructed by {other}")
        regions[ref] = path
    return regions


def top_silk(pcbnew, board, footprints):
    groups = [("board", board.GetDrawings())]
    groups += [(ref, list(fp.GraphicalItems()) + list(fp.GetFields()))
               for ref, fp in footprints.items()]
    for ref, items in groups:
        for item in items:
            if item.GetLayer() == pcbnew.F_SilkS and (
                    not hasattr(item, "IsVisible") or item.IsVisible()):
                yield ref, bounds(item.GetBoundingBox())


def verify_bridges(pcbnew, links, pins, obstructions, silk):
    require(links, "Expected at least one installed JW wire bridge")
    indices = sorted(int(LINK_RE.fullmatch(ref)[1]) for ref in links)
    require(indices == list(range(1, len(indices) + 1)), "JW references must be consecutive from JW1")
    lengths = {}
    link_regions = []
    valid_nets = {net for net, count in Counter(pins.values()).items() if count > 1}
    for ref in sorted(links, key=lambda r: int(LINK_RE.fullmatch(r)[1])):
        fp = links[ref]
        require(fp.GetLayer() == pcbnew.F_Cu and fp.GetAttributes() & pcbnew.FP_BOARD_ONLY,
                f"{ref}: expected a front-mounted board-only footprint")
        require(fp.GetDuplicatePadNumbersAreJumpers(),
                f"{ref}: expected only duplicate-pad-number jumper connectivity")
        pads = list(fp.Pads())
        require(len(pads) == 2 and all(is_plated(pcbnew, p) for p in pads),
                f"{ref}: expected exactly two plated through-hole terminals")
        first, second = pads
        require(first.GetNumber() and first.GetNumber() == second.GetNumber(),
                f"{ref}: terminal pad numbers must be identical and nonempty")
        net = first.GetNetname()
        require(net == second.GetNetname() and net in valid_nets,
                f"{ref}: expected both terminals on the same multi-pin schematic net")
        a, b = sorted((xy(p.GetPosition()) for p in pads), key=lambda point: point[1])
        length = b[1] - a[1]
        require(a[0] == b[0] and 0 < length <= BRIDGE_MAX,
                f"{ref}: not a short vertical bridge: {box_mm(a)} to {box_mm(b)} "
                f"(pitch limit {BRIDGE_MAX / IU:g} mm)")
        wire = (a[0] - WIRE_RADIUS, a[1] - WIRE_RADIUS,
                a[0] + WIRE_RADIUS, b[1] + WIRE_RADIUS)
        regions = [wire, *(bounds(p.GetBoundingBox()) for p in pads)]
        envelope = union(regions)
        require(0 < envelope[0] and envelope[2] < WIDTH and 0 < envelope[1] and envelope[3] < LENGTH,
                f"{ref}: terminal envelope outside board")
        for other, box in obstructions + link_regions:
            require(not any(overlaps(region, box) for region in regions),
                    f"{ref}: wire or terminal envelope intersects {other}")
        for owner, box in silk:
            require(owner == ref or not any(overlaps(region, box) for region in regions),
                    f"{ref}: wire or terminal envelope intersects {owner} top silkscreen")
        lengths[ref] = length / IU
        link_regions.extend((ref, region) for region in regions)
    return lengths


def verify_board(pcbnew, board, parts, pins):
    fps = unique(((f.GetReference(), f) for f in board.GetFootprints()), "board footprint reference")
    require(not (parts.keys() - fps.keys()),
            f"Missing schematic footprints: {sorted(parts.keys() - fps.keys())}")
    links = {}
    for ref in sorted(fps.keys() - parts.keys()):
        fp = fps[ref]
        if LINK_RE.fullmatch(ref):
            links[ref] = fp
            continue
        pads = list(fp.Pads())
        require(HOLE_RE.fullmatch(ref) and len(pads) == 1 and
                pads[0].GetAttribute() == pcbnew.PAD_ATTRIB_NPTH and pads[0].HasDrilledHole() and
                not pads[0].GetNetname() and fp.GetAttributes() & pcbnew.FP_BOARD_ONLY and
                not fp.GetDuplicatePadNumbersAreJumpers(),
                f"{ref}: unexpected board-only footprint (only NPTH mounting holes and JW allowed)")
    pad_map(pcbnew, fps, parts, pins)
    verify_outline(pcbnew, board)
    tracks = list(board.GetTracks())
    require(tracks, "No routed tracks")
    require(board.GetCopperLayerCount() == 2, "Expected a two-layer board stackup")
    require(not any(isinstance(t, pcbnew.PCB_VIA) for t in tracks), "Routing via found")
    require(all(t.GetLayer() == pcbnew.B_Cu for t in tracks), "Track found off B.Cu")
    require(not list(board.Zones()) and not any(list(fp.Zones()) for fp in fps.values()),
            "Unexpected zone; v4 uses B.Cu tracks rather than copper pours")
    require(not any(d.GetLayer() in (pcbnew.F_Cu, pcbnew.B_Cu) for d in board.GetDrawings()) and
            not any(g.GetLayer() in (pcbnew.F_Cu, pcbnew.B_Cu) for fp in fps.values()
                    for g in [*fp.GraphicalItems(), *fp.GetFields()]),
            "Unexpected copper graphic (could bypass B.Cu routing or jumper checks)")
    bodies = {ref: body_envelope(pcbnew, fps[ref]) for ref in sorted(parts)}
    esp_gap = axis_gap(*(bodies[ref] for ref in ESP_REFS))
    require(esp_gap > 0, "Controller/audio module envelopes overlap")
    for ref in sorted(fps.keys() - parts.keys() - links.keys()):
        pad = next(iter(fps[ref].Pads()))
        x, y = xy(pad.GetPosition())
        radius = max(SCREW_RADIUS, max(xy(pad.GetDrillSize())) // 2)
        bodies[ref] = (x - radius, y - radius, x + radius, y + radius)
    insertion = verify_connectors(pcbnew, fps, bodies)
    connector_gap = axis_gap(union([bodies[ref] for ref in CONTROL_CONNECTORS]),
                             union([bodies[ref] for ref in AUDIO_CONNECTORS]))
    require(connector_gap > 0, "Controller and audio connector group envelopes are not separated")
    obstructions = list(bodies.items()) + [(f"{ref} mating path", b) for ref, b in insertion.items()]
    lengths = verify_bridges(pcbnew, links, pins, obstructions, list(top_silk(pcbnew, board, fps)))
    summary = {
        "outline_mm": [WIDTH / IU, LENGTH / IU],
        "connector_envelopes_mm": {ref: box_mm(bodies[ref]) for ref in CONNECTORS},
        "connector_group_separation_along_axis_mm": connector_gap / IU,
        "esp_module_envelopes_mm": {ref: box_mm(bodies[ref]) for ref in ESP_REFS},
        "esp_envelope_separation_along_axis_mm": esp_gap / IU,
        "bottom_tracks": len(tracks),
        "front_tracks": 0,
        "vias": 0,
        "mounting_holes": len(fps) - len(parts) - len(links),
        "bridge_count": len(links),
        "max_bridge_mm": max(lengths.values()),
        "bridge_lengths_mm": lengths,
    }
    return links, summary


def drc(board_path, report_path):
    cli("pcb", "drc", "--format", "json", "--severity-all", "--all-track-errors",
        "-o", report_path, board_path)
    return json_file(report_path)


def verify_drc(pcbnew, board, links, project, reports):
    board_path = project / f"{STEM}.kicad_pcb"
    positive = drc(board_path, reports / f"{STEM}-DRC.json")
    same_checks(positive, json_file(BASELINE / "DAR-1000ES-v3-DRC.json"), "DRC")
    for key in ("violations", "schematic_parity"):
        require(not positive[key], f"Native DRC: {len(positive[key])} {key}; see {reports}")
    installed = len(positive["unconnected_items"])

    variant = reports / "without-installed-bridges"
    variant.mkdir()
    for name in (f"{STEM}.kicad_pro", f"{STEM}.kicad_dru", "fp-lib-table"):
        source = project / name
        if source.is_file():
            shutil.copyfile(source, variant / source.name)
    for library in project.glob("*.pretty"):
        if library.is_dir():
            shutil.copytree(library, variant / library.name)
    # Open the wires without deleting any pads or copper. Otherwise an open
    # could be caused by deleting the landing pad, not by removing the wire.
    for fp in links.values():
        fp.SetDuplicatePadNumbersAreJumpers(False)
    negative_path = variant / board_path.name
    require(pcbnew.SaveBoard(str(negative_path), board), "Could not save negative-test board")
    negative = drc(negative_path, reports / f"{STEM}-DRC-no-installed-bridges.json")
    missing = [item for item in negative["unconnected_items"] if item["severity"] == "error"]
    require(len(missing) > installed, "Opening all JW wires did not increase native DRC missing connections")
    return installed, len(missing)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", type=Path, default=HERE, help="v4 project directory")
    parser.add_argument("--reports", type=Path, required=True, help="new output directory")
    parser.add_argument("--schematic-only", action="store_true",
                        help="run schematic checks during bring-up; not full validation")
    args = parser.parse_args()
    project, reports = args.project.resolve(), args.reports.resolve()
    try:
        import pcbnew

        cli_version = cli("version")
        pcb_version = pcbnew.Version()
        require(cli_version.startswith("10.") and cli_version == pcb_version,
                f"Use a matching KiCad 10 CLI and pcbnew (found {cli_version!r}, {pcb_version!r})")
        required = [".kicad_pro", ".kicad_sch", "-interlock.kicad_sch", "-power.kicad_sch"]
        if not args.schematic_only:
            required.append(".kicad_pcb")
        for suffix in required:
            require((project / f"{STEM}{suffix}").is_file(), f"Missing input: {STEM}{suffix} in {project}")
        reports.mkdir(parents=True)
        parts, pins, erc = verify_schematic(project, reports)
        summary = {"kicad_version": cli_version, "schematic_pins_checked": len(pins),
                   "inherited_erc_review_items": erc, "mode": "schematic-only" if args.schematic_only else "full"}
        if not args.schematic_only:
            board = load_board(pcbnew, project / f"{STEM}.kicad_pcb")
            links, board_summary = verify_board(pcbnew, board, parts, pins)
            summary.update(board_summary)
            summary["native_drc_violations"] = 0
            installed, omitted = verify_drc(pcbnew, board, links, project, reports)
            summary["native_drc_unconnected"] = installed
            summary["negative_test_unconnected"] = omitted
        summary["review"] = "Inherited ERC issues remain; not electrical or fabrication sign-off."
        output = json.dumps(summary, indent=2) + "\n"
        (reports / "summary.json").write_text(output, encoding="utf-8")
        print(output, end="")
        require(not summary.get("native_drc_unconnected"),
                f"Native DRC: {summary.get('native_drc_unconnected')} unconnected items; see {reports}")
        return 0
    except (ValidationError, ImportError, OSError, ValueError, KeyError,
            RuntimeError, ET.ParseError, subprocess.TimeoutExpired) as exc:
        print(f"Verification failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
