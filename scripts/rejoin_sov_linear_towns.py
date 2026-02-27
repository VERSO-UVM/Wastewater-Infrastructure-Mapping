#!/usr/bin/env python3
"""Rejoin town-split SoV linear GeoJSON files into one FeatureCollection.

Default input:
  data/SoV_data/LinearFeatures_by_town

Default output:
  data/SoV_data/Vermont_LinearFeatures_rejoined.geojson

Usage:
  python scripts/rejoin_sov_linear_towns.py
  python scripts/rejoin_sov_linear_towns.py --exclude-unassigned
  python scripts/rejoin_sov_linear_towns.py --output analysis/Vermont_LinearFeatures_rejoined.geojson
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = REPO_ROOT / "data" / "SoV_data" / "LinearFeatures_by_town"
DEFAULT_OUTPUT_FILE = REPO_ROOT / "data" / "SoV_data" / "Vermont_LinearFeatures_rejoined.geojson"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge SoV LinearFeatures_by_town GeoJSON files into one GeoJSON file."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help=f"Directory of town-level GeoJSON files (default: {DEFAULT_INPUT_DIR})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_FILE,
        help=f"Output GeoJSON path (default: {DEFAULT_OUTPUT_FILE})",
    )
    parser.add_argument(
        "--exclude-unassigned",
        action="store_true",
        help="Exclude _UNASSIGNED.geojson from the merge.",
    )
    return parser.parse_args()


def load_geojson(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def derive_town_name(file_stem: str) -> str | None:
    if file_stem.upper() == "_UNASSIGNED":
        return None
    return file_stem.replace("_", " ")


def merge_linear_files(
    input_dir: Path,
    output_path: Path,
    exclude_unassigned: bool = False,
) -> None:
    if not input_dir.exists() or not input_dir.is_dir():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    files = sorted(input_dir.glob("*.geojson"), key=lambda p: p.name.lower())
    if exclude_unassigned:
        files = [path for path in files if path.stem.upper() != "_UNASSIGNED"]

    if not files:
        raise FileNotFoundError(f"No .geojson files found in: {input_dir}")

    merged_features: list[dict[str, Any]] = []
    first_crs: dict[str, Any] | None = None
    per_file_counts: list[tuple[str, int]] = []

    for file_path in files:
        geojson = load_geojson(file_path)
        if geojson.get("type") != "FeatureCollection":
            raise ValueError(f"Expected FeatureCollection in {file_path}")

        features = geojson.get("features")
        if not isinstance(features, list):
            raise ValueError(f"Invalid or missing features list in {file_path}")

        if first_crs is None and isinstance(geojson.get("crs"), dict):
            first_crs = geojson["crs"]

        town_name = derive_town_name(file_path.stem)

        count = 0
        for feature in features:
            if not isinstance(feature, dict):
                continue

            properties = feature.get("properties")
            if not isinstance(properties, dict):
                properties = {}
                feature["properties"] = properties

            properties.setdefault("MergeSourceFile", file_path.name)
            if town_name and not properties.get("TownName"):
                properties["TownName"] = town_name

            merged_features.append(feature)
            count += 1

        per_file_counts.append((file_path.name, count))

    output = {
        "type": "FeatureCollection",
        "features": merged_features,
    }
    if first_crs is not None:
        output["crs"] = first_crs

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False)

    print(f"Merged files: {len(files)}")
    print(f"Total features: {len(merged_features)}")
    print(f"Output: {output_path}")
    print("Top 10 files by feature count:")
    for name, count in sorted(per_file_counts, key=lambda item: item[1], reverse=True)[:10]:
        print(f"  {name}: {count}")


def main() -> None:
    args = parse_args()
    merge_linear_files(
        input_dir=args.input_dir,
        output_path=args.output,
        exclude_unassigned=args.exclude_unassigned,
    )


if __name__ == "__main__":
    main()
