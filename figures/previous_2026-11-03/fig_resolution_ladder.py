"""Slide figure: the same 24 x 24 km of Oklahoma farmland around USCRN Stillwater 2 W at three resolutions:
SMAP L3E 9 km and NISAR L3 SME2 200 m soil moisture (23 Aug 2026, one shared colour scale) and Sentinel-1 VV at 10 m
(25 Aug 2026, the nearest Sentinel-1 look). Inputs: data/processed/imagery/ (code/12_extract_imagery.py).
Output: figures/fig_resolution_ladder.png
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "code"))
import numpy as np
import matplotlib.pyplot as plt
from common import PROC, FIG, load_uscrn
import figstyle as fs

I = os.path.join(PROC, "imagery")
LON, LAT, WBAN = -97.09, 36.12, 53926
KM_LON = 111.32 * np.cos(np.deg2rad(LAT))
fs.apply()

sm_s = np.load(os.path.join(I, "smap_20260823_am.npz")); x0, x1, y0, y1 = sm_s["extent"]
ext_smap = [(x0 - LON) * KM_LON, (x1 - LON) * KM_LON, (y0 - LAT) * 111.32, (y1 - LAT) * 111.32]
n = np.load(os.path.join(I, "nisar_sme2_20260823.npz"))
nis = np.where((n["flag"] >= 0) & ((n["flag"].astype(int) & 1) == 0), n["sm"], np.nan)   # recommended retrievals only
dlon, dlat = abs(np.diff(n["lon"]).mean()), abs(np.diff(n["lat"]).mean())
ext_nis = [(n["lon"].min() - dlon / 2 - LON) * KM_LON, (n["lon"].max() + dlon / 2 - LON) * KM_LON,
           (n["lat"].min() - dlat / 2 - LAT) * 111.32, (n["lat"].max() + dlat / 2 - LAT) * 111.32]
if n["lat"][0] < n["lat"][-1]:          # imshow draws row 0 at the top
    nis = nis[::-1]
s1 = np.load(os.path.join(I, "s1_vv_20260825_24km_10m.npz"))
ext_s1 = [float(s1["x0"] - s1["station_x"]) / 1e3, float(s1["x1"] - s1["station_x"]) / 1e3,
          float(s1["y0"] - s1["station_y"]) / 1e3, float(s1["y1"] - s1["station_y"]) / 1e3]
u = load_uscrn(); u = u[u.wban == WBAN].set_index("time_utc").sm5
probe = float(u.asof(__import__("pandas").Timestamp("2026-08-23 06:00", tz="UTC")))

fig = plt.figure(figsize=(11.0, 4.3))
W, STEP, Y0 = 0.255, 0.32, 0.06
H = W * 11.0 / 4.3
cmap = plt.get_cmap("YlGnBu")
cmap.set_bad("#d9d8d4")
panels = [(sm_s["sm"], ext_smap, cmap, (0.10, 0.30), "a  SMAP radiometer, 9 km (23 Aug, 06:00)", "soil moisture (m³/m³)"),
          (nis, ext_nis, cmap, (0.10, 0.30), "b  NISAR L-band SAR, 200 m (23 Aug)", "soil moisture (m³/m³)"),
          (s1["vv_db"], ext_s1, "gray", (-18, -4), "c  Sentinel-1 C-band SAR, 10 m (25 Aug)", "VV backscatter γ⁰ (dB)")]
for k, (arr, ext, cm, (lo, hi), title, unit) in enumerate(panels):
    ax = fig.add_axes([0.005 + k * STEP, Y0, W, H])
    im = ax.imshow(arr, extent=ext, cmap=cm, vmin=lo, vmax=hi, interpolation="nearest" if k < 2 else "antialiased")
    ax.plot(0, 0, marker="^", ms=7, mfc="#ffd400", mec=fs.INK, mew=0.8)
    ax.set_xlim(-12, 12); ax.set_ylim(-12, 12); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ink = "white" if k == 2 else fs.INK
    ax.plot([-11, -6], [-11, -11], color=ink, lw=1.6, solid_capstyle="butt")
    ax.text(-8.5, -10.5, "5 km", color=ink, fontsize=7, ha="center", va="bottom")
    ax.annotate("", xy=(10, -6.8), xytext=(10, -11.2), arrowprops=dict(arrowstyle="-|>", color=ink, lw=1.0, mutation_scale=8))
    ax.text(10, -6.6, "N", color=ink, fontsize=8, fontweight="bold", ha="center", va="bottom")
    if k < 2:
        ax.text(-11, 11, f"probe: {probe:.2f} m³/m³", fontsize=7, va="top", ha="left",
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.8))
    ax.set_title(title, fontsize=8.6, loc="left", pad=3)
    cax = fig.add_axes([0.005 + k * STEP + W + 0.005, Y0 + 0.08, 0.008, H - 0.16])
    cb = fig.colorbar(im, cax=cax, extend="both"); cb.ax.tick_params(labelsize=6.5); cb.set_label(unit, fontsize=7, labelpad=1)
out = os.path.join(FIG, "fig_resolution_ladder.png")
fig.savefig(out, dpi=250, bbox_inches="tight", pad_inches=0.03); print("saved", out, "probe", round(probe, 3))
