Readable inspection plots — EXPERIMENTAL, NOT FOR FABRICATION
================================================================

These are alternate fitted views of the unchanged
../experiment-silk-7/result.kicad_pcb checkpoint, not a new layout.
The checkpoint board SHA-256 is
44374a3e5e529bad2d6c6b86dc479dcf3c501c83625bc69086c49c34836ce98d.
Original plots, board, project, DRC and other checkpoint evidence remain
unchanged in experiment-silk-7.

  assembly.pdf / .png       F.SilkS, F.CrtYd and Edge.Cuts, black on white
  front-copper.pdf / .png   F.Cu and Edge.Cuts, red copper, unmirrored
  back-copper.pdf / .png    B.Cu and Edge.Cuts, blue copper, unmirrored

Each PDF is a single A4 page with a layer-specific title; each PNG is a
150 dpi preview. The shortened revision and titles fit their cells, and the
warning is on its own line. The derived board filename printed in the
title block is plot.kicad_pcb, not a separate design source. The complete
outline and title block are visible in all three previews. These are fitted,
not 1:1, and are not manufacturing or etching artwork. The plots contain
no net labels; references remain small at full-page scale and some assembly
markings may overlap existing courtyard artwork when enlarged. Use the
checkpoint board and original closeups for detailed investigation.

The original limitations still apply: zero reported DRC and schematic-parity
issues are not physical, electrical, RF or fabrication approval; four DRC
checks were ignored. Decoupling, return paths, antenna, hardware, connector,
clearance and bench validation remain unresolved. See ../README.txt,
../../INSPECTION.txt and the checkpoint clearance notes for details.

Reproduce from the repository root with the existing KiCad 10.0.2 image
(Ghostscript is included). The container's disposable working directory holds
the plot-only board copy; only the PDFs and previews are written to this
directory. The source mount is read-only. Substitute the current numeric user
and group IDs in the chown command if they differ.

  docker run --rm --network none --user 0:0 --workdir /workspace \
    -e TMPDIR=/workspace \
    -v "$PWD/hardware/pcb-redesign/v5/routing/experiment-silk-7:/source:ro" \
    -v "$PWD/hardware/pcb-redesign/v5/routing/inspection-readable:/workspace/output" \
    --entrypoint /bin/bash kicad/kicad:10.0.2 \
    -c 'python3 output/generate.py && chown 1001:1001 output/*.pdf output/*.png'

The generator checks the checkpoint hash, makes only title-block substitutions
in a plot-only copy, and uses explicit KiCad layer selections. It does not
change the source board or refill zones. PNGs are rendered from those PDFs.
