"""Where is the need? CONUS maps from Google Earth Engine, calibrated and checked against USCRN ground truth.

(a) Sentinel-1 revisit, 2026 warm season: COPERNICUS/S1_GRD (IW), distinct acquisition days per 0.1 deg cell.
(b) Wetting events per warm season: storm onsets from gridMET daily rain (IDAHO_EPSCOR/GRIDMET; onset = day with
    >= 5 mm after a day with < 5 mm, mirroring the event rule's 5 mm storm total), averaged over 2025 and 2026 and
    converted to wetting events with one factor fitted at the USCRN stations (events per onset).
(c) Events missed per season by Sentinel-1 = events x (1 - c(R_S1)), where c(R) = E[min(1, W/R)] is the capture of a
    regular sampler, using the 3,340 USCRN event windows W (the analytic model checked in step 01).
(d) Extra events ARMO would capture per season = events x (c(R_comb) - c(R_S1)), R_comb = 1 / (1/R_S1 + 1/R_ARMO),
    shown where cropland (MODIS MCD12Q1) covers >= 25 % of the cell.
Checks against ground truth: GEE revisit vs the Planetary Computer record at the stations (step 02), and gridMET onsets
vs USCRN wetting events per station-season. Outputs: data/processed/need_grid.npz, need_stations.csv, need_summary.csv,
figures/figS14_need_maps_report.png
"""
import os
import numpy as np
import pandas as pd
import ee
import matplotlib.pyplot as plt
import geopandas as gpd
from matplotlib.colors import BoundaryNorm
from common import PROC, RAW, FIG
import figstyle

ee.Initialize(project=os.environ.get("EE_PROJECT", "my-ee-project-ntu-512914"))
X0, Y0, DX, NX, NY = -125.0, 50.0, 0.1, 590, 260          # 0.1 deg grid over CONUS
GRID = dict(dimensions=dict(width=NX, height=NY), crsCode="EPSG:4326",
            affineTransform=dict(scaleX=DX, shearX=0, translateX=X0, shearY=0, scaleY=-DX, translateY=Y0))
SEASONS = {2025: ("2025-04-01", "2025-11-01"), 2026: ("2026-04-01", "2026-10-27")}   # gridMET 2026 ends 26 Oct
S1_SEASON = ("2026-04-01", "2026-11-01")
R_ARMO = 1.42                                               # design D mean revisit (orbit simulation, step 06)
CONUS = ee.FeatureCollection("TIGER/2018/States").filter(
    ee.Filter.inList("STUSPS", ["AK", "HI", "PR", "VI", "GU", "MP", "AS"]).Not())
MASK = ee.Image.constant(1).clip(CONUS.geometry()).mask()


def pixels(img, nx_tiles=6, ny_tiles=2):
    """Fetch the 0.1 deg CONUS grid in tiles (whole-CONUS requests time out for the Sentinel-1 reduction)."""
    out = np.full((NY, NX), np.nan)
    xs = np.linspace(0, NX, nx_tiles + 1).astype(int); ys = np.linspace(0, NY, ny_tiles + 1).astype(int)
    for i in range(ny_tiles):
        for j in range(nx_tiles):
            g = dict(dimensions=dict(width=int(xs[j + 1] - xs[j]), height=int(ys[i + 1] - ys[i])), crsCode="EPSG:4326",
                     affineTransform=dict(scaleX=DX, shearX=0, translateX=X0 + xs[j] * DX, shearY=0, scaleY=-DX,
                                          translateY=Y0 - ys[i] * DX))
            for k in range(3):
                try:
                    a = ee.data.computePixels(dict(expression=img.updateMask(MASK), fileFormat="NUMPY_NDARRAY", grid=g))
                    break
                except ee.EEException as e:
                    print("retry", i, j, e, flush=True)
            a = np.array(a[a.dtype.names[0]], dtype=float) if a.dtype.names else np.array(a, dtype=float)
            out[ys[i]:ys[i + 1], xs[j]:xs[j + 1]] = a
    return out


def s1_days():
    c = ee.ImageCollection("COPERNICUS/S1_GRD").filterDate(*S1_SEASON).filter(ee.Filter.eq("instrumentMode", "IW")) \
        .filterBounds(CONUS.geometry().bounds())
    doy = c.map(lambda im: ee.Image.constant(ee.Number.parse(im.date().format("D"))).toInt16()
                .updateMask(im.select("angle").mask()).rename("doy"))
    return doy.reduce(ee.Reducer.countDistinct())


