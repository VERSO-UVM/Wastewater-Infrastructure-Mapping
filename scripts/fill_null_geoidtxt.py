#!/usr/bin/env python3
"""
Spatial join: fill null GEOIDTXT (and Municipal_Name, County, RPC) in
Vermont_Water_Features.geojson and Vermont_Treatment_Facilities.geojson.

Uses the enriched town boundary file (already has Municipal_Name, County, RPC).
For polygons, uses the centroid of the outer ring as the representative point.
For points, uses the point itself.

Updates files in-place.
"""

import json
import os
from pathlib import Path

ROOT       = Path(__file__).parent.parent
DATA_DIR   = ROOT / "data"
BOUNDARY   = DATA_DIR / "FS_VCGI_OPENDATA_Boundary_BNDHASH_poly_towns_SP_v1_-669012076166787740.geojson"

FILES = [
    "Vermont_Water_Features.geojson",
    "Vermont_Treatment_Facilities.geojson",
]


# ── Geometry helpers ────────────────────────────────────────────────────────

def ring_bbox(ring):
    xs = [c[0] for c in ring]
    ys = [c[1] for c in ring]
    return min(xs), min(ys), max(xs), max(ys)


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


def point_in_geom(px, py, geom):
    t = geom["type"]
    coords = geom["coordinates"]
    polys = [coords] if t == "Polygon" else coords if t == "MultiPolygon" else []
    for rings in polys:
        if point_in_ring(px, py, rings[0]):
            if not any(point_in_ring(px, py, h) for h in rings[1:]):
                return True
    return False


def representative_point(feat):
    geom = feat.get("geometry")
    if not geom:
        return None, None
    t = geom["type"]
    coords = geom["coordinates"]
    if t == "Point":
        return coords[0], coords[1]
    elif t == "Polygon" and coords and coords[0]:
        ring = coords[0]
        return sum(c[0] for c in ring) / len(ring), sum(c[1] for c in ring) / len(ring)
    elif t == "MultiPolygon" and coords:
        largest = max(coords, key=lambda p: len(p[0]))
        ring = largest[0]
        return sum(c[0] for c in ring) / len(ring), sum(c[1] for c in ring) / len(ring)
    return None, None


def main():
    # ── Load enriched town boundaries ───────────────────────────────────────
    print("Loading town boundaries…")
    with open(BOUNDARY) as f:
        towns_fc = json.load(f)

    towns = []
    for feat in towns_fc["features"]:
        p    = feat["properties"]
        geom = feat["geometry"]
        t    = geom["type"]

        all_outer = []
        if t == "Polygon":
            all_outer = geom["coordinates"][0]
        elif t == "MultiPolygon":
            for poly in geom["coordinates"]:
                all_outer.extend(poly[0])

        if not all_outer:
            continue

        bbox = ring_bbox(all_outer)
        towns.append({
            "geoid":          p.get("TOWNGEOID"),
            "Municipal_Name": p.get("Municipal_Name"),
            "County":         p.get("County"),
            "RPC":            p.get("RPC"),
            "geom":           geom,
            "bbox":           bbox,
        })

    print(f"  {len(towns)} town polygons loaded\n")

    # ── Process each file ───────────────────────────────────────────────────
    for fname in FILES:
        fpath = DATA_DIR / fname
        if not fpath.exists():
            print(f"SKIP {fname} (not found)")
            continue

        print(f"Processing {fname}…")
        with open(fpath) as f:
            fc = json.load(f)

        features = fc["features"]
        total    = len(features)
        null_idx = [i for i, f in enumerate(features)
                    if not f.get("properties", {}).get("GEOIDTXT")]

        print(f"  {total:,} features, {len(null_idx):,} with null GEOIDTXT")

        filled   = 0
        no_match = 0

        for idx in null_idx:
            feat = features[idx]
            px, py = representative_point(feat)

            if px is None:
                no_match += 1
                continue

            matched = None
            for town in towns:
                minx, miny, maxx, maxy = town["bbox"]
                if minx <= px <= maxx and miny <= py <= maxy:
                    if point_in_geom(px, py, town["geom"]):
                        matched = town
                        break

            if matched:
                p = features[idx]["properties"]
                p["GEOIDTXT"]      = matched["geoid"]
                p["Municipal_Name"] = matched["Municipal_Name"]
                p["County"]         = matched["County"]
                p["RPC"]            = matched["RPC"]
                filled += 1
            else:
                no_match += 1

        print(f"  Filled: {filled:,}")
        print(f"  Still null: {no_match:,}")

        # Coverage
        for field in ("GEOIDTXT", "Municipal_Name", "County", "RPC"):
            n = sum(1 for f in features if f.get("properties", {}).get(field))
            print(f"  {field}: {n:,}/{total:,} ({n/total*100:.1f}%)")

        with open(fpath, "w") as f:
            json.dump(fc, f, separators=(",", ":"))
        size_mb = os.path.getsize(fpath) / 1024 / 1024
        print(f"  → {fname} ({size_mb:.1f} MB)\n")

    print("Done.")


if __name__ == "__main__":
    main()
