#!/usr/bin/env python3
"""Generate an unrouted v5 synchronization candidate with KiCad 10.

Run from any directory: python3 hardware/pcb-redesign/v5/sync_pcb.py
Requires Docker and the local kicad/kicad:10.0.2 image. Never overwrites an
existing output. New parts are deliberately staged outside the board outline.
The result is not a placement, routing, DRC, or manufacturing approval.
"""
import collections
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUTPUT = HERE / "routing" / "synchronized.kicad_pcb"
IMAGE = "kicad/kicad:10.0.2"


def run(command):
    return subprocess.run(command, check=True, text=True, capture_output=True)


def docker(*args):
    return ["docker", "run", "--rm", "--network", "none", *args, IMAGE]


def parity(board=OUTPUT):
    # Mount files individually so the board has the schematic's project name
    # without creating or changing any project files in the repository.
    command = docker(
        "-v", f"{board}:/project/DAR-1000ES-v5.kicad_pcb:ro",
        "-v", f"{HERE / 'DAR-1000ES-v5.kicad_sch'}:/project/DAR-1000ES-v5.kicad_sch:ro",
        "-v", f"{HERE / 'DAR-1000ES-v5-power.kicad_sch'}:/project/DAR-1000ES-v5-power.kicad_sch:ro",
        "-v", f"{HERE / 'DAR-1000ES-v5-interlock.kicad_sch'}:/project/DAR-1000ES-v5-interlock.kicad_sch:ro",
        "-v", f"{HERE / 'DAR-1000ES-v5.kicad_pro'}:/project/DAR-1000ES-v5.kicad_pro:ro",
        "-v", f"{HERE / 'fp-lib-table'}:/project/fp-lib-table:ro",
        "-v", f"{HERE / 'DAR1000ES.pretty'}:/project/DAR1000ES.pretty:ro",
        "-w", "/project",
    ) + ["kicad-cli", "pcb", "drc", "--schematic-parity", "--severity-all",
         "--format", "json", "-o", "/dev/stdout", "DAR-1000ES-v5.kicad_pcb"]
    result = run(command)
    # KiCad prints progress before its JSON report.
    report, _ = json.JSONDecoder().raw_decode(result.stdout[result.stdout.index("{"):])
    return report


def canonical(root):
    components = {}
    for c in root.findall("./components/comp"):
        ref = c.get("ref")
        if not ref or ref in components:
            raise ValueError(f"missing or duplicate reference {ref}")
        sheet = c.find("sheetpath").get("tstamps")
        ids = c.findtext("tstamps", "").split()
        if not sheet or not ids:
            raise ValueError(f"missing UUID path for {ref}")
        fields = tuple(sorted((f.get("name"), f.text or "") for f in c.findall("./fields/field")))
        if any(not name for name, _ in fields) or len(dict(fields)) != len(fields):
            raise ValueError(f"invalid schematic fields for {ref}")
        components[ref] = (c.findtext("value"), c.findtext("footprint"), sheet, tuple(ids), fields)
    nodes = {}
    names = set()
    for net in root.findall("./nets/net"):
        name = net.get("name")
        if not name or name in names:
            raise ValueError(f"missing or duplicate net name {name}")
        names.add(name)
        for node in net.findall("node"):
            key = (node.get("ref"), node.get("pin"))
            if key in nodes or key[0] not in components or not key[1]:
                raise ValueError(f"invalid or duplicate netlist node {key}")
            nodes[key] = name
    if not components or not nodes:
        raise ValueError("empty schematic netlist")
    return components, nodes


