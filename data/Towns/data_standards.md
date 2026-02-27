# Town Data Standards
## Vermont Municipal Wastewater Infrastructure — Town-Level GeoJSON Files

This document defines the canonical schema for all town-level GeoJSON files and maps their inconsistent field names and values to the SoV (State of Vermont ANR/DEC) authoritative dataset schema. The goal is to normalize and merge town data into the SoV dataset where records do not already exist.

---

## File Types Per Town

Each town directory may contain up to five GeoJSON file types. Not all towns have all types.

| File pattern | Geometry | Description |
|---|---|---|
| `*Border.geojson` / `*Boundary.geojson` | Polygon | Municipal boundary |
| `*LinearFeatures.geojson` | LineString | Pipes, culverts, ditches |
| `*PointFeatures.geojson` | Point | Manholes, catch basins, outfalls, pump stations |
| `*WWTF.geojson` | Point | Wastewater treatment facility record(s) |
| `*ServiceArea.geojson` | Polygon | Sewer system service area boundary |

---

## Coordinate Reference System

All files use **WGS 84 geographic coordinates (EPSG:4326)**, consistent with the SoV dataset. No explicit `crs` property is present.

---

## 1. Border / Boundary Files

### Canonical Schema

| Field | Type | Required | SoV Equivalent | Description |
|---|---|---|---|---|
| `GEOID` | String | Yes | `GEOIDTXT` | 10-digit FIPS municipality code. Key link to SoV dataset. |
| `Name` | String | Yes | — | Municipality name (e.g., `"Barre"`) |
| `Name_LSAD` | String | Yes | — | Name with legal/statistical area description (e.g., `"Barre town"`) |
| `LSAD` | String | Yes | — | Legal/Statistical Area Description code (typically `"43"` for Vermont towns) |
| `Municipal_Wastewater` | String | Yes | — | Whether town has municipal wastewater system: `"Yes"` or `"No"` |
| `OBJECTID` | Integer | Yes | `OBJECTID` | Internal record ID |
| `Shape_Area` | Float | Yes | — | Polygon area (degrees²; often `0` as placeholder) |
| `Shape_Length` | Float | Yes | — | Polygon perimeter (degrees; often `0` as placeholder) |

### Field Name Variations Found

The following non-canonical field names appear in existing files and must be normalized:

| Non-canonical field name | Canonical field name | Notes |
|---|---|---|
| `Municipal Wastewater` | `Municipal_Wastewater` | Space variant |
| `Municipal_Wastewater` | `Municipal_Wastewater` | Already canonical |
| `MunicipalWastewater` | `Municipal_Wastewater` | No-space variant |
| `Municipal Wastewate` | `Municipal_Wastewater` | Truncated typo |
| `Municipal Wastwater` | `Municipal_Wastewater` | Missing 'e' typo |
| `NAME` | `Name` | All-caps variant |
| `Name LSAD` | `Name_LSAD` | Space variant |
| `NAMELSAD` | `Name_LSAD` | No-separator variant |
| `OBJECTID_1` | `OBJECTID` | Duplicate from join — drop |
| `OBJECTID 1` | `OBJECTID` | Space variant — drop |
| `CLASSFP` | — | Drop (not needed) |
| `Yes` / `No` (as field names) | `Municipal_Wastewater` | Severely malformed — field value used as column name |

### Value Normalization

- `Municipal_Wastewater`: normalize all variants to `"Yes"` or `"No"` (capitalize first letter only)

---

## 2. LinearFeatures Files

### Canonical Schema

Aligns with SoV line features. All fields should match SoV property names exactly for merge compatibility.

