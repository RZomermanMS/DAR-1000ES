#!/usr/bin/env python3
"""Replot the preserved silk-7 checkpoint in the pinned KiCad container."""

import hashlib
import subprocess
from pathlib import Path


SOURCE = Path("/source/result.kicad_pcb")
EXPECTED_SHA256 = "44374a3e5e529bad2d6c6b86dc479dcf3c501c83625bc69086c49c34836ce98d"
OUTPUT = Path("output")
BOARD = Path("plot.kicad_pcb")


def run(*args):
    subprocess.run(args, check=True)


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"Expected exactly one occurrence of {old!r}")
    return text.replace(old, new, 1)


def main():
    original = SOURCE.read_bytes()
    if hashlib.sha256(original).hexdigest() != EXPECTED_SHA256:
        raise ValueError("The silk-7 checkpoint has changed; review before replotting")
    text = original.decode("utf-8")
    text = replace_once(text, '(rev "v5 experimental")', '(rev "v5")')
    text = replace_once(
        text,
        '(comment 1 "100 x 300 mm outline; mechanical fit unverified")',
        '(comment 1 "EXPERIMENTAL - NOT FOR FABRICATION")',
    )
    text = replace_once(
        text,
        '(comment 2 "Experimental routing; electrical and RF review required")',
        '(comment 2 "Electrical, RF and mechanical review required")',
    )
    old_title = '(title "DAR-1000ES v5 - experimental, not for fabrication")'
    plots = (
        ("assembly", "DAR-1000ES v5 - ASSEMBLY", "F.SilkS,F.CrtYd,Edge.Cuts", True),
        ("front-copper", "DAR-1000ES v5 - FRONT COPPER (F.Cu)", "F.Cu,Edge.Cuts", False),
        ("back-copper", "DAR-1000ES v5 - BACK COPPER (B.Cu)", "B.Cu,Edge.Cuts", False),
    )
    OUTPUT.mkdir(exist_ok=True)
    for name, title, layers, monochrome in plots:
        BOARD.write_text(replace_once(text, old_title, f'(title "{title}")'), encoding="utf-8")
        command = [
            "kicad-cli", "pcb", "export", "pdf", "--mode-single",
            "--include-border-title", "--scale", "0", "--layers", layers,
            "--output", str(OUTPUT / f"{name}.pdf"),
        ]
        if monochrome:
            command.append("--black-and-white")
        run(*command, str(BOARD))
        run(
            "gs", "-q", "-dSAFER", "-dBATCH", "-dNOPAUSE",
            "-sDEVICE=png16m", "-r150",
            f"-sOutputFile={OUTPUT / (name + '.png')}",
            str(OUTPUT / f"{name}.pdf"),
        )
    BOARD.unlink()


if __name__ == "__main__":
    main()
