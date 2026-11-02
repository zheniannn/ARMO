"""Slide figure: one wetting event in Sentinel-1 imagery (before / after / difference, as in the course's dNBR and
coherence-difference maps), with gridMET rain and the USCRN probe record.
Default site: Stillwater, OK. Extra cases (added 3 Nov 2026): Oakley, KS and Champaign, IL.
Run: python fig_sar_wetting_event.py [stillwater | oakley | champaign]
Inputs: data/processed/imagery/ (code/12_extract_imagery.py <site>) and uscrn_hourly.pkl (code/01_events.py).
Outputs: figures/fig_sar_wetting_event[_<site>].png, data/processed/imagery/[<site>_]sar_event_stats.csv
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

T = lambda s: pd.Timestamp(s, tz="UTC")
SITES = {
    "stillwater": dict(
        lon=-97.09, lat=36.12, wban=53926, prefix="", d0="20260813", d1="20260825", rain="20260813_20260824", rain_max=110,
        bins=(30, 60), window=("2026-08-10", "2026-08-29"), tick_days=2,
        looks={"Sentinel-1": [T("2026-08-13 00:28"), T("2026-08-25 00:28")],
               "NISAR": [T("2026-08-22 11:37"), T("2026-08-23 01:25")], "SMAP": [T("2026-08-23 12:00")]},
        labels=("13 Aug (dry)", "25 Aug (after storms)", "25 − 13 Aug", "13–24 Aug"),
        title="e  USCRN Stillwater 2 W (yellow triangle): two storms between the Sentinel-1 looks; NISAR and SMAP looked near the second peak"),
    "oakley": dict(
        lon=-100.96, lat=38.87, wban=3067, prefix="oakley_", d0="20260804", d1="20260816", rain="20260804_20260815", rain_max=100, dvv_lim=6,
        bins=(30, 60), window=("2026-08-02", "2026-08-19"), tick_days=2,
        looks={"Sentinel-1": [T("2026-08-04 12:52"), T("2026-08-16 12:52")],
               "NISAR": [T("2026-08-12 11:54"), T("2026-08-13 01:41")]},
        labels=("4 Aug (dry)", "16 Aug (after storms)", "16 − 4 Aug", "4–15 Aug"),
        title="e  USCRN Oakley 19 SSW, Kansas (yellow triangle): storms on 14–16 Aug fell after NISAR's looks and before Sentinel-1's second look"),
    "champaign": dict(
        lon=-88.37, lat=40.05, wban=54808, prefix="champaign_", d0="20260904", d1="20260916", rain="20260904_20260916", rain_max=50,
        bins=(20, 35), window=("2026-09-02", "2026-09-19"), tick_days=2,
        looks={"Sentinel-1": [T("2026-09-04 23:48"), T("2026-09-16 23:48")],
               "NISAR": [T("2026-09-11 11:05"), T("2026-09-12 00:50"), T("2026-09-16 10:56")]},
        labels=("4 Sep (dry)", "16 Sep (after rain)", "16 − 4 Sep", "4–16 Sep"),
        title="e  USCRN Champaign 9 SW, Illinois, cropland (yellow triangle): most rain fell on 16 Sep, hours before the second Sentinel-1 look"),
}
SITE = sys.argv[1] if len(sys.argv) > 1 else "stillwater"
C = SITES[SITE]
I = os.path.join(PROC, "imagery")
LON, LAT, WBAN, P = C["lon"], C["lat"], C["wban"], C["prefix"]
KM_LON = 111.32 * np.cos(np.deg2rad(LAT))
fs.apply()

a, b = np.load(os.path.join(I, f"{P}s1_vv_{C['d0']}_60km_40m.npz")), np.load(os.path.join(I, f"{P}s1_vv_{C['d1']}_60km_40m.npz"))
lin = lambda z: 10 ** (z / 10)
ratio = uniform_filter(np.nan_to_num(lin(b["vv_db"]) / lin(a["vv_db"]), nan=1.0), 5)   # 5 x 5 x 40 m = 200 m
d_db = 10 * np.log10(ratio)
d_db[~(np.isfinite(a["vv_db"]) & np.isfinite(b["vv_db"]))] = np.nan                    # outside either swath: no change shown
ext_s1 = [float(a["x0"] - a["station_x"]) / 1e3, float(a["x1"] - a["station_x"]) / 1e3,
          float(a["y0"] - a["station_y"]) / 1e3, float(a["y1"] - a["station_y"]) / 1e3]
g = np.load(os.path.join(I, f"{P}gridmet_rain_{C['rain']}.npz")); rain = g["rain_mm"]; gx0, gx1, gy0, gy1 = g["extent"]
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
            win = d40[row[i, j] - 50:row[i, j] + 50, col[i, j] - 50:col[i, j] + 50]
            if np.isfinite(win).mean() > 0.5:
                blk[i, j] = np.nanmean(win)
m = np.isfinite(blk)
lo_, hi_ = C["bins"]
stats = dict(site=SITE, r_rain_dvv=np.corrcoef(rain[m], blk[m])[0, 1], n_cells=int(m.sum()),
             rain_bin_lo_mm=lo_, rain_bin_hi_mm=hi_,
             dvv_rain_low=np.nanmean(blk[m & (rain < lo_)]), dvv_rain_mid=np.nanmean(blk[m & (rain >= lo_) & (rain < hi_)]),
             dvv_rain_high=np.nanmean(blk[m & (rain >= hi_)]), station_dvv_110m=float(np.nanmean(d40[748:752, 748:752])),
             frac_valid_pixels=float(np.isfinite(d40).mean()))
if SITE == "stillwater":   # keep the original column names used by the claim audit and the deck
    stats = {("dvv_rain_lt30" if k == "dvv_rain_low" else "dvv_rain_30_60" if k == "dvv_rain_mid" else "dvv_rain_ge60" if k == "dvv_rain_high" else k): v
             for k, v in stats.items() if k not in ("site", "rain_bin_lo_mm", "rain_bin_hi_mm", "frac_valid_pixels")}
w0, w1 = C["window"]
u = load_uscrn(); u = u[(u.wban == WBAN) & (u.time_utc >= w0) & (u.time_utc < w1)].set_index("time_utc")
looks = C["looks"]
sm_at = lambda t: float(u.sm5.asof(t))
s1t = looks["Sentinel-1"]
stats.update(sm_before=sm_at(s1t[0]), sm_after=sm_at(s1t[1]), sm_peak=float(u.sm5.max()),
             rain_station_mm=float(u.precip.sum()) if SITE == "stillwater" else float(u.precip[(u.index > s1t[0]) & (u.index <= s1t[1])].sum()))
pd.DataFrame([stats]).to_csv(os.path.join(I, f"{P}sar_event_stats.csv"), index=False)
print(pd.Series(stats).to_string())

# ---- figure
fig = plt.figure(figsize=(11.0, 5.0))
W, STEP, Y0 = 0.19, 0.25, 0.47
H = W * 11.0 / 5.0
L = C["labels"]
maps = [(a["vv_db"], ext_s1, "gray", (-18, -5), f"a  Sentinel-1 VV, {L[0]}", "γ⁰ (dB)"),
        (b["vv_db"], ext_s1, "gray", (-18, -5), f"b  Sentinel-1 VV, {L[1]}", "γ⁰ (dB)"),
        (d_db, ext_s1, "RdBu_r", (-C.get("dvv_lim", 3), C.get("dvv_lim", 3)), f"c  Change, {L[2]}", "ΔVV (dB)"),
        (rain, ext_g, "Blues", (0, C["rain_max"]), f"d  Rain, {L[3]} (gridMET)", "rain (mm)")]
for k, (arr, ext, cmap, (lo, hi), title, unit) in enumerate(maps):
    ax = fig.add_axes([0.01 + k * STEP, Y0, W, H])
    cm = plt.get_cmap(cmap).copy(); cm.set_bad("#d9d9d9")
    im = ax.imshow(arr, extent=ext, cmap=cm, vmin=lo, vmax=hi, interpolation="nearest" if k == 3 else "antialiased")
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

t0, t1 = T(w0), T(w1)
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
axs.set_xlim(t0, t1); axs.xaxis.set_major_locator(mdates.DayLocator(interval=C["tick_days"])); axs.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
axs.legend(loc="upper left", fontsize=6.8, ncol=4, handlelength=1.6, borderaxespad=0.2)
axr.set_title(C["title"], fontsize=8.6, loc="left", pad=3)
out = os.path.join(FIG, "fig_sar_wetting_event.png" if SITE == "stillwater" else f"fig_sar_wetting_event_{SITE}.png")
fig.savefig(out, dpi=250, bbox_inches="tight", pad_inches=0.03); print("saved", out)
