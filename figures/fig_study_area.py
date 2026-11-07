"""Study-area map: 120 USCRN ground-truth stations with wetting events (121 classified by land cover), coloured by median
wetting-window duration, with scale bar, north arrow and legend (template requirement).

Two layouts of the same map: figS01_study_area.png (supplementary S01, report layout) and slide04_study_area.png (deck slide 4:
title, vertical legend below the map, north arrow top right)."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "code"))
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
from common import PROC, RAW, FIG
import figstyle as fs

fs.apply()
ne = os.path.join(RAW, "naturalearth")   # unpacked by code/00_download_raw.py
states = gpd.read_file(os.path.join(ne, "states", "ne_50m_admin_1_states_provinces.shp"))
states = states[(states.iso_a2 == "US") & ~states.name.isin(["Alaska", "Hawaii"])].to_crs(5070)
lakes = gpd.read_file(os.path.join(ne, "lakes", "ne_50m_lakes.shp")).to_crs(5070)
lakes = lakes[lakes.intersects(states.union_all().envelope)]

ev = pd.read_csv(os.path.join(PROC, "events.csv"))
st = ev.groupby("wban").agg(lat=("lat", "first"), lon=("lon", "first"), name=("name", "first"),
                            window_d=("window_h", lambda x: np.median(x) / 24), n=("amp", "size")).reset_index()
pts = gpd.GeoDataFrame(st, geometry=gpd.points_from_xy(st.lon, st.lat), crs=4326).to_crs(5070)
sv = pd.read_csv(os.path.join(PROC, "station_vegetation.csv"))   # WorldCover class at the probe (121 classified stations)
crop = pts[pts.wban.isin(sv[sv.cover == "Cropland"].wban)]
sw = pts[pts.name == "OK_Stillwater_2_W"].geometry.iloc[0]

bounds = [0, 1, 1.5, 2, 2.5, 3, 4, 6]
cmap = ListedColormap(fs.SEQ)
norm = BoundaryNorm(bounds, cmap.N)


def draw(slide):
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    states.plot(ax=ax, color="#f4f3f0", edgecolor="#bdbcb6", linewidth=0.5)
    lakes.plot(ax=ax, color="#dfe9f3", edgecolor="none")
    pts.plot(ax=ax, column="window_d", cmap=cmap, norm=norm, markersize=np.clip(pts.n, 8, 60) * 0.9,
             edgecolor="white", linewidth=0.6, zorder=3)
    ax.scatter(crop.geometry.x, crop.geometry.y, s=95, marker="s", facecolor="none", edgecolor=fs.YELLOW, linewidth=1.6, zorder=4)
    ax.scatter([sw.x], [sw.y], s=150, facecolor="none", edgecolor=fs.INK, linewidth=1.4, zorder=4)
    ax.set_axis_off()
    xmin, ymin, xmax, ymax = states.total_bounds
    ax.set_xlim(xmin - 50e3, xmax + 50e3); ax.set_ylim(ymin - 10e3, ymax + 30e3)
    # scale bar (EPSG:5070 is metric equal-area)
    x0, y0 = xmin + 80e3, ymin + 60e3
    for i, c in enumerate(["#0b0b0b", "white", "#0b0b0b", "white"]):
        ax.add_patch(plt.Rectangle((x0 + i * 250e3, y0), 250e3, 30e3, facecolor=c, edgecolor=fs.INK, lw=0.6, zorder=4))
    for i, lab in enumerate(["0", "500", "1000 km"]):
        ax.text(x0 + i * 500e3, y0 + 55e3, lab, ha="center", fontsize=7)
    # north arrow (approximately true north at map centre for this projection)
    nx, ny = (xmax - 420e3, ymax - 520e3) if slide else (xmin + 130e3, ymin + 300e3)
    ax.annotate("N", xy=(nx, ny + 260e3), xytext=(nx, ny), ha="center",
                fontsize=10, fontweight="bold", arrowprops=dict(arrowstyle="-|>", color=fs.INK, lw=1.5))
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    cb = fig.colorbar(sm, ax=ax, shrink=0.62, pad=0.01, aspect=22)
    cb.set_label("Median wetting-event window (days)\n(SM anomaly ≥ 50 % of peak rise)", fontsize=8)
    cb.outline.set_visible(False)
    h = [plt.scatter([], [], s=n * 0.9, color=fs.SEQ[3], edgecolor="white") for n in (10, 30)]
    h.append(plt.scatter([], [], s=90, facecolor="none", edgecolor=fs.INK, linewidth=1.4))
    h.append(plt.scatter([], [], s=70, marker="s", facecolor="none", edgecolor=fs.YELLOW, linewidth=1.6))
    if slide:
        fig.legend(h, ["10 events", "30 events", "Example station (Stillwater, OK)", f"WorldCover cropland ({len(crop)})"],
                   loc="upper left", ncol=1, bbox_to_anchor=(0.03, 0.14), fontsize=7.2, frameon=False,
                   title="Marker size = number of wetting events", title_fontsize=7.5, alignment="left")
        ax.set_title(f"NOAA USCRN ground truth: {len(sv)} stations ({len(crop)} cropland), 2025–2026", loc="left", fontsize=9.2)
        fig.text(0.03, -0.12, "Projection: CONUS Albers Equal Area (EPSG:5070). Boundaries: Natural Earth 1:50m.",
                 fontsize=6.5, color=fs.INK2)
        out = os.path.join(FIG, "slide04_study_area.png")
    else:
        fig.legend(h, ["10 events", "30 events", "Example station (Stillwater, OK)", f"WorldCover cropland ({len(crop)})"], loc="lower right",
                   ncol=4, bbox_to_anchor=(0.95, 0.06), fontsize=7.2, title="Marker size = number of wetting events", title_fontsize=7.5)
        ax.set_title(f"NOAA USCRN ground truth: {len(pts)} event stations (of {len(sv)} classified; {len(crop)} cropland), 2025–2026",
                     loc="left", fontsize=9.2)
        fig.text(0.01, 0.0, "Projection: CONUS Albers Equal Area (EPSG:5070). Boundaries: Natural Earth 1:50m.",
                 fontsize=6.5, color=fs.INK2)
        out = os.path.join(FIG, "figS01_study_area.png")
    fig.savefig(out)
    plt.close(fig)
    print("saved", out)


draw(slide=False)
draw(slide=True)
print("stations with events:", len(pts), "classified:", len(sv), "cropland:", len(crop))
