#!/usr/bin/env python3
"""
Merge all Vermont town-level GeoJSON files into 5 statewide datasets.
Applies field normalization per data/data_standards.md.

Output files (data/merged/):
  Vermont_Border.geojson
  Vermont_LinearFeatures.geojson
  Vermont_PointFeatures.geojson
  Vermont_ServiceAreas.geojson
  Vermont_WWTF.geojson
"""

import json
import os
import glob
import uuid
import re
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
OUTPUT_DIR = Path("data/merged")
TOWNS_DIR  = Path("data/Towns")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# State-level dump files accidentally placed in town folders (all identical, 33149 features)
# State-level dump files accidentally placed in town folders
# 33149 = identical statewide wastewater line export (7 towns)
# 25687 = identical/near-identical statewide wastewater point export (3 towns)
STATE_LEVEL_FEATURE_COUNTS = {33149, 25687}

# ── Lookup tables ─────────────────────────────────────────────────────────────

LINEAR_TYPE_MAP = {
    "sewer pipe":         3,
    "sanitary line":      3,
    "sewer pipe":         3,
    "combined sewer pipe":13,
    "combined sewer":     13,
    "stormwater pipe":    2,
}

POINT_TYPE_MAP = {
    "sanitary manhole":           4,
    "sewer manhole":              4,
    "combined sewer manhole":     24,
    "combined sewer manhole":     24,
    "combined sewer catchbasin":  2,
    "catchbasin":                 2,
    "combined sewer outfall":     23,
    "known cso outfalls":         23,
    "cb tied to sanitary sewer":  2,
    "stormwater manhole":         8,
    "information point":          17,
    "other":                      17,
    "other - insert comment":     17,
    "unknown point":              17,
}

SOURCE_STR_MAP = {
    "data from municipality":                   3,
    "municipality member knowledge":            2,
    "data collected in field":                  8,
    "wastewater division plans":                6,
    "wastewater division plan interpretation":  6,
    "stormwater permit plan interpretation":    4,
    "stormwater permit plam interpretation":    4,
    "town plan interpretation":                 3,
    "orthophotography interpretation":          5,
    "mapping grade gps":                        7,
    "contractor gis/gps":                       7,
    "act 250 permit plans":                     4,
    "anr web vt":                               None,
    "anrweb.vt":                                None,
    "from rpc":                                 None,
}

SYSTEMTYPE_NORM = {
    "wastewater": "Wastewater",
    "stormwater": "Stormwater",
    "water":      "Water",
    "combined":   "Combined",
    " ":          None,
    "":           None,
}

STATUS_NORM = {
    "existing":  "Existing",
    "e":         "Existing",
    "proposed":  "Proposed",
    "abandoned": "Abandoned",
    "absent":    "Absent",
    "potential": "Potential",
}

# Keys that are always structure / can be skipped in malformed detection
SKIP_KEYS = {
    "OBJECTID", "OBJECTID_1", "OBJECTID 1", "FID",
    "Shape_Length", "Shape_Area", "Shape_STAr", "Shape_STLe", "Shape Length",
    "FacilityID", "PermitRecordID",
}

# ── Regex patterns ────────────────────────────────────────────────────────────
DATE_PAT     = re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$|^\w+ \d{1,2}, \d{4}$")
PERMIT_PAT   = re.compile(r"^\d+-\d+$")
NPDES_PAT    = re.compile(r"^VT\d+$")
DECIMAL_PAT  = re.compile(r"^\d+\.\d+$")
URL_PAT      = re.compile(r"^https?://")
COMMA_INT    = re.compile(r"^\d{1,3}(,\d{3})+$")
YEAR_PAT     = re.compile(r"^\d{4}$")
INT_PAT      = re.compile(r"^\d+$")

# ── Malformed detection ───────────────────────────────────────────────────────

MALFORMED_KEY_VALS = {
    "wastewater", "stormwater", "water", "combined",
    "wastewater system", "wastwater system",
    "existing", "proposed", "abandoned",
    "public",
    "sewer pipe", "sanitary line", "combined sewer pipe", "combined sewer",
    "stormwater pipe",
    "sewer manhole", "sanitary manhole", "combined sewer manhole",
    "combined sewer catchbasin", "combined sewer outfall",
    "municipal discharge", "industrial discharge",
    "municipal", "industrial",
    "vtanr", "anr_admin",
}

def is_malformed(props):
    """Return True if feature properties use domain values as field names."""
    for k in props:
        if k in SKIP_KEYS:
            continue
        ks = str(k).strip().lower()
        if ks in MALFORMED_KEY_VALS:
            return True
        if DATE_PAT.match(str(k).strip()):
            return True
        if DECIMAL_PAT.match(str(k).strip()) and k not in ("0",):
            return True
        if PERMIT_PAT.match(str(k).strip()):
            return True
        if NPDES_PAT.match(str(k).strip()):
            return True
        if URL_PAT.match(str(k).strip()):
            return True
        if COMMA_INT.match(str(k).strip()):
            return True
    return False