def worker():
    import pcbnew as pcb

    netlist = HERE / "DAR-1000ES-v5.net.xml"
    expected = canonical(ET.parse(netlist).getroot())
    fresh = run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadxml",
                 "-o", "/dev/stdout", str(HERE / "DAR-1000ES-v5.kicad_sch")])
    if canonical(ET.fromstring(fresh.stdout)) != expected:
        raise ValueError("XML netlist is stale or differs from the native schematic export")
    components, nodes = expected
    board = pcb.LoadBoard(str(ROOT / "reference" / "pcb-v3-placement-base.kicad_pcb"))
    if board is None or list(board.GetTracks()) or list(board.Zones()) or board.GetCopperLayerCount() != 2:
        raise ValueError("base board must be an unrouted, zone-free, two-layer board")
    edges = [s for s in board.GetDrawings() if s.GetLayer() == pcb.Edge_Cuts]
    if len(edges) != 1 or edges[0].GetShape() != pcb.SHAPE_T_RECT:
        raise ValueError("base board must have one rectangular edge graphic")
    fps = {}
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref in fps:
            raise ValueError(f"duplicate board reference {ref}")
        fps[ref] = fp
    extras = set(fps) - set(components)
    if extras != {f"H{i}" for i in range(1, 7)}:
        raise ValueError(f"unexpected non-schematic footprints: {sorted(extras)}")
    for ref in extras:
        fp = fps[ref]
        if fp.GetPath().AsString() or any(p.GetNetname() or p.GetAttribute() != pcb.PAD_ATTRIB_NPTH for p in fp.Pads()):
            raise ValueError(f"unexpected schematic link or electrical pad on {ref}")
    missing = set(components) - set(fps)
    if missing != {"U11", "R14", "R15", "C14"}:
        raise ValueError(f"unexpected missing base-board parts: {sorted(missing)}")

    for index, ref in enumerate(sorted(missing)):
        value, fpid, sheet, ids, fields = components[ref]
        lib, name = fpid.split(":", 1)
        if lib != "DAR1000ES":
            raise ValueError(f"unsupported footprint library {lib}")
        fp = pcb.FootprintLoad(str(HERE / "DAR1000ES.pretty"), name)
        if fp is None:
            raise ValueError(f"cannot load footprint {fpid}")
        fp.SetFPID(pcb.LIB_ID(lib, name))
        fp.SetReference(ref)
        fp.SetValue(value)
        fp.SetPath(pcb.KIID_PATH(sheet + ids[0]))
        fp.SetPosition(pcb.VECTOR2I(pcb.FromMM(120 + index * 15), pcb.FromMM(10)))
        board.Add(fp)
        fps[ref] = fp

    for ref, (value, fpid, sheet, ids, fields) in components.items():
        fp = fps[ref]
        if fp.GetFPIDAsString() != fpid:
            raise ValueError(f"{ref}: footprint mismatch")
        lib, name = fpid.split(":", 1)
        if lib != "DAR1000ES":
            raise ValueError(f"unsupported footprint library {lib}")
        template = pcb.FootprintLoad(str(HERE / "DAR1000ES.pretty"), name)
        if template is None:
            raise ValueError(f"missing footprint template {fpid}")
        def pad_signature(f):
            return collections.Counter(
                (p.GetNumber(), p.GetFPRelativePosition().x, p.GetFPRelativePosition().y,
                 p.GetShape(), p.GetAttribute(), p.GetSize().x, p.GetSize().y,
                 p.GetDrillSize().x, p.GetDrillSize().y, p.GetDrillShape(),
                 p.GetLayerSet().FmtBin(), p.GetFPRelativeOrientation().AsDegrees() % 360,
                 p.GetOffset().x, p.GetOffset().y, p.GetChamferPositions(),
                 p.GetChamferRectRatio(), p.GetRoundRectRadiusRatio())
                for p in f.Pads())
        if pad_signature(fp) != pad_signature(template):
            raise ValueError(f"{ref}: pad geometry differs from footprint library")
        # A multi-unit footprint has one link to any one of its units. Preserve
        # the base board's chosen unit when it is still a valid schematic UUID.
        old_leaf = fp.GetPath().AsString().split("/")[-1]
        leaf = old_leaf if old_leaf in ids else ids[0]
        fp.SetPath(pcb.KIID_PATH(sheet + leaf))
        fp.SetValue(value)
        for field, text in fields:
            if field != "Footprint":
                fp.SetField(field, text)
        numbers = {p.GetNumber() for p in fp.Pads()}
        missing_pads = {pin for r, pin in nodes if r == ref} - numbers
        if missing_pads:
            raise ValueError(f"{ref}: schematic pads absent from footprint: {sorted(missing_pads)}")

    for name in sorted(set(nodes.values())):
        if board.FindNet(name) is None:
            board.Add(pcb.NETINFO_ITEM(board, name))
    for ref, fp in fps.items():
        for pad in fp.Pads():
            name = nodes.get((ref, pad.GetNumber()), "")
            pad.SetNet(board.FindNet(name) if name else board.FindNet(""))
    if not pcb.SaveBoard(str(OUTPUT), board):
        raise ValueError("KiCad could not save the board")
    reloaded = pcb.LoadBoard(str(OUTPUT))
    if reloaded is None:
        raise ValueError("cannot reload generated board")
    actual = {}
    seen = set()
    for fp in reloaded.GetFootprints():
        ref = fp.GetReference()
        if ref in seen:
            raise ValueError(f"duplicate saved reference {ref}")
        seen.add(ref)
        if ref in components:
            value, fpid, sheet, ids, fields = components[ref]
            if fp.GetFPIDAsString() != fpid or fp.GetValue() != value or fp.GetPath().AsString() not in {sheet + i for i in ids}:
                raise ValueError(f"{ref}: saved footprint identity or UUID path mismatch")
            for field, text in fields:
                if field != "Footprint" and fp.GetFieldText(field) != text:
                    raise ValueError(f"{ref}: saved field {field} differs")
        for pad in fp.Pads():
            key = (ref, pad.GetNumber())
            expected_net = nodes.get(key, "")
            if pad.GetNetname() != expected_net:
                raise ValueError(f"{key}: saved net {pad.GetNetname()} != {expected_net}")
            if expected_net:
                actual[key] = expected_net
    if seen != set(components) | extras or actual != nodes:
        raise ValueError("saved board references or pad net assignments differ")
    print(f"Verified {len(components)} schematic footprints, {len(extras)} mechanical holes, {len(nodes)} connected nodes.")


