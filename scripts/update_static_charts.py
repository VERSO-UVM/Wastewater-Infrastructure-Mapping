#!/usr/bin/env python3
"""
update_static_charts.py
-----------------------
Recomputes the two static statewide chart blocks in index.html from the
current GeoJSON data and writes the updated HTML in-place.

Run from the repo root:
    python scripts/update_static_charts.py

Requirements: Python 3.8+, no third-party packages needed.

What gets updated
-----------------
1. Town Coverage donut (SVG + legend) inside #town-coverage-chart-wrap
2. Linear Feature Length bar chart inside #statewide-chart-wrap
3. Statewide summary paragraphs inside .wwtf-summary-text

The script replaces only the blocks between sentinel comments:
  <!-- [AUTO] town-coverage-chart START -->
  <!-- [AUTO] town-coverage-chart END -->
  <!-- [AUTO] statewide-chart START -->
  <!-- [AUTO] statewide-chart END -->
  <!-- [AUTO] statewide-summary-text START -->
  <!-- [AUTO] statewide-summary-text END -->

If those sentinels are absent the script prints the generated HTML and
exits without modifying the file.
"""

import json
import math
import re
import sys
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────
REPO = Path(__file__).resolve().parent.parent
LINEAR_DIR = REPO / "data" / "linear_by_rpc"
TOWNS_FILE = REPO / "data" / "Vermont_Town_GEOID_RPC_County.geojson"
INDEX_HTML = REPO / "index.html"

RPC_LIST = [
    "ACRPC", "BCRC", "CCRPC", "CVRPC", "LCPC",
    "MARC", "NRPC", "NVDA", "RRPC", "TRORC", "WRC",
]

SYSTEM_COLORS = {
    "Stormwater": "#2980b9",
    "Wastewater": "#c0392b",
    "Water": "#27ae60",
    "Combined": "#8e44ad",
}

SW_ORDER = ["Stormwater", "Wastewater", "Water", "Combined"]


# ── Helpers ────────────────────────────────────────────────────────────


def haversine_m(lon1, lat1, lon2, lat2):
    """Great-circle distance in metres between two WGS-84 points."""
    R = 6_371_000
    to_r = math.pi / 180
    phi1, phi2 = lat1 * to_r, lat2 * to_r
    dphi = (lat2 - lat1) * to_r
    dlam = (lon2 - lon1) * to_r
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    )
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def geom_length_m(geom):
    """Total length of a LineString / MultiLineString geometry in metres."""
    if not geom:
        return 0.0
    if geom["type"] == "LineString":
        rings = [geom["coordinates"]]
    elif geom["type"] == "MultiLineString":
        rings = geom["coordinates"]
    else:
        rings = []
    total = 0.0
    for pts in rings:
        for i in range(1, len(pts)):
            total += haversine_m(
                pts[i - 1][0], pts[i - 1][1], pts[i][0], pts[i][1]
            )
    return total


def include_linear(feat):
    """Mirror JS includeLinear: exclude stormwater features that are not
    Type 2. Type may be stored as int or string in the GeoJSON source."""
    p = feat["properties"]
    raw_type = p.get("Type")
    try:
        feat_type = int(raw_type)
    except (TypeError, ValueError):
        feat_type = raw_type
    return not (p.get("SystemType") == "Stormwater" and feat_type != 2)


def fmt_mi(metres):
    """Convert metres to miles, formatted with comma thousands separator."""
    return f"{metres / 1000 * 0.621371:,.1f} mi"


# ── Step 1: load + aggregate ───────────────────────────────────────────

print("Loading town boundaries...")
with open(TOWNS_FILE) as f:
    towns_gj = json.load(f)
total_towns = len(towns_gj["features"])
print(f"  {total_towns} towns")

by_type = {t: 0.0 for t in SW_ORDER}
feat_count = 0
towns_with_data: set = set()

