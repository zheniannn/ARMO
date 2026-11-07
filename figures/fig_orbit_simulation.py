"""The ARMO orbit simulator (code/06_mission_design.py), shown for design D (SIMULATED looks; OBSERVED fleet and ground truth).

(a) One day of design D over the contiguous US: two satellites 180 deg apart in one 620 km dawn-dusk sun-synchronous
    orbit, each imaging a 25-45 deg off-nadir access swath on its right side.
(b) USCRN Stillwater 2 W, Oklahoma, 10-29 Aug 2026 (the slide 5 period): 5 cm soil moisture and wetting windows, the real
    Sentinel-1 and NISAR looks, and the simulated ARMO looks.
The orbit, access geometry and look rule are the functions in code/06_mission_design.py (orbit, ground_range_km,
accesses), at orbital phase 0 of the 8 phases the capture results average over.
Outputs: figures/figS11_orbit_simulation.png, figures/generated/orbit_simulation_stats.csv
"""
import importlib
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import geopandas as gpd
from matplotlib.patches import Polygon
from pyproj import Transformer
import armo_evidence as ae
import figstyle as fs
from common import PROC, RAW, load_uscrn, season_series

fs.apply()
md = importlib.import_module("06_mission_design")
H_KM, LTAN, E0, E1 = 620, 18.0, 25, 45
WBAN = 53926
DAY = pd.Timestamp("2026-08-22", tz="UTC")
P0, P1 = pd.Timestamp("2026-08-10", tz="UTC"), pd.Timestamp("2026-08-30", tz="UTC")
SAT_COL = {"A": fs.BLUE, "B": fs.ORANGE}
to5070 = Transformer.from_crs(4326, 5070, always_xy=True)

sats = {}
for k, s in enumerate("AB"):
    t, r, v, inc, a, rev = md.orbit(H_KM, LTAN, k * np.pi)        # phase 0; satellite B 180 deg behind A
    sats[s] = (t, r, v, rev)
swath_km = md.ground_range_km(E1, a) - md.ground_range_km(E0, a)
period_min = 2 * np.pi * np.sqrt(a ** 3 / md.MU) / 60


def ground(r, v, eta):
    """Ground point at off-nadir angle eta on the right-hand side (the side accesses() calls R)."""
    rh = r / np.linalg.norm(r, axis=1)[:, None]
    right = np.cross(v, r); right /= np.linalg.norm(right, axis=1)[:, None]
    lam = md.ground_range_km(eta, a) / md.RE
    g = np.cos(lam) * rh + np.sin(lam) * right
    return np.rad2deg(np.arctan2(g[:, 1], g[:, 0])), np.rad2deg(np.arcsin(g[:, 2]))


def segments(mask):
    i = np.flatnonzero(mask)
    return np.split(i, np.flatnonzero(np.diff(i) > 1) + 1) if i.size else []


states = gpd.read_file(os.path.join(RAW, "naturalearth", "states", "ne_50m_admin_1_states_provinces.shp"))
states = states[(states.iso_a2 == "US") & ~states.name.isin(["Alaska", "Hawaii"])].to_crs(5070)
ev = ae.events_real()
stn = ev[ev.wban == WBAN].iloc[0]

fig = plt.figure(figsize=(7.4, 8.4))
gs = fig.add_gridspec(3, 1, height_ratios=[2.9, 0.85, 0.75], hspace=0.14)
ax = fig.add_subplot(gs[0])
states.plot(ax=ax, color="#f4f3f0", edgecolor="#bdbcb6", linewidth=0.5)
n_pass = {}
for s, (t, r, v, rev) in sats.items():
    i0 = int((DAY - md.T0).total_seconds() / md.DT); sl = slice(i0, i0 + int(86400 / md.DT))
    rr, vv = r[sl], v[sl]
    lat = np.rad2deg(np.arcsin(rr[:, 2] / np.linalg.norm(rr, axis=1))); lon = np.rad2deg(np.arctan2(rr[:, 1], rr[:, 0]))
    nl, nb = ground(rr, vv, E0); fl, fb = ground(rr, vv, E1)
    box = lambda lo, la: (lo > -128) & (lo < -64) & (la > 22) & (la < 52)
    segs = [g for g in segments(box(nl, nb) | box(fl, fb)) if g.size > 5]
    n_pass[s] = len(segs)
    for g in segs:
        x0, y0 = to5070.transform(nl[g], nb[g]); x1, y1 = to5070.transform(fl[g], fb[g])
        ax.add_patch(Polygon(np.c_[np.r_[x0, x1[::-1]], np.r_[y0, y1[::-1]]], closed=True, facecolor=SAT_COL[s],
                             alpha=0.18, edgecolor=SAT_COL[s], linewidth=0.5, zorder=2))
        gx, gy = to5070.transform(lon[g], lat[g])
        ax.plot(gx, gy, color=SAT_COL[s], lw=1.0, ls="--", zorder=3)
sx, sy = to5070.transform(stn.lon, stn.lat)
ax.scatter([sx], [sy], marker="*", s=140, color=fs.INK, edgecolor="white", linewidth=0.6, zorder=5)
ax.annotate("Stillwater, OK", (sx, sy), xytext=(8, -12), textcoords="offset points", fontsize=8)
xmin, ymin, xmax, ymax = states.total_bounds
ax.set_xlim(xmin - 50e3, xmax + 50e3); ax.set_ylim(ymin - 30e3, ymax + 30e3); ax.set_axis_off()
h = [plt.Rectangle((0, 0), 1, 1, facecolor=SAT_COL[s], alpha=0.35, edgecolor=SAT_COL[s]) for s in "AB"]
h += [plt.Line2D([], [], color=fs.INK2, lw=1, ls="--")]
ax.legend(h, ["Satellite A access swath", "Satellite B (180° behind A)", "Ground track"], loc="lower left",
          fontsize=7.5, bbox_to_anchor=(0.0, -0.02))
