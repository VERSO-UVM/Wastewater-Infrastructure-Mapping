#!/usr/bin/env python3
"""
merge_linear_by_rpc.py
----------------------
Merge all per-RPC linear GeoJSON files back into a single statewide file.
This is the inverse of split_linear_by_rpc.py.

Run from the repo root:
    python scripts/merge_linear_by_rpc.py

Inputs:  data/linear_by_rpc/Vermont_Linear_<RPC>.geojson  (one per RPC)
Output:  data/Vermont_Linear_Features.geojson
"""

import glob
import json
import os
import sys

INPUT_DIR = "data/linear_by_rpc"
OUTPUT = "data/Vermont_Linear_Features.geojson"

pattern = os.path.join(INPUT_DIR, "Vermont_Linear_*.geojson")
files = sorted(glob.glob(pattern))

if not files:
    print(f"No files found matching {pattern}", file=sys.stderr)
    sys.exit(1)

all_features = []
# Preserve top-level GeoJSON metadata (crs, name, etc.) from the first file
template = None

for path in files:
    rpc = (
        os.path.basename(path)
        .replace("Vermont_Linear_", "")
        .replace(".geojson", "")
    )
    with open(path) as f:
        gj = json.load(f)
    if template is None:
        template = {k: v for k, v in gj.items() if k != "features"}
    all_features.extend(gj["features"])
    print(f"  {rpc}: {len(gj['features']):,} features")

out = {**template, "features": all_features}
with open(OUTPUT, "w") as f:
    json.dump(out, f)

print(f"\nMerged {len(all_features):,} features from {len(files)} files → {OUTPUT}")