def onsets(t0, t1):
    g = ee.ImageCollection("IDAHO_EPSCOR/GRIDMET").filterDate(t0, t1).select("pr").sort("system:time_start")
    lst = g.toList(400); n = g.size()
    on = ee.List.sequence(1, n.subtract(1)).map(
        lambda i: ee.Image(lst.get(i)).gte(5).And(ee.Image(lst.get(ee.Number(i).subtract(1))).lt(5)).toInt())
    return ee.ImageCollection.fromImages(on).sum().rename("onsets")


def cropland():
    """Cropland fraction from MODIS MCD12Q1 v061 (2024, 500 m, IGBP class 12 croplands; class 14 mosaic counted as half).
    The 10 m USDA CDL 2025 exceeds Earth Engine's interactive pixel limits at CONUS scale."""
    lc = ee.Image("MODIS/061/MCD12Q1/2024_01_01").select("LC_Type1")   # 2025 image is incomplete over CONUS
    return lc.eq(12).add(lc.eq(14).multiply(0.5)).rename("crop")


def conus_mask():
    import shapely
    states = gpd.read_file(os.path.join(RAW, "naturalearth", "states", "ne_50m_admin_1_states_provinces.shp"))
    geom = states[(states.iso_a2 == "US") & ~states.name.isin(["Alaska", "Hawaii"])].union_all()
    xx, yy = np.meshgrid(X0 + (np.arange(NX) + 0.5) * DX, Y0 - (np.arange(NY) + 0.5) * DX)
    return shapely.contains_xy(geom, xx, yy)


def capture(R, W):
    """E[min(1, W/R)] for an array of revisits R (days) and USCRN windows W (days)."""
    R = np.asarray(R, float)
    out = np.full(R.shape, np.nan)
    ok = np.isfinite(R) & (R > 0)
    Ws = np.sort(W); cw = np.concatenate([[0], np.cumsum(Ws)])
    k = np.searchsorted(Ws, R[ok])                        # windows shorter than R contribute W/R, longer ones 1
    out[ok] = (cw[k] / R[ok] + (Ws.size - k)) / Ws.size
    return out


