#!/usr/bin/env python3
"""
enrich_linear.py

Compare data/merged/Vermont_LinearFeatures.geojson (30,967 town-sourced features)
against data/SoV_data/Vermont_Water_Investment_Infrastructure_Public_LinearFeatures.geojson
(196,169 authoritative SoV features).

Actions:
  1. For each town feature, check if a matching SoV feature already exists
     (same Type + SystemType, ≥80% of the town feature length within 5m of the SoV line).
  2. Matched town features → enrich the SoV feature's null fields with town values.
  3. Unmatched town features → append as new records with full SoV schema.
  4. New SoV fields TownName and SourceFile are added to all features (null where not matched).

Output overwrites:
  data/SoV_data/Vermont_Water_Investment_Infrastructure_Public_LinearFeatures.geojson

Usage:
  python scripts/enrich_linear.py
"""

import json
import uuid
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import geopandas as gpd
import pandas as pd
import numpy as np
from shapely import STRtree
from shapely.geometry import mapping

PROJECT_ROOT = Path(__file__).parent.parent
SOV_LINEAR = PROJECT_ROOT / "data/SoV_data/Vermont_Water_Investment_Infrastructure_Public_LinearFeatures.geojson"
TOWN_LINEAR = PROJECT_ROOT / "data/merged/Vermont_LinearFeatures.geojson"
OUTPUT = PROJECT_ROOT / "data/SoV_data/Vermont_Water_Investment_Infrastructure_Public_LinearFeatures.geojson"

# Vermont UTM Zone 18N (meters) for spatial distance calculations
UTM_CRS = "EPSG:32618"
WGS84 = "EPSG:4326"

# Duplicate detection thresholds (per data_standards.md)
BUFFER_M = 5.0          # Buffer town features by 5 meters
OVERLAP_THRESH = 0.80   # ≥80% of town feature length must be within SoV buffer

# SoV fields that can be filled with town values where SoV has null
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

# New fields added to SoV schema from town data
NEW_FIELDS = ["TownName", "SourceFile"]

# Canonical SoV output field order
SOV_FIELD_ORDER = [
    "OBJECTID", "GlobalID", "GEOIDTXT", "SystemType", "Type", "Status",
    "Owner", "PermitNo", "Audience", "Source", "SourceDate", "SourceNotes",
    "Notes", "Creator", "CreateDate", "Editor", "EditDate",
    "TownName", "SourceFile",
]


def is_null(val):
    """Return True if val is None, NaN, or empty string."""
    if val is None:
        return True
    if isinstance(val, float) and np.isnan(val):
        return True
    if isinstance(val, str) and val.strip() == "":
        return True
    return False


def to_py(val):
    """Convert numpy types to Python native types for JSON serialization."""
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        if np.isnan(val):
            return None
        return float(val)
    if isinstance(val, (np.bool_,)):
        return bool(val)
    return val


def load_gdf(path, label):
    """Load GeoJSON as GeoDataFrame and print a summary."""
    print(f"Loading {label}...")
    gdf = gpd.read_file(str(path))
    print(f"  {len(gdf):,} features loaded")
    return gdf


