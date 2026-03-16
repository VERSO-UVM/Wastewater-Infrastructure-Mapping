#!/usr/bin/env python3
"""
transform_investment_to_linear_by_rpc.py
----------------------------------------
Transform Vermont_Water_Investment_Infrastructure_Public_-6999738747210364761.geojson
to match the linear infrastructure schema, enrich administrative fields from
Vermont_Town_GEOID_RPC_County.geojson, and split output by RPC.

Run from repo root:
    python scripts/transform_investment_to_linear_by_rpc.py

Input:
  - data/Vermont_Water_Investment_Infrastructure_Public_-6999738747210364761.geojson
  - data/Vermont_Town_GEOID_RPC_County.geojson

Output:
  - data/linear_by_rpc/Vermont_Linear_<RPC>.geojson
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from shapely.geometry import shape

INPUT = Path(
    "data/Vermont_Water_Investment_Infrastructure_Public_-6999738747210364761.geojson"
)
TOWNS = Path("data/Vermont_Town_GEOID_RPC_County.geojson")
OUTPUT_DIR = Path("data/linear_by_rpc")
STATEWIDE_OUTPUT = Path("data/Vermont_Linear_Features_from_investment.geojson")


def load_geojson(path: Path) -> dict:
    with path.open() as f:
        return json.load(f)


def build_town_lookup(towns_geojson: dict) -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    for feature in towns_geojson.get("features", []):
        props = feature.get("properties") or {}
        geoid = props.get("TOWNGEOID")
        if not geoid:
            continue
        lookup[str(geoid)] = {
            "Municipal_Name": props.get("Municipal_Name"),
            "County": props.get("County"),
            "RPC": props.get("RPC"),
        }
    return lookup


def build_town_spatial_index(towns_geojson: dict) -> list[tuple[tuple[float, float, float, float], object, dict[str, str]]]:
    towns_index = []
    for feature in towns_geojson.get("features", []):
        props = feature.get("properties") or {}
        geom = feature.get("geometry")
        if not geom:
            continue
        polygon = shape(geom)
        admin = {
            "Municipal_Name": props.get("Municipal_Name"),
            "County": props.get("County"),
            "RPC": props.get("RPC"),
        }
        towns_index.append((polygon.bounds, polygon, admin))
    return towns_index


def spatial_admin_lookup(feature_geometry: dict | None, towns_index: list[tuple[tuple[float, float, float, float], object, dict[str, str]]]) -> dict[str, str] | None:
    if not feature_geometry:
        return None

    geom = shape(feature_geometry)
    if geom.is_empty:
        return None

    # representative_point() is guaranteed to lie on the geometry for lines/multilines.
    pt = geom.representative_point()
    x, y = pt.x, pt.y

    for (minx, miny, maxx, maxy), polygon, admin in towns_index:
        if minx <= x <= maxx and miny <= y <= maxy and polygon.covers(pt):
            return admin
    return None


def normalize_feature(
    feature: dict,
    town_lookup: dict[str, dict[str, str]],
    towns_index: list[tuple[tuple[float, float, float, float], object, dict[str, str]]],
) -> tuple[dict, bool, bool]:
    props = dict(feature.get("properties") or {})

    # OBJECTID does not appear in the standardized statewide linear schema.
    props.pop("OBJECTID", None)

    geoidtxt = props.get("GEOIDTXT")
    admin = town_lookup.get(str(geoidtxt)) if geoidtxt not in (None, "") else None
    spatial_fallback_used = False

    if not admin:
        admin = spatial_admin_lookup(feature.get("geometry"), towns_index)
        spatial_fallback_used = admin is not None

    if admin:
        props["Municipal_Name"] = admin.get("Municipal_Name")
        props["County"] = admin.get("County")
        props["RPC"] = admin.get("RPC")
        matched = True
    else:
        props["Municipal_Name"] = None
        props["County"] = None
        props["RPC"] = None
        matched = False

    return {
        "type": feature.get("type", "Feature"),
        "properties": props,
        "geometry": feature.get("geometry"),
    }, matched, spatial_fallback_used


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    source = load_geojson(INPUT)
    towns = load_geojson(TOWNS)
    town_lookup = build_town_lookup(towns)
    towns_index = build_town_spatial_index(towns)

    by_rpc: defaultdict[str, list[dict]] = defaultdict(list)
    normalized_features: list[dict] = []
    total = 0
    matched_total = 0
    matched_by_geoid = 0
    matched_by_spatial = 0

    for feature in source.get("features", []):
        normalized, is_matched, used_spatial_fallback = normalize_feature(
            feature, town_lookup, towns_index
        )
        normalized_features.append(normalized)
        total += 1
        matched_total += int(is_matched)
        if is_matched:
            if used_spatial_fallback:
                matched_by_spatial += 1
            else:
                matched_by_geoid += 1

        rpc = normalized["properties"].get("RPC")
        by_rpc[rpc if rpc else "UNKNOWN"].append(normalized)

    template = {k: v for k, v in source.items() if k != "features"}

    statewide = {**template, "features": normalized_features}
    with STATEWIDE_OUTPUT.open("w") as f:
        json.dump(statewide, f)

    print(f"Source features: {total:,}")
    print(f"Matched by GEOIDTXT lookup: {matched_by_geoid:,}")
    print(f"Matched by spatial fallback: {matched_by_spatial:,}")
    print(f"Unmatched after enrichment: {total - matched_total:,}")
    print(f"Statewide transformed file: {STATEWIDE_OUTPUT}")

    for rpc, features in sorted(by_rpc.items()):
        out_path = OUTPUT_DIR / f"Vermont_Linear_{rpc}.geojson"
        out = {**template, "features": features}
        with out_path.open("w") as f:
            json.dump(out, f)
        print(f"  {rpc}: {len(features):,} -> {out_path}")

    print(f"\nWrote {len(by_rpc)} files to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