# ── Normalization helpers ─────────────────────────────────────────────────────

def norm_systemtype(val):
    """Normalize a SystemType value. Returns None for unrecognized values."""
    if val is None:
        return None
    return SYSTEMTYPE_NORM.get(str(val).strip().lower())  # None for unrecognized

def norm_status(val):
    if val is None:
        return None
    return STATUS_NORM.get(str(val).strip().lower())

def norm_type_linear(val):
    if val is None:
        return None
    if isinstance(val, int):
        return val
    try:
        return int(val)
    except (ValueError, TypeError):
        pass
    return LINEAR_TYPE_MAP.get(str(val).strip().lower())

def norm_type_point(val):
    if val is None:
        return None
    if isinstance(val, int):
        return val
    try:
        return int(val)
    except (ValueError, TypeError):
        pass
    return POINT_TYPE_MAP.get(str(val).strip().lower())

def norm_source(val):
    if val is None:
        return None
    if isinstance(val, int):
        return val
    try:
        return int(val)
    except (ValueError, TypeError):
        pass
    mapped = SOURCE_STR_MAP.get(str(val).strip().lower())
    return mapped  # may be None for unrecognized strings

def strip_val(val):
    if isinstance(val, str):
        return val.strip() or None
    return val

def norm_yn(val):
    if val is None:
        return None
    v = str(val).strip().upper()
    if v in ("Y", "YES"):
        return "Y"
    if v in ("N", "NO"):
        return "N"
    return v

def norm_program_category(val):
    if val is None:
        return None
    v = str(val).strip().lower()
    if v in ("municipal", "municipal discharge"):
        return "Municipal Discharge"
    if v in ("industrial", "industrial discharge"):
        return "Industrial Discharge"
    return str(val).strip()

def norm_town_id(val):
    if val is None:
        return None
    s = str(val).replace(",", "").strip()
    try:
        return int(s)
    except ValueError:
        return None

def norm_municipal_ww(val):
    if val is None:
        return None
    v = str(val).strip().lower()
    if v in ("yes", "y", "1"):
        return "Yes"
    if v in ("no", "n", "0", ""):
        return "No"
    return str(val).strip()

# ── Border normalization ──────────────────────────────────────────────────────

BORDER_FIELD_MAP = {
    "name":               "Name",
    "name lsad":          "Name_LSAD",
    "name_lsad":          "Name_LSAD",
    "namelsad":           "Name_LSAD",
    "lsad":               "LSAD",
    "geoid":              "GEOID",
    "objectid":           "OBJECTID",
    "objectid_1":         None,
    "objectid 1":         None,
    "shape_length":       "Shape_Length",
    "shape length":       "Shape_Length",
    "shape_area":         "Shape_Area",
    "municipal wastewater":  "Municipal_Wastewater",
    "municipal_wastewater":  "Municipal_Wastewater",
    "municipalwastewater":   "Municipal_Wastewater",
    "municipal wastewate":   "Municipal_Wastewater",
    "municipal wastwater":   "Municipal_Wastewater",
    "classfp":            None,
}

def normalize_border(props, town_name):
    out = {}
    mw_val = None

    for k, v in props.items():
        kl = str(k).strip().lower()

        # Detect "Yes"/"No" used as field name (Alburgh border pattern)
        if k == "Yes":
            mw_val = "Yes"
            continue
        if k == "No":
            mw_val = "No"
            continue

        mapped = BORDER_FIELD_MAP.get(kl)
        if mapped is None:
            # Try NAME variant used as town name key (e.g. "Alburgh": "Alburgh")
            if str(k).strip() == town_name or str(v).strip() == town_name:
                out.setdefault("Name", str(v).strip() or town_name)
            # LSAD variant used as "<Town>_LSAD": "Alburgh town"
            elif str(k).strip().endswith("_LSAD") or str(k).strip().endswith(" LSAD"):
                out.setdefault("Name_LSAD", str(v).strip())
            # Skip truly unknown keys
            continue
        if mapped == "Municipal_Wastewater":
            mw_val = norm_municipal_ww(v)
        else:
            out[mapped] = v

    if mw_val is not None:
        out["Municipal_Wastewater"] = mw_val
    elif "Municipal_Wastewater" not in out:
        out["Municipal_Wastewater"] = None

    out.setdefault("Name", town_name)
    return out

# ── Linear / Point normalization ──────────────────────────────────────────────

