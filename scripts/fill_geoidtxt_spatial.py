#!/usr/bin/env python3
"""
Spatial join: fill null GEOIDTXT in Vermont_LinearFeatures_SoV.geojson
using town boundary polygons (TOWNGEOID field).

Uses ray-casting point-in-polygon with bounding-box pre-filter.
No external GIS libraries required.

Updates the file in-place.
"""

import json
from pathlib import Path

ROOT        = Path(__file__).parent.parent
BOUNDARIES  = ROOT / "data" / "FS_VCGI_OPENDATA_Boundary_BNDHASH_poly_towns_SP_v1_-669012076166787740.geojson"
LINEAR      = ROOT / "data" / "original merged into one" / "Vermont_LinearFeatures_SoV.geojson"

# ── Geometry helpers ───────────────────────────────────────────────────────────

def ring_bbox(ring):
    xs = [c[0] for c in ring]
    ys = [c[1] for c in ring]
    return min(xs), min(ys), max(xs), max(ys)

def point_in_ring(px, py, ring):
    """Ray-casting point-in-polygon test for a single ring."""
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
    """Test point against a GeoJSON geometry (Polygon or MultiPolygon).
    Holes (inner rings) subtract from containment.
    """
    t = geom["type"]
    coords = geom["coordinates"]

    if t == "Polygon":
        polygons = [coords]
    elif t == "MultiPolygon":
        polygons = coords
    else:
        return False

    for rings in polygons:
        outer = rings[0]
        holes = rings[1:]
        if point_in_ring(px, py, outer):
            # Check not inside a hole
            if any(point_in_ring(px, py, h) for h in holes):
                continue
            return True
    return False

def line_midpoint(coords):
    """Return the midpoint of a LineString coordinate list."""
    n = len(coords)
    mid = coords[n // 2]
    return mid[0], mid[1]

def feature_representative_point(feat):
    """Return a (lon, lat) representative point for a linear feature."""
    geom = feat.get("geometry")
    if not geom:
        return None, None
    t = geom["type"]
    coords = geom["coordinates"]
    if t == "LineString" and coords:
        return line_midpoint(coords)
    elif t == "MultiLineString" and coords and coords[0]:
        # Use longest segment's midpoint
        longest = max(coords, key=len)
        return line_midpoint(longest)
    return None, None


def main():
    # ── Load town boundaries ───────────────────────────────────────────────────
    print(f"Loading town boundaries…")
    with open(BOUNDARIES) as f:
        towns_fc = json.load(f)

    # Build list of (towngeoid, townname, geom, bbox)
    towns = []
    for feat in towns_fc["features"]:
        p = feat["properties"]
        geoid = p.get("TOWNGEOID")
        name  = p.get("TOWNNAMEMC") or p.get("TOWNNAME")
        geom  = feat["geometry"]
        # Compute overall bbox for this town (across all rings/polygons)
        all_coords = []
        t = geom["type"]
        if t == "Polygon":
            all_coords = geom["coordinates"][0]
        elif t == "MultiPolygon":
            for poly in geom["coordinates"]:
                all_coords.extend(poly[0])
        if all_coords:
            minx, miny, maxx, maxy = ring_bbox(all_coords)
            towns.append((geoid, name, geom, minx, miny, maxx, maxy))

    print(f"  {len(towns)} town polygons indexed\n")

    # ── Load linear features ───────────────────────────────────────────────────
    print(f"Loading {LINEAR.name}…")
    with open(LINEAR) as f:
        linear_fc = json.load(f)

    features = linear_fc["features"]
    total = len(features)

    null_geoid = [i for i, f in enumerate(features) if not f["properties"].get("GEOIDTXT")]
    print(f"  {total:,} features, {len(null_geoid):,} with null GEOIDTXT\n")

    # ── Spatial join ───────────────────────────────────────────────────────────
    print("Running spatial join…")
    filled = 0
    no_match = 0
    no_geom = 0
    misses = []

    for idx in null_geoid:
        feat = features[idx]
        px, py = feature_representative_point(feat)

        if px is None:
            no_geom += 1
            continue

        matched_geoid = None
        matched_name  = None

        # Bbox pre-filter then full PiP
        for (geoid, name, geom, minx, miny, maxx, maxy) in towns:
            if not (minx <= px <= maxx and miny <= py <= maxy):
                continue
            if point_in_polygon_geom(px, py, geom):
                matched_geoid = geoid
                matched_name  = name
                break

        if matched_geoid:
            features[idx]["properties"]["GEOIDTXT"] = matched_geoid
            filled += 1
        else:
            no_match += 1
            misses.append((px, py, feat["properties"].get("Creator"), feat["properties"].get("Notes")))

        if (filled + no_match + no_geom) % 2000 == 0:
            done = filled + no_match + no_geom
            print(f"  {done:,}/{len(null_geoid):,} processed…")

    print(f"\nResults:")
    print(f"  Filled:    {filled:,}")
    print(f"  No match:  {no_match:,}")
    print(f"  No geom:   {no_geom:,}")

    if misses:
        print(f"\n  First 10 unmatched points (lon, lat):")
        for lon, lat, creator, notes in misses[:10]:
            print(f"    ({lon:.5f}, {lat:.5f})  creator={creator}  notes={notes!r:.40s}")

    # ── Write updated file ─────────────────────────────────────────────────────
    print(f"\nWriting updated {LINEAR.name}…")
    with open(LINEAR, "w") as f:
        json.dump(linear_fc, f, separators=(",", ":"))

    import os
    size_mb = os.path.getsize(LINEAR) / 1024 / 1024

    # Final null count
    remaining_null = sum(1 for f in features if not f["properties"].get("GEOIDTXT"))
    print(f"  → {LINEAR.name} ({total:,} features, {size_mb:.1f} MB)")
    print(f"  Remaining null GEOIDTXT: {remaining_null:,}")


if __name__ == "__main__":
    main()
