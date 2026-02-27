#!/usr/bin/env python3
"""
enrich_points.py

Compare data/merged/Vermont_PointFeatures.geojson (25,766 town-sourced features)
against data/SoV_data/Vermont_Water_Investment_Infrastructure_Public_points.geojson
(166,004 authoritative SoV features).

Duplicate check: any SoV point of the same Type + SystemType within 10 m of a town
point is considered an existing match (per data_standards.md — point proximity radius).

Actions:
  1. Matched town points → enrich null SoV fields with town values.
  2. Unmatched town points → append as new records with full SoV schema.
  3. New SoV fields TownName and SourceFile added to all features (null where unmatched).

Output overwrites:
  data/SoV_data/Vermont_Water_Investment_Infrastructure_Public_points.geojson

Usage:
  python scripts/enrich_points.py
"""

import json
import uuid
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import numpy as np
from shapely import STRtree
import geopandas as gpd

PROJECT_ROOT = Path(__file__).parent.parent
SOV_POINTS = PROJECT_ROOT / "data/SoV_data/Vermont_Water_Investment_Infrastructure_Public_points.geojson"
TOWN_POINTS = PROJECT_ROOT / "data/merged/Vermont_PointFeatures.geojson"
OUTPUT = PROJECT_ROOT / "data/SoV_data/Vermont_Water_Investment_Infrastructure_Public_points.geojson"

UTM_CRS = "EPSG:32618"   # Vermont UTM Zone 18N, meters

# Proximity radius for point duplicate detection (per data_standards.md)
PROXIMITY_M = 10.0

# SoV null fields that can be filled from town data
ENRICHABLE_FIELDS = [
    "Notes",
    "Source",
    "SourceDate",
    "SourceNotes",
    "Creator",
    "CreateDate",
    "Status",
    "GEOIDTXT",
    "Owner",
]

# New fields added to SoV schema
NEW_FIELDS = ["TownName", "SourceFile"]


def is_null(val):
    if val is None:
        return True
    if isinstance(val, float) and np.isnan(val):
        return True
    if isinstance(val, str) and val.strip() == "":
        return True
    return False


def to_py(val):
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        return None if np.isnan(val) else float(val)
    if isinstance(val, (np.bool_,)):
        return bool(val)
    return val


