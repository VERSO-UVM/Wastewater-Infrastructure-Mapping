#!/usr/bin/env python3
"""
verify_sewer_corridor.py
------------------------
Verify the Estimated Sewer Service Corridor area calculation.

This script:
1. Loads all wastewater and combined sewer features
2. Projects to UTM Zone 18 for accurate calculations
3. Buffers them by 300 feet (91.4 meters) on both sides
4. Unions (dissolves) overlapping buffers
5. Clips to Vermont town boundaries
6. Calculates total area in square miles

Expected: ~111.34 square miles

Run from repo root:
    python scripts/verify_sewer_corridor.py
"""

import json
from pathlib import Path

from shapely.geometry import shape
from shapely.ops import unary_union
import geopandas as gpd
from geopandas import GeoSeries, GeoDataFrame

REPO = Path(__file__).resolve().parent.parent
LINEAR_DIR = REPO / "data" / "linear_by_rpc"
TOWNS_FILE = REPO / "data" / "Vermont_Town_GEOID_RPC_County.geojson"


def load_linear_features():
    """Load all linear features from RPC split files."""
    paths = sorted(LINEAR_DIR.glob("Vermont_Linear_*.geojson"))
    features = []
    for path in paths:
        with path.open() as f:
            gj = json.load(f)
        features.extend(gj.get("features", []))
    return features


def load_vermont_boundary():
    """Load Vermont town boundaries and union them into one polygon."""
    with TOWNS_FILE.open() as f:
        towns_gj = json.load(f)
    
    polygons = []
    for feature in towns_gj.get("features", []):
        geom = feature.get("geometry")
        if geom:
            polygons.append(shape(geom))
    
    if not polygons:
        raise ValueError("No Vermont town polygons loaded")
    
    vermont_boundary = unary_union(polygons)
    return vermont_boundary


def verify_corridor():
    """Calculate the sewer service corridor area."""
    features = load_linear_features()
    vermont_boundary_wgs84 = load_vermont_boundary()
    
    # Filter to wastewater and combined only
    ww_features = [
        f for f in features 
        if (f.get("properties") or {}).get("SystemType") in ("Wastewater", "Combined")
    ]
    
    print(f"Total linear features: {len(features):,}")
    print(f"Wastewater + Combined features: {len(ww_features):,}")
    
    if not ww_features:
        print("No wastewater/combined features found")
        return
    
    # Create GeoDataFrame with wastewater/combined features
    geos = [{"geometry": shape(f.get("geometry"))} for f in ww_features]
    gdf = GeoDataFrame(geos, crs="EPSG:4326")
    
    # Project to UTM Zone 18 for accurate buffering and area calculation
    print("Projecting to UTM Zone 18...")
    gdf_utm = gdf.to_crs("EPSG:32618")  # UTM Zone 18N (covers Vermont)
    
    # 300 feet = 91.4432 meters
    BUFFER_DISTANCE_M = 91.4432
    print(f"Buffering by {BUFFER_DISTANCE_M} meters ({BUFFER_DISTANCE_M / 0.3048:.1f} feet)...")
    gdf_buffered = gdf_utm.copy()
    gdf_buffered["geometry"] = gdf_utm.geometry.buffer(BUFFER_DISTANCE_M)
    
    # Dissolve (union) all buffers using shapely for efficiency
    print("Unioning overlapping buffers (this may take a minute)...")
    buffered_geoms = [geom for geom in gdf_buffered.geometry]
    corridor_utm = unary_union(buffered_geoms)
    
    # Load and project Vermont boundary
    print("Projecting Vermont boundary to UTM...")
    vt_boundary_gdf = GeoDataFrame({"geometry": [vermont_boundary_wgs84]}, crs="EPSG:4326")
    vt_boundary_utm = vt_boundary_gdf.to_crs("EPSG:32618").iloc[0].geometry
    
    # Clip corridor to Vermont boundary
    print("Clipping corridor to Vermont boundary...")
    clipped_corridor_utm = corridor_utm.intersection(vt_boundary_utm)
    
    # Calculate area in square meters
    area_sq_meters = clipped_corridor_utm.area
    
    # Convert to square miles: 1 mile = 1609.34 meters
    sq_miles_per_sq_meter = 1 / (1609.34 ** 2)
    area_sq_miles = area_sq_meters * sq_miles_per_sq_meter
    
    print(f"\n{'='*60}")
    print(f"Sewer Service Corridor Area: {area_sq_miles:.2f} square miles")
    print(f"{'='*60}")
    print(f"\nExpected (from index.html): 111.34 square miles")
    print(f"Difference: {abs(area_sq_miles - 111.34):.2f} square miles ({abs(area_sq_miles - 111.34)/111.34*100:.1f}%)")


if __name__ == "__main__":
    verify_corridor()
