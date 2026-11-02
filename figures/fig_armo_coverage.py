"""Slide figure: revisit over the US for Sentinel-1 (real, 2026), ARMO design D (simulated) and both together,
on one colour scale. Revisit = days in the window / distinct days with at least one look, the same definition as the
Earth Engine Sentinel-1 map (code/10_gee_need_maps.py).
ARMO: two satellites 180 deg apart in one 620 km dawn-dusk orbit, right-looking 25-45 deg off-nadir, flown in the
J2 orbit model of code/06_mission_design.py (one orbital phase), 1 Jun - 10 Nov 2026, on a 0.5 deg grid.
Inputs: data/processed/need_grid.npz (step 10), data/raw/naturalearth (step 00).
Outputs: figures/fig_armo_coverage.png, data/processed/armo_revisit_grid.npz (cache; delete to recompute, ~5 min)
"""
import os
import sys
import importlib
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "code"))
import numpy as np
import geopandas as gpd
import shapely
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm
from common import PROC, RAW, FIG
import figstyle as fs

md = importlib.import_module("06_mission_design")
X0, Y0, DX, NX, NY = -125.0, 50.0, 0.1, 590, 260          # grid of step 10
STEP = 5                                                   # ARMO on every 5th cell: 0.5 deg
fs.apply()
states = gpd.read_file(os.path.join(RAW, "naturalearth", "states", "ne_50m_admin_1_states_provinces.shp"))
states = states[(states.iso_a2 == "US") & ~states.name.isin(["Alaska", "Hawaii"])]
us_geom = states.union_all()
xx, yy = np.meshgrid(X0 + (np.arange(NX) + 0.5) * DX, Y0 - (np.arange(NY) + 0.5) * DX)
us = shapely.contains_xy(us_geom, xx, yy)

days = np.load(os.path.join(PROC, "need_grid.npz"))["days"]
R_s1 = np.where(us & (days > 0), 214.0 / np.where(days > 0, days, 1), np.nan)   # 1 Apr - 31 Oct 2026

f = os.path.join(PROC, "armo_revisit_grid.npz")
if not os.path.exists(f):
    sats = [md.orbit(620, 18.0, s * np.pi) for s in (0, 1)]
    win_d = (md.T1 - md.T0).total_seconds() / 86400
    rr, cc = np.meshgrid(np.arange(STEP // 2, NY, STEP), np.arange(STEP // 2, NX, STEP), indexing="ij")
    R_a = np.full(rr.shape, np.nan)
    for i in range(rr.shape[0]):
        for j in range(rr.shape[1]):
            if not us[rr[i, j], cc[i, j]]:
                continue
            lat, lon = yy[rr[i, j], cc[i, j]], xx[rr[i, j], cc[i, j]]
            tt = np.concatenate([md.accesses(t, r, v, lat, lon, 25, 45, "R", rev) for t, r, v, _, _, rev in sats])
            n_days = np.unique(np.floor(tt / 86400)).size
            R_a[i, j] = win_d / n_days if n_days else np.nan
        print(f"row {i + 1}/{rr.shape[0]}", flush=True)
    np.savez_compressed(f, R_armo=R_a, step=STEP, window_days=win_d)
R_a = np.load(f)["R_armo"]
R_armo = np.where(us, np.repeat(np.repeat(R_a, STEP, 0), STEP, 1)[:NY, :NX], np.nan)
R_comb = 1 / (1 / R_s1 + 1 / R_armo)
med = lambda a: np.nanmedian(a[np.isfinite(a)])
print(f"median revisit: Sentinel-1 {med(R_s1):.2f} d, ARMO {med(R_armo):.2f} d, together {med(R_comb):.2f} d")

fig = plt.figure(figsize=(11.0, 3.2))
ASP = 1 / np.cos(np.deg2rad(37.0))
W = 0.30
H = W * 11.0 * (26 * ASP / 58.5) / 3.2
bounds = [1, 1.5, 2, 3, 4, 5, 6, 8, 10, 12, 16]
cm = plt.get_cmap("Blues", len(bounds) + 1)
norm = BoundaryNorm(bounds, cm.N, extend="both")
ext = [X0, X0 + NX * DX, Y0 - NY * DX, Y0]
bar_deg = 500 / (111.32 * np.cos(np.deg2rad(37.0)))
for k, (arr, title) in enumerate([(R_s1, f"a  Sentinel-1, real 2026 (median {med(R_s1):.1f} d)"),
                                  (R_armo, f"b  ARMO (2 satellites), simulated (median {med(R_armo):.1f} d)"),
                                  (R_comb, f"c  Sentinel-1 + ARMO (median {med(R_comb):.1f} d)")]):
    ax = fig.add_axes([0.005 + k * 0.315, 0.04, W, H])
    im = ax.imshow(arr, extent=ext, origin="upper", cmap=cm, norm=norm, interpolation="nearest")
    states.boundary.plot(ax=ax, color="#555555", linewidth=0.25)
    ax.set_xlabel(""); ax.set_ylabel("")
    ax.set_xlim(-125, -66.5); ax.set_ylim(24, 50); ax.set_aspect(ASP); ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.plot([-78.5, -78.5 + bar_deg], [25.2, 25.2], color=fs.INK, lw=1.0, solid_capstyle="butt")
    ax.text(-78.5 + bar_deg / 2, 25.75, "500 km", fontsize=5.5, ha="center", va="bottom")
    ax.annotate("", xy=(-69.0, 29.0), xytext=(-69.0, 25.0), arrowprops=dict(arrowstyle="-|>", color=fs.INK, lw=0.8, mutation_scale=7))
    ax.text(-69.0, 29.3, "N", fontsize=6.5, fontweight="bold", ha="center", va="bottom")
    ax.set_title(title, fontsize=8.4, loc="left", pad=2)
cax = fig.add_axes([0.955, 0.12, 0.009, H - 0.16])
cb = fig.colorbar(im, cax=cax, ticks=bounds); cb.ax.set_yticklabels([f"{b:g}" for b in bounds]); cb.ax.tick_params(labelsize=6.5); cb.set_label("mean revisit (days)", fontsize=7)
fig.text(0.005, -0.03, "Caveat (added 3 Nov 2026): these are ACCESS opportunities, not imaged coverage or event capture. ARMO assumes the whole 25–45° "
         "access corridor is imaged on every pass (one orbital phase, 0.5° grid, repeated to 0.1°); panel c combines mean rates (1/R = 1/R_S1 + 1/R_ARMO), "
         "not acquisition times.\nEvent-level capture uses real acquisition times (fig_capture_gain_paired_ci); a narrower usable strip lowers it sharply "
         "(fig_swath_capture_sensitivity).", fontsize=6.2, color=fs.INK2)
out = os.path.join(FIG, "fig_armo_coverage.png")
fig.savefig(out, dpi=250, bbox_inches="tight", pad_inches=0.03); print("saved", out)
