#!/usr/bin/env python3
"""Replot the pinned decoupling trial in the KiCad 10.0.2 container."""

import hashlib
import io
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


SOURCE = Path("/source/result.kicad_pcb")
EXPECTED_SHA256 = "53428c44aaf48bd0ea867c7b11f82e9277dcee58e0993fbcc820f4a65fc4612f"
OUTPUT = Path("output")
BOARD = Path("decoupling-plot.kicad_pcb")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

PLOTS = (
    ("assembly", "ASSEMBLY", "F.SilkS,F.CrtYd,Edge.Cuts", True),
    ("front-copper", "FRONT (F.Cu)", "F.Cu,Edge.Cuts", False),
    ("back-copper", "BACK (B.Cu)", "B.Cu,Edge.Cuts", False),
)
# 150 dpi page coordinates, multiplied by four for the 600 dpi render.
CROPS = (
    ("controller", (700, 112, 1044, 650)),
    ("audio", (700, 630, 1044, 1128)),
    ("c7-u9-c14-u11", (700, 920, 960, 1080)),
)


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"Expected exactly one occurrence of {old!r}")
    return text.replace(old, new, 1)


def closeups(name, label):
    result = run(
        "gs", "-q", "-dSAFER", "-dBATCH", "-dNOPAUSE",
        "-sDEVICE=png16m", "-r600", "-sOutputFile=-",
        str(OUTPUT / f"{name}.pdf"), stdout=subprocess.PIPE,
    )
    page = Image.open(io.BytesIO(result.stdout)).convert("RGB")
    if page.size != (7016, 4961):
        raise ValueError(f"Unexpected rendered page size: {page.size}")
    heading_font = ImageFont.truetype(FONT, 34)
    warning_font = ImageFont.truetype(FONT, 27)
    for region, box in CROPS:
        crop = page.crop(tuple(coordinate * 4 for coordinate in box))
        canvas = Image.new("RGB", (crop.width, crop.height + 130), "white")
        canvas.paste(crop, (0, 76))
        draw = ImageDraw.Draw(canvas)
        draw.text((16, 16), f"DECOUPLING TRIAL - {label} - {region}",
                  font=heading_font, fill="black")
        draw.text((16, crop.height + 88), "EXPERIMENTAL - NOT FOR FABRICATION",
                  font=warning_font, fill="black")
        canvas.save(OUTPUT / f"closeup-{name}-{region}.png")


def main():
    original = SOURCE.read_bytes()
    if hashlib.sha256(original).hexdigest() != EXPECTED_SHA256:
        raise ValueError("Decoupling trial board has changed; review before replotting")
    text = original.decode("utf-8")
    text = replace_once(text, '(rev "v5 experimental")', '(rev "v5")')
    text = replace_once(
        text,
        '(comment 1 "100 x 300 mm outline; mechanical fit unverified")',
        '(comment 1 "DECOUPLING TRIAL - NOT FOR FABRICATION")',
    )
    text = replace_once(
        text,
        '(comment 2 "Experimental routing; electrical and RF review required")',
        '(comment 2 "Electrical, RF and mechanical review required")',
    )
    old_title = '(title "DAR-1000ES v5 - experimental, not for fabrication")'
    OUTPUT.mkdir(exist_ok=True)
    for name, label, layers, monochrome in PLOTS:
        title = f'DAR-1000ES v5 DECOUPLING - {label}'
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
        closeups(name, label)
    BOARD.unlink()


if __name__ == "__main__":
    main()