def main():
    if len(sys.argv) == 2 and sys.argv[1] == "--worker":
        worker()
        return
    if len(sys.argv) != 1:
        raise ValueError("no arguments expected")
    # Exclusive creation prevents accidental replacement of an existing board.
    fd = os.open(OUTPUT, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    os.close(fd)
    try:
        result = run(docker("--user", f"{os.getuid()}:{os.getgid()}",
                            "-v", f"{ROOT}:/work", "-w", "/work/v5") +
                     ["python3", "/work/v5/sync_pcb.py", "--worker"])
        print(result.stdout.strip())
        report = parity()
        if "schematic_parity" not in report or report["schematic_parity"]:
            raise ValueError(f"native schematic parity failed: {report.get('schematic_parity')}")
        ignored = {item["key"] for item in report.get("ignored_checks", [])}
        critical = {"missing_footprint", "extra_footprint", "footprint_symbol_mismatch",
                    "footprint_symbol_field_mismatch", "net_conflict"}
        if ignored & critical:
            raise ValueError(f"native schematic parity checks ignored: {sorted(ignored & critical)}")
        print(f"Native schematic parity passed; {len(report.get('unconnected_items', []))} unrouted connections.")
    except BaseException:
        OUTPUT.unlink(missing_ok=True)
        raise


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        if isinstance(exc, subprocess.CalledProcessError):
            print(exc.stdout, exc.stderr, file=sys.stderr)
        print(f"Synchronization failed: {exc}", file=sys.stderr)
        sys.exit(1)
