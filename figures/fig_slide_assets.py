"""Two slide images that PowerPoint cannot draw: the title background and the resolution ladder (ARMO deck).

  slide01_title_background.png   real Sentinel-1D VV image, 25 Aug 2026, around Stillwater, Oklahoma (16:9 crop)
  slide09_resolution_ladder.png  the same 24 x 24 km around USCRN Stillwater, 23-25 Aug 2026: SMAP L3E 9 km, NISAR L3 SME2
                               200 m (recommended retrievals only; grey = flagged or no data) and Sentinel-1D RTC VV 10 m;
                               its legend is figures/fig_resolution_ladder_legend.py
Inputs: data/processed/imagery/ from code/12_extract_imagery.py.
Run: python figures/fig_slide_assets.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "code"))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from common import PROC

I = os.path.join(PROC, "imagery")
INK, GREY = "#1B2631", "#5B6770"
plt.rcParams.update({"font.family": "Calibri", "font.size": 16, "axes.edgecolor": GREY, "axes.labelcolor": INK,
                     "xtick.color": INK, "ytick.color": INK, "axes.spines.top": False, "axes.spines.right": False,
                     "savefig.dpi": 220, "savefig.bbox": "tight", "savefig.facecolor": "white"})
LON, LAT = -97.09, 36.12


def north_arrow(ax, x, y, dy, color=INK, size=14):
    ax.annotate("", xy=(x, y + dy), xytext=(x, y), arrowprops=dict(arrowstyle="-|>", color=color, lw=1.6, mutation_scale=14))
    ax.text(x, y + dy * 1.08, "N", color=color, fontsize=size, fontweight="bold", ha="center", va="bottom")


# ------------------------------------------------------------------ title background: real Sentinel-1 image
a = np.load(os.path.join(I, "s1_vv_20260825_60km_40m.npz"))["vv_db"]
n = a.shape[0]; h = int(n * 9 / 16); r0 = (n - h) // 2
crop = a[r0:r0 + h]
lo, hi = np.nanpercentile(crop, [2, 99.5])
fig = plt.figure(figsize=(16, 9))
ax = fig.add_axes([0, 0, 1, 1]); ax.imshow(np.clip((crop - lo) / (hi - lo), 0, 1), cmap="gray", interpolation="antialiased",
                                           aspect="auto"); ax.set_axis_off()
fig.savefig(os.path.join(HERE, "slide01_title_background.png"), dpi=120, bbox_inches=None, pad_inches=0)
plt.close(fig)

# ------------------------------------------------------------------ resolution ladder at slide size
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
cm_sm = plt.get_cmap("YlGnBu").copy(); cm_sm.set_bad("#D9DCDF")
fig, axes = plt.subplots(1, 3, figsize=(12.6, 4.5))
panels = [(sm_s["sm"], ext_smap, cm_sm, (0.10, 0.30), "soil moisture (m³/m³)"),
          (nis, ext_nis, cm_sm, (0.10, 0.30), "soil moisture (m³/m³)"),
          (s1["vv_db"], ext_s1, "gray", (-18, -4), "VV backscatter (dB)")]
for k, (ax, (arr, ext, cm, (vlo, vhi), unit)) in enumerate(zip(axes, panels)):
    im = ax.imshow(arr, extent=ext, cmap=cm, vmin=vlo, vmax=vhi, interpolation="nearest" if k < 2 else "antialiased")
    ax.plot(0, 0, marker="^", ms=12, mfc="#FFD400", mec=INK, mew=1.0)
    ax.set_xlim(-12, 12); ax.set_ylim(-12, 12); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
    ink = "white" if k == 2 else INK
    ax.plot([-11, -6], [-11, -11], color=ink, lw=2.4, solid_capstyle="butt")
    ax.text(-8.5, -10.4, "5 km", color=ink, fontsize=14, ha="center", va="bottom", fontweight="bold")
    north_arrow(ax, 10, -11.3, 3.6, color=ink)
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.02, extend="both"); cb.ax.tick_params(labelsize=12)
    cb.set_label(unit, fontsize=13)
fig.subplots_adjust(wspace=0.42)
fig.savefig(os.path.join(HERE, "slide09_resolution_ladder.png"))
plt.close(fig)
print("saved figures/slide01_title_background.png, figures/slide09_resolution_ladder.png")
