"""Slide figure: one wetting event at Stillwater, OK, in Sentinel-1 imagery (before / after / difference, as in the
course's dNBR and coherence-difference maps), with gridMET rain and the USCRN probe record.
Inputs: data/processed/imagery/ (code/12_extract_imagery.py) and uscrn_hourly.pkl (code/01_events.py).
Outputs: figures/fig_sar_wetting_event.png, data/processed/imagery/sar_event_stats.csv
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "code"))
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy.ndimage import uniform_filter
from pyproj import Transformer
from common import PROC, FIG, load_uscrn
import figstyle as fs

I = os.path.join(PROC, "imagery")
LON, LAT, WBAN = -97.09, 36.12, 53926
KM_LON = 111.32 * np.cos(np.deg2rad(LAT))
fs.apply()

a, b = np.load(os.path.join(I, "s1_vv_20260813_60km_40m.npz")), np.load(os.path.join(I, "s1_vv_20260825_60km_40m.npz"))
lin = lambda z: 10 ** (z / 10)
ratio = uniform_filter(np.nan_to_num(lin(b["vv_db"]) / lin(a["vv_db"]), nan=1.0), 5)   # 5 x 5 x 40 m = 200 m
d_db = 10 * np.log10(ratio)
ext_s1 = [float(a["x0"] - a["station_x"]) / 1e3, float(a["x1"] - a["station_x"]) / 1e3,
          float(a["y0"] - a["station_y"]) / 1e3, float(a["y1"] - a["station_y"]) / 1e3]
g = np.load(os.path.join(I, "gridmet_rain_20260813_20260824.npz")); rain = g["rain_mm"]; gx0, gx1, gy0, gy1 = g["extent"]
ext_g = [(gx0 - LON) * KM_LON, (gx1 - LON) * KM_LON, (gy0 - LAT) * 111.32, (gy1 - LAT) * 111.32]

# ---- how well does the radar change follow the rain? (4 km gridMET cells, block means of the 40 m change)
d40 = 10 * np.log10(lin(b["vv_db"]) / lin(a["vv_db"]))
tr = Transformer.from_crs(4326, int(a["epsg"]), always_xy=True)
ny, nx = rain.shape
lon = gx0 + (np.arange(nx) + 0.5) * (gx1 - gx0) / nx; lat = gy1 - (np.arange(ny) + 0.5) * (gy1 - gy0) / ny
X, Y = tr.transform(*np.meshgrid(lon, lat))
col, row = ((X - float(a["x0"])) / 40).astype(int), ((float(a["y1"]) - Y) / 40).astype(int)
blk = np.full(rain.shape, np.nan)
for i in range(ny):
    for j in range(nx):
        if 50 <= row[i, j] < 1450 and 50 <= col[i, j] < 1450:
            blk[i, j] = np.nanmean(d40[row[i, j] - 50:row[i, j] + 50, col[i, j] - 50:col[i, j] + 50])
m = np.isfinite(blk)
stats = dict(r_rain_dvv=np.corrcoef(rain[m], blk[m])[0, 1], n_cells=int(m.sum()),
             dvv_rain_lt30=np.nanmean(blk[m & (rain < 30)]), dvv_rain_30_60=np.nanmean(blk[m & (rain >= 30) & (rain < 60)]),
             dvv_rain_ge60=np.nanmean(blk[m & (rain >= 60)]), station_dvv_110m=float(np.nanmean(d40[748:752, 748:752])))
u = load_uscrn(); u = u[(u.wban == WBAN) & (u.time_utc >= "2026-08-10") & (u.time_utc < "2026-08-29")].set_index("time_utc")
looks = {"Sentinel-1": [pd.Timestamp("2026-08-13 00:28", tz="UTC"), pd.Timestamp("2026-08-25 00:28", tz="UTC")],
         "NISAR": [pd.Timestamp("2026-08-22 11:37", tz="UTC"), pd.Timestamp("2026-08-23 01:25", tz="UTC")],
         "SMAP": [pd.Timestamp("2026-08-23 12:00", tz="UTC")]}
sm_at = lambda t: float(u.sm5.asof(t))
stats.update(sm_before=sm_at(looks["Sentinel-1"][0]), sm_after=sm_at(looks["Sentinel-1"][1]), sm_peak=float(u.sm5.max()),
             rain_station_mm=float(u.precip.sum()))
pd.DataFrame([stats]).to_csv(os.path.join(I, "sar_event_stats.csv"), index=False)
print(pd.Series(stats).round(3).to_string())

# ---- figure
fig = plt.figure(figsize=(11.0, 5.0))
W, STEP, Y0 = 0.19, 0.25, 0.47
H = W * 11.0 / 5.0
maps = [(a["vv_db"], ext_s1, "gray", (-18, -5), "a  Sentinel-1 VV, 13 Aug (dry)", "γ⁰ (dB)"),
        (b["vv_db"], ext_s1, "gray", (-18, -5), "b  Sentinel-1 VV, 25 Aug (after storms)", "γ⁰ (dB)"),
        (d_db, ext_s1, "RdBu_r", (-3, 3), "c  Change, 25 − 13 Aug", "ΔVV (dB)"),
        (rain, ext_g, "Blues", (0, 110), "d  Rain, 13–24 Aug (gridMET)", "rain (mm)")]
for k, (arr, ext, cmap, (lo, hi), title, unit) in enumerate(maps):
    ax = fig.add_axes([0.01 + k * STEP, Y0, W, H])
    im = ax.imshow(arr, extent=ext, cmap=cmap, vmin=lo, vmax=hi, interpolation="nearest" if k == 3 else "antialiased")
    ax.plot(0, 0, marker="^", ms=7, mfc="#ffd400", mec=fs.INK, mew=0.8)
    ax.set_xlim(-30, 30); ax.set_ylim(-30, 30); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ink = "white" if k < 2 else fs.INK
    ax.plot([-27, -17], [-27, -27], color=ink, lw=1.6, solid_capstyle="butt")
    ax.text(-22, -25.8, "10 km", color=ink, fontsize=7, ha="center", va="bottom")
    ax.annotate("", xy=(25, -17.5), xytext=(25, -27.5), arrowprops=dict(arrowstyle="-|>", color=ink, lw=1.0, mutation_scale=8))
    ax.text(25, -17, "N", color=ink, fontsize=8, fontweight="bold", ha="center", va="bottom")
    ax.set_title(title, fontsize=8.6, loc="left", pad=3)
    cax = fig.add_axes([0.01 + k * STEP + W + 0.005, Y0 + 0.05, 0.008, H - 0.10])
    cb = fig.colorbar(im, cax=cax, extend="both" if k < 3 else "max"); cb.ax.tick_params(labelsize=6.5)
    cb.set_label(unit, fontsize=7, labelpad=1)

t0, t1 = pd.Timestamp("2026-08-10", tz="UTC"), pd.Timestamp("2026-08-29", tz="UTC")
axr = fig.add_axes([0.06, 0.29, 0.88, 0.10]); axs = fig.add_axes([0.06, 0.04, 0.88, 0.235], sharex=axr)
axr.bar(u.index, u.precip, width=1 / 24, color=fs.BLUE, align="edge")
axr.set_ylabel("rain\n(mm/h)", fontsize=7); axr.tick_params(labelbottom=False, labelsize=7); axr.grid(axis="x", visible=False)
axs.plot(u.index, u.sm5, color=fs.INK, lw=1.4, label="USCRN probe, 5 cm")
cols = {"Sentinel-1": fs.ORANGE, "NISAR": fs.VIOLET, "SMAP": fs.AQUA}
for name, ts in looks.items():
    for i, t in enumerate(ts):
        for ax_ in (axr, axs):
            ax_.axvline(t, color=cols[name], lw=1.6, ls="-" if name == "Sentinel-1" else "--")
        axs.plot([], [], color=cols[name], lw=1.6, ls="-" if name == "Sentinel-1" else "--", label=f"{name} look" if i == 0 else None)
axs.set_ylabel("soil moisture\n(m³/m³)", fontsize=7); axs.tick_params(labelsize=7); axs.grid(axis="x", visible=False)
axs.set_xlim(t0, t1); axs.xaxis.set_major_locator(mdates.DayLocator(interval=2)); axs.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
axs.legend(loc="upper left", fontsize=6.8, ncol=4, handlelength=1.6, borderaxespad=0.2)
axr.set_title("e  USCRN Stillwater 2 W (yellow triangle): two storms between the Sentinel-1 looks; NISAR and SMAP looked near the second peak",
              fontsize=8.6, loc="left", pad=3)
out = os.path.join(FIG, "fig_sar_wetting_event.png")
fig.savefig(out, dpi=250, bbox_inches="tight", pad_inches=0.03); print("saved", out)
