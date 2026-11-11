from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import folium
import polyline
from branca.element import MacroElement, Template

from activity_archive.activity import activity_start_local, activity_type
from activity_archive.paths import ACTIVITIES_DIR, HEATMAPS_DIR

PORTLAND_CENTER = [45.5231, -122.6765]
DEFAULT_ZOOM = 10
OPENFREEMAP_DARK_STYLE = "https://tiles.openfreemap.org/styles/dark"


class OpenFreeMapDark(MacroElement):
    """Add OpenFreeMap's dark vector basemap to a Folium/Leaflet map."""

    _template = Template(
        """
        {% macro header(this, kwargs) %}
        <link rel="stylesheet" href="https://unpkg.com/maplibre-gl@6.3.0/dist/maplibre-gl.css">
        <script type="importmap">
        {
          "imports": {
            "leaflet": "https://unpkg.com/leaflet@1.9.4/dist/leaflet-src.esm.js",
            "maplibre-gl": "https://unpkg.com/maplibre-gl@6.3.0/dist/maplibre-gl.mjs"
          }
        }
        </script>
        {% endmacro %}

        {% macro html(this, kwargs) %}
        <script type="module">
          import { maplibreGL } from "https://unpkg.com/@maplibre/maplibre-gl-leaflet@0.1.4/dist/leaflet-maplibre-gl.mjs";

          const darkBasemap = maplibreGL({
            style: {{ this.style_url | tojson }}
          }).addTo({{ this._parent.get_name() }});
          const lightBasemap = window.L.tileLayer(
            "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            {
              maxZoom: 19,
              attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            }
          );
          window.routeExplorerBasemaps = { dark: darkBasemap, light: lightBasemap };
          window.dispatchEvent(new CustomEvent("routeExplorerBasemapsReady"));

          {{ this._parent.get_name() }}.attributionControl.addAttribution(
            '<a href="https://openfreemap.org/">OpenFreeMap</a> | ' +
            '<a href="https://www.openmaptiles.org/">&copy; OpenMapTiles</a> ' +
            'Data from <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          );
        </script>
        {% endmacro %}
        """
    )

    def __init__(self, style_url: str = OPENFREEMAP_DARK_STYLE) -> None:
        super().__init__()
        self._name = "OpenFreeMapDark"
        self.style_url = style_url