# Field aliases for well-formed linear/point files
LP_FIELD_MAP = {
    "system_type":   "SystemType",
    "system type":   "SystemType",
    "systemtype":    "SystemType",
    "type":          "Type",
    "status":        "Status",
    "source":        "Source",
    "audience":      "Audience",
    "creator":       "Creator",
    "notes":         "Notes",
    "comment":       "Notes",
    "comments":      "Notes",
    "comment ":      "Notes",
    "notes ":        "Notes",
    "map_date":      "CreateDate",
    "map date":      "CreateDate",
    "mapdate":       "CreateDate",
    "source_date":   "SourceDate",
    "source date":   "SourceDate",
    "sourcedate":    "SourceDate",
    "objectid":      "OBJECTID",
    "objectid_1":    None,
    "objectid 1":    None,
    "objectid 1":    None,
    "shape_length":  "Shape_Length",
    "geoidtxt":      "GEOIDTXT",
}

def normalize_linear_props(props, geoidtxt):
    out = {"Audience": "Public", "GEOIDTXT": geoidtxt}
    for k, v in props.items():
        kl = str(k).strip().lower()
        mapped = LP_FIELD_MAP.get(kl)
        if mapped is None:
            continue
        if mapped == "Type":
            out["Type"] = norm_type_linear(v)
        elif mapped == "SystemType":
            out["SystemType"] = norm_systemtype(v)
        elif mapped == "Status":
            s = norm_status(v)
            # Guard: if status was set to a system type value, drop it
            if s is not None:
                out["Status"] = s
        elif mapped == "Source":
            out["Source"] = norm_source(v)
        elif mapped == "Notes":
            existing = out.get("Notes")
            new_val = strip_val(v)
            if existing and new_val and new_val != existing:
                out["Notes"] = f"{existing}; {new_val}"
            elif new_val:
                out["Notes"] = new_val
        elif mapped == "OBJECTID":
            out["OBJECTID"] = v
        elif mapped is not None:
            out[mapped] = strip_val(v)
    return out

def normalize_point_props(props, geoidtxt):
    out = {"Audience": "Public", "GEOIDTXT": geoidtxt}
    for k, v in props.items():
        kl = str(k).strip().lower()
        mapped = LP_FIELD_MAP.get(kl)
        if mapped is None:
            continue
        if mapped == "Type":
            out["Type"] = norm_type_point(v)
        elif mapped == "SystemType":
            out["SystemType"] = norm_systemtype(v)
        elif mapped == "Status":
            s = norm_status(v)
            if s is not None:
                out["Status"] = s
        elif mapped == "Source":
            out["Source"] = norm_source(v)
        elif mapped == "Notes":
            existing = out.get("Notes")
            new_val = strip_val(v)
            if existing and new_val and new_val != existing:
                out["Notes"] = f"{existing}; {new_val}"
            elif new_val:
                out["Notes"] = new_val
        elif mapped == "OBJECTID":
            out["OBJECTID"] = v
        elif mapped is not None:
            out[mapped] = strip_val(v)
    return out

# ── Malformed linear/point reconstruction ────────────────────────────────────

# Keys used as SystemType values in malformed files (key = actual SystemType)
SYSTEMTYPE_KEY_NAMES = {
    "wastewater system", "wastewater system", "wastwater system",
    "wastewater", "stormwater", "combined", "water",
}
SOURCE_KEY_NAMES = {
    "wastewater division plan interpretation",
    "wastewater division plans",
    "stormwater permit plan interpretation",
    "stormwater permit plam interpretation",
    "data from municipality",
    "data collected in field",
    "municipality member knowledge",
    "town plan interpretation",
    "orthophotography interpretation",
    "mapping grade gps",
    "contractor gis/gps",
    "act 250 permit plans",
    "from rpc",
}

def reconstruct_linear_malformed(props, geoidtxt):
    out = {"Audience": "Public", "GEOIDTXT": geoidtxt}
    for k, v in props.items():
        if k == "OBJECTID":
            out["OBJECTID"] = v
            continue
        if k == "Shape_Length":
            out["Shape_Length"] = v
            continue

        ks = str(k).strip().lower()
        vs = str(v).strip() if v is not None else ""

        # SystemType label key (e.g. 'Wastewater System', 'Wastewater system')
        # → SystemType comes from the VALUE; value may also be the Type
        if ks in ("wastewater system", "wastwater system"):
            st = norm_systemtype(vs)
            if st:
                out["SystemType"] = st
            # Fallback: derive from key
            out.setdefault("SystemType", "Wastewater")

        # Bare system type as key (e.g. 'Wastewater ', 'Combined')
        # → KEY is the SystemType; VALUE may be the Type string
        elif ks in ("wastewater", "stormwater", "water", "combined"):
            out.setdefault("SystemType", SYSTEMTYPE_NORM[ks])
            # If value looks like a type string, also capture it
            if vs.lower() in LINEAR_TYPE_MAP:
                out.setdefault("Type", LINEAR_TYPE_MAP[vs.lower()])

        # Status: key IS the status value
        elif ks in ("existing", "proposed", "abandoned"):
            out["Status"] = STATUS_NORM.get(ks, ks.capitalize())

        # Audience: key IS the audience value
        elif ks == "public":
            out["Audience"] = "Public"

        # Type: key is the type string (e.g. 'Sewer pipe', 'Combined Sewer')
        elif ks in LINEAR_TYPE_MAP:
            out.setdefault("Type", LINEAR_TYPE_MAP[ks])
            # If value looks like a valid system type, capture it
            sv = norm_systemtype(vs)
            if sv:
                out.setdefault("SystemType", sv)

        # Source: key is the source label; value is also the source label (use value)
        elif ks in SOURCE_KEY_NAMES:
            out["Source"] = norm_source(vs) or norm_source(ks)

        # Creator: key is org name (VTANR, ANR_ADMIN), value is username
        elif ks in ("vtanr", "anr_admin"):
            out["Creator"] = strip_val(v) or "VTANR"

        # Notes: key is "None" or other placeholder
        elif ks in ("none", "field"):
            out.setdefault("Notes", strip_val(v))

        # Date: key is a date string (e.g. '8/28/2020'), value is epoch ms or date
        elif DATE_PAT.match(str(k).strip()):
            # Store as CreateDate (the key is the date)
            out.setdefault("CreateDate", str(k).strip())

    return out

