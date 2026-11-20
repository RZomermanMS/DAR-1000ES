#!/usr/bin/env python3
"""Recheck the saved PCB read-only, recording its hashes around native DRC."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = Path(subprocess.check_output(
    ["git", "-C", str(HERE), "rev-parse", "--show-toplevel"], text=True).strip())
BOARD = HERE / "result.kicad_pcb"
WORK = HERE / ".verification-work"
IMAGE = "kicad/kicad@sha256:165c81785b2df23a09892f4cc53bc0095a83b469bfbbe07989670d64049677a7"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if WORK.exists():
        raise ValueError(f"Inspect existing scratch directory: {WORK}")
    WORK.mkdir()
    before = sha(BOARD)
    command = [
        "docker", "run", "--rm", "--network", "none",
        "--user", f"{os.getuid()}:{os.getgid()}",
        "-e", "HOME=/nonexistent", "-e", "TMPDIR=/out",
        "-v", f"{ROOT}:/work:ro", "-v", f"{WORK}:/out:rw", "-w", "/work",
        "--entrypoint", "kicad-cli", IMAGE, "pcb", "drc",
        "--format", "json", "--severity-all", "--exit-code-violations",
        "-o", "/out/drc.json", "/work/" + BOARD.relative_to(ROOT).as_posix(),
    ]
    try:
        run = subprocess.run(command, capture_output=True, text=True, check=False)
        after = sha(BOARD)
        report_path = WORK / "drc.json"
        report = json.loads(report_path.read_text()) if report_path.exists() else None
        if report is not None:
            (HERE / "verification-drc.json").write_bytes(report_path.read_bytes())
        evidence = {
            "board": "result.kicad_pcb",
            "sha256_before_drc": before,
            "sha256_after_drc": after,
            "drc_exit_code": run.returncode,
            "drc_report_sha256": sha(report_path) if report else None,
            "kicad_version": report.get("kicad_version") if report else None,
            "violations": len(report["violations"]) if report else None,
            "unconnected_items": len(report["unconnected_items"]) if report else None,
            "ignored_checks": [c["key"] for c in report["ignored_checks"]] if report else None,
            "mode": "native DRC without refill or save; repository mounted read-only",
        }
        (HERE / "verification.json").write_text(json.dumps(evidence, indent=2) + "\n")
        if (run.returncode or before != after or report is None or
                report["violations"] or report["unconnected_items"]):
            print(run.stdout, run.stderr, file=sys.stderr)
            raise RuntimeError("Read-only verification failed; see verification.json")
        print(json.dumps(evidence, indent=2))
    finally:
        shutil.rmtree(WORK)


if __name__ == "__main__":
    main()