def main():
    f = os.path.join(PROC, "need_grid.npz")
    st = pd.read_csv(os.path.join(PROC, "station_seasons.csv"))
    stn = st[st.included].drop_duplicates("wban")[["wban", "lat", "lon"]]
    if not os.path.exists(f):
        part = {}
        for name, fn in [("days", lambda: s1_days().rename("days")), ("on25", lambda: onsets(*SEASONS[2025])),
                         ("on26", lambda: onsets(*SEASONS[2026])),
                         ("crop", lambda: cropland().reduceResolution(ee.Reducer.mean(), maxPixels=4096)
                          .reproject(crs="EPSG:4326", scale=5000))]:
            fp = os.path.join(PROC, f"need_{name}.npy")
            if not os.path.exists(fp):
                np.save(fp, pixels(fn()))
            part[name] = np.load(fp)
        np.savez(f, **part)
    fs = os.path.join(PROC, "need_stations.csv")
    if not os.path.exists(fs):   # station values = the 0.1 deg cell containing each station
        z0 = np.load(f)
        ci = np.clip(((stn.lon - X0) / DX).astype(int), 0, NX - 1); ri = np.clip(((Y0 - stn.lat) / DX).astype(int), 0, NY - 1)
        pd.DataFrame(dict(wban=stn.wban, days=z0["days"][ri, ci], on25=z0["on25"][ri, ci], on26=z0["on26"][ri, ci],
                          crop=z0["crop"][ri, ci])).to_csv(fs, index=False)
    z = np.load(f)
    us = conus_mask()                                  # rasterised state outlines (the EE mask is not kept by every layer)
    days = np.where(us, z["days"], np.nan)
    on = np.where(us, (z["on25"] + z["on26"]) / 2, np.nan); crop = np.where(us, z["crop"], np.nan)
    # ground-truth calibration: USCRN wetting events per station-season vs gridMET onsets
    ev = pd.read_csv(os.path.join(PROC, "events.csv"))
    ns = pd.read_csv(os.path.join(PROC, "need_stations.csv"))
    cnt = ev.groupby(["wban", "season"]).size().rename("events").reset_index()
    inc = st[st.included][["wban", "season"]]
    cnt = inc.merge(cnt, how="left").fillna({"events": 0})
    m = cnt.merge(ns, on="wban")
    m["onsets"] = np.where(m.season == 2025, m.on25, m.on26)
    m = m.dropna(subset=["onsets"])
    k = m.events.sum() / m.onsets.sum()                    # events per onset (pooled ratio)
    r_on = np.corrcoef(m.onsets, m.events)[0, 1]
    # revisit check: GEE distinct S1 days vs Planetary Computer acquisitions at the stations (2026 season)
    s1 = pd.read_csv(os.path.join(PROC, "acq_s1.csv"), parse_dates=["time"])
    s1 = s1[(s1.time >= "2026-04-01") & (s1.time < "2026-11-01")]
    pc = s1.assign(d=s1.time.dt.date).groupby("wban").d.nunique().rename("pc_days")
    chk = ns.set_index("wban").join(pc, how="inner")
    r_days = np.corrcoef(chk.days, chk.pc_days)[0, 1]
    # maps
    W = ev.window_h.to_numpy() / 24
    season_d = 214.0
    R_s1 = np.where(days > 0, season_d / days, np.nan)
    E = k * on
    c_s1 = capture(R_s1, W)
    R_comb = 1 / (1 / R_s1 + 1 / R_ARMO)
    c_comb = capture(R_comb, W)
    missed = E * (1 - c_s1)
    gain = E * (c_comb - c_s1)
    cropm = crop >= 0.25
    v = np.isfinite(R_s1) & np.isfinite(E)
    summ = dict(n_stations=len(chk), r_days_gee_vs_pc=r_days, gee_days_median=chk.days.median(), pc_days_median=chk.pc_days.median(),
                k_events_per_onset=k, r_onsets_events=r_on, n_station_seasons=len(m),
                conus_R_s1_median=np.nanmedian(R_s1[v]), conus_events_median=np.nanmedian(E[v]),
                conus_capture_s1_median=np.nanmedian(c_s1[v]), conus_missed_median=np.nanmedian(missed[v]),
                conus_capture_comb_median=np.nanmedian(c_comb[v]), conus_gain_median=np.nanmedian(gain[v]),
                crop_cells=int((cropm & v).sum()), crop_missed_median=np.nanmedian(missed[cropm & v]),
                crop_gain_median=np.nanmedian(gain[cropm & v]), frac_cells_R_gt_5=np.mean(R_s1[v] > 5))
    pd.DataFrame([summ]).to_csv(os.path.join(PROC, "need_summary.csv"), index=False)
    print(pd.Series(summ).round(3).to_string())
    figure(R_s1, E, missed, np.where(cropm, gain, np.nan), stn, summ)


