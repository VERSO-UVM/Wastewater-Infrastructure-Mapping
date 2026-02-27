# SoV Data Review (Current vs. Original Specification)

This review is based on:
- Original spec: `data/SoV_data/SoV data_standards.md`
- Current files in `data/SoV_data`

## 1) Current Data Inventory

| File | Geometry types | Feature count | Notes |
|---|---|---:|---|
| `Vermont_Border.geojson` | `Polygon`, `MultiPolygon`, `None` | 249 | Border/municipality reference file (not one of the 3 core SoV infrastructure files in the original spec). |
| `Vermont_Water_Investment_Infrastructure_Public_points.geojson` | `Point` | 168,013 | Core point infrastructure dataset. |
| `Vermont_Water_Investment_Infrastructure_Public_shapes.geojson` | `Polygon`, `MultiPolygon` | 3,807 | Core polygon infrastructure dataset. |
| `Vermont_LinearFeatures_rejoined.geojson` | `LineString`, `MultiLineString` | 197,043 | Rejoined statewide linear dataset created from `LinearFeatures_by_town/*.geojson`. |
| `LinearFeatures_by_town/` | `LineString`/`MultiLineString` (across files) | 201 files | Town-split linear source set used for rejoining. |

## 2) Schema Comparison to Original Spec

Original spec defines a shared 17-field schema for infrastructure features:

`OBJECTID, GlobalID, GEOIDTXT, SystemType, Type, Status, Owner, PermitNo, Audience, Source, SourceDate, SourceNotes, Notes, Creator, CreateDate, Editor, EditDate`

### A) Points (`Vermont_Water_Investment_Infrastructure_Public_points.geojson`)
- **Expected fields present:** all 17/17
- **Additional fields not in original spec:**
  - `TownName`
  - `SourceFile`

### B) Shapes (`Vermont_Water_Investment_Infrastructure_Public_shapes.geojson`)
- **Expected fields present:** all 17/17
- **Additional fields not in original spec:**
  - `TownName`
  - `SourceFile`

### C) Rejoined Linear (`Vermont_LinearFeatures_rejoined.geojson`)
- **Expected fields present:** all 17/17
- **Additional fields not in original spec:**
  - `TownName`
  - `SourceFile`
  - `MergeSourceFile` (added during rejoin to preserve source-town file lineage)

### D) Border (`Vermont_Border.geojson`)
This file uses a different schema than the infrastructure 17-field schema. Current border fields:
- `OBJECTID`, `Name`, `Name_LSAD`, `LSAD`, `GEOID`, `Shape_Length`, `Shape_Area`, `TownName`, `Municipal_Wastewater`

## 3) Data Changes from Original Specification

## 3.1 File naming and packaging changes
- Original spec references three core files by hash-style export names.
- Current directory uses explicit descriptive names for points/shapes, and a separately rejoined linear file.
- Linear data is currently managed as town-split files (`LinearFeatures_by_town`) plus a merged product (`Vermont_LinearFeatures_rejoined.geojson`).

## 3.2 Feature count changes (where comparable)
- **Points:** spec listed **166,004**, current file has **168,013** (**+2,009**).
- **Shapes:** spec listed **3,807**, current file has **3,807** (**no change**).
- **Lines:** spec listed **196,169** for the statewide linear export; current rejoined file has **197,043** (**+874**).

> Note: Linear count differences may reflect updates in source town files and/or inclusion of `_UNASSIGNED.geojson` during rejoin.

## 3.3 Geometry observations
- Border includes one feature with `geometry = None` (in addition to polygon geometries).
- Rejoined linear file contains both `LineString` and `MultiLineString` geometries.

## 4) Recommendations for Downstream Use

1. Keep `TownName`, `SourceFile`, and `MergeSourceFile` in exploratory/analysis workflows for traceability.
2. If strict compatibility with the original 17-field schema is required for export, create a derived view that drops extra lineage fields.
3. Document whether `_UNASSIGNED.geojson` should be included or excluded for official statewide totals.
4. Treat `Vermont_Border.geojson` as a separate reference layer with its own schema, not part of the core infrastructure schema validation.

## 5) Reproducibility Notes

The rejoined linear file was generated via:
- `scripts/rejoin_sov_linear_towns.py`

Default output:
- `data/SoV_data/Vermont_LinearFeatures_rejoined.geojson`
