#!/usr/bin/env python3

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from shapely.geometry import shape
from shapely.strtree import STRtree


def safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._ -]+", "", value).strip()
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned or "_EMPTY"


def load_geojson(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_geojson(path: Path, feature_collection_template: dict, features: list) -> None:
    out = {k: v for k, v in feature_collection_template.items() if k != "features"}
    out["features"] = features
    with path.open("w", encoding="utf-8") as file:
        json.dump(out, file, ensure_ascii=False)


def choose_best_town(line_geom, candidate_indices, border_geometries, border_town_names):
    if len(candidate_indices) == 1:
        return border_town_names[candidate_indices[0]]

    best_town = None
    best_score = -1.0
    for idx in candidate_indices:
        intersection = line_geom.intersection(border_geometries[idx])
        score = intersection.length
        if score > best_score:
            best_score = score
            best_town = border_town_names[idx]
    return best_town


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Assign TownName to unassigned linear features via intersection with town borders"
    )
    parser.add_argument("--unassigned", type=Path, required=True, help="Path to _UNASSIGNED.geojson")
    parser.add_argument("--borders", type=Path, required=True, help="Path to Vermont_Border.geojson")
    parser.add_argument("--out-dir", type=Path, required=True, help="Directory containing per-town GeoJSON files")
    parser.add_argument("--town-field", default="TownName", help="Town name field in border properties")
    args = parser.parse_args()

    unassigned_fc = load_geojson(args.unassigned)
    borders_fc = load_geojson(args.borders)

    unassigned_features = unassigned_fc.get("features", [])
    border_features = borders_fc.get("features", [])

    border_geometries = []
    border_town_names = []
    for feature in border_features:
        town_name = (feature.get("properties") or {}).get(args.town_field)
        if not town_name:
            continue
        geom = feature.get("geometry")
        if not geom:
            continue
        border_geometries.append(shape(geom))
        border_town_names.append(str(town_name).strip())

    tree = STRtree(border_geometries)

    matched = 0
    unmatched_features = []
    additions_by_town = defaultdict(list)

    for feature in unassigned_features:
        geom_data = feature.get("geometry")
        if not geom_data:
            unmatched_features.append(feature)
            continue

        line_geom = shape(geom_data)
        candidates = tree.query(line_geom)
        candidate_indices = []
        for idx in candidates:
            idx_int = int(idx)
            if line_geom.intersects(border_geometries[idx_int]):
                candidate_indices.append(idx_int)

        if not candidate_indices:
            unmatched_features.append(feature)
            continue

        town_name = choose_best_town(line_geom, candidate_indices, border_geometries, border_town_names)
        if not town_name:
            unmatched_features.append(feature)
            continue

        props = feature.setdefault("properties", {})
        props["TownName"] = town_name
        additions_by_town[town_name].append(feature)
        matched += 1

    args.out_dir.mkdir(parents=True, exist_ok=True)

    for town_name, town_additions in additions_by_town.items():
        town_path = args.out_dir / f"{safe_filename(town_name)}.geojson"
        if town_path.exists():
            town_fc = load_geojson(town_path)
        else:
            town_fc = {k: v for k, v in unassigned_fc.items() if k != "features"}
            town_fc["features"] = []
        updated_features = town_fc.get("features", []) + town_additions
        write_geojson(town_path, town_fc, updated_features)

    write_geojson(args.unassigned, unassigned_fc, unmatched_features)

    print(f"Processed {len(unassigned_features)} unassigned features")
    print(f"Matched {matched} features into {len(additions_by_town)} town files")
    print(f"Remaining unassigned: {len(unmatched_features)}")


if __name__ == "__main__":
    main()