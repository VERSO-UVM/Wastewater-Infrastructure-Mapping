#!/usr/bin/env python3
"""
Rewrite Vermont_LinearFeatures.geojson to conform to the SoV 17-field schema.

Changes applied (in order):
  1. Fill GEOIDTXT from TownName via municipal_geoid CSV (before TownName is dropped)
  2. Drop non-schema fields: TownName, SourceFile, Shape_Length
  3. Generate UUID4 GlobalID for features missing one
  4. Fix Audience: null / "Private" → "Public"
  5. Infer SystemType from Type code where SystemType is null
  6. Convert CreateDate integer epoch-ms → HTTP date string
  7. Set Source = 0 → null (0 not in SoV source domain)
  8. Reassign OBJECTID sequentially 1..N

Output: data/original merged into one/Vermont_LinearFeatures_SoV.geojson
"""

import csv
import json
import uuid
import datetime
from pathlib import Path

ROOT      = Path(__file__).parent.parent
INPUT     = ROOT / "data" / "original merged into one" / "Vermont_LinearFeatures.geojson"
OUTPUT    = ROOT / "data" / "original merged into one" / "Vermont_LinearFeatures_SoV.geojson"
GEOID_CSV = ROOT / "data" / "municipal_geoid_county_rpc_fips.csv"

# SoV 17-field output order
SOV_FIELDS = [
    "OBJECTID", "GlobalID", "GEOIDTXT", "SystemType", "Type", "Status",
    "Owner", "PermitNo", "Audience", "Source", "SourceDate", "SourceNotes",
    "Notes", "Creator", "CreateDate", "Editor", "EditDate",
]

# Type code → SystemType inference (unambiguous mappings only)
TYPE_TO_SYSTEMTYPE = {
    2:  "Stormwater",
    3:  "Wastewater",
    4:  "Stormwater",
    5:  "Stormwater",
    6:  "Stormwater",
    7:  "Stormwater",
    8:  "Stormwater",
    10: "Stormwater",
    12: "Stormwater",
    13: "Combined",
    14: "Stormwater",
    15: "Water",
    16: "Stormwater",
    17: "Stormwater",
    18: "Stormwater",
    19: "Water",
}


def load_geoid_lookup(csv_path):
    """Build {municipal_name_lower: geoidtxt} from the CSV."""
    lookup = {}
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            name = row["Municipal_Name"].strip().lower()
            geoid = row["GEO_ID"].strip()
            if geoid:
                lookup[name] = geoid
    return lookup


def epoch_ms_to_http(epoch_ms):
    """Convert integer millisecond epoch to HTTP date string."""
    dt = datetime.datetime.fromtimestamp(epoch_ms / 1000, tz=datetime.timezone.utc)
    return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")


def fix_props(props, objectid, geoid_lookup):
    p = dict(props)  # copy

    # ── 1. Fill GEOIDTXT from TownName before dropping it ──────────────────────
    if not p.get("GEOIDTXT"):
        town = (p.get("TownName") or "").strip().lower()
        if town and town in geoid_lookup:
            p["GEOIDTXT"] = geoid_lookup[town]

    # ── 2. Drop non-schema fields ───────────────────────────────────────────────
    for f in ("TownName", "SourceFile", "Shape_Length"):
        p.pop(f, None)

    # ── 3. GlobalID — generate if missing ──────────────────────────────────────
    if not p.get("GlobalID"):
        p["GlobalID"] = "{" + str(uuid.uuid4()).upper() + "}"

    # ── 4. Audience ─────────────────────────────────────────────────────────────
    if p.get("Audience") != "Public":
        p["Audience"] = "Public"

    # ── 5. Infer SystemType from Type ───────────────────────────────────────────
    if not p.get("SystemType"):
        t = p.get("Type")
        inferred = TYPE_TO_SYSTEMTYPE.get(t)
        if inferred:
            p["SystemType"] = inferred

    # ── 6. CreateDate integer epoch → HTTP date string ──────────────────────────
    cd = p.get("CreateDate")
    if isinstance(cd, int):
        p["CreateDate"] = epoch_ms_to_http(cd)

    # ── 7. Source = 0 → null ────────────────────────────────────────────────────
    if p.get("Source") == 0:
        p["Source"] = None

    # ── 8. Reassign OBJECTID ────────────────────────────────────────────────────
    p["OBJECTID"] = objectid

    # ── Build output in canonical SoV field order ───────────────────────────────
    return {f: p.get(f) for f in SOV_FIELDS}