def reconstruct_point_malformed(props, geoidtxt):
    out = {"Audience": "Public", "GEOIDTXT": geoidtxt}
    for k, v in props.items():
        if k == "OBJECTID":
            out["OBJECTID"] = v
            continue
        if k == "Shape_Length":
            out["Shape_Length"] = v
            continue

        ks = str(k).strip().lower()
        vs = str(v).strip() if v is not None else ""

        if ks in SYSTEMTYPE_KEY_NAMES:
            out["SystemType"] = norm_systemtype(vs) or norm_systemtype(ks)
        elif ks in ("existing", "proposed", "abandoned"):
            out["Status"] = STATUS_NORM.get(ks, ks.capitalize())
        elif ks == "public":
            out["Audience"] = "Public"
        elif ks in POINT_TYPE_MAP:
            out["Type"] = POINT_TYPE_MAP[ks]
        elif ks in SOURCE_KEY_NAMES:
            out["Source"] = norm_source(vs) or norm_source(ks)
        elif ks in ("vtanr", "anr_admin"):
            out["Creator"] = strip_val(v) or "VTANR"
        elif ks in ("none", "field"):
            out.setdefault("Notes", strip_val(v))
        elif DATE_PAT.match(str(k).strip()):
            out.setdefault("CreateDate", str(k).strip())

    return out

# ── WWTF normalization ────────────────────────────────────────────────────────

WWTF_FIELD_MAP = {
    "facilityid":                       "FacilityID",
    "facility id":                      "FacilityID",
    "facilityname":                     "FacilityName",
    "facility name":                    "FacilityName",
    "facility name ":                   "FacilityName",
    "permitid":                         "PermitID",
    "permit id":                        "PermitID",
    "npdespermitnumber":                "NPDESPermitNumber",
    "npdes permit number":              "NPDESPermitNumber",
    "permittename":                     "PermitteeName",
    "permittee name":                   "PermitteeName",
    "programcategory":                  "ProgramCategory",
    "program category":                 "ProgramCategory",
    " program category":                "ProgramCategory",
    "designhydrauliccapacityinmgd":     "DesignHydraulicCapacityInMGD",
    "design hydraulic capacity in mgd": "DesignHydraulicCapacityInMGD",
    "septagereceivedatthisfacility":    "SeptageReceivedAtThisFacility",
    "septage received at this facility":"SeptageReceivedAtThisFacility",
    "septage recieved at this facility":"SeptageReceivedAtThisFacility",
    "septage received at thisf acility":"SeptageReceivedAtThisFacility",
    "permitlink":                        "PermitLink",
    "permit link":                       "PermitLink",
    "permit link ":                      "PermitLink",
    "permit link  ":                     "PermitLink",
    "permint link":                      "PermitLink",
    "permitrecordid":                    "PermitRecordID",
    "permit record id":                  "PermitRecordID",
    "latitude":                          "Latitude",
    "longitude":                         "Longitude",
    "objectid":                          "OBJECTID",
    "objectid_1":                        None,
    "fid":                               None,
    "field":                             None,
}

def normalize_wwtf_props(props):
    out = {}
    for k, v in props.items():
        kl = str(k).strip().lower()

        # URL key → PermitLink
        if URL_PAT.match(str(k).strip()):
            out.setdefault("PermitLink", str(k).strip())
            continue

        # Permit ID key with NPDES number as value → NPDESPermitNumber
        if PERMIT_PAT.match(str(k).strip()):
            vs = str(v).strip() if v else ""
            if NPDES_PAT.match(vs):
                out.setdefault("NPDESPermitNumber", vs)
                # Don't override existing PermitID from a proper field
            else:
                out.setdefault("PermitID", str(k).strip())
                if vs and not out.get("FacilityID") and INT_PAT.match(vs):
                    out["FacilityID"] = vs
            continue

        mapped = WWTF_FIELD_MAP.get(kl)
        if mapped is None:
            continue  # Drop unknown/artifact fields

        if mapped == "ProgramCategory":
            out[mapped] = norm_program_category(v)
        elif mapped == "SeptageReceivedAtThisFacility":
            out[mapped] = norm_yn(v)
        elif mapped == "FacilityID":
            # Strip comma-formatting
            s = str(v).replace(",", "").strip() if v else None
            out[mapped] = s
        else:
            out[mapped] = strip_val(v)

    return out

