#!/usr/bin/env python3
"""Render candidate assembly to a fitted PDF and two enlarged PNGs."""
import io
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def main():
    run("kicad-cli", "pcb", "export", "pdf", "--mode-single",
        "--include-border-title", "--scale", "0", "--black-and-white",
        "--layers", "F.SilkS,F.CrtYd,Edge.Cuts", "-o", "assembly.pdf",
        "result.kicad_pcb")
    result = run("gs", "-q", "-dSAFER", "-dBATCH", "-dNOPAUSE",
                 "-sDEVICE=png16m", "-r600", "-sOutputFile=-", "assembly.pdf",
                 stdout=subprocess.PIPE)
    page = Image.open(io.BytesIO(result.stdout)).convert("RGB")
    if page.size != (7016, 4961):
        raise ValueError(f"Unexpected page size {page.size}")
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
    for name, bounds in (("controller", (700, 112, 1044, 650)),
                         ("audio", (700, 630, 1044, 1128))):
        crop = page.crop(tuple(x * 4 for x in bounds))
        canvas = Image.new("RGB", (crop.width, crop.height + 110), "white")
        canvas.paste(crop, (0, 60))
        draw = ImageDraw.Draw(canvas)
        draw.text((10, 10), f"V5 SILK REWORK - {name.upper()}", font=font, fill="black")
        draw.text((10, crop.height + 67), "EXPERIMENTAL - NOT FOR FABRICATION",
                  font=font, fill="black")
        canvas.save(Path(f"assembly-{name}.png"))


if __name__ == "__main__":
    main()