def figure(R, E, missed, gain, stn, sm):
    import textwrap
    figstyle.apply()
    states = gpd.read_file(os.path.join(RAW, "naturalearth", "states", "ne_50m_admin_1_states_provinces.shp"))
    states = states[(states.iso_a2 == "US") & ~states.name.isin(["Alaska", "Hawaii"])]
    ext = [X0, X0 + NX * DX, Y0 - NY * DX, Y0]
    W_IN, H_IN = 7.2, 5.0
    ASP = 1 / np.cos(np.deg2rad(37.0))                 # same latitude correction geopandas applies
    fig = plt.figure(figsize=(W_IN, H_IN))
    caps = [f"Distinct Sentinel-1 acquisition days, 1 Apr–31 Oct 2026 (Earth Engine COPERNICUS/S1_GRD), as mean revisit. "
            f"Agrees with our station record (r = {sm['r_days_gee_vs_pc']:.2f}). Median cell {sm['conus_R_s1_median']:.1f} d.",
            f"gridMET storm onsets (≥ 5 mm after a drier day), mean of 2025–26, × {sm['k_events_per_onset']:.2f} wetting events "
            f"per onset fitted at USCRN (r = {sm['r_onsets_events']:.2f}). Dots: the 120 USCRN stations.",
            f"Events × (1 − capture); capture = E[min(1, W/R)] from the 3,340 USCRN event windows W at each cell's "
            f"revisit R. Median cell {sm['conus_missed_median']:.0f} missed per season.",
            f"Events gained when a 1.4-day ARMO is added to Sentinel-1, on cells with ≥ 25 % cropland (MODIS MCD12Q1 2024). "
            f"Median {sm['crop_gain_median']:.0f} per season."]
    panels = [(R, "a  Sentinel-1 revisit, 2026 warm season (days)", "Blues", [2, 3, 4, 5, 6, 8, 10, 12, 16]),
              (E, "b  Wetting events per warm season (gridMET, USCRN-calibrated)", "Greens", [4, 6, 8, 10, 12, 14, 16, 18, 20]),
              (missed, "c  Wetting events per season missed by Sentinel-1", "Oranges", [2, 4, 6, 8, 10, 12, 14]),
              (gain, "d  Extra events per season with ARMO, on cropland (≥ 25 %)", "Purples", [1, 2, 3, 4, 5, 6, 7, 8])]
    units = ["days", "events per season", "events per season", "events per season"]
    bar_deg = 500 / (111.32 * np.cos(np.deg2rad(37.0)))   # 500 km in longitude, true at 37° N (the aspect latitude)
    mw = 0.405                                          # map width (figure fraction); CONUS box is 58.5 x 26 deg
    mh = mw * W_IN * (26 * ASP / 58.5) / H_IN
    for k, ((arr, title, cmap, bounds), cap) in enumerate(zip(panels, caps)):
        col, row = k % 2, k // 2
        x0 = 0.02 + col * 0.50
        y0 = 0.575 - row * 0.49                         # bottom of the map
        ax = fig.add_axes([x0, y0, mw, mh])
        cm = plt.get_cmap(cmap, len(bounds) + 1)
        im = ax.imshow(arr, extent=ext, origin="upper", cmap=cm, norm=BoundaryNorm(bounds, cm.N, extend="both"),
                       interpolation="nearest")
        states.boundary.plot(ax=ax, color="#555555", linewidth=0.25)
        if title.startswith("b"):
            ax.scatter(stn.lon, stn.lat, s=3, c="black", lw=0, label="USCRN stations")
            ax.legend(loc="lower left", fontsize=6, frameon=False, handletextpad=0.1, borderaxespad=0)
        ax.grid(False); ax.set_xlabel(""); ax.set_ylabel("")
        ax.set_xlim(-125, -66.5); ax.set_ylim(24, 50); ax.set_xticks([]); ax.set_yticks([]); ax.set_aspect(ASP)
        for sp in ax.spines.values():
            sp.set_visible(False)
        # scale bar and north arrow (template requirement), in the open Atlantic east of Florida
        bx, by = -78.5, 25.2
        ax.plot([bx, bx + bar_deg], [by, by], color=figstyle.INK, lw=1.0, solid_capstyle="butt")
        for xx, lab in [(bx, "0"), (bx + bar_deg, "500 km")]:
            ax.plot([xx, xx], [by - 0.25, by + 0.25], color=figstyle.INK, lw=0.6)
            ax.text(xx, by + 0.55, lab, fontsize=5, ha="center", va="bottom", color=figstyle.INK)
        ax.annotate("", xy=(-69.0, 29.0), xytext=(-69.0, 25.0),
                    arrowprops=dict(arrowstyle="-|>", color=figstyle.INK, lw=0.8, mutation_scale=7))
        ax.text(-69.0, 29.3, "N", fontsize=6.5, fontweight="bold", ha="center", va="bottom", color=figstyle.INK)
        fig.text(x0, y0 + mh + 0.008, title, fontsize=7.5, ha="left", va="bottom")
        cax = fig.add_axes([x0 + mw + 0.012, y0 + 0.08 * mh, 0.012, 0.84 * mh])
        cb = fig.colorbar(im, cax=cax)
        cb.ax.tick_params(labelsize=6)
        cb.set_label(units[k], fontsize=6, color=figstyle.INK2, labelpad=2)
        fig.text(x0, y0 - 0.012, textwrap.fill(cap.replace("r = ", "r = ").replace("≥ ", "≥ ").replace(" %", " %"), 76), fontsize=6.3, color=figstyle.INK2, ha="left", va="top",
                 linespacing=1.15)
    out = os.path.join(FIG, "figS14_need_maps_report.png")
    fig.savefig(out, dpi=300, bbox_inches="tight", pad_inches=0.03); print("saved", out)


if __name__ == "__main__":
    main()
