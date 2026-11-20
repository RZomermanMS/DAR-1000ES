#!/bin/bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
D=hardware/pcb-redesign/v5/routing/esp-orientation-comparison
IMAGE=kicad/kicad@sha256:165c81785b2df23a09892f4cc53bc0095a83b469bfbbe07989670d64049677a7
trap 'rm -rf "$D/.config" "$D/.cache" "$D/__pycache__"' EXIT
docker run --rm --network none --user "$(id -u):$(id -g)" \
  -e HOME="/work/$D" -e TMPDIR="/work/$D" -e PYTHONDONTWRITEBYTECODE=1 \
  -v "$PWD:/work:ro" -v "$PWD/$D:/work/$D:rw" -w "/work/$D" \
  --entrypoint /bin/bash "$IMAGE" -c \
  '/usr/bin/python3 test_compare.py && /usr/bin/python3 compare.py > results.json'
