#!/usr/bin/env python3
"""
Spatial join: fill null RPC in all Vermont_*.geojson files using RPC_Boundaries.geojson.

Strategy:
  - For each feature with a null RPC, compute a representative point
    (the point itself for points, midpoint for lines, centroid for polygons)
  - Test containment against each RPC boundary polygon
  - Assign the matching RPC_ABBREV

Updates files in-place.
"""

import json
import os
from pathlib import Path

ROOT       = Path(__file__).parent.parent
DATA_DIR   = ROOT / "data"
RPC_FILE   = DATA_DIR / "RPC_Boundaries.geojson"

FILES = [
    "Vermont_Linear_Features.geojson",
    "Vermont_Point_Features.geojson",
    "Vermont_ServiceAreas.geojson",
    "Vermont_Treatment_Facilities.geojson",
    "Vermont_Water_Features.geojson",
]


# ── Geometry helpers ────────────────────────────────────────────────────────

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
    elif t == "LineString":
        all_pts = coords
    elif t == "MultiLineString":
        for seg in coords:
            all_pts.extend(seg)
    elif t == "Point":
        return coords[0], coords[1], coords[0], coords[1]
    if all_pts:
        return ring_bbox(all_pts)
    return None


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


def representative_point(feat):
    """Return (lon, lat) for any geometry type."""
    geom = feat.get("geometry")
    if not geom:
        return None, None
    t = geom["type"]
    coords = geom["coordinates"]
    if t == "Point":
        return coords[0], coords[1]
    elif t == "LineString" and coords:
        mid = coords[len(coords) // 2]
        return mid[0], mid[1]
    elif t == "MultiLineString" and coords:
        longest = max(coords, key=len)
        mid = longest[len(longest) // 2]
        return mid[0], mid[1]
    elif t == "Polygon" and coords and coords[0]:
        ring = coords[0]
        cx = sum(c[0] for c in ring) / len(ring)
        cy = sum(c[1] for c in ring) / len(ring)
        return cx, cy
    elif t == "MultiPolygon" and coords:
        largest = max(coords, key=lambda p: len(p[0]))
        ring = largest[0]
        cx = sum(c[0] for c in ring) / len(ring)
        cy = sum(c[1] for c in ring) / len(ring)
        return cx, cy
    return None, None


def main():
    # ── Load RPC boundaries ─────────────────────────────────────────────────
    print("Loading RPC boundaries…")
    with open(RPC_FILE) as f:
        rpc_fc = json.load(f)

    rpcs = []
    for feat in rpc_fc["features"]:
        abbrev = feat["properties"].get("RPC_ABBREV")
        geom   = feat["geometry"]
        bbox   = geom_bbox(geom)
        if abbrev and bbox:
            rpcs.append((abbrev, geom, bbox))
            print(f"  {abbrev}: {feat['properties'].get('RPC_NAME')}")
    print(f"  {len(rpcs)} RPC polygon(s) loaded\n")

    if not rpcs:
        print("No RPC polygons found — nothing to do.")
        return

    # ── Process each file ───────────────────────────────────────────────────
    for fname in FILES:
        fpath = DATA_DIR / fname
        if not fpath.exists():
            print(f"  SKIP {fname} (not found)")
            continue

        print(f"Processing {fname}…")
        with open(fpath) as f:
            fc = json.load(f)

        features = fc["features"]
        total = len(features)
        null_idx = [i for i, feat in enumerate(features)
                    if feat.get("properties", {}).get("RPC") is None]

        print(f"  {total:,} total features, {len(null_idx):,} with null RPC")

        filled = 0
        no_match = 0

        for idx in null_idx:
            feat = features[idx]
            px, py = representative_point(feat)
            if px is None:
                no_match += 1
                continue

            matched = None
            for (abbrev, geom, (minx, miny, maxx, maxy)) in rpcs:
                if minx <= px <= maxx and miny <= py <= maxy:
                    if point_in_polygon_geom(px, py, geom):
                        matched = abbrev
                        break

            if matched:
                features[idx]["properties"]["RPC"] = matched
                filled += 1
            else:
                no_match += 1

        print(f"  Filled: {filled:,}")
        print(f"  Still null: {no_match:,}")

        # Final coverage
        nn_rpc = sum(1 for f in features if f.get("properties", {}).get("RPC"))
        print(f"  RPC coverage: {nn_rpc:,}/{total:,} ({nn_rpc/total*100:.1f}%)")

        with open(fpath, "w") as f:
            json.dump(fc, f, separators=(",", ":"))
        size_mb = os.path.getsize(fpath) / 1024 / 1024
        print(f"  → {fname} ({size_mb:.1f} MB)\n")

    print("Done.")


if __name__ == "__main__":
    main()