| Field | Type | Required | SoV Equivalent | Description |
|---|---|---|---|---|
| `OBJECTID` | Integer | Yes | `OBJECTID` | Internal record ID (reassign on merge) |
| `SystemType` | String | Yes | `SystemType` | See [SystemType domain](#systemtype-domain) |
| `Type` | Integer | Yes | `Type` | SoV type code. See [Linear Type Mapping](#linear-type-mapping) |
| `Status` | String | Yes | `Status` | See [Status domain](#status-domain) |
| `Source` | Integer | Yes | `Source` | See [Source domain](#source-domain) |
| `Audience` | String | Yes | `Audience` | Always `"Public"` |
| `Creator` | String | No | `Creator` | Username or organization |
| `Notes` | String | No | `Notes` | Free-text notes |
| `CreateDate` | String | No | `CreateDate` | Date in ISO 8601 format |
| `GEOIDTXT` | String | Yes | `GEOIDTXT` | Municipality FIPS code (derive from town Border file `GEOID`) |
| `Shape_Length` | Float | No | — | Segment length (degrees; recalculate on merge) |

> On merge into the SoV dataset, also populate: `GlobalID` (generate new UUID), `EditDate`, `Editor`, `PermitNo` (if known), `SourceDate`, `SourceNotes`.

### Field Name Variations Found

| Non-canonical field name | Canonical field name | Notes |
|---|---|---|
| `System_Type` | `SystemType` | Underscore variant (most common in town files) |
| `System Type` | `SystemType` | Space variant |
| `Wastewater System` | `SystemType` | Value used as field name — severely malformed |
| `Wastewater system` | `SystemType` | Value used as field name — severely malformed |
| `Comment` | `Notes` | Synonym |
| `Comments` | `Notes` | Synonym |
| `comment` | `Notes` | Lowercase variant |
| `Map_Date` | `CreateDate` | Mapping date used as proxy for creation date |
| `Map Date` | `CreateDate` | Space variant |
| `MapDate` | `CreateDate` | No-separator variant |
| `Source_Date` | `SourceDate` (SoV field) | Underscore variant |
| `Source Date` | `SourceDate` (SoV field) | Space variant |
| `OBJECTID_1` | — | Duplicate from join — drop |
| `Shape_Length` | `Shape_Length` | Already consistent |

> **Malformed files (Alburgh pattern):** Some town files have data values as field names. In these files, the actual field names (date strings, category names, creator names) appear as column headers with the true value in the first row. These files require full schema reconstruction before normalization.

### Linear Type Mapping

Town files use string type names or SoV integer codes interchangeably. Map all to SoV integer codes:

| Town string value | SoV Type code | SoV SystemType |
|---|---|---|
| `"Sewer pipe"` | `3` | `"Wastewater"` |
| `"Sanitary Line"` | `3` | `"Wastewater"` |
| `"Sewer Pipe"` | `3` | `"Wastewater"` |
| `"Combined sewer pipe"` | `13` | `"Combined"` |
| `"Combined Sewer"` | `13` | `"Combined"` |
| `"Stormwater pipe"` | `2` | `"Stormwater"` |
| `3` (integer) | `3` | Preserve existing `SystemType` |
| `13` (integer) | `13` | Preserve existing `SystemType` |

---

## 3. PointFeatures Files

### Canonical Schema

| Field | Type | Required | SoV Equivalent | Description |
|---|---|---|---|---|
| `OBJECTID` | Integer | Yes | `OBJECTID` | Internal record ID (reassign on merge) |
| `SystemType` | String | Yes | `SystemType` | See [SystemType domain](#systemtype-domain) |
| `Type` | Integer | Yes | `Type` | SoV type code. See [Point Type Mapping](#point-type-mapping) |
| `Status` | String | Yes | `Status` | See [Status domain](#status-domain) |
| `Source` | Integer | Yes | `Source` | See [Source domain](#source-domain) |
| `Audience` | String | Yes | `Audience` | Always `"Public"` |
| `Creator` | String | No | `Creator` | Username or organization |
| `Notes` | String | No | `Notes` | Free-text notes |
| `CreateDate` | String | No | `CreateDate` | Date in ISO 8601 format |
| `GEOIDTXT` | String | Yes | `GEOIDTXT` | Municipality FIPS code (derive from town Border file `GEOID`) |

### Field Name Variations Found

Same variations as LinearFeatures, plus:

| Non-canonical field name | Canonical field name | Notes |
|---|---|---|
| `Wastwater system` | `SystemType` | Typo — missing 'e' |
| `OBJECTID 1` | — | Drop |
| `OBJECTID_1` | — | Drop |

### Point Type Mapping

| Town string value | SoV Type code | SoV SystemType |
|---|---|---|
| `"Sanitary Manhole"` | `4` | `"Wastewater"` |
| `"Sewer manhole"` | `4` | `"Wastewater"` |
| `"Sewer Manhole"` | `4` | `"Wastewater"` |
| `"Combined sewer manhole"` | `4` or `24` | `"Combined"` — use `24` if CSO context |
| `"Combined Sewer Manhole"` | `4` or `24` | `"Combined"` |
| `"Combined sewer catchbasin"` | `2` | `"Combined"` |
| `"Catchbasin"` | `2` | `"Combined"` |
| `"Combined sewer outfall"` | `23` | `"Combined"` |
| `"Known CSO Outfalls"` | `23` | `"Combined"` |
| `"CB tied to Sanitary Sewer"` | `2` | `"Combined"` |
| `"Stormwater manhole"` | `8` | `"Stormwater"` |
| `"Information point"` | `17` | Preserve `SystemType` |
| `"Information Point"` | `17` | Preserve `SystemType` |
| `"Other"` | `17` | Preserve `SystemType` — add note |
| `"Other - insert comment"` | `17` | Preserve `SystemType` — migrate comment to `Notes` |
| `"Unknown Point"` | `17` | Preserve `SystemType` — flag for review |
| `4` (integer) | `4` | Preserve existing `SystemType` |
| `23` (integer) | `23` | Preserve existing `SystemType` |
| `25` (integer) | `25` | Preserve existing `SystemType` |
| `9`, `12`, `15`, `27` (integers) | same | Already SoV codes |

---

## 4. WWTF Files

### Canonical Schema

WWTF files do not have a direct equivalent in the three SoV polygon/line/point files. They correspond to ANR/DEC NPDES permit records. The canonical schema is:

| Field | Type | Required | Description |
|---|---|---|---|
| `OBJECTID` | Integer | Yes | Internal record ID |
| `FacilityID` | String | Yes | ANR internal facility ID |
| `FacilityName` | String | Yes | Facility common name (e.g., `"Barre City"`) |
| `PermitID` | String | Yes | ANR permit ID (e.g., `"3-1272"`) |
| `NPDESPermitNumber` | String | Yes | EPA NPDES permit number (e.g., `"VT0100889"`) |
| `PermitteName` | String | Yes | Legal permittee name (e.g., `"City of Barre"`) |
| `ProgramCategory` | String | Yes | `"Municipal Discharge"` or `"Industrial Discharge"` |
| `DesignHydraulicCapacityInMGD` | String | Yes | Design flow capacity in million gallons per day |
| `SeptageReceivedAtThisFacility` | String | Yes | `"Y"` or `"N"` |
| `PermitLink` | String | No | URL to ANR permit document |
| `PermitRecordID` | String | No | ANR web record ID |
| `Latitude` | String | No | Decimal degrees (WGS 84) |
| `Longitude` | String | No | Decimal degrees (WGS 84) |

### Field Name Variations Found

Two parallel naming conventions exist across files — convert all to camelCase canonical:

| Non-canonical (spaced) | Canonical (camelCase) | Notes |
|---|---|---|
| `Facility Name` | `FacilityName` | |
| `Facility Name ` | `FacilityName` | Trailing space |
| `Facility ID` | `FacilityID` | |
| `NPDES Permit Number` | `NPDESPermitNumber` | |
| `Permittee Name` | `PermitteeName` | |
| `Design Hydraulic Capacity In MGD` | `DesignHydraulicCapacityInMGD` | |
| `Septage Received At This Facility` | `SeptageReceivedAtThisFacility` | |
| `Septage Recieved At This Facility` | `SeptageReceivedAtThisFacility` | Typo |
| `Septage Received At ThisF acility` | `SeptageReceivedAtThisFacility` | Split-word typo |
| `Permit Link` | `PermitLink` | |
| `Permit Link ` | `PermitLink` | Trailing space |
| `Permit Link  ` | `PermitLink` | Two trailing spaces |
| `Permint Link` | `PermitLink` | Typo |
| `Permit ID` | `PermitID` | |
| `Permit Record ID` | `PermitRecordID` | |
| ` Program Category` | `ProgramCategory` | Leading space |
| `Field` | — | Artifact column — drop |
| `FID` | — | Artifact column — drop |

> **Malformed files (Alburgh pattern):** Some WWTF files use actual field values (permit IDs, URLs, facility names) as column headers. These require full schema reconstruction. Identify by checking if any column header matches a permit ID pattern (`3-NNNN`) or a URL pattern.

### Value Normalization

- `SeptageReceivedAtThisFacility`: normalize to `"Y"` or `"N"` only
- `ProgramCategory`: normalize to `"Municipal Discharge"` or `"Industrial Discharge"` (collapse `"Municipal"` → `"Municipal Discharge"`, `"Industrial"` → `"Industrial Discharge"`)
- `DesignHydraulicCapacityInMGD`: always store as string with 2 decimal places (e.g., `"0.07"`)

---

## 5. ServiceArea Files

### Canonical Schema

| Field | Type | Required | Description |
|---|---|---|---|
| `OBJECTID` | Integer | Yes | Internal record ID |
| `SystemName` | String | Yes | Sewer system name (e.g., `"Barre City"`) |
| `SystemOwner` | String | Yes | Owning entity name |
| `TreatmentFacility` | String | Yes | PermitID of the receiving WWTF (e.g., `"3-1272"`) |
| `TownID` | Integer | Yes | ANR town ID code (e.g., `23005`) |
| `Creator` | String | No | Creator username or organization |
| `GISDate` | String | No | Date GIS boundary was created (ISO 8601 or year) |
| `GISUpdate` | String | No | Date boundary was last updated |
| `GISNotes` | String | No | Notes on boundary methodology |
| `Shape_Area` | Float | No | Area (degrees²) |
| `Shape_Length` | Float | No | Perimeter (degrees) |

### Field Name Variations Found

Three parallel naming conventions exist — normalize all to no-separator camelCase:

| Non-canonical | Canonical | Convention |
|---|---|---|
| `System_Name` | `SystemName` | Underscore variant |
| `System Name` | `SystemName` | Space variant |
| `sSYSNAME` | `SystemName` | Legacy abbreviated |
| `System_Owner` | `SystemOwner` | Underscore variant |
| `System Owner` | `SystemOwner` | Space variant |
| `sSYSOWNER` | `SystemOwner` | Legacy abbreviated |
| `Treatment_Facility` | `TreatmentFacility` | Underscore variant |
| `Treatment Facility` | `TreatmentFacility` | Space variant |
| `sTRTMNTFAC` | `TreatmentFacility` | Legacy abbreviated |
| `iTOWN` | `TownID` | Legacy abbreviated |
| `Town ID` | `TownID` | Space variant |
| `GIS_Notes` | `GISNotes` | Underscore variant |
| `GIS Notes` | `GISNotes` | Space variant |
| `sGISNOTES` | `GISNotes` | Legacy abbreviated |
| `GIS_Date` | `GISDate` | Underscore variant |
| `GIS Date` | `GISDate` | Space variant |
| `sGISDATE` | `GISDate` | Legacy abbreviated |
| `GIS_Update` | `GISUpdate` | Underscore variant |
| `GIS Update` | `GISUpdate` | Space variant |
| `iUPDATE` | `GISUpdate` | Legacy abbreviated |
| `sGISSOURCE` | — | Legacy field — drop or migrate to `Creator` |
| `sGISORG` | `Creator` | Legacy abbreviated |
| `sGISPERSON` | — | Drop |
| `iCONSYR` | — | Drop (connection year — deprecated) |
| `iTOTCON` | — | Drop (total connections — deprecated) |
| `iRESCON` | — | Drop |
| `iNONRESCON` | — | Drop |
| `sQCPERSON` | — | Drop |
| `sQCSTATUS` | — | Drop |
| `Shape_STAr` | `Shape_Area` | Truncated variant |
| `Shape_STLe` | `Shape_Length` | Truncated variant |
| `OBJECTID_1` | — | Duplicate from join — drop |
| `Shape Length` | `Shape_Length` | Space variant |
| `VTANR` | `Creator` | Use `"VTANR"` as value, not column name |

> **Malformed files:** Some files use data values (facility names, town names, dates) as column headers. These require full schema reconstruction.

---

## Shared Domain Tables

### SystemType Domain

| Value | Description |
|---|---|
| `"Stormwater"` | Stormwater system |
| `"Wastewater"` | Sanitary sewer system |
| `"Water"` | Potable water system |
| `"Combined"` | Combined sewer system |
| `null` | Not assigned |

Town files sometimes store these as `System_Type` or `System Type` with the same values. Normalize to `SystemType`.

### Status Domain

| Canonical value | Non-canonical variants to normalize |
|---|---|
| `"Existing"` | `"E"`, `"Existing "` (trailing space) |
| `"Proposed"` | — |
| `"Abandoned"` | — |
| `"Absent"` | — |
| `"Potential"` | — |

Discard rows where `Status` contains a `SystemType` value (e.g., `"Wastewater"` in the Status field is a data error).

### Source Domain

Town files frequently use human-readable strings instead of the SoV integer codes. Map on merge:

| Town string | SoV integer code |
|---|---|
| `"Data from Municipality"` | `3` |
| `"Municipality Member Knowledge"` | `2` |
| `"Data Collected in Field"` | `8` |
| `"Wastewater Division Plans"` | `6` |
| `"Stormwater Permit Plan Interpretation"` | `4` |
| `"Stormwater Permit Plam Interpretation"` | `4` (typo — normalize first) |
| `"Town Plan Interpretation"` | `3` |
| `"Orthophotography Interpretation"` | `5` |
| `"Mapping Grade GPS"` | `7` |
| `"Contractor GIS/GPS"` | `7` |
| `"Act 250 Permit Plans"` | `4` |
| `"ANR Web VT"` | `null` (external reference — move to `SourceNotes`) |
| `"ANRweb.VT"` | `null` (same as above) |

---

## Malformed File Pattern (Alburgh-style)

Several towns (Alburgh confirmed; others may exist) have GeoJSON files where actual field values were used as column headers during export. These are identifiable by:

- Column names that are dates (e.g., `"8/28/2020"`, `"9/10/2020"`)
- Column names that are category values (e.g., `"Wastewater System"`, `"Sewer pipe"`, `"Existing"`)
- Column names that are usernames or URLs
- Only one or two rows of data

**Reconstruction approach:**
1. Identify the header row's column names as the first feature's values
2. Map each column name to its corresponding canonical field using domain knowledge
3. Reconstruct the properties dict with canonical field names
4. Validate against the canonical schema before adding to the dataset

---

## Merge Checklist

Before merging town features into the SoV dataset:

- [ ] Field names normalized to SoV canonical names
- [ ] `SystemType` is one of the canonical string values (or null)
- [ ] `Type` is converted to SoV integer code
- [ ] `Source` is converted to SoV integer code
- [ ] `Status` is one of the canonical string values
- [ ] `GEOIDTXT` populated from town Border file `GEOID`
- [ ] `GlobalID` generated as new UUID (do not reuse or leave blank)
- [ ] `Audience` set to `"Public"`
- [ ] Geometry is valid (no self-intersections, coordinates in WGS 84 range)
- [ ] Duplicate check: spatial proximity + `Type` + `SystemType` match against existing SoV features
- [ ] Malformed files reconstructed before field mapping
