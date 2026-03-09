# Vermont Wastewater Infrastructure Map

[![DOI](https://zenodo.org/badge/764833070.svg)](https://zenodo.org/doi/10.5281/zenodo.11508708)

An open, statewide dataset and interactive mapping site for wastewater and stormwater infrastructure across all 256 Vermont municipalities — built by UVM students in partnership with the Vermont Agency of Natural Resources.

* **Live site:** [Vermont Wastewater Infrastructure Map](https://verso-uvm.github.io/Wastewater-Infrastructure-Mapping/)
* **ANR ArcGIS webmap:** [Vermont ANR Water Infrastructure Viewer](https://vtanr.maps.arcgis.com/apps/mapviewer/index.html?webmap=de7e8f0627b5482a851b379e29200a74)
* **Vermont Geodata Portal:** [Vermont Water Infrastructure on Geodata Portal](https://geodata.vermont.gov/maps/01210da4457d42a1bbcc43f7e54cbad6/about)

> **Data status:** The primary dataset was completed in June 2025. The data collection phase is archived — for updates to the underlying infrastructure data, contact the Vermont Agency of Natural Resources. The mapping site continues to receive improvements.

---

## What's in This Repo

The Wastewater Infrastructure Map is a collaborative effort led by the Vermont Research Open Source Program Office (VERSO) at the University of Vermont, supported by the Windham Regional Commission, Vermont state agencies, and funded by the Leahy Institute. The goal was to map and analyze wastewater infrastructure across every town in Vermont. Developed with 15 undergraduate interns through UVM's Open Research Community Accelerator (ORCA) student internship program from Fall 2024 to June 2025, this project delivers comprehensive geospatial datasets aimed at informing regional planning, economic development, and housing growth.

Learn more about the project on the [project about page](https://verso-uvm.github.io/Wastewater-Infrastructure-Mapping/about.html).

---

## Objectives

* Thoroughly map sewer systems (pipes, manholes, outflows), treatment facilities, service areas, and onsite soil suitability.
* Fill in missing infrastructure data gaps left by existing Vermont GIS resources.
* Produce user-friendly, public-domain datasets that support infrastructure planning and align with broader Vermont Climate, Energy, and Transportation plans.

---

## Project Timeline & Scope

Initiated: Fall 2024 under Chris Campany (Windham Regional Commission), funded by UVM's Leahy Institute.

### Milestones

* Exploratory research & cataloging — Nov 2024
* Outreach to local system managers — Feb 2025
* Data architecture development — Feb 2025
* Statewide dataset completion — June 2025
* Interactive mapping site launched — June 2025
* Site enhancements (RPC Explorer, zoning analysis, flood risk analysis) — 2025–2026

---

## Map Layers

The interactive site includes the following data layers:

| Layer | Description |
| --- | --- |
| **Wastewater Linear Features** | Pipes, culverts, and open channels from wastewater, stormwater, water supply, and combined systems (222,766+ features) |
| **Point Features** | Manholes, catch basins, outfalls, and pump stations |
| **Sewer Service Areas** | Geographic boundaries of municipal sewer service coverage (186 areas) |
| **Treatment Facilities** | 293 municipal, industrial, and pretreatment facilities with NPDES permit records and hydraulic capacity data |
| **Zoning Districts** | Housing allowance zoning (F1F–F4F) within the sewer service corridor, sourced from the Vermont Zoning Atlas |
| **FEMA Flood Zones** | FEMA National Flood Hazard Layer (NFHL) flood zone overlay via FEMA ArcGIS REST API |
| **Onsite Soil Ratings** | Onsite sewage disposal soil suitability classification (USDA NRCS) |

Learn more about the data schema on the [data page](https://verso-uvm.github.io/Wastewater-Infrastructure-Mapping/data.html).

---

## Statewide Analysis

The site includes several statewide analyses computed from the dataset:

* **Sewer Service Corridor:** A 300-foot buffer on all wastewater and combined sewer lines yields an estimated corridor of **111.34 square miles** (~1.2% of Vermont's land area).
* **Treatment Facilities by RPC:** 160 of 293 facilities categorized by permit type (Municipal, Industrial, Pretreatment Discharge) across all 11 Regional Planning Commissions.
* **Flood Risk:** 21 of 157 characterized facilities (13.4%) are located within FEMA Special Flood Hazard Areas. Highest exposure in MARC (43%), RRPC (24%), and TRORC (24%).
* **Housing Zoning in the Corridor:** F1F–F4F housing allowances mapped within the sewer corridor, showing permitted, public hearing required, and prohibited zoning by area.

---

## Regional Planning Commission Explorer

The site includes an interactive RPC Explorer allowing users to select any of Vermont's 11 RPCs and view:

* Town boundaries, sewer service areas, treatment facilities, and linear features for that region
* Zoning district overlays
* FEMA flood zone layer
* Summary statistics: total infrastructure length by system type, facility counts, and zoning breakdowns

---

## Repository Structure

```text
/
├── index.html              # Main interactive map and analysis site
├── about.html              # Project history and team
├── data.html               # Data schema and download links
├── contribute.html         # How to contribute
├── styles.css              # Site stylesheet
├── data/
│   ├── Vermont_Treatment_Facilities.geojson
│   ├── Vermont_Service_Areas.geojson
│   ├── Vermont_Point_Features.geojson
│   ├── Vermont_Water_Features.geojson
│   ├── Vermont_Wastewater_Districts.geojson
│   ├── Vermont_Town_GEOID_RPC_County.geojson
│   ├── linear_by_rpc/      # Linear features split by RPC for performance
│   └── Zoning Data/        # Per-RPC zoning GeoJSON files
├── scripts/                # Python analysis scripts
└── analysis/               # Data standards and methodology notes
```

---

## Tech Stack

* **Frontend:** Vanilla HTML/CSS/JavaScript, no build step required
* **Mapping:** [Leaflet.js](https://leafletjs.com/) v1.9.4 + [esri-leaflet](https://esri.github.io/esri-leaflet/) v3.0.12
* **Data:** GeoJSON files served statically via GitHub Pages
* **External services:** FEMA NFHL ArcGIS REST API (flood zones), Vermont Zoning Atlas GeoJSON

---

## Team

### Summer 2024

* Team Lead: Emma Eash
* Adrien Monks
* Aleah Young
* Fernanda De Oliveira Girelli
* James Catanzaro
* Jane Bregenzer

### Fall 2024

* Team Lead: Emma Eash
* Aleah Young
* Gabe Christiansen
* Louise Vaillancourt
* Matthew Premysler
* Sian Hernit
* Sophia Miller-Grande

### Spring 2025

* Team Lead: Emma Eash
* Aleah Young
* Louise Vaillancourt
* Matthew Premysler
* Sian Hernit
* Sophie Miller-Grande

### Summer 2025

* Gabe Christiansen (Lead)
* Andrew Chen
* Duncan Niess
* Harrison Taylor
* Julianna Elton
* Lily Fitzpatrick
* Louise Vaillancourt

---

## Data Sources

Most data used is from the Vermont Agency of Natural Resources (see [Existing GIS Data](https://github.com/VERSO-UVM/Wastewater-Infrastructure-Mapping/blob/main/ExistingGISData.md)). Some new data has been digitized from town plans or documents provided by municipalities. The Onsite Sewage Disposal Soil Ratings map was prepared by the U.S. Department of Agriculture, Natural Resources Conservation Service. Zoning data is sourced from the [Vermont Zoning Atlas](https://verso-uvm.github.io/Vermont-Zoning-Atlas/). Flood zone data is provided by [FEMA NFHL](https://www.fema.gov/flood-maps/national-flood-hazard-layer).

---

## Funding

This project was made possible with a grant from the [Leahy Institute for Rural Partnerships](https://www.uvm.edu/ruralpartnerships).

---

## Partnerships

This project is in collaboration with:

* [Windham Regional Commission](http://www.windhamregional.org/)
* [Vermont Center for Geographic Information](https://vcgi.vermont.gov/)
* [Vermont Department of Environmental Conservation](https://dec.vermont.gov/)
* [Vermont Agency of Commerce and Community Development](https://accd.vermont.gov/)
