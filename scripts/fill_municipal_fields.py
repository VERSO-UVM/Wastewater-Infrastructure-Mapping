#!/usr/bin/env python3
"""
Fill null Municipal_Name, County, RPC on all Vermont_*.geojson using:
  1. municipal_geoid_county_rpc_fips.csv  (primary — 198 towns, has all 3 fields)
  2. Town boundary GeoJSON               (fallback — all 256 towns)
       - Municipal_Name from TOWNNAMEMC
       - County from CNTY code (14 unambiguous codes)
       - RPC from CNTY only where county maps to a single RPC;
         null for Bennington / Orange / Windsor (multiple RPCs per county)

Edits files in-place.
"""

import csv
import json
import os
from pathlib import Path

ROOT        = Path(__file__).parent.parent
DATA_DIR    = ROOT / "data"
CSV_PATH    = DATA_DIR / "municipal_geoid_county_rpc_fips.csv"
BOUNDARY    = DATA_DIR / "FS_VCGI_OPENDATA_Boundary_BNDHASH_poly_towns_SP_v1_-669012076166787740.geojson"

# Vermont county FIPS code → county name (all 14, unambiguous)
CNTY_TO_COUNTY = {
    1:  "Addison",
    3:  "Bennington",
    5:  "Caledonia",
    7:  "Chittenden",
    9:  "Essex",
    11: "Franklin",
    13: "Grand Isle",
    15: "Lamoille",
    17: "Orange",
    19: "Orleans",
    21: "Rutland",
    23: "Washington",
    25: "Windham",
    27: "Windsor",
}

# Counties with a single RPC (safe to derive)
COUNTY_TO_RPC_SINGLE = {
    "Addison":    "ACRPC",
    "Caledonia":  "NVDA",
    "Chittenden": "CCRPC",
    "Essex":      "NVDA",
    "Franklin":   "NRPC",
    "Grand Isle": "NRPC",
    "Lamoille":   "LCPC",
    "Orleans":    "NVDA",
    "Rutland":    "RRPC",
    "Washington": "CVRPC",
    "Windham":    "WRC",
    # Bennington, Orange, Windsor intentionally omitted — multiple RPCs
}


def build_lookups():
    # Primary: CSV (198 towns — full Municipal_Name, County, RPC)
    csv_lookup = {}
    with open(CSV_PATH, newline="") as f:
        for row in csv.DictReader(f):
            gid = row["GEO_ID"].strip()
            if gid:
                csv_lookup[gid] = {
                    "Municipal_Name": row["Municipal_Name"].strip() or None,
                    "County":         row["County"].strip() or None,
                    "RPC":            row["RPC"].strip() or None,
                }

    # Fallback: boundary file (256 towns — derives County + Municipal_Name)
    boundary_lookup = {}
    with open(BOUNDARY) as f:
        towns_fc = json.load(f)
    for feat in towns_fc["features"]:
        p    = feat["properties"]
        gid  = p.get("TOWNGEOID", "").strip()
        cnty = p.get("CNTY")
        if not gid:
            continue
        county = CNTY_TO_COUNTY.get(cnty)
        rpc    = COUNTY_TO_RPC_SINGLE.get(county)  # None for ambiguous counties
        boundary_lookup[gid] = {
            "Municipal_Name": p.get("TOWNNAMEMC") or p.get("TOWNNAME"),
            "County":         county,
            "RPC":            rpc,
        }

    return csv_lookup, boundary_lookup


def resolve(gid, csv_lookup, boundary_lookup):
    if gid and gid in csv_lookup:
        return csv_lookup[gid]
    if gid and gid in boundary_lookup:
        return boundary_lookup[gid]
    return {"Municipal_Name": None, "County": None, "RPC": None}


def main():
    print("Building lookups…")
    csv_lookup, boundary_lookup = build_lookups()
    print(f"  CSV: {len(csv_lookup)} towns")
    print(f"  Boundary: {len(boundary_lookup)} towns\n")

    files = sorted(DATA_DIR.glob("Vermont_*.geojson"))
    print(f"Files: {[f.name for f in files]}\n")

    for fpath in files:
        print(f"Processing {fpath.name}…")
        with open(fpath) as f:
            fc = json.load(f)

        features = fc["features"]
        total    = len(features)

        c_csv      = 0
        c_boundary = 0
        c_null     = 0

        for feat in features:
            p   = feat.get("properties") or {}
            gid = p.get("GEOIDTXT")

            # Only update null fields (don't overwrite already-filled values)
            needs_fill = (
                p.get("Municipal_Name") is None or
                p.get("County") is None or
                p.get("RPC") is None
            )
            if not needs_fill:
                continue

            vals = resolve(gid, csv_lookup, boundary_lookup)

            if p.get("Municipal_Name") is None:
                p["Municipal_Name"] = vals["Municipal_Name"]
            if p.get("County") is None:
                p["County"] = vals["County"]
            if p.get("RPC") is None:
                p["RPC"] = vals["RPC"]

            if gid and gid in csv_lookup:
                c_csv += 1
            elif gid and gid in boundary_lookup:
                c_boundary += 1
            else:
                c_null += 1

        print(f"  {total:>8,} total features")
        print(f"  {c_csv:>8,} filled from CSV")
        print(f"  {c_boundary:>8,} filled from boundary file")
        print(f"  {c_null:>8,} still null (no GEOIDTXT match)")

        # Final coverage
        nn_mun    = sum(1 for f in features if f["properties"].get("Municipal_Name"))
        nn_county = sum(1 for f in features if f["properties"].get("County"))
        nn_rpc    = sum(1 for f in features if f["properties"].get("RPC"))
        print(f"  Municipal_Name: {nn_mun:,}/{total:,} ({nn_mun/total*100:.1f}%)")
        print(f"  County:         {nn_county:,}/{total:,} ({nn_county/total*100:.1f}%)")
        print(f"  RPC:            {nn_rpc:,}/{total:,} ({nn_rpc/total*100:.1f}%)")

        with open(fpath, "w") as f:
            json.dump(fc, f, separators=(",", ":"))

        size_mb = os.path.getsize(fpath) / 1024 / 1024
        print(f"  → {fpath.name} ({size_mb:.1f} MB)\n")

    print("Done.")


if __name__ == "__main__":
    main()
