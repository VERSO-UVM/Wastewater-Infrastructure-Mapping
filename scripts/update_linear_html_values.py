#!/usr/bin/env python3
"""
update_linear_html_values.py
----------------------------
Recompute linear-feature-derived values from data/linear_by_rpc/*.geojson and
update hardcoded values in HTML pages.

This script updates:
  - index.html:
      * "Linear Features" dataset count in About section
      * wastewater+combined segment count in sewer corridor note
      * auto-generated statewide chart/summary/town-coverage blocks
        (delegated to scripts/update_static_charts.py)
  - data.html:
      * linear dataset count in file TOC
      * linear section headline feature count
      * linear SystemType table counts
      * linear Type code table counts
      * known data quality counts tied to linear features

Run from repo root:
    python scripts/update_linear_html_values.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
LINEAR_DIR = REPO / "data" / "linear_by_rpc"
INDEX_HTML = REPO / "index.html"
DATA_HTML = REPO / "data.html"
CHART_SCRIPT = REPO / "scripts" / "update_static_charts.py"


TYPE_LABELS = {
    2: "Storm Sewer / Drain Pipe",
    3: "Sanitary Sewer Pipe",
    4: "Culvert",
    5: "Open Channel / Ditch",
    19: "Water Main",
    7: "Swale",
    6: "Wet Swale",
    10: "Roadside Ditch",
    8: "Grass-Lined Channel",
    13: "Combined Sewer",
    16: "Subsurface Drain",
    17: "Other / Unknown",
    12: "French Drain",
    18: "Force Main",
    14: "Pervious Pavement Underdrain",
    15: "Filter Strip",
}


def fmt_int(n: int) -> str:
    return f"{n:,}"


def load_linear_features() -> list[dict]:
    paths = sorted(LINEAR_DIR.glob("Vermont_Linear_*.geojson"))
    if not paths:
        raise FileNotFoundError(f"No linear files found in {LINEAR_DIR}")

    features: list[dict] = []
    for path in paths:
        with path.open() as f:
            gj = json.load(f)
        features.extend(gj.get("features", []))
    return features


def compute_metrics(features: list[dict]) -> dict:
    system_counts = Counter((f.get("properties") or {}).get("SystemType") for f in features)
    type_counts = Counter((f.get("properties") or {}).get("Type") for f in features)

    null_status = sum(1 for f in features if (f.get("properties") or {}).get("Status") in (None, ""))
    null_type = sum(1 for f in features if (f.get("properties") or {}).get("Type") in (None, ""))
    null_geoid = sum(1 for f in features if (f.get("properties") or {}).get("GEOIDTXT") in (None, ""))
    ww_combined_segments = sum(
        1
        for f in features
        if (f.get("properties") or {}).get("SystemType") in ("Wastewater", "Combined")
    )

    return {
        "total": len(features),
        "system": system_counts,
        "type": type_counts,
        "null_status": null_status,
        "null_type": null_type,
        "null_geoid": null_geoid,
        "ww_combined_segments": ww_combined_segments,
    }


def replace_or_fail(text: str, pattern: str, repl: str, description: str) -> str:
    new_text, count = re.subn(pattern, repl, text, flags=re.MULTILINE)
    if count == 0:
        raise RuntimeError(f"Failed to update {description}: pattern not found")
    return new_text


def update_index_html(metrics: dict) -> None:
    text = INDEX_HTML.read_text(encoding="utf-8")

    text = replace_or_fail(
        text,
        r"(<li><strong>Linear Features</strong>[^\(]*\()\d[\d,]*( features\)</li>)",
        rf"\g<1>{fmt_int(metrics['total'])}\g<2>",
        "index linear feature count",
    )

    text = replace_or_fail(
        text,
        r"(calculation is based on )\d[\d,]*( mapped wastewater and combined sewer segments)",
        rf"\g<1>{fmt_int(metrics['ww_combined_segments'])}\g<2>",
        "index sewer corridor segment count",
    )

    INDEX_HTML.write_text(text, encoding="utf-8")


def update_data_html(metrics: dict) -> None:
    text = DATA_HTML.read_text(encoding="utf-8")

    total_s = fmt_int(metrics["total"])
    text = replace_or_fail(
        text,
        r"(<a href=\"#linear\">Vermont_Linear_Features\.geojson</a> — pipes, culverts, channels \()\d[\d,]*( features\))",
        rf"\g<1>{total_s}\g<2>",
        "data TOC linear feature count",
    )

    text = replace_or_fail(
        text,
        r"(<h2 id=\"linear\">Vermont_Linear_Features\.geojson</h2>\s*<div class=\"file-section\">\s*<p><strong>)\d[\d,]*( features &middot; LineString / MultiLineString</strong><br>)",
        rf"\g<1>{total_s}\g<2>",
        "data linear section feature count",
    )

    system_map = {
        "Stormwater": fmt_int(metrics["system"].get("Stormwater", 0)),
        "Wastewater": fmt_int(metrics["system"].get("Wastewater", 0)),
        "Water": fmt_int(metrics["system"].get("Water", 0)),
        "Combined": fmt_int(metrics["system"].get("Combined", 0)),
        "null": fmt_int(metrics["system"].get(None, 0)),
    }
    for label, count_str in system_map.items():
        text = replace_or_fail(
            text,
            rf"(<tr><td>{re.escape(label)}</td><td>)\d[\d,]*(</td></tr>)",
            rf"\g<1>{count_str}\g<2>",
            f"data SystemType count for {label}",
        )

    for code, label in TYPE_LABELS.items():
        count_str = fmt_int(metrics["type"].get(code, 0))
        text = replace_or_fail(
            text,
            rf"(<tr><td>{code}</td><td>{re.escape(label)}</td><td>[^<]*</td><td>)\d[\d,]*(</td></tr>)",
            rf"\g<1>{count_str}\g<2>",
            f"data type count for code {code}",
        )

    text = replace_or_fail(
        text,
        r"(Null <code>Status</code></td><td>Linear \()\d[\d,]*( features\), Point \(178\)</td>)",
        rf"\g<1>{fmt_int(metrics['null_status'])}\g<2>",
        "data null Status count",
    )

    text = replace_or_fail(
        text,
        r"(Null <code>Type</code></td><td>Linear \()\d[\d,]*(\), Water \(1\)</td>)",
        rf"\g<1>{fmt_int(metrics['null_type'])}\g<2>",
        "data null Type count",
    )

    text = replace_or_fail(
        text,
        r"(Null <code>GEOIDTXT</code></td><td>Linear \()([^\)]*)(\)</td>)",
        rf"\g<1>{fmt_int(metrics['null_geoid'])} features\g<3>",
        "data null GEOIDTXT count",
    )

    DATA_HTML.write_text(text, encoding="utf-8")


def run_static_chart_updater() -> None:
    proc = subprocess.run(
        [sys.executable, str(CHART_SCRIPT)],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "update_static_charts.py failed:\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}"
        )


def main() -> None:
    features = load_linear_features()
    metrics = compute_metrics(features)

    run_static_chart_updater()
    update_index_html(metrics)
    update_data_html(metrics)

    print("Updated HTML values from current linear features:")
    print(f"  Total linear features: {fmt_int(metrics['total'])}")
    print(f"  Wastewater+Combined segments: {fmt_int(metrics['ww_combined_segments'])}")
    print(f"  Null Status: {fmt_int(metrics['null_status'])}")
    print(f"  Null Type: {fmt_int(metrics['null_type'])}")
    print(f"  Null GEOIDTXT: {fmt_int(metrics['null_geoid'])}")


if __name__ == "__main__":
    main()