def reconstruct_wwtf_malformed(props):
    """Reconstruct a fully malformed WWTF feature from value-as-key pattern."""
    out = {}
    names = []   # collect candidate facility/permittee names

    for k, v in props.items():
        if k == "OBJECTID":
            out["OBJECTID"] = v
            continue
        if k in ("PermitRecordID",):
            out["PermitRecordID"] = strip_val(v)
            continue
        if k in ("FacilityID",):
            out["FacilityID"] = str(v).replace(",", "").strip() if v else None
            continue

        ks = str(k).strip()
        vs = str(v).strip() if v is not None else ""

        if URL_PAT.match(ks):
            out.setdefault("PermitLink", ks)
        elif NPDES_PAT.match(ks):
            out.setdefault("NPDESPermitNumber", ks)
        elif PERMIT_PAT.match(ks):
            if NPDES_PAT.match(vs):
                out.setdefault("NPDESPermitNumber", vs)
                out.setdefault("PermitID", ks)
            elif INT_PAT.match(vs) and vs != ks:
                out.setdefault("FacilityID", vs)
                out.setdefault("PermitID", ks)
            else:
                # Key = value = permit ID
                out.setdefault("PermitID", ks)
        elif DECIMAL_PAT.match(ks):
            # Key is the MGD value itself
            out.setdefault("DesignHydraulicCapacityInMGD", ks)
        elif ks.lower() in ("n", "no"):
            out.setdefault("SeptageReceivedAtThisFacility", "N")
        elif ks.lower() in ("y", "yes"):
            out.setdefault("SeptageReceivedAtThisFacility", "Y")
        elif ks.lower() in ("municipal discharge", "industrial discharge", "municipal", "industrial"):
            out.setdefault("ProgramCategory", norm_program_category(ks))
        elif COMMA_INT.match(ks):
            # Comma-formatted integer (likely FacilityID)
            out.setdefault("FacilityID", ks.replace(",", ""))
        else:
            # Looks like a name string — collect candidates
            # Use value (which is usually the correctly-spelled version)
            val = vs if vs else ks
            if val and val not in names:
                names.append(val)

    # Assign collected names: first → FacilityName, second → PermitteeName
    if names:
        out.setdefault("FacilityName", names[0])
    if len(names) >= 2:
        out.setdefault("PermitteeName", names[1])

    return out

# ── ServiceArea normalization ─────────────────────────────────────────────────

SA_FIELD_MAP = {
    "system_name":    "SystemName",
    "system name":    "SystemName",
    "ssysname":       "SystemName",
    "system_owner":   "SystemOwner",
    "system owner":   "SystemOwner",
    "ssysowner":      "SystemOwner",
    "treatment_facility": "TreatmentFacility",
    "treatment facility": "TreatmentFacility",
    "strtmntfac":     "TreatmentFacility",
    "itown":          "TownID",
    "town id":        "TownID",
    "townid":         "TownID",
    "creator":        "Creator",
    "gis_notes":      "GISNotes",
    "gis notes":      "GISNotes",
    "sgisnotes":      "GISNotes",
    "gis_date":       "GISDate",
    "gis date":       "GISDate",
    "sgisdate":       "GISDate",
    "gis_update":     "GISUpdate",
    "gis update":     "GISUpdate",
    "iupdate":        "GISUpdate",
    "sgissource":     None,
    "sgisorg":        "Creator",
    "sgisperson":     None,
    "iconsyr":        None,
    "itotcon":        None,
    "irescon":        None,
    "inonrescon":     None,
    "sqcperson":      None,
    "sqcstatus":      None,
    "objectid":       "OBJECTID",
    "objectid_1":     None,
    "shape_area":     "Shape_Area",
    "shape_star":     "Shape_Area",
    "shape area":     "Shape_Area",
    "shape_length":   "Shape_Length",
    "shape_stle":     "Shape_Length",
    "shape length":   "Shape_Length",
    "vtanr":          "Creator",
}

def normalize_servicearea_props(props):
    out = {}
    for k, v in props.items():
        kl = str(k).strip().lower()
        mapped = SA_FIELD_MAP.get(kl)
        if mapped is None:
            continue
        if mapped == "TownID":
            out[mapped] = norm_town_id(v)
        elif mapped == "Creator" and kl == "vtanr":
            out.setdefault("Creator", "VTANR")
        else:
            out[mapped] = strip_val(v)
    return out

