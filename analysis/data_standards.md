# Vermont Wastewater Infrastructure — Data Standards & Field Reference

This document describes the schema, field types, domain values, and usage notes for every file in `data/`. It is the primary reference for anyone working with this dataset.

---

## File Inventory

| File | Features | Geometry | Description |
|---|---|---|---|
| `Vermont_Linear_Features.geojson` | 222,766 | LineString / MultiLineString | Pipes, culverts, channels, and other linear infrastructure |
| `Vermont_Point_Features.geojson` | 185,223 | Point | Manholes, catch basins, outfalls, pump stations, and other point infrastructure |
| `Vermont_Water_Features.geojson` | 3,807 | Polygon / MultiPolygon | Stormwater management areas (ponds, basins, detention areas) |
| `Vermont_ServiceAreas.geojson` | 186 | Polygon / MultiPolygon | Municipal sewer/stormwater system service boundaries |
| `Vermont_Treatment_Facilities.geojson` | 179 | Point | Wastewater treatment facilities (NPDES permit records) |
| `Vermont_Town_GEOID_RPC_County.geojson` | 256 | Polygon | Vermont municipal boundaries with FIPS identifiers and administrative lookups |

---

## Shared Administrative Fields

Three fields are appended to every feature in the five main data files (all except `Vermont_Town_GEOID_RPC_County.geojson`) to enable consistent administrative filtering:

| Field | Type | Description | Example |
|---|---|---|---|
| `GEOIDTXT` | String | 10-digit FIPS place code — primary join key to `Vermont_Town_GEOID_RPC_County.geojson` | `"5002303250"` |
| `Municipal_Name` | String | Human-readable town/city name | `"Burlington"` |
| `County` | String | Vermont county name (14 counties) | `"Chittenden"` |
| `RPC` | String | Regional Planning Commission abbreviation (11 RPCs) | `"CCRPC"` |

**County values:** Addison, Bennington, Caledonia, Chittenden, Essex, Franklin, Grand Isle, Lamoille, Orange, Orleans, Rutland, Washington, Windham, Windsor

**RPC values:** ACRPC, BCRC, CCRPC, CVRPC, LCPC, MARC, NRPC, NVDA, RRPC, TRORC, WRC

---

## Shared Infrastructure Schema Fields

`Vermont_Linear_Features.geojson`, `Vermont_Point_Features.geojson`, and `Vermont_Water_Features.geojson` share this base schema (17 fields from the original ANR/DEC dataset, plus the 4 administrative fields above, minus OBJECTID which is not present in the output files):

| Field | Type | Nullable | Description |
|---|---|---|---|
| `GlobalID` | String (UUID) | No | Globally unique identifier. Format: `"{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}"` |
| `GEOIDTXT` | String | Yes | 10-digit FIPS code for the municipality (shared admin field; see above) |
| `SystemType` | String | Yes | High-level infrastructure category. See domain table below |
| `Type` | Integer | Yes | Feature type code within SystemType. See domain table below |
| `Status` | String | Yes | Construction/operational status. See domain table below |
| `Owner` | String | Yes | Owner of the feature. Mostly null in current data |
| `PermitNo` | String | Yes | Regulatory permit number, if applicable |
| `Audience` | String | No | Data access level. Always `"Public"` in this dataset |
| `Source` | Integer | Yes | Source of the data. See source code table below |
| `SourceDate` | String/Number | Yes | Date of original source data (inconsistent format — may be ISO date string or millisecond epoch integer) |
| `SourceNotes` | String | Yes | Free-text notes about the data source |
| `Notes` | String | Yes | General feature notes or comments |
| `Creator` | String | Yes | Username or identifier of the person who created the record |
| `CreateDate` | String | Yes | Date the record was created (ISO 8601 format) |
| `Editor` | String | Yes | Username of the last editor |
| `EditDate` | String | Yes | Date of the last edit (ISO 8601 format) |
| `Municipal_Name` | String | No | Municipality name (shared admin field) |
| `County` | String | No | County name (shared admin field) |
| `RPC` | String | No | Regional Planning Commission (shared admin field) |

---

## 1. Vermont_Linear_Features.geojson

**222,766 features** · LineString / MultiLineString · Pipes, culverts, channels

### SystemType Domain