def find_duplicates_and_new(sov_utm, town_utm):
    """
    Spatial comparison between SoV and town linear features.

    Returns:
      matched_pairs:  dict {town_iloc → sov_iloc}  (best SoV match per town feature)
      new_town_idxs:  list of town_iloc values with no SoV match
      enrichment_map: dict {sov_iloc → {field: value}} for null-fill updates
    """
    print("Projecting SoV to UTM...")
    sov_proj = sov_utm  # already projected before call

    print("Buffering town features (5 m)...")
    town_geoms = np.array(town_utm.geometry.values)
    town_buffered = np.array(town_utm.geometry.buffer(BUFFER_M).values)
    sov_geoms = np.array(sov_utm.geometry.values)

    # Pre-extract arrays for fast lookup
    sov_types = sov_utm["Type"].values
    sov_systypes = sov_utm["SystemType"].values
    town_types = town_utm["Type"].values
    town_systypes = town_utm["SystemType"].values

    print("Building SoV spatial index (STRtree)...")
    tree = STRtree(sov_geoms)

    print("Querying spatial index for candidate pairs...")
    # Returns arrays of (town_iloc, sov_iloc) pairs where buffered town ∩ sov ≠ ∅
    t_idxs, s_idxs = tree.query(town_buffered, predicate="intersects")
    print(f"  {len(t_idxs):,} candidate pairs before type filtering")

    # For each town feature, find the best-matching SoV feature
    # best_match[town_iloc] = (sov_iloc, overlap_ratio)
    best_match = {}

    matched_pairs_count = 0
    skip_type_count = 0

    for k in range(len(t_idxs)):
        t_idx = int(t_idxs[k])
        s_idx = int(s_idxs[k])

        # Must match Type and SystemType
        t_type = town_types[t_idx]
        s_type = sov_types[s_idx]
        t_sys = town_systypes[t_idx]
        s_sys = sov_systypes[s_idx]

        if t_type != s_type or t_sys != s_sys:
            skip_type_count += 1
            continue

        t_geom = town_geoms[t_idx]
        if t_geom is None or t_geom.is_empty:
            continue
        t_len = t_geom.length
        if t_len == 0:
            continue

        t_buf = town_buffered[t_idx]
        s_geom = sov_geoms[s_idx]

        try:
            # Portion of the SoV line within the town 5-meter buffer
            inter = t_buf.intersection(s_geom)
            overlap = inter.length / t_len
        except Exception:
            continue

        prev = best_match.get(t_idx)
        if prev is None or overlap > prev[1]:
            best_match[t_idx] = (s_idx, overlap)

    print(f"  {skip_type_count:,} pairs skipped (type mismatch)")

    # Classify town features
    matched_pairs = {}   # town_iloc → sov_iloc (for duplicates ≥ threshold)
    new_town_idxs = []   # town_iloc values with no match

    for t_idx in range(len(town_geoms)):
        match = best_match.get(t_idx)
        if match is not None and match[1] >= OVERLAP_THRESH:
            matched_pairs[t_idx] = match[0]
            matched_pairs_count += 1
        else:
            new_town_idxs.append(t_idx)

    print(f"  Matched (duplicates): {matched_pairs_count:,}")
    print(f"  New features to add:  {len(new_town_idxs):,}")

    # Build enrichment map: for each matched SoV feature, which town values can fill nulls?
    enrichment_map = {}  # sov_iloc → {field: value}
    enriched_feature_count = 0

    town_df = town_utm.drop(columns=["geometry"], errors="ignore")
    sov_df = sov_utm.drop(columns=["geometry"], errors="ignore")

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

        # Always capture TownName and SourceFile from matched town feature
        for field in NEW_FIELDS:
            if field in t_row.index:
                val = t_row[field]
                if not is_null(val):
                    updates[field] = to_py(val)

        if updates:
            enriched_feature_count += 1
            # Multiple town features could match same SoV feature — merge updates
            if s_idx in enrichment_map:
                # Don't overwrite existing enrichment values
                for k, v in updates.items():
                    if k not in enrichment_map[s_idx]:
                        enrichment_map[s_idx][k] = v
            else:
                enrichment_map[s_idx] = updates

    print(f"  SoV features eligible for enrichment: {enriched_feature_count:,}")
    return matched_pairs, new_town_idxs, enrichment_map


def build_new_feature(town_feat_props, town_feat_geom, next_objectid):
    """
    Convert a town GeoDataFrame row into a SoV-schema GeoJSON feature dict.
    All SoV fields are preserved; town-only fields are dropped except TownName/SourceFile.
    """
    props = {}

    props["OBJECTID"] = next_objectid
    props["GlobalID"] = str(uuid.uuid4())
    props["GEOIDTXT"] = to_py(town_feat_props.get("GEOIDTXT"))
    props["SystemType"] = to_py(town_feat_props.get("SystemType"))
    props["Type"] = to_py(town_feat_props.get("Type"))

    # Status: normalize "E" → "Existing"
    status = to_py(town_feat_props.get("Status"))
    if status == "E":
        status = "Existing"
    props["Status"] = status

    props["Owner"] = None          # not in town data
    props["PermitNo"] = None       # not in town data
    props["Audience"] = to_py(town_feat_props.get("Audience")) or "Public"
    props["Source"] = to_py(town_feat_props.get("Source"))
    props["SourceDate"] = to_py(town_feat_props.get("SourceDate"))
    props["SourceNotes"] = None
    props["Notes"] = to_py(town_feat_props.get("Notes"))
    props["Creator"] = to_py(town_feat_props.get("Creator"))
    props["CreateDate"] = to_py(town_feat_props.get("CreateDate"))
    props["Editor"] = None
    props["EditDate"] = None
    props["TownName"] = to_py(town_feat_props.get("TownName"))
    props["SourceFile"] = to_py(town_feat_props.get("SourceFile"))

    geom_dict = mapping(town_feat_geom) if town_feat_geom is not None else None

    return {"type": "Feature", "properties": props, "geometry": geom_dict}


