#!/usr/bin/env python3
"""Verify exported KiCad XML connectivity, including baseline preservation."""
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "reference" / "pcb-v3-netlist.xml"


def read(path):
    root = ET.parse(path).getroot()
    nets = {n.get("name"): {(p.get("ref"), p.get("pin")) for p in n.findall("node")}
            for n in root.findall("./nets/net")}
    pins = {pin: name for name, members in nets.items() for pin in members}
    return nets, pins


def same(pins, *nodes):
    names = {pins[n] for n in nodes}
    assert len(names) == 1, (nodes, names)
    return names.pop()


def verify_safety_parts(root):
    """Reject altered safety-critical values and symbol/part selections."""
    expected = {}

    def add(refs, value, library, symbol, mpn=None):
        for ref in refs:
            expected[ref] = (value, library, symbol, mpn)

    add(("R1", "R2", "R3", "R5", "R6"), "10k", "Device", "R")
    add(("R7", "R8", "R9", "R10", "R11", "R13", "R15"), "100k", "Device", "R")
    add(("R12", "R14"), "1k", "Device", "R")
    add(("U8", "U9"), "SN74AHCT00N", "DAR1000ES", "SN74AHCT00N")
    add(("U2", "U3", "U4", "U6", "U7"), "SN74AHCT125N", "DAR1000ES",
        "SN74AHCT125N", "SN74AHCT125N")
    add(("U10", "U11"), "MCP100-475DI/TO", "DAR1000ES", "MCP100-475DI_TO")
    add(("C8", "C11", "C13", "C14"), "100nF", "Device", "C")
    add(("C9",), "470uF 16V", "Device", "C_Polarized", "EEU-FR1C471")
    add(("C10", "C12"), "100uF 16V", "Device", "C_Polarized", "EEU-FR1C101")

    components = {}
    for component in root.findall("./components/comp"):
        ref = component.get("ref")
        if not ref or ref in components:
            raise ValueError(f"Missing or duplicate component reference: {ref!r}")
        components[ref] = component
    for ref, (value, library, symbol, mpn) in expected.items():
        component = components.get(ref)
        if component is None:
            raise ValueError(f"{ref}: required component missing")
        values = component.findall("value")
        sources = component.findall("libsource")
        source = sources[0] if len(sources) == 1 else None
        actual = (values[0].text if len(values) == 1 else None,
                  source.get("lib") if source is not None else None,
                  source.get("part") if source is not None else None)
        if actual != (value, library, symbol):
            raise ValueError(f"{ref}: expected {(value, library, symbol)!r}, got {actual!r}")
        if mpn is not None:
            fields = component.findall("./fields/field[@name='MPN']")
            properties = component.findall("./property[@name='MPN']")
            if (len(fields) != 1 or fields[0].text != mpn or
                    len(properties) != 1 or properties[0].get("value") != mpn):
                raise ValueError(f"{ref}: expected MPN {mpn!r} in field and property")