| Value | Feature count |
|---|---|
| `"Stormwater"` | 149,345 |
| `"Wastewater"` | 60,612 |
| `"Water"` | 10,616 |
| `"Combined"` | 2,048 |
| null | 145 |

### Type Code Domain (Integer)

| Code | Label | SystemType | Count |
|---|---|---|---|
| 2 | Storm Sewer / Drain Pipe | Stormwater | 74,883 |
| 3 | Sanitary Sewer Pipe | Wastewater | 60,301 |
| 4 | Culvert | Stormwater | 32,243 |
| 5 | Open Channel / Ditch | Stormwater | 27,346 |
| 19 | Water Main | Water | 10,613 |
| 7 | Swale | Stormwater | 3,976 |
| 6 | Wet Swale | Stormwater | 3,557 |
| 10 | Roadside Ditch | Stormwater | 3,341 |
| 8 | Grass-Lined Channel | Stormwater | 2,983 |
| 13 | Combined Sewer | Combined | 2,343 |
| 16 | Subsurface Drain | Stormwater | 321 |
| 17 | Other / Unknown | — | 255 |
| 12 | French Drain | Stormwater | 208 |
| 18 | Force Main | Wastewater | 181 |
| 14 | Pervious Pavement Underdrain | Stormwater | 56 |
| 15 | Filter Strip | Stormwater | 12 |
| null | — | — | 147 |

### Status Domain

| Value | Count |
|---|---|
| `"Existing"` | 189,437 |
| `"Proposed"` | 3,742 |
| `"Abandoned"` | 1,486 |
| `"Absent"` | 5 |
| null | 28,096 |

### Source Code Domain (Integer)

| Code | Meaning | Count |
|---|---|---|
| 1 | As-built plan interpretation | 318 |
| 2 | Municipality member knowledge | 4,908 |
| 3 | Data from municipality | 93,009 |
| 4 | Stormwater / Act 250 permit plan interpretation | 15,159 |
| 5 | Orthophotography interpretation | 1,436 |
| 6 | Wastewater division plans | 21,003 |
| 7 | Mapping-grade GPS / contractor GIS | 41,300 |
| 8 | Data collected in field | 2,829 |
| 10 | ANR dataset | 15,889 |
| 11 | Town plan interpretation | 964 |
| 12 | LiDAR / remote sensing | 9,488 |
| 13 | Engineering report | 6,459 |
| 14 | Survey-grade GPS | 271 |
| 15 | Other | 193 |
| null | Unknown / not recorded | 9,540 |

### Creator Values

| Value | Count |
|---|---|
| `"ANR_ADMIN"` | 160,622 |
| `"DAVID.AINLEY"` | 49,477 |
| `"VTANR"` | 8,403 |
| `"anrCleanWater"` | 2,407 |
| `"JIM.PEASE"` | 866 |
| `"cleanwatervt"` | 474 |
| Other | ~62 |
| null | 455 |

---

## 2. Vermont_Point_Features.geojson

**185,223 features** · Point · Manholes, catch basins, outfalls, pump stations

### SystemType Domain

| Value | Count |
|---|---|
| `"Stormwater"` | 133,919 |
| `"Wastewater"` | 46,183 |
| `"Combined"` | 2,714 |
| `"Water"` | 2,406 |
| null | 1 |

### Type Code Domain (Integer)

| Code | Label | SystemType | Count |
|---|---|---|---|
| 2 | Catch Basin / Inlet | Stormwater / Combined | 45,430 |
| 3 | Culvert Inlet/Outlet | Stormwater | 5,092 |
| 4 | Sanitary / Wastewater Manhole | Wastewater / Combined | 45,637 |
| 5 | Storm Structure / Junction | Stormwater | 10,445 |
| 6 | Wet Pond Outlet Structure | Stormwater | 1,033 |
| 7 | Dry Detention Outlet | Stormwater | 129 |
| 8 | Storm Manhole | Stormwater | 32,108 |
| 9 | Detention / Retention Outlet | Stormwater | 31,457 |
| 11 | Cleanout | Wastewater | 218 |
| 12 | Grease Trap / Interceptor | Wastewater | 1,268 |
| 14 | Pervious Pavement Feature | Stormwater | 933 |
| 15 | Outlet / Outfall | Stormwater | 3,279 |
| 16 | Underdrain Outlet | Stormwater | 595 |
| 17 | Other / Unknown | — | 2,955 |
| 19 | Water Service Connection | Water | 262 |
| 22 | Sewer Lateral Connection | Wastewater | 1,340 |
| 23 | CSO Outfall | Combined | 167 |
| 24 | Stormwater Outfall | Stormwater | 428 |
| 25 | Pump Station | Wastewater / Stormwater | 1,124 |
| 27 | Valve / Gate | Water / Wastewater | 1,121 |
| 28 | Meter / Monitoring Point | Various | 202 |

