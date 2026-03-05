#!/usr/bin/env python3
"""
Spatial join: fill null GEOIDTXT in Vermont_PointFeatures_SoV.geojson
using town boundary polygons. Updates the file in-place.
"""

import json
from pathlib import Path

ROOT        = Path(__file__).parent.parent
BOUNDARIES  = ROOT / "data" / "FS_VCGI_OPENDATA_Boundary_BNDHASH_poly_towns_SP_v1_-669012076166787740.geojson"
POINTS      = ROOT / "data" / "original merged into one" / "Vermont_PointFeatures_SoV.geojson"


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


def point_in_polygon_geom(px, py, geom):
    t = geom["type"]
    coords = geom["coordinates"]
    polygons = [coords] if t == "Polygon" else coords if t == "MultiPolygon" else []
    for rings in polygons:
        if point_in_ring(px, py, rings[0]):
            if not any(point_in_ring(px, py, h) for h in rings[1:]):
                return True
    return False


def nearest_town(px, py, towns):
    import math
    best_dist, best_geoid = float("inf"), None
    for geoid, name, geom, minx, miny, maxx, maxy in towns:
        cx = (minx + maxx) / 2
        cy = (miny + maxy) / 2
        d = math.hypot(px - cx, py - cy)
        if d < best_dist:
            best_dist, best_geoid = d, geoid
    return best_geoid


def main():
    print("Loading town boundaries…")
    with open(BOUNDARIES) as f:
        towns_fc = json.load(f)

    towns = []
    for feat in towns_fc["features"]:
        p    = feat["properties"]
        geom = feat["geometry"]
        t    = geom["type"]
        outer = geom["coordinates"][0] if t == "Polygon" else \
                max(geom["coordinates"], key=lambda p: len(p[0]))[0]
        minx, miny, maxx, maxy = ring_bbox(outer)
        towns.append((p["TOWNGEOID"], p.get("TOWNNAMEMC"), geom, minx, miny, maxx, maxy))

    print(f"  {len(towns)} town polygons\n")

    print(f"Loading {POINTS.name}…")
    with open(POINTS) as f:
        fc = json.load(f)

    features  = fc["features"]
    total     = len(features)
    null_idx  = [i for i, f in enumerate(features) if not f["properties"].get("GEOIDTXT")]
    print(f"  {total:,} features, {len(null_idx):,} with null GEOIDTXT\n")

    filled = no_match = 0

    for n, idx in enumerate(null_idx, 1):
        feat = features[idx]
        geom = feat.get("geometry")
        if not geom or geom["type"] != "Point":
            no_match += 1
            continue

        px, py = geom["coordinates"][0], geom["coordinates"][1]
        matched = None

        for (geoid, name, tgeom, minx, miny, maxx, maxy) in towns:
            if minx <= px <= maxx and miny <= py <= maxy:
                if point_in_polygon_geom(px, py, tgeom):
                    matched = geoid
                    break

        # Fallback: nearest town centroid (for points on/just outside boundary)
        if not matched:
            matched = nearest_town(px, py, towns)
            if matched:
                no_match += 1  # count as fallback, not clean match
                features[idx]["properties"]["GEOIDTXT"] = matched
                continue

        if matched:
            features[idx]["properties"]["GEOIDTXT"] = matched
            filled += 1

        if n % 5000 == 0:
            print(f"  {n:,}/{len(null_idx):,} processed…")

    print(f"\nResults:")
    print(f"  Filled by polygon containment: {filled:,}")
    print(f"  Filled by nearest-neighbour:   {no_match:,}")

    print(f"\nWriting updated {POINTS.name}…")
    with open(POINTS, "w") as f:
        json.dump(fc, f, separators=(",", ":"))

    import os
    remaining = sum(1 for f in features if not f["properties"].get("GEOIDTXT"))
    print(f"  → {os.path.getsize(POINTS)/1024/1024:.1f} MB")
    print(f"  Remaining null GEOIDTXT: {remaining}")


if __name__ == "__main__":
    main()
