#!/bin/sh
# Copy the canonical engine into the integration (HACS only ships custom_components/).
set -e
cd "$(dirname "$0")/.."
dst=custom_components/sublunary/engine
mkdir -p "$dst"
rm -f "$dst"/*.py
cp sublunary/*.py "$dst"/
echo "vendored: $(ls "$dst" | tr '\n' ' ')"