### Status Domain

| Value | Count |
|---|---|
| `"Existing"` | 180,383 |
| `"Proposed"` | 3,692 |
| `"Abandoned"` | 765 |
| `"Potential"` | 178 |
| `"Absent"` | 27 |
| null | 178 |

### Source Code Domain

Same codes as Linear Features (see Source Code Domain table in Section 1).

### Creator Values

| Value | Count |
|---|---|
| `"DAVIDA"` | 56,169 |
| `"DAVID.AINLEY"` | 40,816 |
| `"DA"` | 33,198 |
| `"CS"` | 22,166 |
| `"VTANR"` | 6,479 |
| `"JIMP"` | 4,915 |
| `"anrCleanWater"` | 2,755 |
| `"JP"` | 1,469 |
| Other | ~575 |
| null | 15,314 |

---

## 3. Vermont_Water_Features.geojson

**3,807 features** · Polygon / MultiPolygon · Stormwater management areas (ponds, basins, detention areas)

> **Note:** These are stormwater infrastructure polygons from the ANR/DEC dataset, not municipal sewer service areas. Do not conflate with `Vermont_ServiceAreas.geojson`.

### SystemType Domain

| Value | Count |
|---|---|
| `"Stormwater"` | 3,803 |
| null | 4 |

### Type Code Domain (Integer)

| Code | Label | Count |
|---|---|---|
| 13 | Extended Detention Basin | 568 |
| 6 | Wet Pond | 475 |
| 19 | Infiltration Basin / Trench | 420 |
| 8 | Infiltration Basin (shallow) | 435 |
| 2 | Bioretention / Rain Garden | 334 |
| 14 | Pervious Pavement Area | 278 |
| 10 | Roadside Ditch / Buffer Strip | 276 |
| 17 | Other / Unknown | 207 |
| 20 | Sand Filter | 195 |
| 7 | Dry Detention Pond | 171 |
| 16 | Grass Swale | 167 |
| 15 | Filter Strip | 101 |
| 21 | Constructed Wetland | 64 |
| 9 | Detention Basin (General) | 63 |
| 18 | Cistern / Underground Storage | 52 |
| null | — | 1 |

### Status Domain

| Value | Count |
|---|---|
| `"Existing"` | 2,758 |
| `"Proposed"` | 987 |
| `"Potential"` | 50 |
| `"Abandoned"` | 9 |
| `"Absent"` | 1 |
| null | 2 |

### Additional Notes for Water Features
- `TownName` and `SourceFile` fields are present but always null (added for schema consistency with enriched files)
- `Source` is null for 540 features (14% of file)
- `Creator` is null for 332 features

---

## 4. Vermont_ServiceAreas.geojson

**186 features** · Polygon / MultiPolygon · Municipal sewer/stormwater service boundaries

> These polygons represent the geographic extent of each municipal collection system, not ANR infrastructure polygons.

### Schema

| Field | Type | Nullable | Description | Example |
|---|---|---|---|---|
| `TownID` | Integer | No | Internal town identifier (legacy ANR field) | `13005` |
| `SystemName` | String | Yes | Name of the collection system | `"Alburgh Waste Water Treatment Facility"` |
| `SystemOwner` | String | Yes | Entity responsible for the system | `"Village of Alburgh"` |
| `TownName` | String | No | Municipality name (from source file) | `"Alburgh"` |
| `TreatmentFacility` | String | Yes | ANR permit ID or name of the receiving WWTF | `"3-1245"` |
| `GISDate` | String | Yes | Date of original GIS work (inconsistent format — year, ISO date, or MM/DD/YY) | `"2008-06-24"` |
| `GISUpdate` | String | Yes | Date GIS was last updated (same format inconsistency as GISDate) | `"2008"` |
| `GISNotes` | String | Yes | Free-text GIS notes | — |
| `Creator` | String | Yes | Record creator identifier | `"VTANR"` |
| `SourceFile` | String | No | Original source filename | `"AlburghServieArea.geojson"` |
| `GEOIDTXT` | String | No | 10-digit FIPS code (shared admin field) | `"5001300860"` |
| `Municipal_Name` | String | No | Municipality name (shared admin field) | `"Alburgh"` |
| `County` | String | No | County name (shared admin field) | `"Grand Isle"` |
| `RPC` | String | No | Regional Planning Commission (shared admin field) | `"NRPC"` |