def main():
    print(f"Loading {INPUT.name}…")
    with open(INPUT) as f:
        data = json.load(f)

    features = data["features"]
    total = len(features)
    print(f"  {total:,} features\n")

    geoid_lookup = load_geoid_lookup(GEOID_CSV)
    print(f"Loaded GEOID lookup: {len(geoid_lookup)} municipalities\n")

    # Counters
    c_geoid_filled   = 0
    c_globalid_gen   = 0
    c_audience_fixed = 0
    c_systemtype_inf = 0
    c_date_converted = 0
    c_source_zeroed  = 0

    out_features = []

    for i, feat in enumerate(features, start=1):
        p = feat.get("properties") or {}

        # Track before fixing
        had_geoid      = bool(p.get("GEOIDTXT"))
        had_globalid   = bool(p.get("GlobalID"))
        had_systemtype = bool(p.get("SystemType"))
        audience_ok    = p.get("Audience") == "Public"
        date_is_int    = isinstance(p.get("CreateDate"), int)
        source_zero    = p.get("Source") == 0

        new_props = fix_props(p, objectid=i, geoid_lookup=geoid_lookup)

        # Count changes
        if not had_geoid and new_props.get("GEOIDTXT"):
            c_geoid_filled += 1
        if not had_globalid:
            c_globalid_gen += 1
        if not audience_ok:
            c_audience_fixed += 1
        if not had_systemtype and new_props.get("SystemType"):
            c_systemtype_inf += 1
        if date_is_int:
            c_date_converted += 1
        if source_zero:
            c_source_zeroed += 1

        out_features.append({
            "type": "Feature",
            "geometry": feat.get("geometry"),
            "properties": new_props,
        })

        if i % 50000 == 0:
            print(f"  processed {i:,}/{total:,}…")

    out_fc = {"type": "FeatureCollection", "features": out_features}

    print(f"\nWriting {OUTPUT.name}…")
    with open(OUTPUT, "w") as f:
        json.dump(out_fc, f, separators=(",", ":"))

    import os
    size_mb = os.path.getsize(OUTPUT) / 1024 / 1024

    print(f"  → {OUTPUT} ({total:,} features, {size_mb:.1f} MB)\n")
    print("=" * 55)
    print("CHANGES APPLIED")
    print("=" * 55)
    print(f"  GEOIDTXT filled from TownName lookup: {c_geoid_filled:>7,}")
    print(f"  GlobalID generated (new UUID4):       {c_globalid_gen:>7,}")
    print(f"  Audience fixed → 'Public':            {c_audience_fixed:>7,}")
    print(f"  SystemType inferred from Type:        {c_systemtype_inf:>7,}")
    print(f"  CreateDate epoch→HTTP date string:    {c_date_converted:>7,}")
    print(f"  Source 0 → null:                      {c_source_zeroed:>7,}")
    print(f"  OBJECTID reassigned 1..{total:,}")

    # Quick validation: check output schema
    print("\nValidation — field coverage in output:")
    from collections import defaultdict
    nn = defaultdict(int)
    for feat in out_features:
        for k, v in feat["properties"].items():
            if v is not None:
                nn[k] += 1
    for field in SOV_FIELDS:
        count = nn[field]
        pct = count / total * 100
        print(f"  {field:<15} {count:>8,}  ({pct:5.1f}%)")

    # Check for any unexpected extra fields
    all_keys = set()
    for feat in out_features[:1000]:
        all_keys.update(feat["properties"].keys())
    extra = all_keys - set(SOV_FIELDS)
    if extra:
        print(f"\n  ⚠ Unexpected fields still present: {extra}")
    else:
        print(f"\n  ✓ Output contains exactly the 17 SoV schema fields")


if __name__ == "__main__":
    main()
