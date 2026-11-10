"""Interactive travel-time map of the Helsinki region, built with Bokeh.

Hover any 250 m grid cell to see its travel times to Helsinki Central Railway Station,
and use the menu to switch between car, public transport, and walking.
Writes a single standalone HTML file that opens in any browser, with no server needed.
"""

import argparse
from pathlib import Path

import geopandas as gpd
from bokeh.io import output_file, save
from bokeh.layouts import column
from bokeh.models import ColorBar, CustomJS, GeoJSONDataSource, HoverTool, Select
from bokeh.palettes import Magma256
from bokeh.plotting import figure
from bokeh.transform import linear_cmap

DATA_FILE = Path(__file__).parent / "data" / "helsinki_region_travel_times_to_railway_station.gpkg"
MODES = {  # menu label -> column in the travel-time matrix (rush-hour times, minutes)
    "Public transport": "pt_r_t",
    "Car": "car_r_t",
    "Walking": "walk_t",
}
MAX_MINUTES = 90  # cap the color scale so a few very long walks don't wash out the map


def load_cells(path: Path) -> gpd.GeoDataFrame:
    cols = ["from_id", *MODES.values(), "geometry"]
    grid = gpd.read_file(path)[cols]
    grid = grid[(grid[list(MODES.values())] >= 0).all(axis=1)]  # -1 = no route; keep cells with all three modes
    grid = grid.to_crs(3857)  # Web Mercator so the cells line up with the basemap tiles
    grid["geometry"] = grid.geometry.set_precision(1)  # round to whole meters: same squares, much smaller HTML
    grid["minutes"] = grid["pt_r_t"].clip(upper=MAX_MINUTES)  # column the map colors by; JS swaps it per mode
    return grid


def build_map(data_path: Path, out_path: Path) -> Path:
    grid = load_cells(data_path)
    source = GeoJSONDataSource(geojson=grid.to_json(drop_id=True))

    p = figure(title="Travel time to Helsinki Central Railway Station (rush hour)",
               x_axis_type="mercator", y_axis_type="mercator", match_aspect=True,
               sizing_mode="stretch_both", tools="pan,wheel_zoom,reset,save", active_scroll="wheel_zoom")
    p.add_tile("OpenStreetMap.Mapnik")  # free OSM basemap, attribution added automatically
    p.axis.visible = False
    p.grid.visible = False

    mapper = linear_cmap("minutes", palette=list(reversed(Magma256)), low=0, high=MAX_MINUTES)
    cells = p.patches("xs", "ys", source=source, fill_color=mapper, fill_alpha=0.75, line_color=None)
    p.add_layout(ColorBar(color_mapper=mapper["transform"], title="Minutes (90+ capped)", width=12), "right")

    p.add_tools(HoverTool(renderers=[cells], tooltips=[
        ("Grid cell (YKR ID)", "@from_id"),
        ("Public transport", "@pt_r_t min"),
        ("Car", "@car_r_t min"),
        ("Walking", "@walk_t min"),
    ]))

    # Dropdown recolors the map in the browser by copying the chosen mode into "minutes"
    select = Select(title="Travel mode", value="Public transport", options=list(MODES), width=220)
    select.js_on_change("value", CustomJS(args=dict(source=source, modes=MODES, cap=MAX_MINUTES), code="""
        const col = modes[cb_obj.value];
        const d = source.data;
        d['minutes'] = d[col].map(v => Math.min(v, cap));
        source.change.emit();
    """))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    output_file(out_path, title="Helsinki travel-time explorer", mode="cdn")  # loads BokehJS from CDN to keep the file small
    save(column(select, p, sizing_mode="stretch_both"))
    print(f"Mapped {len(grid):,} grid cells -> {out_path} ({out_path.stat().st_size / 1e6:.1f} MB)")
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DATA_FILE, help="travel-time GeoPackage")
    parser.add_argument("--out", type=Path, default=Path("docs/index.html"), help="output HTML path")
    args = parser.parse_args()
    build_map(args.data, args.out)
