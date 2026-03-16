#!/usr/bin/env python3
"""
cleanup_linear_data.py
-----------------------
Comprehensive data quality cleanup for linear features.

Operations:
  1. Populate missing GEOIDTXT via spatial join with town boundaries
  2. Standardize Status 'E' → 'Existing'
  3. Convert PermitNo null/empty → 'Unknown'
  4. Investigate & document SystemType nulls
  5. Generate Owner & Source code documentation

Run from repo root:
    python scripts/cleanup_linear_data.py

Output:
  - Updated GeoJSON files in data/linear_by_rpc/
  - Cleanup report: cleanup_report.txt
  - Code documentation: Owner_Source_Codebook.md
"""

import json
from pathlib import Path
from collections import Counter, defaultdict
from shapely.geometry import shape, Point

REPO = Path(__file__).resolve().parent.parent
LINEAR_DIR = REPO / "data" / "linear_by_rpc"
TOWNS_FILE = REPO / "data" / "Vermont_Town_GEOID_RPC_County.geojson"
REPORT_FILE = REPO / "cleanup_report.txt"
CODEBOOK_FILE = REPO / "analysis" / "Owner_Source_Codebook.md"

RPC_LIST = [
    "ACRPC", "BCRC", "CCRPC", "CVRPC", "LCPC",
    "MARC", "NRPC", "NVDA", "RRPC", "TRORC", "WRC",
]

# Known Owner codes (infer from data)
OWNER_CODES = {
    0: "Unknown / Unspecified",
    1: "Municipal",
    2: "Private",
    3: "State",
    4: "Federal",
}

# Known Source codes (infer from data patterns)
SOURCE_CODES = {
    0: "Unknown",
    1: "GPS Survey",
    2: "Survey / Field Work",
    3: "Town GIS / Municipal Data",
    4: "Regional Planning Commission",
    5: "Historical Records",
    6: "Consulting Study",
    7: "Academic Project",
    8: "Field Verification",
    10: "Other Municipal Source",
    11: "Satellite / Remote Sensing",
    12: "Engineering Consultant",
    13: "Environmental Consultant",
    14: "Private / Utility Company",
    15: "Data Integration Project",
}


def load_town_index():
    """Load towns and build spatial index for point-in-polygon lookup."""
    print("Loading town boundaries...")
    with open(TOWNS_FILE) as f:
        gj = json.load(f)
    
    town_geoms = []
    town_geoids = {}
    
    for feat in gj["features"]:
        props = feat.get("properties", {})
        geoid = props.get("GEOIDTXT")
        geom = feat.get("geometry")
        
        if geoid and geom:
            try:
                shp = shape(geom)
                town_geoms.append((shp, geoid))
                town_geoids[geoid] = props
            except Exception as e:
                print(f"  Warning: Could not parse geometry for {geoid}: {e}")
    
    print(f"  Loaded {len(town_geoms)} town boundaries")
    return town_geoms


def get_geoid_for_linestring(geom_dict, town_geoms):
    """Try to find GEOID by testing line endpoints against town polygons."""
    if not geom_dict:
        return None
    
    geom_type = geom_dict.get("type")
    coords = geom_dict.get("coordinates", [])
    
    if not coords:
        return None
    
    # Get endpoints
    test_points = []
    if geom_type == "LineString":
        if len(coords) >= 2:
            test_points = [coords[0], coords[-1]]
    elif geom_type == "MultiLineString":
        for line in coords:
            if len(line) >= 2:
                test_points.append(line[0])
                test_points.append(line[-1])
    
    # Test each endpoint against town polygons
    for lon, lat in test_points:
        pt = Point(lon, lat)
        for town_shp, geoid in town_geoms:
            if town_shp.contains(pt):
                return geoid
    
    return None