def main():
    nets, p = read(HERE / "DAR-1000ES-v5.net.xml")
    oldnets, oldpins = read(BASE)
    root = ET.parse(HERE / "DAR-1000ES-v5.net.xml").getroot()
    verify_safety_parts(root)
    expected_connectors = {
        "J2": ("GND", "LOCAL_5V"),
        "J3": ("GND", "/FLGDATA", "/FLGCLK", "/FLCLEAR"),
        "J4": ("/FLSTB", "/FLSDATA", "/FLSCLK"),
        "J5": ("GND", "/OUT0", "/OUT1", "/OUT2"),
        "J6": ("/IN0", "/IN1", "/IN2", "/IN3"),
        "J7": ("/IN4", "/IN5", "/IN6", "/IN7"),
        "J8": ("/OUT3", "/OUT4", "/OUT5"),
        "J9": ("GND", "/A.MUTE", "/D.MUTE", "/RELAY"),
        "J10": ("GND", "/ATT", "/SHIFT", "/LATCH", "/INIT"),
        "J11": ("GND", "/BCKI", "/DATA", "/LRCK"),
        "J12": ("GND", "SONY_5V_SENSE"),
    }
    for ref, names in expected_connectors.items():
        assert {pin for part, pin in p if part == ref} == {str(i) for i in range(1, len(names) + 1)}
        for i, name in enumerate(names, 1):
            assert p[(ref, str(i))] == name, (ref, i, p[(ref, str(i))], name)
    for gate, request, good, output in [
        (("U8", "4", "5", "6"), "ENABLE_U3", "CTRL_POWER_GOOD", "U3_OE_N"),
        (("U8", "9", "10", "8"), "ENABLE_U4", "CTRL_POWER_GOOD", "U4_OE_N"),
        (("U9", "9", "10", "8"), "ENABLE_U2", "AUDIO_POWER_GOOD", "U2_OE_N"),
        (("U9", "1", "2", "3"), "ENABLE_U6", "AUDIO_POWER_GOOD", "U6_OE_N"),
        (("U9", "4", "5", "6"), "ENABLE_U7", "AUDIO_POWER_GOOD", "U7_OE_N"),
    ]:
        ref, a, b, y = gate
        assert (p[(ref, a)], p[(ref, b)], p[(ref, y)]) == (request, good, output)
        assert {(r, g, int(not (r and g))) for r in (0, 1) for g in (0, 1)} == {
            (0, 0, 1), (0, 1, 1), (1, 0, 1), (1, 1, 0)}
    for ref in ("U8", "U9"):
        assert p[(ref, "14")] == "LOCAL_5V" and p[(ref, "7")] == "GND"
        assert p[(ref, "12")] == p[(ref, "13")] == "GND"
        assert len(nets[p[(ref, "11")]]) == 1
    assert p[("U8", "1")] == p[("U8", "2")] == "GND"
    assert len(nets[p[("U8", "3")]]) == 1
    for connector, buf, source in [
        ("1", "8", "J1.7"), ("2", "3", "J1.12"), ("3", "11", "J1.5")]:
        name = same(p, ("J4", connector), ("U4", buf))
        assert name == { "1": "/FLSTB", "2": "/FLSDATA", "3": "/FLSCLK"}[connector]
        same(p, ("U4", {"8": "9", "3": "2", "11": "12"}[buf]), ("U1-CONTROLLER1", source))
    for pin, buf, gpio in [("2", "8", "J1.4"), ("3", "3", "J1.5"), ("4", "11", "J1.6")]:
        same(p, ("J9", pin), ("U2", buf))
        same(p, ("U2", {"8": "9", "3": "2", "11": "12"}[buf]), ("U6-AUDIO1", gpio))
    same(p, ("U2", "5"), ("U6-AUDIO1", "J1.7"))
    same(p, ("U6-AUDIO1", "J1.12"), ("R7", "1"), ("U9", "9"))
    for u, gate, pullup in [("U2", "U9.8", "R1"), ("U3", "U8.6", "R2"),
                            ("U4", "U8.8", "R3"), ("U6", "U9.3", "R5"),
                            ("U7", "U9.6", "R6")]:
        gr, gp = gate.split(".")
        same(p, *( [(u, n) for n in ("1", "4", "10", "13")] + [(gr, gp), (pullup, "2" if pullup in ("R1", "R3", "R5") else "1")] ))
    assert same(p, ("U10", "2"), ("U11", "2"), ("J12", "2"), ("C8", "1"), ("C14", "1")) == "SONY_5V_SENSE"
    assert same(p, ("U10", "1"), ("R12", "1")) == "SONY_RESET_N_RAW"
    assert same(p, ("U11", "1"), ("R14", "1")) == "AUDIO_RESET_N_RAW"
    assert same(p, ("R12", "2"), ("R13", "1"), ("U8", "5"), ("U8", "10")) == "CTRL_POWER_GOOD"
    assert same(p, ("R14", "2"), ("R15", "1"), ("U9", "2"), ("U9", "5"), ("U9", "10")) == "AUDIO_POWER_GOOD"
    for r in ("R7", "R8", "R9", "R10", "R11", "R13", "R15"):
        assert p[(r, "2")] == "GND"
    for r, enable in [("R7", "ENABLE_U2"), ("R8", "ENABLE_U3"), ("R9", "ENABLE_U4"),
                      ("R10", "ENABLE_U6"), ("R11", "ENABLE_U7")]:
        assert p[(r, "1")] == enable
    for r, pin in [("R1", "1"), ("R2", "2"), ("R3", "1"), ("R5", "1"), ("R6", "2")]:
        assert p[(r, pin)] == "LOCAL_5V"
    for cap, rail in [("C9", "LOCAL_5V"), ("C10", "ESP_CTRL_5V"),
                      ("C11", "ESP_CTRL_5V"), ("C12", "ESP_AUDIO_5V"), ("C13", "ESP_AUDIO_5V")]:
        assert p[(cap, "1")] == rail and p[(cap, "2")] == "GND"
    for pin in ("J1.1", "J1.2"):
        assert len(nets[p[("U6-AUDIO1", pin)]]) == 1
        for ctrl_pin in ("J1.1", "J1.2"):
            assert p[("U6-AUDIO1", pin)] != p[("U1-CONTROLLER1", ctrl_pin)]
    for esp in ("U1-CONTROLLER1", "U6-AUDIO1"):
        assert p[(esp, "J3.1")] == p[(esp, "J1.22")] == "GND"
    components = {c.get("ref"): c.findtext("value") for c in root.findall("./components/comp")}
    for net in root.findall("./nets/net"):
        nodes = net.findall("node")
        gpio = any(n.get("ref") in ("U1-CONTROLLER1", "U6-AUDIO1")
                   and n.get("pinfunction", "").startswith(("IO", "TX_IO", "RX_IO")) for n in nodes)
        if gpio:
            for n in nodes:
                ref, pin = n.get("ref"), n.get("pin")
                if ref.startswith("R") and pin in ("1", "2"):
                    other = "2" if pin == "1" else "1"
                    assert p[(ref, other)] != "LOCAL_5V", (net.get("name"), ref)

    controller = {"U1-CONTROLLER1", "U3", "U4", "U5", "U8", "U10",
                  "J3", "J4", "J5", "J6", "J7", "J8", "JP1",
                  "R2", "R3", "R4", "R8", "R9", "R12", "R13",
                  "C1", "C2", "C6", "C8", "C10", "C11"}
    audio = {"U6-AUDIO1", "U2", "U6", "U7", "U9", "U11",
             "J9", "J10", "J11", "JP2", "R1", "R5", "R6", "R7",
             "R10", "R11", "R14", "R15", "C3", "C4", "C5", "C7", "C12", "C13", "C14"}
    shared = {"J2", "J12", "C9"}
    assert not (controller & audio or controller & shared or audio & shared)
    refs = set(components)
    assert {ref for ref, pin in p} <= refs
    assert refs == controller | audio | shared, ("unknown", refs - controller - audio - shared,
                                                "missing", (controller | audio | shared) - refs)
    uart_tx = same(p, ("U1-CONTROLLER1", "J3.18"), ("U6-AUDIO1", "J1.19"))
    uart_rx = same(p, ("U1-CONTROLLER1", "J3.17"), ("U6-AUDIO1", "J1.20"))
    assert nets[uart_tx] == {("U1-CONTROLLER1", "J3.18"), ("U6-AUDIO1", "J1.19")}
    assert nets[uart_rx] == {("U1-CONTROLLER1", "J3.17"), ("U6-AUDIO1", "J1.20")}
    allowed = {"GND", "LOCAL_5V", "SONY_5V_SENSE", uart_tx, uart_rx}
    crossing = {name for name, nodes in nets.items()
                if {r for r, _ in nodes} & controller and {r for r, _ in nodes} & audio}
    assert crossing == allowed, (crossing - allowed, allowed - crossing)
    print("Cross-section nets:", ", ".join(sorted(crossing)))

    # Compare every untouched physical terminal's net partition to v3.
    changed = {("U1-CONTROLLER1", x) for x in ("J1.6", "J1.15", "J1.16", "J1.17", "J1.18", "J3.1")}
    changed |= {("U6-AUDIO1", x) for x in ("J1.4", "J1.5", "J1.6", "J1.7", "J1.12", "J3.1")}
    changed |= {("U2", x) for x in ("2", "5", "9", "12")}
    changed |= {("U8", x) for x in ("1", "2", "3", "5", "10")}
    changed |= {("U9", x) for x in ("2", "5", "8", "9", "10")}
    changed |= {("R12", "2"), ("R13", "1")}
    newrefs = {"U11", "R14", "R15", "C14"}
    expected_newpins = {("U11", x) for x in ("1", "2", "3")}
    expected_newpins |= {(ref, pin) for ref in ("R14", "R15", "C14") for pin in ("1", "2")}
    assert set(p) == set(oldpins) | expected_newpins, (set(p) - set(oldpins) - expected_newpins, set(oldpins) - set(p))
    for pin in ("J1.6", "J1.15", "J1.16", "J1.17", "J1.18"):
        assert len(nets[p[("U1-CONTROLLER1", pin)]]) == 1
    added_names = {
        "/AUDIO_U2_AMUTE", "/AUDIO_U2_DMUTE", "/AUDIO_U2_RELAY", "/AUDIO_U2_SPARE",
        "/FLSCLK", "/FLSDATA", "/FLSTB", "AUDIO_POWER_GOOD", "AUDIO_RESET_N_RAW", "CTRL_POWER_GOOD",
        "unconnected-(U1-CONTROLLER1-IO10-PadJ1.16)", "unconnected-(U1-CONTROLLER1-IO11-PadJ1.17)",
        "unconnected-(U1-CONTROLLER1-IO12-PadJ1.18)", "unconnected-(U1-CONTROLLER1-IO6-PadJ1.6)",
        "unconnected-(U1-CONTROLLER1-IO9-PadJ1.15)", "unconnected-(U8-1Y-Pad3)",
    }
    removed_names = {
        "Net-(J4-Pin_1)", "Net-(J4-Pin_2)", "Net-(J4-Pin_3)", "Net-(U1-CONTROLLER1-GND-PadJ3.1)",
        "Net-(U1-CONTROLLER1-IO9)", "Net-(U1-CONTROLLER1-IO10)", "Net-(U1-CONTROLLER1-IO11)",
        "Net-(U1-CONTROLLER1-IO12)", "SONY_POWER_GOOD", "unconnected-(U9-3Y-Pad8)",
        "unconnected-(U6-AUDIO1-IO4-PadJ1.4)", "unconnected-(U6-AUDIO1-IO5-PadJ1.5)",
        "unconnected-(U6-AUDIO1-IO6-PadJ1.6)", "unconnected-(U6-AUDIO1-IO7-PadJ1.7)",
        "unconnected-(U6-AUDIO1-IO8-PadJ1.12)",
    }
    assert set(nets) == (set(oldnets) - removed_names) | added_names
    def partition(netmap):
        return {frozenset(n for n in nodes if n not in changed and n[0] not in newrefs)
                for nodes in netmap.values()} - {frozenset()}
    assert partition(nets) == partition(oldnets), (
        partition(oldnets) - partition(nets), partition(nets) - partition(oldnets))
    print("PASS: v5 netlist connectivity, section boundaries, capacitor rails, and v3 preservation")


if __name__ == "__main__":
    main()
