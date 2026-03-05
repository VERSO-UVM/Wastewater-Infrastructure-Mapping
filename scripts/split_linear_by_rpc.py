#!/usr/bin/env python3
"""Split Vermont_Linear_Features.geojson into per-RPC files."""

import json
import os
from collections import defaultdict

INPUT = "data/Vermont_Linear_Features.geojson"
OUTPUT_DIR = "data/linear_by_rpc"

os.makedirs(OUTPUT_DIR, exist_ok=True)

print(f"Reading {INPUT}...")
with open(INPUT) as f:
    gj = json.load(f)

by_rpc = defaultdict(list)
null_count = 0

for feat in gj["features"]:
    rpc = feat["properties"].get("RPC")
    if rpc:
        by_rpc[rpc].append(feat)
    else:
        null_count += 1
        by_rpc["UNKNOWN"].append(feat)

template = {k: v for k, v in gj.items() if k != "features"}

for rpc, features in sorted(by_rpc.items()):
    out_path = os.path.join(OUTPUT_DIR, f"Vermont_Linear_{rpc}.geojson")
    out = {**template, "features": features}
    with open(out_path, "w") as f:
        json.dump(out, f)
    print(f"  {rpc}: {len(features):,} features → {out_path}")

print(f"\nTotal: {len(gj['features']):,} features across {len(by_rpc)} RPCs")
if null_count:
    print(f"  ({null_count} features had null RPC → UNKNOWN)")