class RouteExplorer(MacroElement):
    """Render filterable routes with unified and activity-specific colors."""

    _template = Template(
        """
        {% macro header(this, kwargs) %}
        <style>
          .route-explorer-control {
            background: rgba(16, 23, 18, 0.94);
            border: 1px solid rgba(190, 208, 195, 0.18);
            border-radius: 12px;
            box-shadow: 0 5px 18px rgba(0, 0, 0, 0.34);
            color: #eef4ef;
            font: 600 13px/1.2 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            padding: 10px;
            width: min(390px, calc(100vw - 70px));
          }
          .route-explorer-row {
            display: grid;
            column-gap: 8px;
            row-gap: 8px;
          }
          .route-explorer-row.primary { grid-template-columns: 1.35fr 1fr; }
          .route-explorer-row.secondary { grid-template-columns: repeat(3, minmax(0, 1fr)); }
          .route-explorer-row + .route-explorer-row { margin-top: 8px; }
          .route-explorer-field {
            display: grid;
            gap: 4px;
            grid-template-columns: minmax(0, 1fr);
            min-width: 0;
          }
          .route-explorer-field > label {
            color: #9eaaa1;
            font-size: 10px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
          }
          .route-explorer-control select {
            appearance: none;
            background: #263029;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath fill='%23b7c2ba' d='M1.4 1.2 6 5.8l4.6-4.6L12 2.6l-6 6-6-6z'/%3E%3C/svg%3E");
            background-position: right 9px center;
            background-repeat: no-repeat;
            border: 1px solid transparent;
            border-radius: 999px;
            color: #d8e1da;
            cursor: pointer;
            font: inherit;
            padding: 6px 26px 6px 9px;
            width: 100%;
          }
          .route-explorer-control select {
            border-radius: 8px;
            min-width: 0;
          }
          .route-explorer-legend {
            align-items: center;
            color: #b7c2ba;
            display: none;
            font-size: 11px;
            gap: 9px;
            margin-top: 8px;
          }
          .route-explorer-legend.visible { display: flex; flex-wrap: wrap; }
          .route-explorer-legend span { align-items: center; display: inline-flex; gap: 4px; }
          .route-explorer-legend i { border-radius: 50%; height: 8px; width: 8px; }
          @media (max-width: 520px) {
            .route-explorer-control { padding: 8px; }
            .route-explorer-control select { font-size: 11px; padding: 5px 22px 5px 7px; }
          }
        </style>
        {% endmacro %}

        {% macro script(this, kwargs) %}
        const routeExplorerData = {{ this.routes | tojson }};
        const routeExplorerColors = {
          run: "#ff006e",
          hike: "#65e572",
          walk: "#2da8ff",
          ride: "#ffd43b"
        };
        const routeExplorerState = {
          activity: "all",
          colorMode: "unified",
          heat: true,
          mapTheme: "dark",
          year: "all"
        };
        const routeExplorerLayers = [];

        routeExplorerData.forEach((route) => {
          const halo = L.polyline(route.coords, {
            color: "#f4f7f0",
            weight: 8,
            opacity: 0.070,
            interactive: false
          }).addTo({{ this._parent.get_name() }});
          const core = L.polyline(route.coords, {
            color: "#ff006e",
            weight: 1.5,
            opacity: 0.66
          }).addTo({{ this._parent.get_name() }});
          core.bindTooltip(`${route.name} · ${route.type_label} · ${route.date}`, { sticky: true });
          routeExplorerLayers.push({ ...route, halo, core });
        });

        const routeExplorerControl = L.control({ position: "topright" });
        routeExplorerControl.onAdd = () => {
          const container = L.DomUtil.create("div", "route-explorer-control");
          const years = [...new Set(routeExplorerData.map((route) => route.year))]
            .filter(Boolean)
            .sort((a, b) => b - a);
          container.innerHTML = `
            <div class="route-explorer-row primary">
              <div class="route-explorer-field">
                <label for="route-activity-filter">Filter</label>
                <select id="route-activity-filter" data-filter-select>
                  <option value="all">All Activities</option>
                  <option value="run">Runs</option>
                  <option value="walk">Walks</option>
                  <option value="ride">Rides</option>
                  <option value="hike">Hikes</option>
                </select>
              </div>
              <div class="route-explorer-field">
                <label for="route-year-filter">Year</label>
                <select id="route-year-filter" data-year-select>
                  <option value="all">All Years</option>
                  ${years.map((year) => `<option value="${year}">${year}</option>`).join("")}
                </select>
              </div>
            </div>
            <div class="route-explorer-row secondary">
              <div class="route-explorer-field">
                <label for="route-style-filter">Style</label>
                <select id="route-style-filter" data-color-select>
                  <option value="unified">All</option>
                  <option value="activity">Activity</option>
                </select>
              </div>
              <div class="route-explorer-field">
                <label for="route-heat-filter">Heat</label>
                <select id="route-heat-filter" data-heat-select>
                  <option value="on">On</option>
                  <option value="off">Off</option>
                </select>
              </div>
              <div class="route-explorer-field">
                <label for="route-map-filter">Map</label>
                <select id="route-map-filter" data-map-select>
                  <option value="dark">Dark</option>
                  <option value="light">Light</option>
                </select>
              </div>
            </div>
            <div class="route-explorer-legend">
              <span><i style="background:#ff006e"></i>Runs</span>
              <span><i style="background:#65e572"></i>Hikes</span>
              <span><i style="background:#2da8ff"></i>Walks</span>
              <span><i style="background:#ffd43b"></i>Rides</span>
            </div>`;
          L.DomEvent.disableClickPropagation(container);
          L.DomEvent.disableScrollPropagation(container);
          return container;
        };
        routeExplorerControl.addTo({{ this._parent.get_name() }});

        const routeExplorerContainer = routeExplorerControl.getContainer();
        const updateRouteExplorerBasemap = () => {
          const basemaps = window.routeExplorerBasemaps;
          if (!basemaps) return;
          const map = {{ this._parent.get_name() }};
          const showDark = routeExplorerState.mapTheme === "dark";
          if (showDark) {
            if (map.hasLayer(basemaps.light)) map.removeLayer(basemaps.light);
            if (!map.hasLayer(basemaps.dark)) basemaps.dark.addTo(map);
          } else {
            if (map.hasLayer(basemaps.dark)) map.removeLayer(basemaps.dark);
            if (!map.hasLayer(basemaps.light)) basemaps.light.addTo(map);
          }
        };
        const updateRouteExplorer = () => {
          routeExplorerLayers.forEach((route) => {
            const visible =
              (routeExplorerState.activity === "all" || route.type === routeExplorerState.activity) &&
              (routeExplorerState.year === "all" || String(route.year) === routeExplorerState.year);
            const byActivity = routeExplorerState.colorMode === "activity";
            const darkMap = routeExplorerState.mapTheme === "dark";
            route.halo.setStyle({
              color: darkMap ? "#f4f7f0" : "#33006e",
              opacity: visible && routeExplorerState.heat ? (darkMap ? 0.070 : 0.10) : 0
            });
            route.core.setStyle({
              color: byActivity ? routeExplorerColors[route.type] : "#ff006e",
              opacity: visible ? (byActivity ? 0.84 : 0.66) : 0,
              weight: byActivity ? 1.8 : 1.5
            });
            if (route.core.getElement()) {
              route.core.getElement().style.pointerEvents = visible ? "auto" : "none";
            }
          });
          routeExplorerContainer.querySelector(".route-explorer-legend")
            .classList.toggle("visible", routeExplorerState.colorMode === "activity");
          updateRouteExplorerBasemap();
        };

        routeExplorerContainer.querySelector("[data-filter-select]").addEventListener("change", (event) => {
          routeExplorerState.activity = event.target.value;
          updateRouteExplorer();
        });
        routeExplorerContainer.querySelector("[data-color-select]").addEventListener("change", (event) => {
          routeExplorerState.colorMode = event.target.value;
          updateRouteExplorer();
        });
        routeExplorerContainer.querySelector("[data-heat-select]").addEventListener("change", (event) => {
          routeExplorerState.heat = event.target.value === "on";
          updateRouteExplorer();
        });
        routeExplorerContainer.querySelector("[data-map-select]").addEventListener("change", (event) => {
          routeExplorerState.mapTheme = event.target.value;
          updateRouteExplorer();
        });
        routeExplorerContainer.querySelector("[data-year-select]").addEventListener("change", (event) => {
          routeExplorerState.year = event.target.value;
          updateRouteExplorer();
        });
        window.addEventListener("routeExplorerBasemapsReady", updateRouteExplorerBasemap);
        {% endmacro %}
        """
    )

    def __init__(self, routes: list[dict[str, Any]]) -> None:
        super().__init__()
        self._name = "RouteExplorer"
        self.routes = routes