def main():
    # ── 1. Load datasets ───────────────────────────────────────────────────────
    print("Loading SoV points...")
    sov = gpd.read_file(str(SOV_POINTS))
    print(f"  {len(sov):,} features")

    print("Loading merged town points...")
    town = gpd.read_file(str(TOWN_POINTS))
    print(f"  {len(town):,} features")

    # ── 2. Project to UTM ──────────────────────────────────────────────────────
    print("Projecting to UTM Zone 18N...")
    sov_utm = sov.to_crs(UTM_CRS)
    town_utm = town.to_crs(UTM_CRS)

    # ── 3. Build spatial index and find candidate pairs ───────────────────────
    print(f"Buffering town points ({PROXIMITY_M} m)...")
    town_geoms = np.array(town_utm.geometry.values)
    town_buffered = np.array(town_utm.geometry.buffer(PROXIMITY_M).values)
    sov_geoms = np.array(sov_utm.geometry.values)

    sov_types = sov_utm["Type"].values
    sov_systypes = sov_utm["SystemType"].values
    town_types = town_utm["Type"].values
    town_systypes = town_utm["SystemType"].values

    print("Building SoV spatial index...")
    tree = STRtree(sov_geoms)

    print("Querying for candidate pairs...")
    t_idxs, s_idxs = tree.query(town_buffered, predicate="intersects")
    print(f"  {len(t_idxs):,} candidate pairs")

    # For each town point, find the nearest SoV point within PROXIMITY_M
    # that matches Type + SystemType.
    # best_match[town_iloc] = (sov_iloc, distance)
    best_match = {}
    skip_type = 0

    for k in range(len(t_idxs)):
        t_idx = int(t_idxs[k])
        s_idx = int(s_idxs[k])

        if town_types[t_idx] != sov_types[s_idx] or town_systypes[t_idx] != sov_systypes[s_idx]:
            skip_type += 1
            continue

        t_geom = town_geoms[t_idx]
        s_geom = sov_geoms[s_idx]

        if t_geom is None or s_geom is None:
            continue

        try:
            dist = t_geom.distance(s_geom)
        except Exception:
            continue

        if dist <= PROXIMITY_M:
            prev = best_match.get(t_idx)
            if prev is None or dist < prev[1]:
                best_match[t_idx] = (s_idx, dist)

    print(f"  {skip_type:,} pairs skipped (type mismatch)")

    matched_pairs = {}   # town_iloc → sov_iloc
    new_town_idxs = []

    for t_idx in range(len(town_geoms)):
        match = best_match.get(t_idx)
        if match is not None:
            matched_pairs[t_idx] = match[0]
        else:
            new_town_idxs.append(t_idx)

    print(f"  Matched: {len(matched_pairs):,} | New: {len(new_town_idxs):,}")

    # ── 4. Build enrichment map ────────────────────────────────────────────────
    town_df = town_utm.drop(columns=["geometry"], errors="ignore")
    sov_df = sov_utm.drop(columns=["geometry"], errors="ignore")

    enrichment_map = {}
    enriched_count = 0

    for t_idx, s_idx in matched_pairs.items():
        t_row = town_df.iloc[t_idx]
        s_row = sov_df.iloc[s_idx]
        updates = {}

        for field in ENRICHABLE_FIELDS:
            sov_val = s_row.get(field) if field in s_row.index else None
            if is_null(sov_val):
                town_val = t_row.get(field) if field in t_row.index else None
                if not is_null(town_val):
                    updates[field] = to_py(town_val)

        for field in NEW_FIELDS:
            if field in t_row.index:
                val = t_row[field]
                if not is_null(val):
                    updates[field] = to_py(val)

        if updates:
            enriched_count += 1
            if s_idx in enrichment_map:
                for k, v in updates.items():
                    if k not in enrichment_map[s_idx]:
                        enrichment_map[s_idx][k] = v
            else:
                enrichment_map[s_idx] = updates

    print(f"  SoV features eligible for enrichment: {enriched_count:,}")

    # Free GeoPandas memory
    del sov_utm, town_utm, sov, town
    import gc
    gc.collect()

    # ── 5. Load raw GeoJSON ────────────────────────────────────────────────────
    print("\nLoading raw SoV JSON...")
    with open(SOV_POINTS) as f:
        sov_raw = json.load(f)
    sov_feats = sov_raw["features"]

    print("Loading raw town JSON...")
    with open(TOWN_POINTS) as f:
        town_raw = json.load(f)
    town_feats = town_raw["features"]

    # ── 6. Apply enrichment to existing SoV features ──────────────────────────
    print("\nApplying enrichment updates...")
    enrichment_applied = 0
    field_fill_counts = {f: 0 for f in ENRICHABLE_FIELDS}

    for i, feat in enumerate(sov_feats):
        props = feat["properties"]
        for field in NEW_FIELDS:
            if field not in props:
                props[field] = None

        if i in enrichment_map:
            enrichment_applied += 1
            for field, value in enrichment_map[i].items():
                props[field] = value
                if field in field_fill_counts:
                    field_fill_counts[field] += 1

    print(f"  SoV features updated: {enrichment_applied:,}")
    for field, count in field_fill_counts.items():
        if count > 0:
            print(f"    {field}: {count:,}")

    # ── 7. Append new town point features ─────────────────────────────────────
    print(f"\nAppending {len(new_town_idxs):,} new features...")

    existing_oids = [
        f["properties"].get("OBJECTID")
        for f in sov_feats
        if f["properties"].get("OBJECTID") is not None
    ]
    next_oid = max(existing_oids) + 1 if existing_oids else 1

    for t_iloc in new_town_idxs:
        town_feat = town_feats[t_iloc]
        p = town_feat["properties"]

        status = p.get("Status")
        if status == "E":
            status = "Existing"

        new_props = {
            "OBJECTID":    next_oid,
            "GlobalID":    str(uuid.uuid4()),
            "GEOIDTXT":    p.get("GEOIDTXT"),
            "SystemType":  p.get("SystemType"),
            "Type":        p.get("Type"),
            "Status":      status,
            "Owner":       None,
            "PermitNo":    None,
            "Audience":    p.get("Audience") or "Public",
            "Source":      p.get("Source"),
            "SourceDate":  p.get("SourceDate"),
            "SourceNotes": None,
            "Notes":       p.get("Notes"),
            "Creator":     p.get("Creator"),
            "CreateDate":  p.get("CreateDate"),
            "Editor":      None,
            "EditDate":    None,
            "TownName":    p.get("TownName"),
            "SourceFile":  p.get("SourceFile"),
        }
        next_oid += 1

        sov_feats.append({
            "type": "Feature",
            "properties": new_props,
            "geometry": town_feat.get("geometry"),
        })

    print(f"  Total features: {len(sov_feats):,}")

    # ── 8. Write output ────────────────────────────────────────────────────────
    print(f"\nWriting {OUTPUT.name}...")
    sov_raw["features"] = sov_feats
    with open(OUTPUT, "w") as f:
        json.dump(sov_raw, f, separators=(",", ":"))

    size_mb = OUTPUT.stat().st_size / 1e6
    print(f"  Written {len(sov_feats):,} features ({size_mb:.1f} MB)")

    print("\n══ Summary ══════════════════════════════════════════════════════════")
    print(f"  Original SoV features:   166,004")
    print(f"  Town features compared:   {len(town_feats):,}")
    print(f"  Matched (already in SoV): {len(matched_pairs):,}")
    print(f"  New features appended:    {len(new_town_idxs):,}")
    print(f"  SoV features enriched:    {enrichment_applied:,}")
    print(f"  Final feature count:      {len(sov_feats):,}")
    print(f"  Output size:              {size_mb:.1f} MB")
    print("\nDone.")


if __name__ == "__main__":
    main()
