# Vermont Wastewater Infrastructure — Master Data Standards

This document describes the overall data architecture, dataset relationships, and normalization strategy for this project. The goal is to merge town-level municipal data (`data/Towns/`) into the authoritative statewide dataset (`data/SoV_data/`) where records do not already exist.

---

## Dataset Overview

| Dataset | Location | Authority | Record count (approx.) | Geometry types |
|---|---|---|---|---|
| State of Vermont (SoV) | `data/SoV_data/` | ANR/DEC (authoritative) | ~366,000 features | Point, Line, Polygon |
| Town files | `data/Towns/` | Municipal / ANR field collection | ~650,000+ features across ~260 towns | Point, Line, Polygon |

### Key Principle

**The SoV dataset is the normalization target.** Town data should be evaluated for inclusion in the SoV dataset. Records that already exist in SoV (matched by spatial proximity + type) should not be duplicated. New or corrected geometries from town files should be added using SoV's schema.

---

## Dataset Relationship

```
data/
├── SoV_data/                          ← Authoritative statewide GIS
│   ├── *8923...geojson  (Polygons)    ← Stormwater management areas
│   ├── *4064...geojson  (Points)      ← Point infrastructure
│   ├── *-6999...geojson (Lines)       ← Linear infrastructure
│   └── data_standards.md              ← SoV schema documentation
│
└── Towns/
    ├── {TownName}/
    │   ├── *Border.geojson            ← Municipal boundary (GEOID linkage to SoV)
    │   ├── *LinearFeatures.geojson    ← Town pipes/culverts → merge to SoV Lines
    │   ├── *PointFeatures.geojson     ← Town manholes/CBs → merge to SoV Points
    │   ├── *WWTF.geojson              ← Treatment facility record (separate layer)
    │   └── *ServiceArea.geojson       ← Service area polygon (separate layer)
    └── data_standards.md              ← Town schema + normalization rules
```

---

## Municipality Linkage

The `GEOID` field in `*Border.geojson` files maps to the `GEOIDTXT` field in SoV feature files. This is the primary spatial/administrative join key.

| Town file field | SoV field | Format | Example |
|---|---|---|---|
| `GEOID` (Border) | `GEOIDTXT` | 10-digit string | `"5002303250"` |

When adding town features to SoV, populate `GEOIDTXT` from the town's Border file `GEOID` value.

---

## Merge Strategy by File Type

### LinearFeatures → SoV Lines

1. **Normalize fields** per `Towns/data_standards.md`
2. **Convert `Type`** from string to SoV integer code
3. **Convert `Source`** from string to SoV integer code
4. **Populate `GEOIDTXT`** from town Border file
5. **Spatial duplicate check**: buffer each candidate feature 5m; if an existing SoV feature of the same `Type` and `SystemType` overlaps > 80%, skip
6. **Generate `GlobalID`**: new UUID4 for each added feature
7. **Set `Audience = "Public"`**, `Creator = "Municipality"` (or original creator if available)

### PointFeatures → SoV Points

Same as linear, with duplicate check using 10m radius proximity instead of buffer overlap.

### WWTF → Separate Layer

WWTF records do not map to any of the three SoV infrastructure files. They represent ANR NPDES permit records, not individual infrastructure features. Maintain as a separate canonical layer. Normalize per `Towns/data_standards.md` WWTF schema.

### ServiceArea → Separate Layer

Service area polygons represent the geographic extent of each sewer system. Maintain as a separate canonical layer. Normalize per `Towns/data_standards.md` ServiceArea schema.

### Border → Reference Only

Town boundary files are reference data only — do not merge into SoV. Use `GEOID` as the linkage key.

---

## Canonical Field Mapping Summary

The table below summarizes how town file fields map to SoV fields across the main mergeable file types (LinearFeatures and PointFeatures):

| Town field (all variants) | SoV canonical field | Action |
|---|---|---|
| `System_Type`, `System Type`, `SystemType` | `SystemType` | Rename to `SystemType` |
| `Type` (string) | `Type` (integer) | Convert via type mapping table |
| `Type` (integer SoV code) | `Type` | Keep as-is |
| `Status` | `Status` | Normalize values |
| `Source` (string) | `Source` (integer) | Convert via source mapping table |
| `Source` (integer) | `Source` | Keep as-is |
| `Comment`, `Comments`, `comment` | `Notes` | Rename to `Notes` |
| `Map_Date`, `Map Date`, `MapDate` | `CreateDate` | Rename; normalize date format |
| `Source_Date`, `Source Date`, `SourceDate` | `SourceDate` | Rename |
| `Audience` | `Audience` | Keep; set to `"Public"` if null |
| `Creator`, `VTANR` | `Creator` | Keep or set to `"VTANR"` |
| `OBJECTID` | `OBJECTID` | Reassign on merge |
| `OBJECTID_1`, `OBJECTID 1` | — | Drop |
| `Shape_Length` | `Shape_Length` | Recalculate on merge |

