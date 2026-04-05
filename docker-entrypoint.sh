#!/bin/sh
# docker-entrypoint.sh — Zero-Minute Dispatch backend startup
#
# Downloads the BART model to the mounted volume on FIRST boot only.
# On all subsequent starts the weights are already present → instant startup.

set -e

MODEL_MARKER="/cache/huggingface/.bart_downloaded"

if [ ! -f "$MODEL_MARKER" ]; then
    echo "════════════════════════════════════════════════"
    echo "  First boot: downloading BART model (~1.6 GB)"
    echo "  This runs ONCE and is stored on the volume."
    echo "════════════════════════════════════════════════"
    python download_model.py
    touch "$MODEL_MARKER"
    echo "  ✓ BART model ready."
else
    echo "  ✓ BART model found in volume cache — skipping download."
fi

# Hand off to the CMD (uvicorn)
exec "$@"