### Data Quality Notes
- `SystemOwner`: null for 23 of 186 features (12%)
- `TreatmentFacility`: null for 37 of 186 features (20%); populated values are either ANR permit IDs (format `"N-NNNN"`) or informal facility names
- `GISDate` and `GISUpdate`: inconsistent formats — values range from bare years (`"2001"`) to ISO dates (`"2008-06-24"`) to MM/DD/YY (`"06/08/25"`)
- `TownName` and `Municipal_Name` carry the same information from different sources; prefer `Municipal_Name` for joins

---

## 5. Vermont_Treatment_Facilities.geojson

**179 features** · Point · Wastewater treatment facilities (sourced from ANR NPDES permit database)

> These are permit-level records, not GIS infrastructure features. They represent treatment facilities with active or historical discharge permits, linked to a geographic point location.

### Schema

| Field | Type | Nullable | Description | Example |
|---|---|---|---|---|
| `FacilityID` | String | Yes | ANR internal facility identifier | `"VT0020001"` |
| `FacilityName` | String | Yes | Name of the treatment facility | `"Burlington WWTF"` |
| `PermitID` | String | Yes | ANR permit record ID | `"3-1001"` |
| `NPDESPermitNumber` | String | Yes | Federal NPDES permit number | `"VT0020001"` |
| `PermitRecordID` | String | Yes | Additional permit tracking ID | — |
| `PermitteeName` | String | Yes | Legal name of the permit holder | `"City of Burlington"` |
| `ProgramCategory` | String | Yes | Type of discharge permit | See domain below |
| `DesignHydraulicCapacityInMGD` | String | Yes | Design flow capacity in million gallons per day (stored as string) | `"8.10"` |
| `SeptageReceivedAtThisFacility` | String | Yes | Whether the facility accepts septage | `"Y"` or `"N"` |
| `PermitLink` | String | Yes | URL to the ANR permit record | — |
| `Latitude` | String | Yes | Facility latitude (stored as string, WGS 84) | `"44.4758"` |
| `Longitude` | String | Yes | Facility longitude (stored as string, WGS 84) | `"-73.2120"` |
| `TownName` | String | Yes | Municipality name (from source file) | `"Burlington"` |
| `SourceFile` | String | Yes | Original source filename | `"BurlingtonWWTF.geojson"` |
| `GEOIDTXT` | String | Yes | 10-digit FIPS code (shared admin field) | `"5000410300"` |
| `Municipal_Name` | String | No | Municipality name (shared admin field) | `"Burlington"` |
| `County` | String | No | County name (shared admin field) | `"Chittenden"` |
| `RPC` | String | No | Regional Planning Commission (shared admin field) | `"CCRPC"` |

### ProgramCategory Domain

| Value | Count |
|---|---|
| `"Municipal Discharge"` | 79 |
| `"Industrial Discharge"` | 65 |
| `"Pretreatment Discharge"` | 16 |
| null | 19 |

### SeptageReceivedAtThisFacility Domain

| Value | Count |
|---|---|
| `"N"` | 137 |
| `"Y"` | 23 |
| null | 19 |

### Data Quality Notes
- `DesignHydraulicCapacityInMGD`, `Latitude`, and `Longitude` are stored as strings — convert to float/numeric for analysis
- 19 features (10.6%) have null values across `ProgramCategory`, `SeptageReceivedAtThisFacility`, and `DesignHydraulicCapacityInMGD` — these appear to be facilities with incomplete permit data
- Geometry is always a single Point (the facility location); coordinates duplicate the `Latitude`/`Longitude` fields

---

## 6. Vermont_Town_GEOID_RPC_County.geojson

**256 features** · Polygon · Vermont municipal boundaries

