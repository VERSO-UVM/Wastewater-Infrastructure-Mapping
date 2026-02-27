#!/usr/bin/env python3

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path


def safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._ -]+", "", value).strip()
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned or "_EMPTY"


def split_geojson(input_path: Path, output_dir: Path, property_name: str, missing_label: str) -> None:
    with input_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if data.get("type") != "FeatureCollection":
        raise ValueError("Input file must be a GeoJSON FeatureCollection")

    features = data.get("features", [])
    grouped = defaultdict(list)

    for feature in features:
        properties = feature.get("properties") or {}
        value = properties.get(property_name)
        key = str(value).strip() if value is not None else ""
        if not key:
            key = missing_label
        grouped[key].append(feature)

    output_dir.mkdir(parents=True, exist_ok=True)

    base = {k: v for k, v in data.items() if k != "features"}
    for group_name, group_features in grouped.items():
        out = dict(base)
        out["features"] = group_features
        filename = f"{safe_filename(group_name)}.geojson"
        out_path = output_dir / filename
        with out_path.open("w", encoding="utf-8") as file:
            json.dump(out, file, ensure_ascii=False)

    print(f"Wrote {len(grouped)} files to {output_dir}")
    if missing_label in grouped:
        print(f"{missing_label}: {len(grouped[missing_label])} features")


def main() -> None:
    parser = argparse.ArgumentParser(description="Split a GeoJSON FeatureCollection into files by a property")
    parser.add_argument("input", type=Path, help="Path to input GeoJSON FeatureCollection")
    parser.add_argument("output_dir", type=Path, help="Directory to write output files")
    parser.add_argument("--property", default="TownName", help="Feature property to split by (default: TownName)")
    parser.add_argument("--missing-label", default="_UNASSIGNED", help="Label for missing or blank values")
    args = parser.parse_args()

    split_geojson(args.input, args.output_dir, args.property, args.missing_label)


if __name__ == "__main__":
    main()