---

## Type Code Cross-Reference

### Linear Features

| Town value | SoV `Type` | SoV `SystemType` |
|---|---|---|
| `"Sewer pipe"` / `"Sanitary Line"` / `"Sewer Pipe"` | `3` | `"Wastewater"` |
| `"Combined sewer pipe"` / `"Combined Sewer"` | `13` | `"Combined"` |
| `"Stormwater pipe"` | `2` | `"Stormwater"` |
| Integer `3` | `3` | (preserve existing) |
| Integer `13` | `13` | (preserve existing) |

### Point Features

| Town value | SoV `Type` | SoV `SystemType` |
|---|---|---|
| `"Sanitary Manhole"` / `"Sewer manhole"` / `"Sewer Manhole"` | `4` | `"Wastewater"` |
| `"Combined sewer manhole"` / `"Combined Sewer Manhole"` | `4` | `"Combined"` |
| `"Combined sewer catchbasin"` / `"Catchbasin"` | `2` | `"Combined"` |
| `"Combined sewer outfall"` / `"Known CSO Outfalls"` | `23` | `"Combined"` |
| `"CB tied to Sanitary Sewer"` | `2` | `"Combined"` |
| `"Stormwater manhole"` | `8` | `"Stormwater"` |
| `"Information point"` / `"Information Point"` | `17` | (preserve existing) |
| `"Other"` / `"Other - insert comment"` | `17` | (preserve existing) |
| `"Unknown Point"` | `17` | (preserve existing) |
| Integer `4`, `23`, `25`, `9`, `12`, `15`, `27` | same | (preserve existing) |

---

## Source Code Cross-Reference

| Town string | SoV `Source` integer |
|---|---|
| `"Data from Municipality"` | `3` |
| `"Municipality Member Knowledge"` | `2` |
| `"Data Collected in Field"` | `8` |
| `"Wastewater Division Plans"` | `6` |
| `"Stormwater Permit Plan Interpretation"` | `4` |
| `"Stormwater Permit Plam Interpretation"` | `4` |
| `"Town Plan Interpretation"` | `3` |
| `"Orthophotography Interpretation"` | `5` |
| `"Mapping Grade GPS"` | `7` |
| `"Contractor GIS/GPS"` | `7` |
| `"Act 250 Permit Plans"` | `4` |
| `"ANR Web VT"` / `"ANRweb.VT"` | `null` (move to `SourceNotes`) |
| `""` (empty string) | `null` |

---

## Known Data Quality Issues — Town Files

| Issue | Affected files | Resolution |
|---|---|---|
| Field values used as column names | Alburgh (confirmed), others likely | Reconstruct schema from domain knowledge |
| Duplicate OBJECTIDs (all `0`) | Many files | Reassign on merge |
| `System_Type` / `System Type` / `SystemType` inconsistency | ~50/50 split | Rename to `SystemType` |
| String type values instead of integer codes | Most town files | Convert via type mapping table |
| String source values instead of integer codes | Most town files | Convert via source mapping table |
| `Status = "E"` | Several files | Normalize to `"Existing"` |
| `Status = "Wastewater"` | Point files | Data error — use `SystemType` field instead; set Status to `null` or `"Existing"` |
| Trailing/leading spaces in field names | WWTF files | Strip whitespace from all field names |
| Trailing/leading spaces in values | Various | Strip on import |
| Inconsistent `WWTF` file schemas (camelCase vs. spaced) | ~50/50 split of towns | Normalize to camelCase canonical |
| `Shape_Area` and `Shape_Length` = `0` | Many files | Recalculate from geometry on merge |
| Missing `GEOIDTXT` | All town feature files | Derive from town's Border file `GEOID` |
| Typos in field names (`Wastwater`, `Permint`, `Septage Recieved`) | Scattered | Normalize via field name mapping table |
| Mixed coordinate precision | Various | No action needed (WGS 84 consistent) |
| `Municipal_Wastewater` field name variants (5 variants) | Border files | Normalize to `Municipal_Wastewater` |

---

## Detailed Standards

- **SoV dataset schema:** [`data/SoV_data/data_standards.md`](SoV_data/data_standards.md)
- **Town dataset schema + normalization rules:** [`data/Towns/data_standards.md`](Towns/data_standards.md)