print(f"Loading {len(RPC_LIST)} RPC linear files...")
for rpc in RPC_LIST:
    path = LINEAR_DIR / f"Vermont_Linear_{rpc}.geojson"
    if not path.exists():
        print(f"  WARNING: {path.name} not found — skipping", file=sys.stderr)
        continue
    with open(path) as f:
        gj = json.load(f)
    for feat in gj["features"]:
        if not include_linear(feat):
            continue
        p = feat["properties"]
        st = p.get("SystemType", "")
        if st not in by_type:
            continue
        by_type[st] += geom_length_m(feat.get("geometry"))
        feat_count += 1
        if st in ("Wastewater", "Combined"):
            geoid = p.get("GEOIDTXT") or p.get("GEOID")
            if geoid:
                towns_with_data.add(str(geoid))
    print(f"  {rpc}: {len(gj['features']):,} features")

towns_has = len(towns_with_data)
towns_none = total_towns - towns_has
total_len = sum(by_type.values())

print("\nResults:")
print(
    f"  Towns with data : {towns_has} / {total_towns}"
    f" ({towns_has / total_towns * 100:.1f}%)"
)
for st, m in by_type.items():
    print(f"  {st:<12}: {fmt_mi(m)}")
print(f"  Total           : {fmt_mi(total_len)}  ({feat_count:,} segments)")


# ── Step 2: build SVG donut ────────────────────────────────────────────


def svg_donut(has, total, cx=110, cy=110, r=90, hole=52):
    """Return joined SVG elements for a two-slice donut chart."""
    slices = [
        {"count": has, "color": "#1a7a9a"},
        {"count": total - has, "color": "#bdc3c7"},
    ]
    pct_text = f"{has / total * 100:.0f}%"
    paths = []
    deg = 0.0
    for s in slices:
        sweep = min(s["count"] / total * 360, 359.9999)
        s_rad = math.radians(deg - 90)
        e_rad = math.radians(deg + sweep - 90)
        large = 1 if sweep > 180 else 0
        ox1 = cx + r * math.cos(s_rad)
        oy1 = cy + r * math.sin(s_rad)
        ox2 = cx + r * math.cos(e_rad)
        oy2 = cy + r * math.sin(e_rad)
        ix1 = cx + hole * math.cos(e_rad)
        iy1 = cy + hole * math.sin(e_rad)
        ix2 = cx + hole * math.cos(s_rad)
        iy2 = cy + hole * math.sin(s_rad)
        d = (
            f"M {ox1:.1f} {oy1:.1f} "
            f"A {r} {r} 0 {large} 1 {ox2:.1f} {oy2:.1f} "
            f"L {ix1:.1f} {iy1:.1f} "
            f"A {hole} {hole} 0 {large} 0 {ix2:.1f} {iy2:.1f} Z"
        )
        color = s["color"]
        paths.append(
            f'<path d="{d}" fill="{color}" stroke="#fff" stroke-width="2"/>'
        )
        deg += sweep

    paths.append(
        f'<text x="{cx}" y="{cy - 10}" text-anchor="middle"'
        f' font-size="22" font-weight="700" fill="#1a3a4a">{pct_text}</text>'
    )
    paths.append(
        f'<text x="{cx}" y="{cy + 10}" text-anchor="middle"'
        f' font-size="11" fill="#666">of towns</text>'
    )
    paths.append(
        f'<text x="{cx}" y="{cy + 26}" text-anchor="middle"'
        f' font-size="11" fill="#666">have data</text>'
    )
    return "\n            ".join(paths)


# ── Step 3: render HTML blocks ─────────────────────────────────────────

# Town coverage chart
svg_paths = svg_donut(towns_has, total_towns)
has_pct = f"{towns_has / total_towns * 100:.1f}"
none_pct = f"{towns_none / total_towns * 100:.1f}"
town_chart_html = (
    '        <div class="pie-chart-wrap">\n'
    '          <svg viewBox="0 0 220 220" width="220" height="220">\n'
    f"            {svg_paths}\n"
    "          </svg>\n"
    '          <div class="pie-legend">\n'
    '            <div class="pie-legend-item">\n'
    '              <span class="pie-legend-swatch"'
    ' style="background:#1a7a9a;"></span>\n'
    "              <span>Has mapped wastewater or combined sewer"
    f" &mdash; <strong>{towns_has}</strong> towns ({has_pct}%)</span>\n"
    "            </div>\n"
    '            <div class="pie-legend-item">\n'
    '              <span class="pie-legend-swatch"'
    ' style="background:#bdc3c7;"></span>\n'
    "              <span>No mapped wastewater or combined sewer"
    f" &mdash; <strong>{towns_none}</strong> towns ({none_pct}%)</span>\n"
    "            </div>\n"
    "          </div>\n"
    "        </div>"
)

