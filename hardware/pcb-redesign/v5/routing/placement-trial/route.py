#!/usr/bin/env python3
"""Reproducible, fail-closed wrapper for the independent v5 routing experiments."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
IMAGE = "kicad/kicad:10.0.2"
SHA256 = "f6f51bb02245e8e717f9359bd260cc9c5c0b1bc0acc8b7cb2cd5b8ffeb5de3c7"


def inside_repo(path):
    p = Path(path).resolve(strict=True)
    if not p.is_file() or not p.is_relative_to(ROOT):
        raise ValueError(f"input must be a regular file inside repository: {path}")
    return p


def container_path(path):
    return "/work/" + str(path.relative_to(ROOT))


def run(cmd, **kwargs):
    print("+", " ".join(map(str, cmd)), flush=True)
    subprocess.run(cmd, check=True, **kwargs)


def kicad(*args):
    home = HERE / ".kicad-home"
    home.mkdir(exist_ok=True)
    cmd = ["docker", "run", "--rm", "--network", "none",
           "-v", f"{ROOT}:/work:ro", "-v", f"{HERE}:{container_path(HERE)}:rw",
           "--user", f"{os.getuid()}:{os.getgid()}",
           "-e", f"HOME={container_path(home)}", "--entrypoint"]
    run(cmd + list(args))


def verify_jar(filename):
    jar = Path(filename).resolve(strict=True)
    if hashlib.sha256(jar.read_bytes()).hexdigest() != SHA256:
        raise ValueError("jar SHA-256 mismatch")
    return jar


def ops(action, **kw):
    args = ["/usr/bin/python3", IMAGE, container_path(HERE / "board_ops.py"), action]
    for k, v in kw.items():
        args += ["--" + k.replace("_", "-"), container_path(v) if isinstance(v, Path) else str(v)]
    kicad(*args)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("place", help="apply an explicit complete placement plan")
    p.add_argument("--board", required=True)
    p.add_argument("--netlist", required=True)
    p.add_argument("--plan", required=True)
    p.add_argument("--output", required=True, help="new .kicad_pcb directly in routing/")
    p = sub.add_parser("route", help="route an already reviewed placement")
    for key in ("board", "netlist", "project"):
        p.add_argument("--" + key, required=True)
    p.add_argument("--rules", help="matching .kicad_dru, if applicable")
    p.add_argument("--mode", choices=("single", "two"), required=True)
    p.add_argument("--name", required=True, help="new run directory name")
    p.add_argument("--java", default="/usr/lib/jvm/temurin-25-jdk-amd64/bin/java")
    p.add_argument("--jar", required=True, help="Freerouting 2.5.0 jar (SHA-256 verified before use)")
    p.add_argument("--timeout", type=int, default=900)
    p.add_argument("--passes", type=int, default=30)
    p.add_argument("--boundary", type=float, required=True, help="horizontal section boundary Y in mm")
    p.add_argument("--audio-side", choices=("upper", "lower"), required=True)
    p = sub.add_parser("pour", help="experiment with F.Cu and B.Cu GND fills")
    for key in ("board", "netlist", "project"):
        p.add_argument("--" + key, required=True)
    p.add_argument("--rules")
    p.add_argument("--name", required=True)
    p.add_argument("--boundary", type=float, required=True)
    p.add_argument("--audio-side", choices=("upper", "lower"), required=True)
    p = sub.add_parser("silk", help="move assembly metadata and add provisional hole courtyards")
    for key in ("board", "netlist", "project"):
        p.add_argument("--" + key, required=True)
    p.add_argument("--rules")
    p.add_argument("--name", required=True)
    p.add_argument("--boundary", type=float, required=True)
    p.add_argument("--audio-side", choices=("upper", "lower"), required=True)
    args = parser.parse_args()
    board, netlist = inside_repo(args.board), inside_repo(args.netlist)
    if args.action == "place":
        plan = inside_repo(args.plan)
        out = Path(args.output).resolve()
        if out.parent != HERE or out.suffix != ".kicad_pcb" or out.exists():
            raise ValueError("output must be a new .kicad_pcb directly in routing/")
        ops("place", board=board, netlist=netlist, plan=plan, output=out)
        return
    project = inside_repo(args.project)
    rules = inside_repo(args.rules) if args.rules else None
    if not rules and project.with_suffix(".kicad_dru").exists():
        raise ValueError("project has custom rules; supply --rules explicitly")
    if args.action == "route" and not (1 <= args.timeout <= 3600 and 1 <= args.passes <= 100):
        raise ValueError("timeout must be 1..3600 seconds and passes 1..100")
    if not args.name or not all(c.isascii() and (c.isalnum() or c in "_-") for c in args.name):
        raise ValueError("name must contain only ASCII letters, digits, _ or -")
    output = HERE / args.name
    output.mkdir(exist_ok=False)
    # A separate project adjacent to the output gives KiCad the intended DRC settings.
    project_data = json.loads(project.read_text(encoding="utf-8"))
    settings = project_data["board"]["design_settings"]
    if settings.get("drc_exclusions"):
        raise ValueError("project contains DRC exclusions")
    settings["rule_severities"]["missing_courtyard"] = "error"
    for stem in ("input", "result"):
        (output / (stem + ".kicad_pro")).write_text(
            json.dumps(project_data, indent=2) + "\n", encoding="utf-8")
    library_table = project.parent / "fp-lib-table"
    local_library = project.parent / "DAR1000ES.pretty"
    if not library_table.is_file() or not local_library.is_dir():
        raise ValueError("project-local fp-lib-table and DAR1000ES.pretty are required")
    shutil.copyfile(library_table, output / "fp-lib-table")
    shutil.copytree(local_library, output / "DAR1000ES.pretty")
    if rules:
        shutil.copyfile(rules, output / "result.kicad_dru")
        shutil.copyfile(rules, output / "input.kicad_dru")
    fresh = output / "input.kicad_pcb"
    shutil.copyfile(board, fresh)
    with (output / "inputs.sha256").open("w", encoding="utf-8") as manifest:
        for source in (board, netlist, project, rules):
            if source:
                manifest.write(f"{hashlib.sha256(source.read_bytes()).hexdigest()}  {source.relative_to(ROOT)}\n")
    if args.action in ("pour", "silk"):
        result = output / "result.kicad_pcb"
        arguments = dict(board=fresh, netlist=netlist, output=result,
                         boundary=args.boundary, audio_side=args.audio_side)
        ops(args.action, **arguments)
        refill = ["--refill-zones", "--save-board"] if args.action == "pour" else []
        kicad("/usr/bin/kicad-cli", IMAGE, "pcb", "drc", "--format", "json", "--severity-all",
              *refill, "--exit-code-violations", "--output", container_path(output / "drc.json"),
              container_path(result))
        print("Native DRC passed; return-current and physical reviews remain mandatory.")
        return
    dsn, ses, result = (output / "route.dsn", output / "route.ses", output / "result.kicad_pcb")
    ops("export", board=fresh, netlist=netlist, output=dsn,
        boundary=args.boundary, audio_side=args.audio_side)
    jar = verify_jar(args.jar)
    env = os.environ.copy()
    env.update({"FREEROUTING__USAGE_AND_DIAGNOSTIC_DATA__DISABLE_ANALYTICS": "true",
                "FREEROUTING__API_SERVER__ENABLED": "false",
                "FREEROUTING__GUI__ENABLED": "false",
                "FREEROUTING__MCP_SERVER__ENABLED": "false"})
    cmd = [args.java, "-Xmx2g", "-jar", str(jar), "-de", str(dsn), "-do", str(ses),
           "--router.autorouter.max_passes=" + str(args.passes),
           "--router.max_threads=2", "--router.optimizer.max_threads=2",
           "--router.automatic_neckdown=false",
           "--router.fanout.enabled=false", "--router.optimizer.enabled=false",
           "--router.copper_to_edge_clearance_um=500"]
    if args.mode == "single":
        cmd += ["--router.layers.routable=false,true"]
    with (output / "router.log").open("w", encoding="utf-8") as log:
        run(cmd, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=args.timeout)
    if not ses.is_file() or not ses.stat().st_size:
        raise ValueError("router did not create an SES")
    ops("import", board=fresh, netlist=netlist, ses=ses, mode=args.mode, output=result,
        boundary=args.boundary, audio_side=args.audio_side)
    kicad("/usr/bin/kicad-cli", IMAGE, "pcb", "drc", "--format", "json", "--severity-all",
          "--exit-code-violations", "--output", container_path(output / "drc.json"),
          container_path(result))
    print("Native DRC passed. Physical/mechanical, electrical, and schematic checks remain mandatory.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
