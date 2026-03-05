#!/usr/bin/env python3
"""
Step 1: Enrich the town boundary file with Municipal_Name, County, and RPC.

Sources:
  - municipal_geoid_county_rpc_fips.csv          (198 towns — primary, most accurate)
  - FS_VCGI_OPENDATA_Boundary_BNDHASH_poly_rpcs  (11 RPC polygons — spatial fallback)
  - Town TOWNNAMEMC / CNTY fields                (256 towns — names + county codes)

Strategy per town (TOWNGEOID):
  1. CSV match       → use CSV Municipal_Name, County, RPC (most authoritative)
  2. Spatial join    → compute town centroid, find containing RPC polygon → get RPC
     then derive County from CNTY code
     and Municipal_Name from TOWNNAMEMC

Adds fields: Municipal_Name, County, RPC to every feature in the boundary file.
Saves enriched boundary in-place.

Step 2: Use the enriched boundary as a complete lookup to fill null Municipal_Name,
County, and RPC in all Vermont_*.geojson files (keyed on GEOIDTXT = TOWNGEOID).
"""

import csv
import json
import os
from pathlib import Path

ROOT       = Path(__file__).parent.parent
DATA_DIR   = ROOT / "data"
BOUNDARY   = DATA_DIR / "FS_VCGI_OPENDATA_Boundary_BNDHASH_poly_towns_SP_v1_-669012076166787740.geojson"
RPC_BOUNDS = DATA_DIR / "FS_VCGI_OPENDATA_Boundary_BNDHASH_poly_rpcs_SP_v1_6311464461427737166.geojson"
CSV_PATH   = DATA_DIR / "municipal_geoid_county_rpc_fips.csv"

VERMONT_FILES = [
    "Vermont_Linear_Features.geojson",
    "Vermont_Point_Features.geojson",
    "Vermont_ServiceAreas.geojson",
    "Vermont_Treatment_Facilities.geojson",
    "Vermont_Water_Features.geojson",
]

# Vermont county FIPS → county name
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

# Normalize RPC abbreviations to match existing data
RPC_INITIALS_MAP = {
    "NWRPC": "NRPC",   # boundary file uses NWRPC; data uses NRPC
}


# ── Geometry helpers ────────────────────────────────────────────────────────

def ring_centroid(ring):
    """Simple arithmetic centroid of a ring's vertices."""
    xs = [c[0] for c in ring]
    ys = [c[1] for c in ring]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def geom_centroid(geom):
    """Centroid of the largest outer ring of a Polygon or MultiPolygon."""
    t = geom["type"]
    coords = geom["coordinates"]
    if t == "Polygon":
        return ring_centroid(coords[0])
    elif t == "MultiPolygon":
        largest = max(coords, key=lambda p: len(p[0]))
        return ring_centroid(largest[0])
    return None, None


def ring_bbox(ring):
    xs = [c[0] for c in ring]
    ys = [c[1] for c in ring]
    return min(xs), min(ys), max(xs), max(ys)


def geom_bbox(geom):
    t = geom["type"]
    coords = geom["coordinates"]
    all_pts = []
    if t == "Polygon":
        all_pts = coords[0]
    elif t == "MultiPolygon":
        for poly in coords:
            all_pts.extend(poly[0])
    return ring_bbox(all_pts) if all_pts else None


