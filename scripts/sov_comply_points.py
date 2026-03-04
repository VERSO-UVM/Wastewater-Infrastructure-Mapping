#!/usr/bin/env python3
"""
Rewrite Vermont_PointFeatures.geojson to conform to the SoV 17-field schema.

Changes applied:
  1. Drop non-schema fields: TownName, SourceFile
  2. Generate UUID4 GlobalID for features missing one
  3. Fix SystemType " " (space) → null
  4. Infer SystemType from Type code where null
  5. Convert CreateDate integer epoch-ms → HTTP date string
  6. Reassign OBJECTID sequentially 1..N
  7. Set Editor null → "UVM"
  (GEOIDTXT spatial fill handled separately by fill_geoidtxt_spatial_points.py)

Output: data/original merged into one/Vermont_PointFeatures_SoV.geojson
"""

import json
import uuid
import datetime
from pathlib import Path

ROOT   = Path(__file__).parent.parent
INPUT  = ROOT / "data" / "original merged into one" / "Vermont_PointFeatures.geojson"
OUTPUT = ROOT / "data" / "original merged into one" / "Vermont_PointFeatures_SoV.geojson"

SOV_FIELDS = [
    "OBJECTID", "GlobalID", "GEOIDTXT", "SystemType", "Type", "Status",
    "Owner", "PermitNo", "Audience", "Source", "SourceDate", "SourceNotes",
    "Notes", "Creator", "CreateDate", "Editor", "EditDate",
]

# Point Type → SystemType (unambiguous mappings)
POINT_TYPE_TO_SYSTEMTYPE = {
    2:  "Stormwater",   # catch basin
    3:  "Stormwater",   # drain inlet
    4:  "Wastewater",   # sanitary manhole
    5:  "Stormwater",   # storm drain inlet
    6:  "Stormwater",   # stormwater outfall
    7:  "Stormwater",   # junction box
    8:  "Stormwater",   # storm manhole
    9:  "Stormwater",   # cleanout
    11: "Stormwater",   # drywell
    12: "Stormwater",   # catch basin variant
    14: "Stormwater",   # drain well
    15: "Stormwater",   # drain inlet DI
    16: "Stormwater",   # concrete box inlet
    19: "Stormwater",   # outlet structure
    22: "Wastewater",   # wastewater access point
    23: "Combined",     # CSO outfall
    24: "Combined",     # combined sewer interconnection
    27: "Stormwater",   # stand pipe
    28: "Stormwater",   # stormwater connection
    # Type 17 (cap/cleanout/roof drain) and 25 (pump station) are ambiguous — leave as-is
}


def epoch_ms_to_http(epoch_ms):
    dt = datetime.datetime.fromtimestamp(epoch_ms / 1000, tz=datetime.timezone.utc)
    return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")


def fix_props(props, objectid):
    p = dict(props)

    # 1. Drop non-schema fields
    for f in ("TownName", "SourceFile"):
        p.pop(f, None)

    # 2. GlobalID
    if not p.get("GlobalID"):
        p["GlobalID"] = "{" + str(uuid.uuid4()).upper() + "}"

    # 3. SystemType " " → null, then infer from Type
    st = p.get("SystemType")
    if st == " " or st == "":
        p["SystemType"] = None
    if not p.get("SystemType"):
        t = p.get("Type")
        inferred = POINT_TYPE_TO_SYSTEMTYPE.get(t)
        if inferred:
            p["SystemType"] = inferred

    # 4. CreateDate int → HTTP
    cd = p.get("CreateDate")
    if isinstance(cd, int):
        p["CreateDate"] = epoch_ms_to_http(cd)

    # 5. OBJECTID
    p["OBJECTID"] = objectid

    # 6. Editor null → "UVM"
    if not p.get("Editor"):
        p["Editor"] = "UVM"

    # Audience always Public
    if p.get("Audience") != "Public":
        p["Audience"] = "Public"

    return {f: p.get(f) for f in SOV_FIELDS}


def main():
    print(f"Loading {INPUT.name}…")
    with open(INPUT) as f:
        data = json.load(f)

    features = data["features"]
    total = len(features)
    print(f"  {total:,} features\n")

    c_globalid   = 0
    c_space_st   = 0
    c_infer_st   = 0
    c_date       = 0
    c_editor     = 0
    c_audience   = 0

    out_features = []

    for i, feat in enumerate(features, start=1):
        p = feat.get("properties") or {}

        had_globalid = bool(p.get("GlobalID"))
        had_st       = bool(p.get("SystemType"))
        space_st     = p.get("SystemType") in (" ", "")
        date_is_int  = isinstance(p.get("CreateDate"), int)
        no_editor    = not p.get("Editor")
        bad_aud      = p.get("Audience") != "Public"

        new_props = fix_props(p, objectid=i)

        if not had_globalid:           c_globalid += 1
        if space_st:                   c_space_st += 1
        if not had_st and new_props.get("SystemType"): c_infer_st += 1
        if date_is_int:                c_date += 1
        if no_editor:                  c_editor += 1
        if bad_aud:                    c_audience += 1

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
    print(f"  → {OUTPUT.name} ({total:,} features, {size_mb:.1f} MB)\n")

    print("=" * 55)
    print("CHANGES APPLIED")
    print("=" * 55)
    print(f"  GlobalID generated:              {c_globalid:>8,}")
    print(f"  SystemType ' ' → null:           {c_space_st:>8,}")
    print(f"  SystemType inferred from Type:   {c_infer_st:>8,}")
    print(f"  CreateDate epoch → HTTP string:  {c_date:>8,}")
    print(f"  Editor null → 'UVM':             {c_editor:>8,}")
    print(f"  Audience fixed → 'Public':       {c_audience:>8,}")
    print(f"  OBJECTID reassigned 1..{total:,}")

    # Validation
    from collections import defaultdict
    nn = defaultdict(int)
    for feat in out_features:
        for k, v in feat["properties"].items():
            if v is not None:
                nn[k] += 1

    print("\nValidation — field coverage:")
    for field in SOV_FIELDS:
        count = nn[field]
        pct = count / total * 100
        print(f"  {field:<15} {count:>8,}  ({pct:5.1f}%)")

    extra = set(out_features[0]["properties"].keys()) - set(SOV_FIELDS)
    if extra:
        print(f"\n  ⚠ Unexpected fields: {extra}")
    else:
        print(f"\n  ✓ Exactly 17 SoV schema fields")

    null_geoid = sum(1 for f in out_features if not f["properties"].get("GEOIDTXT"))
    print(f"\n  Null GEOIDTXT remaining: {null_geoid:,} → run fill_geoidtxt_spatial_points.py next")


if __name__ == "__main__":
    main()
