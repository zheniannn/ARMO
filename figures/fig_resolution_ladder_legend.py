"""Legend only, for the slide 5 figure (SMAP 9 km | NISAR 200 m | Sentinel-1 10 m, Stillwater, 23-25 Aug 2026).
Symbols and colours match the ladder (figures/fig_slide_assets.py,
slide09_resolution_ladder.png): same files, quality screen, colour maps, limits, grey (#D9DCDF), marker.
Nothing in the data or the screening is changed.

Verified for the legend (printed when run):
  grey in the NISAR panel = no recommended retrieval: retrieval-quality flag bit 0 set (excluded by the screen) or
  fill value -9999 (no retrieval, mostly outside the swath). SMAP and Sentinel-1 panels have no grey pixels.
  USCRN 5 cm probe (WBAN 53926) on 23 Aug 2026: 0.297 m3/m3 at the NISAR pass (01:25 UTC), 0.290 at the SMAP AM pass
  (hour ending 13:00 UTC) -> "0.29-0.30 m3/m3".
Output: figures/slide09_resolution_ladder_legend.png (white background; the deck's ladder legend)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "code"))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from common import PROC, load_uscrn

I = os.path.join(PROC, "imagery")
INK, GREY, NODATA = "#1B2631", "#5B6770", "#D9DCDF"          # fig_slide_assets.py palette
plt.rcParams.update({"font.family": "Calibri", "font.size": 16, "axes.edgecolor": GREY, "axes.labelcolor": INK,
                     "xtick.color": INK, "ytick.color": INK, "savefig.facecolor": "white", "svg.fonttype": "none"})
LON, LAT, WBAN = -97.09, 36.12, 53926


def north_arrow(ax, x, y, dy, color=INK, size=14):            # as fig_slide_assets.py
    ax.annotate("", xy=(x, y + dy), xytext=(x, y), arrowprops=dict(arrowstyle="-|>", color=color, lw=1.6, mutation_scale=14))
    ax.text(x, y + dy * 1.08, "N", color=color, fontsize=size, fontweight="bold", ha="center", va="bottom")


# ---- data, exactly as fig_slide_assets.py (resolution ladder)
sm_s = np.load(os.path.join(I, "smap_20260823_am.npz")); x0, x1, y0, y1 = sm_s["extent"]
KM_LON = 111.32 * np.cos(np.deg2rad(LAT))
ext_smap = [(x0 - LON) * KM_LON, (x1 - LON) * KM_LON, (y0 - LAT) * 111.32, (y1 - LAT) * 111.32]
nz = np.load(os.path.join(I, "nisar_sme2_20260823.npz"))
nis = np.where((nz["flag"] >= 0) & ((nz["flag"].astype(int) & 1) == 0), nz["sm"], np.nan)
dlon, dlat = abs(np.diff(nz["lon"]).mean()), abs(np.diff(nz["lat"]).mean())
ext_nis = [(nz["lon"].min() - dlon / 2 - LON) * KM_LON, (nz["lon"].max() + dlon / 2 - LON) * KM_LON,
           (nz["lat"].min() - dlat / 2 - LAT) * 111.32, (nz["lat"].max() + dlat / 2 - LAT) * 111.32]
if nz["lat"][0] < nz["lat"][-1]:
    nis = nis[::-1]
s1 = np.load(os.path.join(I, "s1_vv_20260825_24km_10m.npz"))
ext_s1 = [float(s1["x0"] - s1["station_x"]) / 1e3, float(s1["x1"] - s1["station_x"]) / 1e3,
          float(s1["y0"] - s1["station_y"]) / 1e3, float(s1["y1"] - s1["station_y"]) / 1e3]

# ---- legend facts, verified from the data
fl, sm = nz["flag"], nz["sm"]
flagged = int(((fl >= 0) & ((fl.astype(int) & 1) == 1)).sum()); fill = int((fl < 0).sum())
assert int(np.isnan(nis).sum()) == flagged + fill
assert not np.isnan(sm_s["sm"]).any() and not np.isnan(s1["vv_db"]).any(), "grey would appear in another panel"
u = load_uscrn(); u = u[u.wban == WBAN].set_index("time_utc").sm5
t_nisar = pd.Timestamp(str(nz["granule"]).split("_")[11][:15], tz="UTC")
p_nisar = float(u[u.index >= t_nisar.ceil("h")].iloc[0])                          # hour-end record containing the pass
t_smap = pd.Timestamp("2026-08-23", tz="UTC") + pd.Timedelta(hours=6 - LON / 15)  # 06:00 local solar (code/08_sensor_tests.py)
p_smap = float(u[u.index >= t_smap.ceil("h")].iloc[0])
lo_, hi_ = sorted((round(p_nisar, 2), round(p_smap, 2)))
probe_txt = f"{lo_:.2f}–{hi_:.2f}" if lo_ != hi_ else f"{lo_:.2f}"
print(f"grey (NISAR): {flagged} flagged + {fill} fill = {flagged + fill} of {nis.size} pixels; "
      f"probe {p_nisar:.3f} at NISAR {t_nisar:%H:%M}, {p_smap:.3f} at SMAP {t_smap:%H:%M} UTC")

# ---- legend only (transparent background, to place under the existing slide image)
handles = [Patch(fc=NODATA, ec=GREY, lw=0.6, label="No recommended NISAR retrieval (quality-flagged or no data)"),
           Line2D([], [], ls="none", marker="^", ms=13, mfc="#FFD400", mec=INK, mew=1.0,
                  label=f"USCRN in-situ probe, 5 cm: {probe_txt} m³/m³ during the 23 Aug 2026 passes")]
fig = plt.figure(figsize=(7.0, 0.9))
fig.legend(handles=handles, loc="center left", ncol=1, frameon=False, labelspacing=0.7, fontsize=14, labelcolor=INK,
           handlelength=1.4, handleheight=1.0, columnspacing=2.4, handletextpad=0.6)
fig.savefig(os.path.join(HERE, "slide09_resolution_ladder_legend.png"), dpi=400, bbox_inches="tight", pad_inches=0.12,
            facecolor="white")
plt.close(fig)
print("saved figures/slide09_resolution_ladder_legend.png")