def reconstruct_servicearea_malformed(props):
    out = {}
    names = []

    for k, v in props.items():
        ks = str(k).strip()
        vs = str(v).strip() if v is not None else ""

        if k == "OBJECTID":
            out["OBJECTID"] = v
            continue
        if k in ("Shape_Length", "Shape_Area"):
            out[k] = v
            continue
        if k in ("PermitRecordID",):
            out["PermitRecordID"] = vs
            continue

        kl = ks.lower()

        # Check for canonical-like field names first
        if kl in SA_FIELD_MAP and SA_FIELD_MAP[kl] is not None:
            mapped = SA_FIELD_MAP[kl]
            if mapped == "TownID":
                out.setdefault(mapped, norm_town_id(v))
            elif mapped == "Creator" and kl == "vtanr":
                out.setdefault("Creator", strip_val(v) or "VTANR")
            else:
                out.setdefault(mapped, strip_val(v))
            continue

        # Permit ID key → TreatmentFacility
        if PERMIT_PAT.match(ks):
            out.setdefault("TreatmentFacility", ks)
            continue

        # Comma-formatted integer → TownID
        if COMMA_INT.match(ks):
            out.setdefault("TownID", int(ks.replace(",", "")))
            continue

        # Integer key → TownID (use value which may be different/correct)
        if INT_PAT.match(ks) and len(ks) >= 4:
            # Value is the authoritative TownID
            tid = norm_town_id(vs) if vs else norm_town_id(ks)
            out.setdefault("TownID", tid)
            continue

        # Year key → GISDate
        if YEAR_PAT.match(ks):
            out.setdefault("GISDate", ks)
            continue

        # Date key → GISUpdate
        if DATE_PAT.match(ks):
            out.setdefault("GISUpdate", ks)
            continue

        # "None" → GISNotes
        if kl == "none":
            out.setdefault("GISNotes", strip_val(v))
            continue

        # "N" or "No" → possibly GISNotes or just drop
        if kl in ("n", "no"):
            continue

        # VTANR → Creator
        if kl == "vtanr":
            out.setdefault("Creator", strip_val(v) or "VTANR")
            continue

        # Long text string → collect as names
        if len(ks) > 5:
            # Use value (usually the correctly-spelled version), fall back to key
            val = vs if vs and vs.lower() != kl else ks
            if val and val not in names:
                names.append(val)

    # Assign collected names: first → SystemName, second → SystemOwner
    if names:
        out.setdefault("SystemName", names[0])
    if len(names) >= 2:
        out.setdefault("SystemOwner", names[1])

    return out

# ── File discovery helpers ─────────────────────────────────────────────────────

def find_border_file(town_dir):
    """Find the border file for a town, searching recursively through subdirectories."""
    # Search both direct and one-level-deep subdirectories
    search_dirs = [town_dir] + [d for d in town_dir.iterdir() if d.is_dir()]
    for sdir in search_dirs:
        # Look for geojson and json files
        for ext in ("*.geojson", "*.json"):
            for m in glob.glob(str(sdir / ext)):
                b = os.path.basename(m)
                if any(x in b for x in ("Border", "Boundary", "Bound")):
                    return m
        # Fallback: any .json/.geojson that isn't Linear/Point/WWTF/Service
        for ext in ("*.geojson", "*.json"):
            for m in glob.glob(str(sdir / ext)):
                b = os.path.basename(m)
                if not any(x in b for x in ("Linear", "Point", "WWTF", "WWT.", "Service", "Servie")):
                    return m
    return None

def find_files_by_type(town_dir, keywords):
    """Find files matching keyword list, searching recursively through subdirectories."""
    results = []
    search_dirs = [town_dir] + [d for d in town_dir.iterdir() if d.is_dir()]
    for sdir in search_dirs:
        for ext in ("*.geojson", "*.json"):
            for f in glob.glob(str(sdir / ext)):
                b = os.path.basename(f)
                if any(kw in b for kw in keywords):
                    results.append(f)
    return results

# ── Hardcoded overrides for corrupted source data ────────────────────────────

# Towns where all files have a one-position field shift due to GIS export corruption.
# The GEOID appears in the 'Name' field of the border file.
FIELD_SHIFT_TOWNS = {"Williamstown"}

# Ordered canonical WWTF field names — used to reconstruct shifted features
WWTF_CANONICAL_ORDER = [
    "FacilityID", "FacilityName", "DesignHydraulicCapacityInMGD",
    "SeptageReceivedAtThisFacility", "PermitID", "PermitteeName",
    "ProgramCategory", "NPDESPermitNumber", "PermitLink",
]