> This is the reference/lookup file for all administrative joins. It provides the authoritative FIPS codes, county names, and RPC assignments for all 256 Vermont municipalities.

### Schema

| Field | Type | Nullable | Description | Example |
|---|---|---|---|---|
| `OBJECTID` | Integer | No | Sequential record identifier | `1` |
| `FIPS6` | Integer | No | 6-digit county+place FIPS numeric code | `9030` |
| `TOWNGEOID` | String | No | 10-digit FIPS place code — matches `GEOIDTXT` in all other files | `"5000911800"` |
| `TOWNNAME` | String | No | Town name in ALL CAPS | `"CANAAN"` |
| `TOWNNAMEMC` | String | No | Town name in mixed case | `"Canaan"` |
| `CNTY` | Integer | No | County numeric code | `9` |
| `Municipal_Name` | String | No | Normalized town name (same as `TOWNNAMEMC`, consistent with other files) | `"Canaan"` |
| `County` | String | No | County name | `"Essex"` |
| `RPC` | String | No | Regional Planning Commission abbreviation | `"NVDA"` |

### Key Join: TOWNGEOID → GEOIDTXT

To join any infrastructure feature to its municipality boundary:
```
Vermont_Town_GEOID_RPC_County.TOWNGEOID == Vermont_Linear_Features.GEOIDTXT
```
This is the primary spatial-administrative join across the entire dataset.

---

## Cross-File Relationships

```
Vermont_Town_GEOID_RPC_County.geojson  (256 municipalities — reference)
    │
    │  TOWNGEOID == GEOIDTXT
    ├──▶ Vermont_Linear_Features.geojson     (linear infrastructure, 205 municipalities)
    ├──▶ Vermont_Point_Features.geojson      (point infrastructure, 207 municipalities)
    ├──▶ Vermont_Water_Features.geojson      (stormwater mgmt areas)
    ├──▶ Vermont_ServiceAreas.geojson        (service boundaries)
    └──▶ Vermont_Treatment_Facilities.geojson (WWTF permit records)
```

---

## Common Filtering Patterns

### By system type
```python
# Wastewater pipes only
linear[linear["SystemType"] == "Wastewater"]

# Stormwater catch basins
points[(points["SystemType"] == "Stormwater") & (points["Type"] == 2)]
```

### By municipality
```python
# All features in Burlington
linear[linear["GEOIDTXT"] == "5000410300"]
# or equivalently:
linear[linear["Municipal_Name"] == "Burlington"]
```

### By county or RPC
```python
linear[linear["County"] == "Chittenden"]
points[points["RPC"] == "CCRPC"]
```

### Join to town boundaries
```python
import geopandas as gpd
towns = gpd.read_file("data/Vermont_Town_GEOID_RPC_County.geojson")
linear = gpd.read_file("data/Vermont_Linear_Features.geojson")
merged = linear.merge(towns[["TOWNGEOID","geometry"]], left_on="GEOIDTXT", right_on="TOWNGEOID")
```

---

## Known Data Quality Issues

| Issue | Affected files | Notes |
|---|---|---|
| `SourceDate` format inconsistency | Linear, Point | Some values are ISO date strings; others are millisecond epoch integers (from town data enrichment) |
| `GISDate` / `GISUpdate` format inconsistency | ServiceAreas | Mix of bare years, ISO dates, and MM/DD/YY strings |
| Numeric fields stored as strings | Treatment Facilities | `DesignHydraulicCapacityInMGD`, `Latitude`, `Longitude` — cast to float before analysis |
| Null `Status` | Linear (28,096), Point (178) | Assume `"Existing"` for infrastructure-era features where null |
| Null `Type` | Linear (147), Water (1) | Unclassifiable features from source data; retain and flag |
| Null `GEOIDTXT` | Linear (~handful) | Windsor town features — border file was empty; cannot be spatially linked |
| `Creator` username variants | Point | `"DA"`, `"DAVIDA"`, `"DAVID.AINLEY"` are the same person; `"CS"`, `"JIMP"`, `"JP"` are initials |
| `TownName` vs `Municipal_Name` | ServiceAreas, Treatment Facilities | Both carry municipality name; `Municipal_Name` is the consistent cross-file field |
| `Owner` field | Linear, Point, Water | Almost entirely null in current dataset |