def point_in_ring(px, py, ring):
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > py) != (yj > py)) and \
           (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def point_in_polygon_geom(px, py, geom):
    t = geom["type"]
    coords = geom["coordinates"]
    polygons = [coords] if t == "Polygon" else coords if t == "MultiPolygon" else []
    for rings in polygons:
        if point_in_ring(px, py, rings[0]):
            if not any(point_in_ring(px, py, h) for h in rings[1:]):
                return True
    return False


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    # ── Load CSV lookup (198 towns) ─────────────────────────────────────────
    print("Loading CSV lookup…")
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
    print(f"  {len(csv_lookup)} towns in CSV\n")

    # ── Load RPC polygons (11 regions) ──────────────────────────────────────
    print("Loading RPC boundaries…")
    with open(RPC_BOUNDS) as f:
        rpc_fc = json.load(f)

    rpcs = []
    for feat in rpc_fc["features"]:
        p      = feat["properties"]
        abbrev = p.get("INITIALS", "")
        abbrev = RPC_INITIALS_MAP.get(abbrev, abbrev)   # normalize
        geom   = feat["geometry"]
        bbox   = geom_bbox(geom)
        if abbrev and bbox:
            rpcs.append((abbrev, geom, bbox))
            print(f"  {abbrev}: {p.get('SHORTNAME')}")
    print(f"  {len(rpcs)} RPC polygons loaded\n")

    def spatial_rpc(px, py):
        for (abbrev, geom, (minx, miny, maxx, maxy)) in rpcs:
            if minx <= px <= maxx and miny <= py <= maxy:
                if point_in_polygon_geom(px, py, geom):
                    return abbrev
        return None

    # ── Enrich town boundary file ───────────────────────────────────────────
    print("Enriching town boundary file…")
    with open(BOUNDARY) as f:
        towns_fc = json.load(f)

    lookup = {}           # TOWNGEOID → {Municipal_Name, County, RPC}
    csv_hits = 0
    spatial_hits = 0
    unresolved = 0

    for feat in towns_fc["features"]:
        p    = feat["properties"]
        gid  = p.get("TOWNGEOID", "").strip()
        cnty = p.get("CNTY")

        county   = CNTY_TO_COUNTY.get(cnty)
        raw_name = p.get("TOWNNAMEMC") or p.get("TOWNNAME")

        if gid and gid in csv_lookup:
            # CSV is most authoritative
            vals = csv_lookup[gid]
            csv_hits += 1
        else:
            # Spatial join for RPC
            cx, cy = geom_centroid(feat["geometry"])
            rpc = spatial_rpc(cx, cy) if cx is not None else None
            if rpc:
                spatial_hits += 1
            else:
                unresolved += 1
            vals = {
                "Municipal_Name": raw_name,
                "County":         county,
                "RPC":            rpc,
            }

        # Write enrichment fields onto the town polygon properties
        p["Municipal_Name"] = vals["Municipal_Name"]
        p["County"]         = vals["County"]
        p["RPC"]            = vals["RPC"]

        if gid:
            lookup[gid] = {
                "Municipal_Name": vals["Municipal_Name"],
                "County":         vals["County"],
                "RPC":            vals["RPC"],
            }

    total_towns = len(towns_fc["features"])
    print(f"  {total_towns} towns total")
    print(f"  {csv_hits} resolved from CSV")
    print(f"  {spatial_hits} resolved by spatial join")
    print(f"  {unresolved} unresolved")

    with open(BOUNDARY, "w") as f:
        json.dump(towns_fc, f, separators=(",", ":"))
    size_mb = os.path.getsize(BOUNDARY) / 1024 / 1024
    print(f"  → boundary file saved ({size_mb:.1f} MB)\n")

    print(f"Lookup built: {len(lookup)} TOWNGEOID entries\n")

    # ── Fill nulls in all Vermont_*.geojson ─────────────────────────────────
    for fname in VERMONT_FILES:
        fpath = DATA_DIR / fname
        if not fpath.exists():
            print(f"  SKIP {fname} (not found)")
            continue

        print(f"Processing {fname}…")
        with open(fpath) as f:
            fc = json.load(f)

        features = fc["features"]
        total    = len(features)

        updated  = 0
        no_match = 0

        for feat in features:
            p   = feat.get("properties") or {}
            gid = p.get("GEOIDTXT")

            needs = (
                p.get("Municipal_Name") is None or
                p.get("County") is None or
                p.get("RPC") is None
            )
            if not needs:
                continue

            if gid and gid in lookup:
                vals = lookup[gid]
                if p.get("Municipal_Name") is None:
                    p["Municipal_Name"] = vals["Municipal_Name"]
                if p.get("County") is None:
                    p["County"] = vals["County"]
                if p.get("RPC") is None:
                    p["RPC"] = vals["RPC"]
                updated += 1
            else:
                no_match += 1

        # Coverage stats
        nn_mun    = sum(1 for f in features if f["properties"].get("Municipal_Name"))
        nn_county = sum(1 for f in features if f["properties"].get("County"))
        nn_rpc    = sum(1 for f in features if f["properties"].get("RPC"))

        print(f"  {total:,} features | updated: {updated:,} | no GEOIDTXT match: {no_match:,}")
        print(f"  Municipal_Name: {nn_mun:,}/{total:,} ({nn_mun/total*100:.1f}%)")
        print(f"  County:         {nn_county:,}/{total:,} ({nn_county/total*100:.1f}%)")
        print(f"  RPC:            {nn_rpc:,}/{total:,} ({nn_rpc/total*100:.1f}%)")

        with open(fpath, "w") as f:
            json.dump(fc, f, separators=(",", ":"))
        size_mb = os.path.getsize(fpath) / 1024 / 1024
        print(f"  → {fname} ({size_mb:.1f} MB)\n")

    print("Done.")


if __name__ == "__main__":
    main()