def reconstruct_shifted_wwtf(props):
    """Fix a WWTF feature where all values are shifted one field to the right.

    The file was exported with a corrupted first-column value (garbled unicode),
    pushing every value one position to the right relative to its field name.
    We extract values positionally and re-align them.
    """
    # Extract raw values in dict order (Python 3.7+ preserves insertion order)
    raw_values = list(props.values())

    # Drop the first value (the corrupted leading field, e.g. '㠀줡翻')
    shifted_values = raw_values[1:]

    # Align positionally to canonical field order
    out = {}
    for i, field in enumerate(WWTF_CANONICAL_ORDER):
        out[field] = shifted_values[i] if i < len(shifted_values) else None

    # Apply value normalization
    out["SeptageReceivedAtThisFacility"] = norm_yn(out.get("SeptageReceivedAtThisFacility"))
    out["ProgramCategory"] = norm_program_category(out.get("ProgramCategory"))
    out["FacilityID"] = str(out["FacilityID"]).replace(",", "").strip() if out.get("FacilityID") else None

    return out

def extract_geoid_from_shifted_border(props):
    """In field-shifted border files, the GEOID is stored in the 'Name' field."""
    name_val = str(props.get("Name", "")).strip()
    if re.match(r"^\d{10}$", name_val) and name_val.startswith("50"):
        return name_val
    return None

# ── GeoJSON writer ────────────────────────────────────────────────────────────

def make_feature(geometry, properties):
    return {
        "type": "Feature",
        "geometry": geometry,
        "properties": properties,
    }

