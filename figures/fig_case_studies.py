"""SAR-rainfall-soil-moisture case studies for the ARMO slides (Stillwater OK in the deck; Oakley KS, Champaign IL optional).

Five panels per site: (a) Sentinel-1 RTC VV before, (b) after, (c) change, (d) gridMET rain over the same interval,
(e) USCRN hourly rain + 5 cm soil moisture + satellite acquisition times + wetting windows (events_real.csv).
Two versions per site: *_scientific (reference layout, small type) and *_presentation (16:9, large type).
Supplementary NISAR L-band figure (*_nisar_*) where a same-track before/after GCOV pair exists
(code/13_extract_nisar_gcov.py).

Inputs (no data are changed):
  data/processed/imagery/[<site>_]s1_vv_<date>_60km_40m.npz      code/12_extract_imagery.py (Planetary Computer S1 RTC)
  data/processed/imagery/[<site>_]gridmet_rain_<d0>_<d1>.npz      same script (Earth Engine IDAHO_EPSCOR/GRIDMET, 0.01 deg)
  data/processed/imagery/nisar_gcov/*.npz                          code/13_extract_nisar_gcov.py
  data/processed/acquisition_validity.csv                          code/14_check_station_validity.py
  data/processed/uscrn_hourly.pkl, events_real.csv, acq_s1.csv, acq_nisar.csv
Conventions (verified 3 Nov 2026):
  USCRN hourly values are labelled at the END of the hour; bars span (h-1, h], windows (t_ws-1 h, t_we-1 h].
  gridMET day D (Earth Engine id YYYYMMDD) holds rain from D 12:00 to D+1 12:00 UTC (station test: r = 0.82-0.99,
  every other convention r <= 0.73). A day is counted in an interval if >= 12 h of it lies inside the interval.
  The 0.01 deg gridMET grid repeats each native 1/24 deg (~4 km) cell ~16 times, so statistics use NATIVE cells.
All three sites are always computed (they share the colour scales). By default only the two figures used in the
deck are saved: figures/slide06_stillwater_sentinel1.png and slide07_stillwater_nisar.png; pass --all
to also save every site and both styles in figures/case_studies/. Statistics: figures/generated/case_study_stats.csv, case_study_nisar_stats.csv.
Run: python figures/fig_case_studies.py [--all]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "case_studies")          # --all only: every site and style
SAVE_ALL = "--all" in sys.argv
DECK = {"stillwater_presentation": "slide06_stillwater_sentinel1",   # saved in figures/ under the slide number
        "stillwater_nisar_presentation": "slide07_stillwater_nisar"}
sys.path.insert(0, os.path.join(ROOT, "code"))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import matplotlib.patheffects as pe
from scipy.ndimage import uniform_filter, distance_transform_edt
from pyproj import Transformer
from common import PROC, load_uscrn, rd

I = os.path.join(PROC, "imagery")
NI_DIR = os.path.join(I, "nisar_gcov")
T = lambda s: pd.Timestamp(s, tz="UTC")
H, HALF = pd.Timedelta(hours=1), pd.Timedelta(minutes=30)
GM_X0, GM_Y1, GM_D = -124.78749996666667, 49.42083333333334, 1 / 24      # gridMET native grid (Earth Engine metadata)
INK, GREY, LIGHT, PALE = "#1B2631", "#5B6770", "#D5DDE3", "#D3E6F1"
S1_COL, NI_COL, RAIN_COL = "#E07B00", "#7B3FA0", "#2F5F8A"
VV_LIM, DVV_LIM, RAIN_MAX = (-18, -5), 4.0, 110          # shared by all three sites (see audit for the percentiles)

SITES = {
    "stillwater": dict(name="Stillwater 2 W, Oklahoma", short="Stillwater", wban=53926, lon=-97.09, lat=36.12, prefix="",
                       d0="20260813", d1="20260825", rain="20260813_20260824", bins=(30, 60),
                       ts=("2026-08-10", "2026-08-29"), nisar=("20260811", "20260823")),
    "oakley": dict(name="Oakley 19 SSW, Kansas", short="Oakley", wban=3067, lon=-100.96, lat=38.87, prefix="oakley_",
                   d0="20260804", d1="20260816", rain="20260804_20260815", bins=(30, 60),
                   ts=("2026-08-02", "2026-08-21"), nisar=("20260724", "20260817")),
    "champaign": dict(name="Champaign 9 SW, Illinois (cropland)", short="Champaign", wban=54808, lon=-88.37, lat=40.05,
                      prefix="champaign_", d0="20260904", d1="20260916", rain="20260904_20260916", bins=(20, 35),
                      ts=("2026-09-02", "2026-09-19"), nisar=("20260904", "20260916")),
}
u_all = load_uscrn()
ev_all = rd("events_real.csv", parse_dates=["t_start", "t_peak", "t_ws", "t_we"])


def one_per_pass(a):
    a = a.sort_values("time")
    return a[(a.time.diff() > H) | a.time.diff().isna()]


_VF = os.path.join(PROC, "acquisition_validity.csv")       # check_station_validity.py: pixel actually valid at the station?
VALID = pd.read_csv(_VF, parse_dates=["time"]) if os.path.exists(_VF) else pd.DataFrame(columns=["wban", "sensor", "time", "valid"])


def usable(wban, sensor, t):
    v = VALID[(VALID.wban == wban) & (VALID.sensor == sensor) & ((VALID.time - t).abs() < pd.Timedelta(minutes=2))]
    if v.empty:
        print(f"  (validity not checked: {sensor} {t:%d %b %H:%M} at {wban})")
        return True
    return bool(v.valid.astype(str).str.lower().eq("true").any())


S1_ACQ = pd.read_csv(os.path.join(PROC, "acq_s1.csv"), parse_dates=["time"])
NI_ACQ = pd.read_csv(os.path.join(PROC, "acq_nisar.csv"), parse_dates=["time"])


def gm_days(t0, t1):
    """gridMET days (labelled D: D 12Z -> D+1 12Z) with >= 12 h inside [t0, t1]."""
    days = pd.date_range(t0.floor("D") - pd.Timedelta(days=1), t1.floor("D"), freq="D")
    keep = [d for d in days if (min(t1, d + pd.Timedelta(hours=36)) - max(t0, d + pd.Timedelta(hours=12))) >= pd.Timedelta(hours=12)]
    return keep[0], keep[-1]


def gridmet_sum(site, d_first, d_last):
    """Rain over gridMET days d_first..d_last; existing files reused, NISAR intervals fetched once (cached)."""
    c = SITES[site]
    tag = f"{d_first:%Y%m%d}_{d_last:%Y%m%d}"
    for f in (os.path.join(I, f"{c['prefix']}gridmet_rain_{tag}.npz"), os.path.join(NI_DIR, f"{site}_gridmet_rain_{tag}.npz")):
        if os.path.exists(f):
            g = np.load(f); return g["rain_mm"], g["extent"], f
    import ee
    ee.Initialize(project=os.environ.get("EE_PROJECT", "my-ee-project-ntu-512914"))
    img = ee.ImageCollection("IDAHO_EPSCOR/GRIDMET").filterDate(f"{d_first:%Y-%m-%d}", f"{d_last + pd.Timedelta(days=1):%Y-%m-%d}").select("pr").sum()
    lat = c["lat"]; dlat = 30 / 111.32; dlon = 30 / (111.32 * np.cos(np.deg2rad(lat)))
    x0, y0, x1, y1 = c["lon"] - dlon, lat - dlat, c["lon"] + dlon, lat + dlat
    nx, ny = int(np.ceil((x1 - x0) / 0.01)), int(np.ceil((y1 - y0) / 0.01))
    req = dict(expression=img, fileFormat="NUMPY_NDARRAY", grid=dict(dimensions=dict(width=nx, height=ny),
               affineTransform=dict(scaleX=0.01, shearX=0, translateX=x0, shearY=0, scaleY=-0.01, translateY=y1), crsCode="EPSG:4326"))
    a = ee.data.computePixels(req)["pr"].astype("float32")
    ext = np.array((x0, x0 + nx * 0.01, y1 - ny * 0.01, y1))
    f = os.path.join(NI_DIR, f"{site}_gridmet_rain_{tag}.npz")
    np.savez_compressed(f, rain_mm=a, extent=ext); print("fetched", f)
    return a, ext, f


def native_stats(d40, x0, y1, epsg, rain, ext, bins, rng, res=40.0):
    """Change vs rain on native gridMET cells: mean of 40 m dB change per cell (>= 50 % valid, cell fully in box)."""
    n = d40.shape[0]
    xs = x0 + (np.arange(n) + 0.5) * res; ys = y1 - (np.arange(n) + 0.5) * res
    X, Y = np.meshgrid(xs, ys)
    lon, lat = Transformer.from_crs(epsg, 4326, always_xy=True).transform(X, Y)
    ci = np.floor((lon - GM_X0) / GM_D).astype(int); ri = np.floor((GM_Y1 - lat) / GM_D).astype(int)
    # native-cell rain from the 0.01 deg cells whose centres lie in the cell (Earth Engine nearest resampling)
    gx0, gx1, gy0, gy1 = ext; ny, nx = rain.shape
    glon = gx0 + (np.arange(nx) + 0.5) * (gx1 - gx0) / nx; glat = gy1 - (np.arange(ny) + 0.5) * (gy1 - gy0) / ny
    GL, GA = np.meshgrid(glon, glat)
    gr = pd.DataFrame(dict(ci=np.floor((GL - GM_X0) / GM_D).astype(int).ravel(), ri=np.floor((GM_Y1 - GA) / GM_D).astype(int).ravel(),
                           r=rain.ravel())).groupby(["ci", "ri"]).r.agg(["mean", "min", "max"])
    assert ((gr["max"] - gr["min"]) < 1e-6).all(), "gridMET not constant within a native cell"
    df = pd.DataFrame(dict(ci=ci.ravel(), ri=ri.ravel(), d=d40.ravel()))
    g = df.groupby(["ci", "ri"]).agg(n=("d", "size"), nv=("d", "count"), d=("d", "mean")).join(gr["mean"].rename("r"), how="inner")
    full = g.n >= 0.9 * g.n.quantile(0.9)
    out = {}
    for lab, ok in (("main", full & (g.nv >= 0.5 * g.n)), ("valid90", full & (g.nv >= 0.9 * g.n))):
        c = g[ok]
        out[f"{lab}_n"] = len(c)
        out[f"{lab}_r"] = float(np.corrcoef(c.r, c.d)[0, 1])
    c = g[full & (g.nv >= 0.5 * g.n)].reset_index()
    out["spearman"] = float(c[["r", "d"]].corr("spearman").iloc[0, 1])
    # block bootstrap: 3 x 3-cell (~12 km) blocks, to respect spatial autocorrelation
    c["blk"] = (c.ci // 3).astype(str) + "_" + (c.ri // 3).astype(str)
    blocks = c.groupby("blk").indices; keys = list(blocks)
    rs = []
    for _ in range(2000):
        idx = np.concatenate([blocks[keys[k]] for k in rng.integers(0, len(keys), len(keys))])
        if np.std(c.r.values[idx]) > 0:
            rs.append(np.corrcoef(c.r.values[idx], c.d.values[idx])[0, 1])
    out["r_ci"] = tuple(np.percentile(rs, [2.5, 97.5]))
    lo, hi = bins
    out["dvv_low"] = float(c.d[c.r < lo].mean()) if (c.r < lo).any() else np.nan
    out["n_low"] = int((c.r < lo).sum())
    out["dvv_high"] = float(c.d[c.r >= hi].mean()) if (c.r >= hi).any() else np.nan
    out["n_high"] = int((c.r >= hi).sum())
    q1, q2 = np.quantile(c.r, [1 / 3, 2 / 3])
    out["terc_low"], out["terc_high"] = float(c.d[c.r <= q1].mean()), float(c.d[c.r >= q2].mean())
    out["terc_bounds"] = (float(q1), float(q2))
    out["rain_range"] = (float(c.r.min()), float(c.r.max()))
    # 8 km aggregation (2 x 2 native cells)
    c2 = c.assign(c2=c.ci // 2, r2=c.ri // 2).groupby(["c2", "r2"]).agg(d=("d", "mean"), r=("r", "mean"), k=("d", "size"))
    c2 = c2[c2.k == 4]
    out["agg8_n"], out["agg8_r"] = len(c2), float(np.corrcoef(c2.r, c2.d)[0, 1])
    out["box_median_d"] = float(np.nanmedian(d40))
    return out


def existing_stats(a, b, rain, ext, lon0, lat0, bins):
    """Exact re-run of the first SAR wetting-event figure (since retired): 0.01 deg cells, 4 km windows of the 40 m change."""
    d40 = b["vv_db"] - a["vv_db"]
    gx0, gx1, gy0, gy1 = ext; ny, nx = rain.shape
    tr = Transformer.from_crs(4326, int(a["epsg"]), always_xy=True)
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
    m = np.isfinite(blk); lo, hi = bins
    return dict(r=float(np.corrcoef(rain[m], blk[m])[0, 1]), n=int(m.sum()),
                low=float(np.nanmean(blk[m & (rain < lo)])) if (m & (rain < lo)).any() else np.nan,
                high=float(np.nanmean(blk[m & (rain >= hi)])))


def edge_trim(d, km=5.0, res=40.0):
    """Sensitivity: drop pixels within km of a swath edge / no-data stripe (edge noise floor and incidence effects)."""
    ok = uniform_filter(np.isfinite(d).astype(float), 25) >= 0.5        # 1 km smoothing: isolated invalid pixels are not edges
    return np.where(distance_transform_edt(ok) * res / 1e3 >= km, d, np.nan)


def change_map(a_db, b_db):
    lin = lambda z: 10 ** (z / 10)
    ok = np.isfinite(a_db) & np.isfinite(b_db)
    ratio = uniform_filter(np.where(ok, lin(b_db) / np.where(ok, lin(a_db), 1), 1.0), 5)      # 5 x 5 x 40 m = 200 m
    d = 10 * np.log10(ratio); d[~ok] = np.nan
    return d


# ------------------------------------------------------------------ analysis
rng = np.random.default_rng(42)
DATA, rows = {}, []
for site, c in SITES.items():
    P = c["prefix"]
    a, b = np.load(os.path.join(I, f"{P}s1_vv_{c['d0']}_60km_40m.npz")), np.load(os.path.join(I, f"{P}s1_vv_{c['d1']}_60km_40m.npz"))
    t0, t1 = pd.Timestamp(str(a["time"])), pd.Timestamp(str(b["time"]))
    assert str(a["item"])[:3] == str(b["item"])[:3] and int(a["epsg"]) == int(b["epsg"])
    assert all(float(a[k]) == float(b[k]) for k in ("x0", "x1", "y0", "y1")), "S1 grids differ"
    # gridMET days as in the existing extraction (12_extract_imagery.py); checked below against the station's hourly rain
    g0, g1 = (T(x) for x in c["rain"].split("_"))
    rain, ext, rain_file = gridmet_sum(site, g0, g1)
    d40 = b["vv_db"] - a["vv_db"]
    st = native_stats(d40, float(a["x0"]), float(a["y1"]), int(a["epsg"]), rain, ext, c["bins"], rng)
    # sensitivity: open water masked (gamma0 < -18 dB on either date: wind on reservoirs changes VV, not soil moisture)
    d40w = np.where((a["vv_db"] < -18) | (b["vv_db"] < -18), np.nan, d40)
    stw = native_stats(d40w, float(a["x0"]), float(a["y1"]), int(a["epsg"]), rain, ext, c["bins"], rng)
    st.update(water_masked_r=stw["main_r"], water_masked_n=stw["main_n"], water_frac=float(np.mean(np.isnan(d40w) & np.isfinite(d40))))
    ste = native_stats(edge_trim(d40), float(a["x0"]), float(a["y1"]), int(a["epsg"]), rain, ext, c["bins"], rng)
    st.update(edge5km_r=ste["main_r"], edge5km_n=ste["main_n"])
    ex = existing_stats(a, b, rain, ext, c["lon"], c["lat"], c["bins"])
    w0, w1 = T(c["ts"][0]), T(c["ts"][1])
    u = u_all[(u_all.wban == c["wban"]) & (u_all.time_utc > w0) & (u_all.time_utc <= w1 + H)].set_index("time_utc")
    u = u.reindex(pd.date_range(u.index.min(), u.index.max(), freq="h"))
    ev = ev_all[(ev_all.wban == c["wban"]) & (ev_all.t_we - H > w0) & (ev_all.t_ws - H < w1)].sort_values("t_start")
    s1 = one_per_pass(S1_ACQ[(S1_ACQ.wban == c["wban"])]); s1 = s1[(s1.time >= w0) & (s1.time < w1)]
    ni = one_per_pass(NI_ACQ[(NI_ACQ.wban == c["wban"])]); ni = ni[(ni.time >= w0) & (ni.time < w1)]
    inside = lambda ts: [t for t in ts for _, e in ev.iterrows() if e.t_ws - H <= t < e.t_we - H]
    lab = lambda x, y: float(u.precip[(u.index - H >= x) & (u.index <= y)].sum())
    sm_at = lambda t: float(u.sm5[u.index >= t.ceil("h")].iloc[0])      # the hour containing the acquisition
    pre3 = lambda t: float(u.precip[(u.index > t - 3 * H) & (u.index <= t.ceil("h"))].sum())
    dz = change_map(a["vv_db"], b["vv_db"])
    row = dict(site=site, s1_before=f"{t0:%d %b %Y %H:%M}", s1_after=f"{t1:%d %b %Y %H:%M}", s1_orbit=str(a["item"])[:3],
               s1_items=f"{a['item']} | {b['item']}", gridmet_days=f"{g0:%d %b} to {g1:%d %b} (= {g0 + 12 * H:%d %b %H:%M} to {g1 + 36 * H:%d %b %H:%M} UTC)",
               station_rain_s1_interval=lab(t0, t1), station_rain_gridmet_interval=lab(g0 + 12 * H, g1 + 36 * H),
               rain_3h_before_s1_after=pre3(t1), sm_before=sm_at(t0), sm_after=sm_at(t1),
               station_dvv_160m=float(np.nanmean(d40[748:752, 748:752])), frac_valid=float(np.isfinite(d40).mean()),
               dvv_p98_abs=float(np.nanpercentile(np.abs(dz), 98)), vv_p2=float(np.nanpercentile(a["vv_db"], 2)), vv_p98=float(np.nanpercentile(a["vv_db"], 98)),
               rain_max=float(np.nanmax(rain)),
               existing_r=ex["r"], existing_n=ex["n"], existing_low=ex["low"], existing_high=ex["high"],
               n_events=len(ev), events="; ".join(f"{e.t_start:%d %b} {e.rain_mm:.1f} mm, window {e.t_ws - H:%d %b %H:%M}-{e.t_we - H:%d %b %H:%M} ({e.window_h:.0f} h{', storm-truncated' if e.censored else ''})" for _, e in ev.iterrows()),
               s1_in_windows="; ".join(f"{t:%d %b %H:%M}{'' if usable(c['wban'], 'Sentinel-1', t) else ' (INVALID at station)'}" for t in inside(s1.time)) or "none",
               nisar_in_windows="; ".join(f"{t:%d %b %H:%M}{'' if usable(c['wban'], 'NISAR', t) else ' (INVALID at station)'}" for t in inside(ni.time)) or "none",
               s1_all="; ".join(f"{t:%d %b %H:%M} (orbit {o})" for t, o in zip(s1.time, s1.rel_orbit)),
               nisar_all="; ".join(f"{t:%d %b %H:%M} (track {k}{d})" for t, k, d in zip(ni.time, ni.track, ni.direction)),
               **{k: v for k, v in st.items()})
    rows.append(row)
    DATA[site] = dict(a=a, b=b, dz=dz, rain=rain, ext=ext, u=u, ev=ev, s1=s1, ni=ni, t0=t0, t1=t1, g0=g0, g1=g1, st=st, row=row)
stats = pd.DataFrame(rows).set_index("site")
stats.T.to_csv(os.path.join(HERE, "generated", "case_study_stats.csv"))
pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 140)
print(stats.T.to_string())


# ------------------------------------------------------------------ figures
plt.rcParams.update({"font.family": "Calibri", "svg.fonttype": "none", "axes.edgecolor": GREY, "axes.labelcolor": INK,
                     "xtick.color": INK, "ytick.color": INK, "savefig.facecolor": "white"})


def km_extent(z):
    return [float(z["x0"] - z["station_x"]) / 1e3, float(z["x1"] - z["station_x"]) / 1e3,
            float(z["y0"] - z["station_y"]) / 1e3, float(z["y1"] - z["station_y"]) / 1e3]


def km_extent_gm(ext, lon0, lat0):
    k = 111.32 * np.cos(np.deg2rad(lat0)); gx0, gx1, gy0, gy1 = ext
    return [(gx0 - lon0) * k, (gx1 - lon0) * k, (gy0 - lat0) * 111.32, (gy1 - lat0) * 111.32]


def dm(t):
    return f"{t.day} {t:%b}"


def map_panel(fig, rect, arr, ext, cmap, lims, title, unit, cb_ext, dark, S):
    ax = fig.add_axes(rect)
    cm = plt.get_cmap(cmap).copy(); cm.set_bad("#C9CED3")
    im = ax.imshow(arr, extent=ext, cmap=cm, vmin=lims[0], vmax=lims[1], interpolation="nearest" if cmap == "Blues" else "antialiased")
    ax.plot(0, 0, marker="^", ms=S["tri"], mfc="#FFD400", mec=INK, mew=0.9, zorder=5)
    ax.set_xlim(-30, 30); ax.set_ylim(-30, 30); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
    ink = "white" if dark else INK
    halo = [pe.withStroke(linewidth=2.2, foreground=INK if dark else "white")]
    ax.plot([-27, -17], [-26.5, -26.5], color=ink, lw=S["lw_bar"], solid_capstyle="butt", path_effects=halo)
    ax.text(-22, -25.3, "10 km", color=ink, fontsize=S["f_map"], ha="center", va="bottom", path_effects=halo)
    ax.annotate("", xy=(25, -16.5), xytext=(25, -27.5), arrowprops=dict(arrowstyle="-|>", color=ink, lw=1.1, mutation_scale=S["f_map"] + 2,
                                                                         path_effects=halo))
    ax.text(25, -16, "N", color=ink, fontsize=S["f_map"] + 1, fontweight="bold", ha="center", va="bottom", path_effects=halo)
    ax.set_title(title.replace(" | ", " " if S["one_line"] else "\n"), fontsize=S["f_title"], loc="left", pad=3, color=INK,
                 linespacing=1.0)
    cax = fig.add_axes([rect[0] + rect[2] + 0.004, rect[1] + 0.10 * rect[3], S["cb_w"], 0.80 * rect[3]])
    cb = fig.colorbar(im, cax=cax, extend=cb_ext); cb.ax.tick_params(labelsize=S["f_tick"], length=2, pad=1)
    if unit == "γ⁰ (dB)":
        cb.set_ticks(np.arange(np.ceil(lims[0] / 4) * 4, lims[1] + 0.1, 4))
    cb.set_label(unit, fontsize=S["f_tick"], labelpad=2)
    cb.outline.set_visible(False)
    return ax


def timeseries(fig, rect_r, rect_s, D, c, S, hourly, title, pair, pair_col, pair_label):
    u, ev = D["u"], D["ev"]
    w0, w1 = T(c["ts"][0]), T(c["ts"][1])
    axr = fig.add_axes(rect_r); axs = fig.add_axes(rect_s, sharex=axr)
    if hourly:
        axr.bar(u.index - H, u.precip.fillna(0), width=1 / 24, align="edge", color=RAIN_COL, lw=0, zorder=3)
        axr.set_ylabel("rain\n(mm/h)", fontsize=S["f_lab"])
    else:   # 6-hourly totals for projection (hour-end records grouped into 00-06, 06-12, ... UTC)
        p = u.precip.fillna(0); r6 = p.groupby((p.index - H).floor("6h")).sum()
        assert abs(r6.sum() - p.sum()) < 1e-9
        axr.bar(r6.index, r6.values, width=0.25, align="edge", color=RAIN_COL, lw=0, zorder=3)
        axr.set_ylabel("rain\n(mm/6 h)", fontsize=S["f_lab"])
    axr.set_ylim(0, axr.get_ylim()[1] * 1.05)
    axr.tick_params(labelbottom=False, labelsize=S["f_tick"])
    axs.plot(u.index - HALF, u.sm5, color=INK, lw=S["lw_sm"], zorder=5)        # NaN hours stay as gaps
    for _, e in ev.iterrows():
        for ax_ in (axr, axs):
            ax_.axvspan(e.t_ws - H, e.t_we - H, color=PALE, lw=0, zorder=0)
    n_bad = 0
    for sensor, col, lw, ls in (("Sentinel-1", S1_COL, S["lw_look"] + 0.6, "-"), ("NISAR", NI_COL, S["lw_look"], (0, (4, 2)))):
        for t in D["s1" if sensor == "Sentinel-1" else "ni"].time:
            ok = usable(c["wban"], sensor, t)
            n_bad += not ok
            for ax_ in (axr, axs):   # flagged-invalid passes: faint line + cross, so they are not read as observations
                ax_.axvline(t, color=col, lw=lw, ls=ls, zorder=4, alpha=1.0 if ok else 0.3)
            if not ok:
                axs.plot(t, 0.5, marker="X", ms=S["tri"] + 1, color=col, mec="white", mew=0.8, transform=axs.get_xaxis_transform(), zorder=7)
    for t in pair:
        axs.plot(t, 1.0, marker="v", ms=S["tri"], color=pair_col, mec="white", mew=0.6, transform=axs.get_xaxis_transform(),
                 clip_on=False, zorder=7)
    axs.set_ylabel("5 cm soil moisture\n(m³/m³)", fontsize=S["f_lab"]); axs.tick_params(labelsize=S["f_tick"])
    axs.set_xlim(w0, w1)
    axs.xaxis.set_major_locator(mdates.DayLocator(interval=2)); axs.xaxis.set_minor_locator(mdates.DayLocator())
    axs.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    axs.set_xlabel(f"{w0:%Y} (UTC)", fontsize=S["f_tick"], color=GREY, labelpad=1)
    for ax_ in (axr, axs):
        ax_.grid(axis="y", color=LIGHT, lw=0.6); ax_.set_axisbelow(True)
        ax_.spines["top"].set_visible(False); ax_.spines["right"].set_visible(False)
    axr.set_title(title, fontsize=S["f_title"], loc="left", pad=3, color=INK)
    h = [Line2D([], [], color=INK, lw=S["lw_sm"], label="USCRN 5 cm soil moisture"),
         Patch(fc=PALE, ec="none", label="wetting window"),
         Line2D([], [], color=S1_COL, lw=S["lw_look"] + 0.6, label="Sentinel-1 acquisition"),
         Line2D([], [], color=NI_COL, lw=S["lw_look"], ls=(0, (4, 2)), label="NISAR acquisition"),
         Line2D([], [], color=pair_col, marker="v", ls="none", ms=S["tri"], label=pair_label)]
    if n_bad:
        h.append(Line2D([], [], color=GREY, marker="X", ls="none", ms=S["tri"] + 1, label="pass flagged invalid at station"))
    axs.legend(handles=h, loc="upper left", fontsize=S["f_leg"], ncol=len(h) if len(h) <= 5 else 3, frameon=True, framealpha=0.94, edgecolor="none",
               handlelength=1.8, borderaxespad=0.3, columnspacing=1.2)
    lo, hi = axs.get_ylim(); axs.set_ylim(lo, hi + (hi - lo) * 0.30)


STYLES = {
    "scientific": dict(size=(11.0, 5.6), one_line=True, f_title=8.8, f_tick=7.2, f_lab=7.6, f_map=7.2, f_leg=7.2, f_foot=7.4,
                       tri=7, cb_w=0.008, lw_bar=1.6, lw_sm=1.3, lw_look=1.3, map_w=0.19, map_y=0.505, ts=(0.06, 0.94),
                       rain_h=0.085, sm_h=0.22, dpi=300),
    "presentation": dict(size=(13.333, 7.5), one_line=False, f_title=13, f_tick=11, f_lab=12, f_map=11, f_leg=11.5, f_foot=12.5,
                         tri=10, cb_w=0.009, lw_bar=2.2, lw_sm=2.0, lw_look=1.8, map_w=0.205, map_y=0.495, ts=(0.07, 0.975),
                         rain_h=0.095, sm_h=0.235, dpi=400),
}


def footer_text(st, bins, sensor="ΔVV"):
    lo, hi = bins
    lo_txt = (f"{st['dvv_low']:+.1f} dB where rain < {lo} mm (n = {st['n_low']})" if st["n_low"]
              else f"no cell received < {lo} mm (rain {st['rain_range'][0]:.0f}–{st['rain_range'][1]:.0f} mm everywhere)")
    return (f"{sensor} vs gridMET rain, native 4 km cells: r = {st['main_r']:.2f} (95 % CI {st['r_ci'][0]:.2f} to {st['r_ci'][1]:.2f}, "
            f"n = {st['main_n']}).  Mean {sensor} {st['dvv_high']:+.1f} dB where rain ≥ {hi} mm (n = {st['n_high']}); {lo_txt}.")


def five_panel(site, ver, M, out_name, pair, pair_col, pair_label, foot, source):
    """M: list of 4 (array, extent, cmap, lims, title, unit, cb_ext, dark)."""
    c, D, S = SITES[site], DATA[site], STYLES[ver]
    fig = plt.figure(figsize=S["size"])
    W = S["map_w"]; Hh = W * S["size"][0] / S["size"][1]
    for k, m in enumerate(M):
        map_panel(fig, [0.005 + k * 0.25, S["map_y"], W, Hh], *m, S)
    x0, x1 = S["ts"]
    top = S["map_y"] - (0.075 if ver == "scientific" else 0.085)
    sm_bottom = top - S["rain_h"] - 0.012 - S["sm_h"]
    timeseries(fig, [x0, top - S["rain_h"], x1 - x0, S["rain_h"]], [x0, sm_bottom, x1 - x0, S["sm_h"]],
               D, c, S, hourly=(ver == "scientific"),
               title=f"e  USCRN {c['name']}: rainfall, soil moisture and satellite acquisitions",
               pair=pair, pair_col=pair_col, pair_label=pair_label)
    fy = sm_bottom - (0.075 if ver == "scientific" else 0.085)     # below the date labels and the "(UTC)" axis label
    fig.text(0.005, fy, foot, fontsize=S["f_foot"], color=INK, ha="left", va="top")
    if ver == "scientific":
        fig.text(0.005, fy - 0.04, source, fontsize=S["f_foot"] - 0.8, color=GREY, ha="left", va="top", linespacing=1.15)
    if out_name in DECK:
        fig.savefig(os.path.join(HERE, f"{DECK[out_name]}.png"), dpi=S["dpi"], bbox_inches="tight", pad_inches=0.05)
    if SAVE_ALL:
        os.makedirs(OUT, exist_ok=True)
        fig.savefig(os.path.join(OUT, f"{out_name}.png"), dpi=S["dpi"], bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)


for site, c in SITES.items():
    D = DATA[site]
    db, da = dm(D["t0"]), dm(D["t1"])
    ext_s1, ext_g = km_extent(D["a"]), km_extent_gm(D["ext"], c["lon"], c["lat"])
    M = [(D["a"]["vv_db"], ext_s1, "gray", VV_LIM, f"a  Sentinel-1 VV, {db} | (before rain)", "γ⁰ (dB)", "both", True),
         (D["b"]["vv_db"], ext_s1, "gray", VV_LIM, f"b  Sentinel-1 VV, {da} | (after rain)", "γ⁰ (dB)", "both", True),
         (D["dz"], ext_s1, "RdBu_r", (-DVV_LIM, DVV_LIM), f"c  Change, | {da} − {db}", "ΔVV (dB)", "both", False),
         (D["rain"], ext_g, "Blues", (0, RAIN_MAX), f"d  Rain, {dm(D['g0'])}–{dm(D['g1'] + pd.Timedelta(days=1))} | (gridMET, 12 UTC days)",
          "rain (mm)", "max", False)]
    src = (f"Sentinel-1D RTC γ⁰ VV, relative orbit {int(D['s1'].set_index('time').rel_orbit.get(D['t1'].floor('s'), D['s1'].rel_orbit.iloc[0]))}, "
           f"{D['t0']:%d %b %H:%M} and {D['t1']:%d %b %H:%M} UTC (Planetary Computer); 40 m; map c = 200 m boxcar of the linear ratio. "
           f"gridMET pr summed {D['g0'] + 12 * H:%d %b %H:%M} to {D['g1'] + 36 * H:%d %b %H:%M} UTC, 4 km cells.\n"
           f"USCRN hourly02, WBAN {c['wban']} (values at hour end). Grey = no data. North arrow = UTM grid north (≈ 1° from true north). "
           "Acquisition lines: every Sentinel-1 and NISAR pass over the station (data/processed/acq_s1.csv, acq_nisar.csv).")
    for ver in STYLES:
        five_panel(site, ver, M, f"{site}_{ver}", (D["t0"], D["t1"]), S1_COL, "Sentinel-1 pair in maps a–c",
                   footer_text(D["st"], c["bins"]), src)
print("main figures written")


# ------------------------------------------------------------------ NISAR L-band supplementary (same-track GCOV pairs)
nrows = []
_ni = [np.load(p)["hh_db"] for s_, c_ in SITES.items() for p in (os.path.join(NI_DIR, f"{s_}_nisar_{d}_60km_40m.npz") for d in c_["nisar"]) if os.path.exists(p)]
NI_LIM = (2 * np.floor(min(np.nanpercentile(z, 2) for z in _ni) / 2), 2 * np.ceil(max(np.nanpercentile(z, 98) for z in _ni) / 2)) if _ni else (-20, -4)
print("NISAR HH display range (shared, 2nd-98th percentile over all images):", NI_LIM)
match = pd.read_csv(os.path.join(PROC, "nisar_matched.csv"), parse_dates=["time"])
for site, c in list(SITES.items()):
    D = DATA[site]
    fa, fb = (os.path.join(NI_DIR, f"{site}_nisar_{d}_60km_40m.npz") for d in c["nisar"])
    if not (os.path.exists(fa) and os.path.exists(fb)):
        print("NISAR pair missing for", site); continue
    na, nb = np.load(fa), np.load(fb)
    assert int(na["epsg"]) == int(nb["epsg"]) and all(abs(float(na[k]) - float(nb[k])) < 1e-6 for k in ("x0", "x1", "y0", "y1")), "NISAR grids differ"
    ta = pd.Timestamp(eval(str(na["meta"]))["zeroDopplerStartTime"][:19], tz="UTC")
    tb = pd.Timestamp(eval(str(nb["meta"]))["zeroDopplerStartTime"][:19], tz="UTC")
    g0, g1 = gm_days(ta, tb)
    rain_n, ext_n, _ = gridmet_sum(site, g0, g1)
    pol = "hh"
    dzn = change_map(na[f"{pol}_db"], nb[f"{pol}_db"])
    d40n = nb[f"{pol}_db"] - na[f"{pol}_db"]
    stn = native_stats(d40n, float(na["x0"]), float(na["y1"]), int(na["epsg"]), rain_n, ext_n, c["bins"], rng)
    stn_e = native_stats(edge_trim(d40n), float(na["x0"]), float(na["y1"]), int(na["epsg"]), rain_n, ext_n, c["bins"], rng)
    stn.update(edge5km_r=stn_e["main_r"], edge5km_n=stn_e["main_n"], edge5km_ci=stn_e["r_ci"])
    extra = {}
    for p in ("hv", "vv"):     # other polarisations as a check on vegetation / surface change (HV = volume scattering)
        if f"{p}_db" in na.files and f"{p}_db" in nb.files:
            sp = native_stats(nb[f"{p}_db"] - na[f"{p}_db"], float(na["x0"]), float(na["y1"]), int(na["epsg"]), rain_n, ext_n, c["bins"], rng)
            extra.update({f"d{p}_r": sp["main_r"], f"d{p}_box_median": sp["box_median_d"], f"d{p}_low": sp["dvv_low"], f"d{p}_high": sp["dvv_high"]})
    u = D["u"]
    sm_at = lambda t: float(u_all[(u_all.wban == c["wban"]) & (u_all.time_utc >= t.ceil("h"))].sm5.iloc[0])
    lab_rain = lambda x, y: float(u_all[(u_all.wban == c["wban"]) & (u_all.time_utc - H >= x) & (u_all.time_utc <= y)].precip.sum())
    mm = match[(match.wban == c["wban"]) & (match.time.dt.floor("min").isin([ta.floor("min"), tb.floor("min")]))]
    sme2 = {f"{t:%d %b}": (f"{r.sm_3x3_rec:.3f}" if np.isfinite(r.sm_3x3_rec) else "no recommended retrieval") for t, r in zip(mm.time, mm.itertuples())}
    nrows.append(dict(site=site, granules=f"{na['granule']} | {nb['granule']}", modes=f"{str(na['granule']).split('_')[8]}_{str(na['granule']).split('_')[9]} -> "
                      f"{str(nb['granule']).split('_')[8]}_{str(nb['granule']).split('_')[9]}", pols=str(na["pols"]) + " / " + str(nb["pols"]),
                      t_before=f"{ta:%d %b %H:%M}", t_after=f"{tb:%d %b %H:%M}", valid_before=float(na["frac_valid"]), valid_after=float(nb["frac_valid"]),
                      sm_before=sm_at(ta), sm_after=sm_at(tb), rain_station=lab_rain(ta, tb), rain_3h_before_after=lab_rain(tb - 3 * H, tb.ceil("h")),
                      gridmet_days=f"{g0:%d %b}–{g1:%d %b}", station_dhh_160m=float(np.nanmean(d40n[748:752, 748:752])),
                      sme2_station=str(sme2), **extra, **{f"n_{k}": v for k, v in stn.items()}))
    ext_n_km = km_extent(na); ext_gn = km_extent_gm(ext_n, c["lon"], c["lat"])
    M = [(na["hh_db"], ext_n_km, "gray", NI_LIM, f"a  NISAR L-band HH, {dm(ta)} | (before rain)", "γ⁰ (dB)", "both", True),
         (nb["hh_db"], ext_n_km, "gray", NI_LIM, f"b  NISAR L-band HH, {dm(tb)} | (after rain)", "γ⁰ (dB)", "both", True),
         (dzn, ext_n_km, "RdBu_r", (-DVV_LIM, DVV_LIM), f"c  Change, | {dm(tb)} − {dm(ta)}", "ΔHH (dB)", "both", False),
         (rain_n, ext_gn, "Blues", (0, RAIN_MAX), f"d  Rain, {dm(g0)}–{dm(g1 + pd.Timedelta(days=1))} | (gridMET, 12 UTC days)", "rain (mm)", "max", False)]
    mode_note = ("" if nrows[-1]["modes"].split(" -> ")[0] == nrows[-1]["modes"].split(" -> ")[1]
                 else f" Modes differ ({nrows[-1]['modes']}): 20 vs 40 MHz bandwidth; both RTC γ⁰ at 20 m, compared after 40 m averaging.")
    src = (f"NISAR L2 GCOV PROVISIONAL (product 1.0.11), track {str(na['granule']).split('_')[5]}{str(na['granule']).split('_')[6]}, frame "
           f"{str(na['granule']).split('_')[7]}: same geometry. RTC γ⁰ HH, {int(na['native_spacing_m'])} m and {int(nb['native_spacing_m'])} m → 40 m mean of linear values; mask 0/255 removed. "
           f"No noise, Faraday-rotation or RFI correction in the product.{mode_note}\n"
           f"gridMET pr {g0 + 12 * H:%d %b %H:%M} to {g1 + 36 * H:%d %b %H:%M} UTC. Not comparable in dB with Sentinel-1 C-band VV "
           f"(different frequency, polarisation and geometry). USCRN WBAN {c['wban']}.")
    c_ts = dict(c); c_ts["ts"] = (f"{(ta - pd.Timedelta(days=2)):%Y-%m-%d}", f"{(tb + pd.Timedelta(days=3)):%Y-%m-%d}")
    w0, w1 = T(c_ts["ts"][0]), T(c_ts["ts"][1])
    Dn = dict(D)
    uu = u_all[(u_all.wban == c["wban"]) & (u_all.time_utc > w0) & (u_all.time_utc <= w1 + H)].set_index("time_utc")
    Dn["u"] = uu.reindex(pd.date_range(uu.index.min(), uu.index.max(), freq="h"))
    Dn["ev"] = ev_all[(ev_all.wban == c["wban"]) & (ev_all.t_we - H > w0) & (ev_all.t_ws - H < w1)]
    s1 = one_per_pass(S1_ACQ[S1_ACQ.wban == c["wban"]]); Dn["s1"] = s1[(s1.time >= w0) & (s1.time < w1)]
    ni = one_per_pass(NI_ACQ[NI_ACQ.wban == c["wban"]]); Dn["ni"] = ni[(ni.time >= w0) & (ni.time < w1)]
    DATA[site + "_nisar"] = Dn; SITES[site + "_nisar"] = c_ts
    bad = [f"{t:%d %b}" for t in (ta, tb) if not usable(c["wban"], "NISAR", t)]
    bad_note = (f"\nStation pixel flagged invalid (mask 0) on {' and '.join(bad)}: the scene change is shown, "
                "but NISAR did not observe the probe site." if bad else "")
    for ver in STYLES:
        five_panel(site + "_nisar", ver, M, f"{site}_nisar_{ver}", (ta, tb), NI_COL, "NISAR pair in maps a–c",
                   footer_text(stn, c["bins"], "ΔHH") + bad_note, src)
if not nrows:
    sys.exit("no NISAR pairs extracted yet: run extract_nisar_gcov.py")
nis = pd.DataFrame(nrows).set_index("site")
nis.T.to_csv(os.path.join(HERE, "generated", "case_study_nisar_stats.csv"))
print(nis.T.to_string())