ENABLED_HEATMAPS = [
    "map",
]


HEATMAP_STYLES = [
    {
        "name": "map",
        "output": "map.html",
        "basemap": "dark",
        "interactive": True,
    },
]


def iter_activity_files() -> list[Path]:
    return sorted(ACTIVITIES_DIR.glob("*.json"))


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def extract_polyline(data: dict[str, Any]) -> str | None:
    map_data = data.get("map")
    if not isinstance(map_data, dict):
        return None

    return map_data.get("polyline") or map_data.get("summary_polyline")


def route_category(data: dict[str, Any]) -> str | None:
    raw_type = activity_type(data).lower()
    if "run" in raw_type:
        return "run"
    if "hike" in raw_type:
        return "hike"
    if "walk" in raw_type:
        return "walk"
    if "ride" in raw_type or "cycle" in raw_type:
        return "ride"
    return None


def load_route_from_file(path: Path) -> dict[str, Any] | None:
    data = load_json(path)
    if not data:
        print(f"Skipping {path.name}: unreadable or non-dict JSON")
        return None

    encoded = extract_polyline(data)
    if not encoded:
        print(f"Skipping {path.name}: no polyline found")
        return None

    try:
        coords = polyline.decode(encoded)
    except Exception as e:
        print(f"Skipping {path.name}: failed to decode polyline ({e})")
        return None

    if not coords:
        print(f"Skipping {path.name}: decoded polyline was empty")
        return None

    category = route_category(data)
    started_at = activity_start_local(data)
    if not category or not started_at:
        print(f"Skipping {path.name}: unsupported activity type or missing date")
        return None

    return {
        "coords": coords,
        "type": category,
        "type_label": category.title(),
        "name": str(data.get("name") or category.title()),
        "year": started_at.year,
        "date": started_at.strftime("%b %d, %Y").replace(" 0", " "),
    }


def load_all_routes() -> tuple[list[dict[str, Any]], int]:
    total_files = 0
    routes: list[dict[str, Any]] = []

    for path in iter_activity_files():
        total_files += 1
        route = load_route_from_file(path)
        if route:
            routes.append(route)

    return routes, total_files


def build_map(basemap: str = "dark") -> folium.Map:
    m = folium.Map(
        location=PORTLAND_CENTER,
        zoom_start=DEFAULT_ZOOM,
        tiles="OpenStreetMap" if basemap == "light" else None,
    )
    if basemap == "dark":
        OpenFreeMapDark().add_to(m)
    return m


def render_style(style: dict[str, Any], routes: list[dict[str, Any]]) -> Path:
    m = build_map(style.get("basemap", "dark"))
    RouteExplorer(routes).add_to(m)

    HEATMAPS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = HEATMAPS_DIR / style["output"]
    m.save(str(out_path))
    return out_path


def get_enabled_styles() -> list[dict[str, Any]]:
    styles_by_name = {style["name"]: style for style in HEATMAP_STYLES}
    unknown_names = [name for name in ENABLED_HEATMAPS if name not in styles_by_name]

    if unknown_names:
        raise ValueError(f"Unknown enabled heatmap style(s): {', '.join(unknown_names)}")

    return [styles_by_name[name] for name in ENABLED_HEATMAPS]


def main() -> None:
    if not ACTIVITIES_DIR.exists():
        raise FileNotFoundError(f"Activities directory not found: {ACTIVITIES_DIR}")

    routes, total_files = load_all_routes()

    print(f"Scanned files: {total_files}")
    print(f"Routes loaded: {len(routes)}")

    for style in get_enabled_styles():
        out_path = render_style(style, routes)
        print(f"Saved {style['name']}: {out_path}")


if __name__ == "__main__":
    main()
