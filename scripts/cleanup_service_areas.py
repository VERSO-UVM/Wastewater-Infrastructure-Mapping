#!/usr/bin/env python3
"""
Light cleanup for Vermont_ServiceAreas.geojson.

Changes:
  1. Fill null GEOIDTXT via spatial join against town boundary polygons
  2. Drop Shape_Area and Shape_Length (mixed/unreliable units — degrees vs metres)
  3. Reassign OBJECTID sequentially 1..N
  4. Creator = '0' → null
  5. Fill null SystemName from TownName (reasonable fallback)
  6. Normalise GISDate / GISUpdate to YYYY or YYYY-MM-DD where parseable

Writes in-place.
"""

import json
import re
from pathlib import Path

ROOT        = Path(__file__).parent.parent
BOUNDARIES  = ROOT / "data" / "FS_VCGI_OPENDATA_Boundary_BNDHASH_poly_towns_SP_v1_-669012076166787740.geojson"
SERVICE     = ROOT / "data" / "Vermont_ServiceAreas.geojson"

# ── Date normalisation ─────────────────────────────────────────────────────────

MONTH_NAMES = {
    "january":"01","february":"02","march":"03","april":"04",
    "may":"05","june":"06","july":"07","august":"08",
    "september":"09","october":"10","november":"11","december":"12",
    "jan":"01","feb":"02","mar":"03","apr":"04","jun":"06",
    "jul":"07","aug":"08","sep":"09","oct":"10","nov":"11","dec":"12",
}

def normalise_date(val):
    """Return YYYY or YYYY-MM-DD; return original string if unparseable."""
    if not val:
        return val
    v = str(val).strip()
    # Already a 4-digit year
    if re.match(r'^\d{4}$', v):
        return v
    # MM/DD/YYYY or M/D/YYYY
    m = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})$', v)
    if m:
        return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    # Month DD, YYYY
    m = re.match(r'^([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})$', v)
    if m:
        mon = MONTH_NAMES.get(m.group(1).lower())
        if mon:
            return f"{m.group(3)}-{mon}-{int(m.group(2)):02d}"
    # DD/MM/YYYY — ambiguous, skip
    return v

# ── Spatial helpers ────────────────────────────────────────────────────────────

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
    polys = [geom["coordinates"]] if t == "Polygon" else geom["coordinates"]
    for rings in polys:
        if point_in_ring(px, py, rings[0]):
            if not any(point_in_ring(px, py, h) for h in rings[1:]):
                return True
    return False

def polygon_centroid(geom):
    """Rough centroid of the largest ring."""
    t = geom["type"]
    if t == "Polygon":
        ring = geom["coordinates"][0]
    else:
        ring = max(geom["coordinates"], key=lambda p: len(p[0]))[0]
    xs = [c[0] for c in ring]
    ys = [c[1] for c in ring]
    return sum(xs) / len(xs), sum(ys) / len(ys)

def find_geoid(geom, towns):
    """Return TOWNGEOID for the town polygon containing the feature centroid."""
    px, py = polygon_centroid(geom)
    for geoid, tgeom, minx, miny, maxx, maxy in towns:
        if minx <= px <= maxx and miny <= py <= maxy:
            if point_in_polygon_geom(px, py, tgeom):
                return geoid
    # Fallback: nearest centroid
    import math
    best_d, best_geoid = float("inf"), None
    for geoid, tgeom, minx, miny, maxx, maxy in towns:
        cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
        d = math.hypot(px - cx, py - cy)
        if d < best_d:
            best_d, best_geoid = d, geoid
    return best_geoid

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    # Load town boundaries
    print("Loading town boundaries…")
    with open(BOUNDARIES) as f:
        towns_fc = json.load(f)
    towns = []
    for feat in towns_fc["features"]:
        geom = feat["geometry"]
        t = geom["type"]
        outer = geom["coordinates"][0] if t == "Polygon" else \
                max(geom["coordinates"], key=lambda p: len(p[0]))[0]
        minx, miny, maxx, maxy = ring_bbox(outer)
        towns.append((feat["properties"]["TOWNGEOID"], geom, minx, miny, maxx, maxy))
    print(f"  {len(towns)} town polygons\n")

    # Load service areas
    print(f"Loading {SERVICE.name}…")
    with open(SERVICE) as f:
        fc = json.load(f)
    features = fc["features"]
    total = len(features)
    print(f"  {total} features\n")

    c_geoid    = 0
    c_creator  = 0
    c_sysname  = 0
    c_date     = 0

    for i, feat in enumerate(features, start=1):
        p = feat["properties"]

        # 1. Fill null GEOIDTXT via spatial join
        if not p.get("GEOIDTXT") and feat.get("geometry"):
            p["GEOIDTXT"] = find_geoid(feat["geometry"], towns)
            c_geoid += 1

        # 2. Drop Shape_Area and Shape_Length
        p.pop("Shape_Area", None)
        p.pop("Shape_Length", None)

        # 3. OBJECTID sequential
        p["OBJECTID"] = i

        # 4. Creator '0' → null
        if p.get("Creator") == "0":
            p["Creator"] = None
            c_creator += 1

        # 5. Fill null SystemName from TownName
        if not p.get("SystemName") and p.get("TownName"):
            p["SystemName"] = p["TownName"]
            c_sysname += 1

        # 6. Normalise GISDate / GISUpdate
        for field in ("GISDate", "GISUpdate"):
            orig = p.get(field)
            normed = normalise_date(orig)
            if normed != orig:
                p[field] = normed
                c_date += 1

    print("CHANGES APPLIED")
    print("=" * 45)
    print(f"  GEOIDTXT filled (spatial join):  {c_geoid}")
    print(f"  Creator '0' → null:              {c_creator}")
    print(f"  SystemName filled from TownName: {c_sysname}")
    print(f"  Date values normalised:          {c_date}")
    print(f"  Shape_Area / Shape_Length:       dropped")
    print(f"  OBJECTID reassigned 1..{total}")

    # Write
    print(f"\nWriting {SERVICE.name}…")
    with open(SERVICE, "w") as f:
        json.dump(fc, f, separators=(",", ":"))

    import os
    size_kb = os.path.getsize(SERVICE) / 1024
    print(f"  → {size_kb:.0f} KB")

    # Validation
    print("\nFinal field coverage:")
    from collections import defaultdict
    nn = defaultdict(int)
    all_fields = set()
    for feat in features:
        for k, v in feat["properties"].items():
            all_fields.add(k)
            if v is not None:
                nn[k] += 1

    for field in sorted(all_fields):
        count = nn[field]
        pct = count / total * 100
        print(f"  {field:<22} {count:>5}  ({pct:5.1f}%)")

    remaining_null_geoid = sum(1 for f in features if not f["properties"].get("GEOIDTXT"))
    print(f"\n  Remaining null GEOIDTXT: {remaining_null_geoid}")


if __name__ == "__main__":
    main()