ax.set_title(f"ARMO design D, one day ({DAY:%d %b %Y}): two satellites 180° apart in a {H_KM} km dawn–dusk orbit\n"
             f"(inclination {inc:.1f}°, period {period_min:.0f} min), each imaging {E0}–{E1}° off-nadir = {swath_km:.0f} km access swath",
             loc="left", fontsize=8.6)
fs.panel_label(ax, "a")

# (b) Stillwater timeline
df = load_uscrn()
sm = season_series(df, WBAN, 2026)
sm = sm[(sm.index >= P0) & (sm.index < P1)]
e = ev[(ev.wban == WBAN) & (ev.t_start >= P0) & (ev.t_start < P1)]
s1 = pd.read_csv(os.path.join(PROC, "acq_s1.csv"), parse_dates=["time"])
ni = pd.read_csv(os.path.join(PROC, "acq_nisar.csv"), parse_dates=["time"])
looks = {"Sentinel-1": s1[s1.wban == WBAN].time.drop_duplicates(),
         "NISAR": ni[ni.wban == WBAN].time.sort_values()}
looks["NISAR"] = looks["NISAR"][looks["NISAR"].diff().fillna(pd.Timedelta(days=1)) > pd.Timedelta(hours=1)]
armo_all = []
for s, (t, r, v, rev) in sats.items():
    ts = md.T0 + pd.to_timedelta(md.accesses(t, r, v, stn.lat, stn.lon, E0, E1, "R", rev), unit="s")
    looks[f"ARMO sat {s}"] = pd.Series(ts); armo_all.append(ts)
armo_all = pd.DatetimeIndex(np.sort(np.concatenate([x.values for x in armo_all]))).tz_localize("UTC")

b = fig.add_subplot(gs[1]); c = fig.add_subplot(gs[2], sharex=b)
for w in e.itertuples():
    for axx in (b, c):
        axx.axvspan(w.t_ws, min(w.t_we, P1), color=fs.YELLOW, alpha=0.25, lw=0)
b.plot(sm.index, sm.sm5, color=fs.INK, lw=1.3)
b.set_ylabel("5 cm soil\nmoisture (m³/m³)", fontsize=8)
b.tick_params(labelbottom=False)
b.set_title(f"USCRN Stillwater 2 W, {P0:%d}–{P1 - pd.Timedelta(days=1):%d %b %Y}: wetting windows (yellow), real looks and "
            "simulated ARMO looks", loc="left", fontsize=8.6)
fs.panel_label(b, "b")
rows = [("Sentinel-1", fs.VIOLET), ("NISAR", fs.GREEN), ("ARMO sat A", SAT_COL["A"]), ("ARMO sat B", SAT_COL["B"])]
for y, (name, col) in enumerate(rows[::-1]):
    x = looks[name]; x = x[(x >= P0) & (x < P1)]
    c.vlines(x, y - 0.32, y + 0.32, color=col, lw=2.2)
c.set_yticks(range(len(rows))); c.set_yticklabels([n for n, _ in rows[::-1]], fontsize=8)
c.set_ylim(-0.6, len(rows) - 0.4); c.grid(axis="y", visible=False)
c.xaxis.set_major_locator(mdates.DayLocator(interval=2)); c.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
c.set_xlim(P0, P1)
fig.text(0.01, 0.035, "Orbit: circular, J2 nodal precession at the sun-synchronous rate, spherical Earth, 10 s steps. A look = closest approach "
         "with the station 25–45° off-nadir on the\nlooking side. SIMULATED looks at orbital phase 0 of 8; capture results average all 8 "
         "phases and assume the whole access swath is imaged.", fontsize=6.6, color=fs.INK2, va="top")

era = (armo_all >= ae.ERA[0]) & (armo_all < ae.ERA[1])
gaps = np.diff(armo_all[era]) / pd.Timedelta(days=1)
gaps = gaps[gaps > 0.25]
ae.save(fig, "figS11_orbit_simulation")
pd.DataFrame([
    dict(quantity="altitude (km)", value=H_KM), dict(quantity="inclination (deg)", value=inc),
    dict(quantity="orbital period (min)", value=period_min), dict(quantity="access swath (km)", value=swath_km),
    dict(quantity=f"CONUS passes on {DAY:%Y-%m-%d}, satellite A", value=n_pass["A"]),
    dict(quantity=f"CONUS passes on {DAY:%Y-%m-%d}, satellite B", value=n_pass["B"]),
    dict(quantity="ARMO looks at Stillwater, 17 Jun-31 Oct 2026 (phase 0)", value=int(era.sum())),
    dict(quantity="median gap between ARMO looks at Stillwater (d, looks < 6 h apart merged)", value=float(np.median(gaps))),
]).to_csv(os.path.join(ae.GEN, "orbit_simulation_stats.csv"), index=False)
print(f"inclination {inc:.2f} deg, period {period_min:.1f} min, swath {swath_km:.0f} km, passes {n_pass}, "
      f"Stillwater looks {int(era.sum())}, median gap {np.median(gaps):.2f} d")
