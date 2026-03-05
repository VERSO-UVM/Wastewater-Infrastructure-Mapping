#!/usr/bin/env python3
"""
For every Vermont_*.geojson in data/:
  - Drop OBJECTID
  - Add Municipal_Name, County, RPC from municipal_geoid_county_rpc_fips.csv
    joined on GEOIDTXT = GEO_ID

Edits files in-place.
"""

import csv
import json
import os
from pathlib import Path

ROOT     = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
CSV_PATH = DATA_DIR / "municipal_geoid_county_rpc_fips.csv"

# ── Load CSV lookup {GEO_ID: {Municipal_Name, County, RPC}} ───────────────────
print("Loading CSV lookup…")
lookup = {}
with open(CSV_PATH, newline="") as f:
    for row in csv.DictReader(f):
        gid = row["GEO_ID"].strip()
        if gid not in lookup:
            lookup[gid] = {
                "Municipal_Name": row["Municipal_Name"].strip() or None,
                "County":         row["County"].strip() or None,
                "RPC":            row["RPC"].strip() or None,
            }
print(f"  {len(lookup)} municipalities in lookup\n")

# ── Process each Vermont_*.geojson ────────────────────────────────────────────
files = sorted(DATA_DIR.glob("Vermont_*.geojson"))
print(f"Files to process: {[f.name for f in files]}\n")

for fpath in files:
    print(f"Processing {fpath.name}…")
    with open(fpath) as f:
        fc = json.load(f)

    features   = fc["features"]
    total      = len(features)
    no_match   = 0
    null_geoid = 0

    for feat in features:
        p = feat.get("properties") or {}

        # Drop OBJECTID
        p.pop("OBJECTID", None)

        # Lookup Municipal_Name, County, RPC from GEOIDTXT
        gid = p.get("GEOIDTXT")
        if gid and gid in lookup:
            p["Municipal_Name"] = lookup[gid]["Municipal_Name"]
            p["County"]         = lookup[gid]["County"]
            p["RPC"]            = lookup[gid]["RPC"]
        else:
            p["Municipal_Name"] = None
            p["County"]         = None
            p["RPC"]            = None
            if gid:
                no_match += 1
            else:
                null_geoid += 1

        feat["properties"] = p

    # Coverage stats
    matched = total - no_match - null_geoid
    print(f"  {total:>8,} features")
    print(f"  {matched:>8,} matched to CSV ({matched/total*100:.1f}%)")
    if no_match:
        print(f"  {no_match:>8,} GEOIDTXT not in CSV → null")
    if null_geoid:
        print(f"  {null_geoid:>8,} null GEOIDTXT → null")

    with open(fpath, "w") as f:
        json.dump(fc, f, separators=(",", ":"))

    size_mb = os.path.getsize(fpath) / 1024 / 1024
    print(f"  → {fpath.name} ({size_mb:.1f} MB)\n")

print("Done.")