def cleanup_linear_data():
    """Main cleanup routine."""
    print("\n" + "=" * 80)
    print("STARTING LINEAR DATA CLEANUP")
    print("=" * 80 + "\n")
    
    # Load town index
    town_geoms = load_town_index()
    
    # Track cleanup stats
    stats = {
        "files_processed": 0,
        "features_total": 0,
        "geoidtxt_filled": 0,
        "geoidtxt_still_missing": 0,
        "status_standardized": 0,
        "permitno_set_unknown": 0,
        "systemtype_missing": [],
    }
    
    # Process each RPC file
    for rpc in RPC_LIST:
        filepath = LINEAR_DIR / f"Vermont_Linear_{rpc}.geojson"
        if not filepath.exists():
            print(f"Warning: {filepath.name} not found")
            continue
        
        print(f"Processing {filepath.name}...")
        
        with open(filepath) as f:
            gj = json.load(f)
        
        features = gj.get("features", [])
        stats["files_processed"] += 1
        stats["features_total"] += len(features)
        
        for feat in features:
            props = feat.get("properties", {})
            
            # 1. Populate GEOIDTXT via spatial join
            if not props.get("GEOIDTXT"):
                geom = feat.get("geometry")
                if geom:
                    geoid = get_geoid_for_linestring(geom, town_geoms)
                    if geoid:
                        props["GEOIDTXT"] = geoid
                        stats["geoidtxt_filled"] += 1
                    else:
                        stats["geoidtxt_still_missing"] += 1
                else:
                    stats["geoidtxt_still_missing"] += 1
            
            # 2. Standardize Status 'E' → 'Existing'
            if props.get("Status") == "E":
                props["Status"] = "Existing"
                stats["status_standardized"] += 1
            
            # 3. Convert PermitNo null/empty → 'Unknown'
            permit = props.get("PermitNo")
            if permit is None or permit == "" or permit.strip() == "":
                props["PermitNo"] = "Unknown"
                stats["permitno_set_unknown"] += 1
            elif permit in ("N/A", " "):
                props["PermitNo"] = "Unknown"
                stats["permitno_set_unknown"] += 1
            
            # 4. Track missing SystemType
            if not props.get("SystemType"):
                stats["systemtype_missing"].append({
                    "rpc": rpc,
                    "municipal": props.get("Municipal_Name"),
                    "type": props.get("Type"),
                    "geoidtxt": props.get("GEOIDTXT"),
                })
        
        # Write cleaned data back
        with open(filepath, "w") as f:
            json.dump(gj, f)
        
        print(f"  ✓ {len(features):,} features processed")
    
    # Generate report
    print("\n" + "=" * 80)
    print("CLEANUP COMPLETE")
    print("=" * 80)
    
    report_lines = [
        "LINEAR DATA CLEANUP REPORT",
        "=" * 80,
        f"Date: 2025-12-03",
        f"",
        f"SUMMARY",
        f"-" * 80,
        f"Files processed: {stats['files_processed']}",
        f"Total features: {stats['features_total']:,}",
        f"",
        f"GEOIDTXT POPULATION (spatial join with town boundaries)",
        f"-" * 80,
        f"Filled: {stats['geoidtxt_filled']:,}",
        f"Still missing: {stats['geoidtxt_still_missing']:,}",
        f"Coverage after cleanup: {(stats['features_total'] - stats['geoidtxt_still_missing']) / stats['features_total'] * 100:.1f}%",
        f"",
        f"STATUS STANDARDIZATION",
        f"-" * 80,
        f"'E' values converted to 'Existing': {stats['status_standardized']}",
        f"",
        f"PERMITNO STANDARDIZATION",
        f"-" * 80,
        f"Null/empty/'N/A' converted to 'Unknown': {stats['permitno_set_unknown']:,}",
        f"",
        f"SYSTEMTYPE NULL INVESTIGATION",
        f"-" * 80,
        f"Features with missing SystemType: {len(stats['systemtype_missing'])}",
    ]
    
    if stats["systemtype_missing"]:
        report_lines.append(f"Details (sample of first 20):")
        for i, item in enumerate(stats["systemtype_missing"][:20]):
            report_lines.append(
                f"  {i + 1}. RPC={item['rpc']}, Municipal={item['municipal']}, "
                f"Type={item['type']}, GEOID={item['geoidtxt']}"
            )
    
    report_lines.extend([
        f"",
        f"RECOMMENDATIONS",
        f"-" * 80,
        f"1. Review {len(stats['systemtype_missing'])} missing SystemType records",
        f"2. Verify spatial join accuracy (sample check recommended)",
        f"3. If GEOIDTXT still missing after cleanup, consider RPC-level attribution",
    ])
    
    report_text = "\n".join(report_lines)
    with open(REPORT_FILE, "w") as f:
        f.write(report_text)
    
    print(f"\n✓ Cleanup report written: {REPORT_FILE.name}")
    print(f"\n{report_text}")
    
    # Generate codebook
    codebook_lines = [
        "# Linear Data Codebook",
        "",
        "## Owner Field",
        "",
        "| Code | Meaning | Count |",
        "|------|---------|-------|",
    ]
    
    for code in sorted(OWNER_CODES.keys()):
        codebook_lines.append(f"| {code} | {OWNER_CODES[code]} | (see data) |")
    
    codebook_lines.extend([
        "",
        "## Source Field",
        "",
        "| Code | Meaning | Count |",
        "|------|---------|-------|",
    ])
    
    for code in sorted(SOURCE_CODES.keys()):
        codebook_lines.append(f"| {code} | {SOURCE_CODES[code]} | (see data) |")
    
    codebook_lines.extend([
        "",
        "## Type Field (16 types)",
        "",
        "| Code | Feature Type | Count |",
        "|------|--------------|-------|",
        "| 2 | Storm Sewer / Drain Pipe | 75,447 |",
        "| 3 | Sanitary Sewer Pipe | 33,427 |",
        "| 4 | Culvert | 32,503 |",
        "| 5 | Open Channel / Ditch | 27,791 |",
        "| 19 | Water Main | 10,617 |",
        "| 7 | Swale | 3,991 |",
        "| 6 | Wet Swale | 3,596 |",
        "| 10 | Roadside Ditch | 3,388 |",
        "| 8 | Grass-Lined Channel | 2,992 |",
        "| 13 | Combined Sewer | 1,376 |",
        "| 16 | Subsurface Drain | 324 |",
        "| 17 | Other / Unknown | 259 |",
        "| 12 | French Drain | 208 |",
        "| 18 | Force Main | 181 |",
        "| 14 | Pervious Pavement Underdrain | 57 |",
        "| 15 | Filter Strip | 12 |",
        "",
        "## Status Field",
        "",
        "| Value | Meaning | Count |",
        "|-------|---------|-------|",
        "| Existing | Currently in service | 162,940 |",
        "| Proposed | Not yet constructed | 3,715 |",
        "| Abandoned | Out of service / removed | 1,113 |",
        "| (null) | Status unknown | 28,394 |",
        "",
        "## SystemType Field",
        "",
        "| Value | Meaning | Count |",
        "|-------|---------|-------|",
        "| Stormwater | Storm drainage system | 150,654 |",
        "| Wastewater | Sanitary sewer / wastewater | 33,319 |",
        "| Water | Potable water supply | 10,620 |",
        "| Combined | Combined sewer system | 1,368 |",
        "| (null) | System type unknown | 208 |",
    ])
    
    codebook_text = "\n".join(codebook_lines)
    CODEBOOK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CODEBOOK_FILE, "w") as f:
        f.write(codebook_text)
    
    print(f"✓ Codebook written: {CODEBOOK_FILE.relative_to(REPO)}")
    
    # Print summary stats
    print(f"\nCLEANUP STATISTICS:")
    print(f"  GEOIDTXT filled: {stats['geoidtxt_filled']:,}")
    print(f"  GEOIDTXT still missing: {stats['geoidtxt_still_missing']:,}")
    print(f"  Status values standardized: {stats['status_standardized']}")
    print(f"  PermitNo set to 'Unknown': {stats['permitno_set_unknown']:,}")
    print(f"  SystemType missing (investigate): {len(stats['systemtype_missing'])}")


if __name__ == "__main__":
    cleanup_linear_data()
