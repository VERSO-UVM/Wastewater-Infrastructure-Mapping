# SoV Data Standards
## Vermont Water Investment Infrastructure — State of Vermont (ANR/DEC)

These three GeoJSON files represent the authoritative statewide wastewater, stormwater, water, and combined sewer infrastructure dataset maintained by the Vermont Agency of Natural Resources (ANR), Department of Environmental Conservation (DEC). They are the normalization target for all town-level data.

---

## Files

| File suffix | Geometry | Feature count | Description |
|---|---|---|---|
| `...8923448805365789173.geojson` | Polygon / MultiPolygon | 3,807 | Stormwater management areas (ponds, basins, galleries) |
| `...4064670580023137264.geojson` | Point | 166,004 | Infrastructure point features (manholes, catch basins, outfalls, pump stations) |
| `...−6999738747210364761.geojson` | LineString / MultiLineString | 196,169 | Infrastructure linear features (pipes, culverts, ditches, mains) |

> **Note:** File names contain a numeric hash suffix; they should be referenced by geometry type, not filename.

---

## Coordinate Reference System

All three files use **WGS 84 geographic coordinates (EPSG:4326)**. No explicit `crs` property is present in the GeoJSON — this is the GeoJSON specification default.

---

## Shared Property Schema

All three files share the same 17 properties:

| Field | Type | Required | Description |
|---|---|---|---|
| `OBJECTID` | Integer | Yes | Internal ArcGIS record ID. Not stable across exports. |
| `GlobalID` | String (UUID) | Yes | Globally unique identifier (GUID). Stable primary key. |
| `GEOIDTXT` | String | Yes | 10-digit FIPS-style municipality code. Links to `GEOID` in town Border files (e.g., `5002303250`). |
| `SystemType` | String | Yes | Infrastructure system category. See [SystemType domain](#systemtype-domain) below. |
| `Type` | Integer | Yes | Feature type code within a system. See [Type code tables](#type-code-tables) below. |
| `Status` | String | Yes | Lifecycle status. See [Status domain](#status-domain) below. |
| `Owner` | Integer | No | Ownership code. See [Owner domain](#owner-domain) below. |
| `PermitNo` | String | No | ANR/DEC permit number (e.g., `4389-9003`). |
| `Audience` | String | Yes | Data visibility. Always `"Public"` in this dataset. |
| `Source` | Integer | No | Data source code. See [Source domain](#source-domain) below. |
| `SourceDate` | String | No | Date of source material. Rarely populated. |
| `SourceNotes` | String | No | Free-text source citation (plan file name, map reference, etc.). |
| `Notes` | String | No | Free-text feature notes. |
| `Creator` | String | No | Username of the record creator. |
| `CreateDate` | String | No | Creation date in HTTP date format (e.g., `"Thu, 01 Oct 2009 00:00:00 GMT"`). |
| `Editor` | String | No | Username of the last editor (e.g., `"DAVID.AINLEY"`). |
| `EditDate` | String | No | Last edit date in HTTP date format. |

---

## Domain Tables

### SystemType Domain

| Value | Description |
|---|---|
| `"Stormwater"` | Stormwater conveyance and management infrastructure |
| `"Wastewater"` | Sanitary sewer (gravity and force main) infrastructure |
| `"Water"` | Potable water distribution and transmission infrastructure |
| `"Combined"` | Combined sewer (carries both sanitary and stormwater flows) |
| `" "` | Unknown / unclassified (data quality issue — treat as null) |
| `null` | Not assigned |

> **Polygon file:** All features are `Stormwater` only.

---

### Status Domain

| Value | Description |
|---|---|
| `"Existing"` | Feature is currently in service |
| `"Proposed"` | Feature is planned but not yet constructed |
| `"Abandoned"` | Feature is out of service (no longer active) |
| `"Absent"` | Feature was expected but not found in field verification |
| `"Potential"` | Feature location is speculative or unconfirmed |
| `"E"` | Data quality issue — treat as `"Existing"` (appears in line file only) |

---

### Owner Domain

| Code | Description |
|---|---|
| `0` | Unknown |
| `1` | Municipal |
| `2` | State |
| `3` | Private |
| `4` | Federal |
| `null` | Not assigned |

---

### Source Domain

Source codes indicate how/where the feature data was obtained. Corresponding town-file string values are noted for mapping.

| Code | Description | Town file equivalent |
|---|---|---|
| `1` | Record drawings / engineering as-builts | — |
| `2` | Stormwater permit plans / Municipal member knowledge | `"Municipality Member Knowledge"` |
| `3` | Field observation / historical municipal sewer maps | `"Data from Municipality"`, `"Town Plan Interpretation"` |
| `4` | Stormwater permit application plans | `"Stormwater Permit Plan Interpretation"`, `"Act 250 Permit Plans"` |
| `5` | Orthophotography interpretation (NAIP or similar) | `"Orthophotography Interpretation"` |
| `6` | Stormwater permit inspection plans | `"Wastewater Division Plans"` |
| `7` | GPS survey / external consultant data | `"Mapping Grade GPS"`, `"Contractor GIS/GPS"` |
| `8` | Dye testing / field investigation | `"Data Collected in Field"` |
| `10` | Scanned municipal paper maps | — |
| `11` | Highway/corridor plan sheets | — |
| `12` | Database load / spatial processing | — |
| `13` | Specific engineering plan documents | — |
| `14` | Commercial / industrial site plans | — |
| `15` | Other permit plan documents | — |

---

## Type Code Tables

Type codes are integers. Their meaning depends on `SystemType` and geometry.

### Lines — Type Codes

| Type | Primary SystemType | Description |
|---|---|---|
| `2` | Stormwater | Storm drain pipe (closed conduit) |
| `3` | Stormwater / Wastewater | Sanitary sewer pipe / gravity main |
| `4` | Stormwater | Culvert (closed conduit under road or fill) |
| `5` | Stormwater | Open channel / drainage ditch |
| `6` | Stormwater | Subsurface drain / footing drain |
| `7` | Stormwater | Underdrain / perforated pipe |
| `8` | Stormwater | Roof drain leader |
| `10` | Stormwater | Storm conveyance (general / unclassified pipe) |
| `12` | Stormwater | Infiltration trench / perforated pipe in stone trench |
| `13` | Combined | Combined sewer pipe |
| `14` | Stormwater | Foundation drain / curtain drain |
| `15` | Stormwater / Water | Water channel (concrete/steel) or water service line |
| `16` | Stormwater | Overland flow path |
| `17` | Stormwater | Trench drain |
| `18` | Stormwater | Large culvert / concrete tunnel |
| `19` | Water | Water main / distribution line |

### Points — Type Codes

| Type | Primary SystemType | Description |
|---|---|---|
| `2` | Stormwater | Catch basin |
| `3` | Stormwater | Drain inlet |
| `4` | Wastewater | Sanitary manhole |
| `5` | Stormwater | Storm drain inlet |
| `6` | Stormwater | Stormwater outfall |
| `7` | Stormwater | Junction box |
| `8` | Stormwater | Storm manhole |
| `9` | Stormwater | Cleanout / storm cleanout |
| `11` | Stormwater | Drywell / drain well |
| `12` | Stormwater | Catch basin (larger / variant) |
| `14` | Stormwater | Drain well / unknown inlet |
| `15` | Stormwater | Drain inlet — DI type |
| `16` | Stormwater | Concrete box inlet |
| `17` | Stormwater / Wastewater | Cap point / cleanout / roof drain connection |
| `19` | Stormwater | Outlet structure / detention outlet |
| `22` | Wastewater | Wastewater access point |
| `23` | Combined | CSO outfall / siphon structure |
| `24` | Combined | Cross-connection / combined sewer interconnection |
| `25` | Combined | Pump station / lift station |
| `27` | Stormwater | Stand pipe / riser |
| `28` | Stormwater | Stormwater connection point |

### Polygons — Type Codes

All polygons are `Stormwater` system type.

| Type | Description |
|---|---|
| `2` | Stormwater management area (general / unclassified) |
| `6` | Wet pond / retention pond |
| `7` | Dry detention pond / dry swale |
| `8` | Infiltration basin |
| `9` | Sand filter |
| `10` | Natural pooling area (no engineered outlet) |
| `13` | Extended detention basin |
| `14` | Pocket pond / level spreader |
| `15` | Underground detention system (large-diameter pipe gallery) |
| `16` | Underground infiltration gallery |
| `17` | Other / water reuse tank |
| `18` | Filter strip / fire pond |
| `19` | Proprietary treatment device (manufactured unit) |
| `20` | Underground chamber / sedimentation basin / constructed wetland |
| `21` | Filter strip / permeable pavement variant |

---

## Date Format

Dates in `CreateDate` and `EditDate` use HTTP date format:
```
"Thu, 01 Oct 2009 00:00:00 GMT"
```
When processing, parse with `datetime.strptime(d, "%a, %d %b %Y %H:%M:%S %Z")` or convert to ISO 8601 (`YYYY-MM-DD`).

---

## Key Relationships

- `GEOIDTXT` → `GEOID` in town `*Border.geojson` files (municipality linkage)
- `PermitNo` → ANR permit database (external)
- `GlobalID` → stable cross-dataset feature identifier

---

## Known Data Quality Issues

| Issue | Scope | Recommendation |
|---|---|---|
| `SystemType = " "` (space) | Points file | Treat as null; reclassify if `Type` code is unambiguous |
| `Status = "E"` | Lines file | Normalize to `"Existing"` |
| `Type = null` | Polygons file (1 feature) | Flag for review |
| `SystemType = null` with non-null Type | All files | Cross-reference `Type` code table to infer system type |
| HTTP date format in `CreateDate`/`EditDate` | All files | Parse and store as ISO 8601 |