# Linear length bar chart
sw_max = max((by_type[t] for t in SW_ORDER), default=1)
bar_rows = []
labels = {"Water": "Water Supply"}
for t in SW_ORDER:
    length = by_type[t]
    pct = length / sw_max * 100
    label = labels.get(t, t)
    color = SYSTEM_COLORS[t]
    fill = (
        f'<div class="chart-bar-fill"'
        f' style="width:{pct:.1f}%;background:{color};"></div>'
    )
    bar_rows.append(
        f'        <div class="chart-bar-row">\n'
        f'          <span class="chart-bar-label">{label}</span>\n'
        f'          <div class="chart-bar-track">{fill}</div>\n'
        f'          <span class="chart-bar-value">{fmt_mi(length)}</span>\n'
        f"        </div>"
    )
linear_chart_html = "\n".join(bar_rows)

# Summary paragraphs
longest_type = max(SW_ORDER, key=lambda t: by_type[t])
longest_pct = by_type[longest_type] / total_len * 100
ww = fmt_mi(by_type["Wastewater"])
sw = fmt_mi(by_type["Stormwater"])
wa = fmt_mi(by_type["Water"])
co = fmt_mi(by_type["Combined"])
tot = fmt_mi(total_len)
long_len = fmt_mi(by_type[longest_type])

p1 = (
    f"Vermont's mapped linear infrastructure dataset spans <strong>{tot}</strong>"
    f" across <strong>{feat_count:,} individual segments</strong> collected from"
    f" all 11 Regional Planning Commissions. {longest_type} features account for"
    f" the largest share at <strong>{long_len}</strong>"
    f" ({longest_pct:.0f}%). Stormwater figures here reflect enclosed storm sewer"
    " pipe (Type 2) only, excluding open channels, culverts, swales, and ditches."
)
p2 = (
    f"Wastewater (sanitary sewer) lines total <strong>{ww}</strong>,"
    f" water supply lines <strong>{wa}</strong>, and combined sewer lines"
    " &mdash; where stormwater and wastewater share a single pipe &mdash;"
    f" account for <strong>{co}</strong>. The small combined sewer total"
    " reflects Vermont's largely separate sewer systems, with legacy combined"
    " infrastructure concentrated in a few older urban centers."
)
summary_html = (
    '      <div class="wwtf-summary-text">\n'
    f"        <p>{p1}</p>\n"
    f"        <p>{p2}</p>\n"
    "      </div>"
)


# ── Step 4: patch index.html ───────────────────────────────────────────

START = "<!-- [AUTO] {key} START -->"
END = "<!-- [AUTO] {key} END -->"

BLOCKS = {
    "town-coverage-chart": town_chart_html,
    "statewide-chart": linear_chart_html,
    "statewide-summary-text": summary_html,
}

html = INDEX_HTML.read_text(encoding="utf-8")
updated = html
missing = []

for key, content in BLOCKS.items():
    pattern = (
        r"<!-- \[AUTO\] " + re.escape(key) + r" START -->.*?"
        r"<!-- \[AUTO\] " + re.escape(key) + r" END -->"
    )
    start_tag = f"<!-- [AUTO] {key} START -->"
    end_tag = f"<!-- [AUTO] {key} END -->"
    replacement = f"{start_tag}\n{content}\n      {end_tag}"
    new_html, count = re.subn(pattern, replacement, updated, flags=re.DOTALL)
    if count:
        updated = new_html
        print(f"\nPatched: {key}")
    else:
        missing.append(key)

if missing:
    keys = ", ".join(missing)
    print(f"\nWARNING: sentinel comment(s) not found — {keys}")
    print("Add the sentinel comments to index.html, then re-run.")
    print("Generated HTML:\n")
    print("=== town-coverage-chart ===")
    print(town_chart_html)
    print("\n=== statewide-chart ===")
    print(linear_chart_html)
    print("\n=== statewide-summary-text ===")
    print(summary_html)
else:
    INDEX_HTML.write_text(updated, encoding="utf-8")
    print("\nindex.html updated successfully.")

print("\nDone.")