def write_geojson(path, features):
    fc = {
        "type": "FeatureCollection",
        "features": features,
    }
    with open(path, "w") as f:
        json.dump(fc, f, separators=(",", ":"))
    print(f"  → {path} ({len(features):,} features)")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    border_features   = []
    linear_features   = []
    point_features    = []
    wwtf_features     = []
    service_features  = []

    skipped   = []
    warnings  = []

    town_dirs = sorted([
        d for d in Path(TOWNS_DIR).iterdir() if d.is_dir() and not d.name.startswith(".")
    ])

    print(f"Processing {len(town_dirs)} town directories…\n")

    for town_dir in town_dirs:
        town_name = town_dir.name

        # ── Get GEOID from border file ────────────────────────────────────────
        border_path = find_border_file(town_dir)
        geoidtxt = None

        if border_path:
            try:
                with open(border_path) as f:
                    bd = json.load(f)
                for feat in bd.get("features", []):
                    props = feat.get("properties", {})
                    gid = props.get("GEOID")
                    # Handle field-shifted towns: GEOID is in the Name field
                    if town_name in FIELD_SHIFT_TOWNS and (not gid or not str(gid).startswith("50")):
                        gid = extract_geoid_from_shifted_border(props)
                        if gid:
                            warnings.append(f"[FIELD-SHIFT] {town_name}: reconstructed GEOID {gid} from shifted border")
                    if gid and str(gid).startswith("50"):
                        geoidtxt = str(gid)
                        break

                # Normalize border features
                for feat in bd.get("features", []):
                    props = feat.get("properties", {})
                    if town_name in FIELD_SHIFT_TOWNS:
                        # Reconstruct shifted border: Name field holds GEOID
                        norm_props = {
                            "GEOID": extract_geoid_from_shifted_border(props) or geoidtxt,
                            "Name": town_name,
                            "Name_LSAD": f"{town_name} town",
                            "LSAD": "43",
                            "Municipal_Wastewater": None,  # Unknown due to corruption
                            "Shape_Length": props.get("Shape_Length", 0),
                            "Shape_Area": props.get("Shape_Area", 0),
                            "OBJECTID": props.get("OBJECTID"),
                        }
                        warnings.append(f"[FIELD-SHIFT] {town_name}: border fields reconstructed from shifted data")
                    else:
                        norm_props = normalize_border(props, town_name)
                    norm_props["TownName"] = town_name
                    if geoidtxt:
                        norm_props.setdefault("GEOID", geoidtxt)
                    border_features.append(make_feature(feat.get("geometry"), norm_props))

            except Exception as e:
                warnings.append(f"[BORDER] {border_path}: {e}")

        if not geoidtxt:
            warnings.append(f"[WARN] No GEOID found for {town_name} — GEOIDTXT will be null")

        # ── Linear features ───────────────────────────────────────────────────
        for fp in find_files_by_type(town_dir, ["Linear"]):
            try:
                with open(fp) as f:
                    data = json.load(f)
                feats = data.get("features", [])
                # Skip state-level duplicate files
                if len(feats) in STATE_LEVEL_FEATURE_COUNTS:
                    warnings.append(f"[SKIP-DUPLICATE] {fp}: {len(feats)} features match state-level dump — skipped")
                    continue
                count = 0
                for feat in feats:
                    props = feat.get("properties", {})
                    if is_malformed(props):
                        norm = reconstruct_linear_malformed(props, geoidtxt)
                    else:
                        norm = normalize_linear_props(props, geoidtxt)
                    norm["TownName"] = town_name
                    norm["SourceFile"] = os.path.basename(fp)
                    linear_features.append(make_feature(feat.get("geometry"), norm))
                    count += 1
                print(f"  [Linear] {town_name}: {count} features from {os.path.basename(fp)}")
            except Exception as e:
                warnings.append(f"[LINEAR] {fp}: {e}")

        # ── Point features ────────────────────────────────────────────────────
        for fp in find_files_by_type(town_dir, ["Point"]):
            try:
                with open(fp) as f:
                    data = json.load(f)
                feats_pt = data.get("features", [])
                if len(feats_pt) in STATE_LEVEL_FEATURE_COUNTS:
                    warnings.append(f"[SKIP-DUPLICATE] {fp}: {len(feats_pt)} features match state-level dump — skipped")
                    continue
                count = 0
                null_geom_count = 0
                for feat in feats_pt:
                    if feat.get("geometry") is None:
                        null_geom_count += 1
                        continue  # Skip features with no geometry
                    props = feat.get("properties", {})
                    if is_malformed(props):
                        norm = reconstruct_point_malformed(props, geoidtxt)
                    else:
                        norm = normalize_point_props(props, geoidtxt)
                    norm["TownName"] = town_name
                    norm["SourceFile"] = os.path.basename(fp)
                    point_features.append(make_feature(feat.get("geometry"), norm))
                    count += 1
                if null_geom_count:
                    warnings.append(f"[NULL-GEOM] {fp}: {null_geom_count} features skipped (null geometry)")
                print(f"  [Point]  {town_name}: {count} from {os.path.basename(fp)}")
            except Exception as e:
                warnings.append(f"[POINT] {fp}: {e}")

        # ── WWTF features ─────────────────────────────────────────────────────
        for fp in find_files_by_type(town_dir, ["WWTF", "WWT"]):
            # Exclude files containing other keywords accidentally matched
            if any(x in os.path.basename(fp) for x in ["Linear", "Point", "Service", "Servie", "Border", "Boundary"]):
                continue
            try:
                with open(fp) as f:
                    data = json.load(f)
                count = 0
                for feat in data.get("features", []):
                    props = feat.get("properties", {})
                    if town_name in FIELD_SHIFT_TOWNS:
                        norm = reconstruct_shifted_wwtf(props)
                    elif is_malformed(props):
                        norm = reconstruct_wwtf_malformed(props)
                    else:
                        norm = normalize_wwtf_props(props)
                    norm["TownName"] = town_name
                    norm["SourceFile"] = os.path.basename(fp)
                    if geoidtxt:
                        norm["GEOIDTXT"] = geoidtxt
                    wwtf_features.append(make_feature(feat.get("geometry"), norm))
                    count += 1
                print(f"  [WWTF]   {town_name}: {count} features from {os.path.basename(fp)}")
            except Exception as e:
                warnings.append(f"[WWTF] {fp}: {e}")

        # ── Service areas ─────────────────────────────────────────────────────
        for fp in find_files_by_type(town_dir, ["Service", "Servie"]):
            try:
                with open(fp) as f:
                    data = json.load(f)
                count = 0
                for feat in data.get("features", []):
                    props = feat.get("properties", {})
                    if is_malformed(props):
                        norm = reconstruct_servicearea_malformed(props)
                    else:
                        norm = normalize_servicearea_props(props)
                    norm["TownName"] = town_name
                    norm["SourceFile"] = os.path.basename(fp)
                    if geoidtxt:
                        norm.setdefault("GEOIDTXT", geoidtxt)
                    service_features.append(make_feature(feat.get("geometry"), norm))
                    count += 1
                print(f"  [Svc]    {town_name}: {count} features from {os.path.basename(fp)}")
            except Exception as e:
                warnings.append(f"[SERVICE] {fp}: {e}")

    # ── Write outputs ─────────────────────────────────────────────────────────
    print("\nWriting output files…")
    write_geojson(OUTPUT_DIR / "Vermont_Border.geojson",         border_features)
    write_geojson(OUTPUT_DIR / "Vermont_LinearFeatures.geojson", linear_features)
    write_geojson(OUTPUT_DIR / "Vermont_PointFeatures.geojson",  point_features)
    write_geojson(OUTPUT_DIR / "Vermont_WWTF.geojson",           wwtf_features)
    write_geojson(OUTPUT_DIR / "Vermont_ServiceAreas.geojson",   service_features)

    # ── Report ────────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"  Border features:   {len(border_features):>7,}")
    print(f"  Linear features:   {len(linear_features):>7,}")
    print(f"  Point features:    {len(point_features):>7,}")
    print(f"  WWTF features:     {len(wwtf_features):>7,}")
    print(f"  ServiceArea feats: {len(service_features):>7,}")
    print(f"  Total:             {sum([len(border_features),len(linear_features),len(point_features),len(wwtf_features),len(service_features)]):>7,}")

    if warnings:
        print(f"\nWARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  {w}")

    if skipped:
        print(f"\nSKIPPED ({len(skipped)}):")
        for s in skipped:
            print(f"  {s}")

if __name__ == "__main__":
    main()