def main():
    # ── 1. Load datasets ──────────────────────────────────────────────────────
    sov = load_gdf(SOV_LINEAR, "SoV LinearFeatures")
    town = load_gdf(TOWN_LINEAR, "Town merged LinearFeatures")

    # ── 2. Project to UTM for spatial operations ───────────────────────────
    print("Projecting to UTM Zone 18N (EPSG:32618)...")
    sov_utm = sov.to_crs(UTM_CRS)
    town_utm = town.to_crs(UTM_CRS)

    # ── 3. Spatial comparison ─────────────────────────────────────────────────
    print("\n── Spatial duplicate detection ──────────────────────────────────────")
    matched_pairs, new_town_idxs, enrichment_map = find_duplicates_and_new(sov_utm, town_utm)

    # ── 4. Load raw GeoJSON for output construction ──────────────────────────
    # Free GeoPandas GDFs before loading raw JSON to minimize peak memory
    del sov_utm, town_utm
    import gc
    gc.collect()

    print("\n── Loading raw GeoJSON for output ──────────────────────────────────")
    print(f"Loading raw SoV JSON ({SOV_LINEAR.stat().st_size / 1e6:.1f} MB)...")
    with open(SOV_LINEAR) as f:
        sov_raw = json.load(f)
    sov_feats = sov_raw["features"]

    print(f"Loading raw town JSON ({TOWN_LINEAR.stat().st_size / 1e6:.1f} MB)...")
    with open(TOWN_LINEAR) as f:
        town_raw = json.load(f)
    town_feats = town_raw["features"]

    # ── 5. Add new schema fields to all existing SoV features ────────────────
    print("\n── Applying enrichment and schema updates ───────────────────────────")
    enrichment_applied = 0
    field_fill_counts = {f: 0 for f in ENRICHABLE_FIELDS}
    new_field_counts = {f: 0 for f in NEW_FIELDS}

    for i, feat in enumerate(sov_feats):
        props = feat["properties"]

        # Add new fields with null defaults
        for field in NEW_FIELDS:
            if field not in props:
                props[field] = None

        # Apply enrichment updates from matched town features
        if i in enrichment_map:
            enrichment_applied += 1
            updates = enrichment_map[i]
            for field, value in updates.items():
                props[field] = value
                if field in field_fill_counts:
                    field_fill_counts[field] += 1
                elif field in new_field_counts:
                    new_field_counts[field] += 1

    print(f"  SoV features updated: {enrichment_applied:,}")
    if any(v > 0 for v in field_fill_counts.values()):
        print("  Field fill-in counts:")
        for field, count in field_fill_counts.items():
            if count > 0:
                print(f"    {field}: {count:,}")

    # ── 6. Append new town features ──────────────────────────────────────────
    print(f"\n── Appending {len(new_town_idxs):,} new features ─────────────────────────")

    # Determine next OBJECTID (max existing + 1)
    existing_oids = [
        f["properties"].get("OBJECTID")
        for f in sov_feats
        if f["properties"].get("OBJECTID") is not None
    ]
    next_oid = max(existing_oids) + 1 if existing_oids else 1

    # Load WGS84 town geometries for the new features
    # (town_raw already has WGS84 geometries)
    new_feature_dicts = []
    for t_iloc in new_town_idxs:
        town_feat = town_feats[t_iloc]
        props = town_feat["properties"]
        geom_dict = town_feat.get("geometry")

        # Convert geometry dict to shapely for mapping (already WGS84 from merged file)
        new_feat_props = {**props}  # copy

        new_props = {}
        new_props["OBJECTID"] = next_oid
        next_oid += 1
        new_props["GlobalID"] = str(uuid.uuid4())
        new_props["GEOIDTXT"] = new_feat_props.get("GEOIDTXT")
        new_props["SystemType"] = new_feat_props.get("SystemType")
        new_props["Type"] = new_feat_props.get("Type")

        status = new_feat_props.get("Status")
        if status == "E":
            status = "Existing"
        new_props["Status"] = status

        new_props["Owner"] = None
        new_props["PermitNo"] = None
        new_props["Audience"] = new_feat_props.get("Audience") or "Public"
        new_props["Source"] = new_feat_props.get("Source")
        new_props["SourceDate"] = new_feat_props.get("SourceDate")
        new_props["SourceNotes"] = None
        new_props["Notes"] = new_feat_props.get("Notes")
        new_props["Creator"] = new_feat_props.get("Creator")
        new_props["CreateDate"] = new_feat_props.get("CreateDate")
        new_props["Editor"] = None
        new_props["EditDate"] = None
        new_props["TownName"] = new_feat_props.get("TownName")
        new_props["SourceFile"] = new_feat_props.get("SourceFile")

        new_feature_dicts.append({
            "type": "Feature",
            "properties": new_props,
            "geometry": geom_dict,
        })

    sov_feats.extend(new_feature_dicts)
    print(f"  Total features after append: {len(sov_feats):,}")

    # ── 7. Write output ───────────────────────────────────────────────────────
    print(f"\n── Writing output → {OUTPUT.name} ──────────────────────────────────")
    sov_raw["features"] = sov_feats
    with open(OUTPUT, "w") as f:
        json.dump(sov_raw, f, separators=(",", ":"))

    size_mb = OUTPUT.stat().st_size / 1e6
    print(f"  Written {len(sov_feats):,} features ({size_mb:.1f} MB)")

    # ── 8. Summary ────────────────────────────────────────────────────────────
    print("\n══ Summary ══════════════════════════════════════════════════════════")
    print(f"  Original SoV features:       196,169")
    print(f"  Town features compared:       {len(town_feats):,}")
    print(f"  Matched (already in SoV):    {len(matched_pairs):,}")
    print(f"  New features appended:        {len(new_town_idxs):,}")
    print(f"  SoV features enriched:        {enrichment_applied:,}")
    print(f"  Final feature count:          {len(sov_feats):,}")
    print(f"  Output size:                  {size_mb:.1f} MB")
    print("\nDone.")


if __name__ == "__main__":
    main()
