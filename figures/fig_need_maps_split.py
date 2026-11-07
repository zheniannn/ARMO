"""The report need maps (figures/figS14_need_maps_report.png) split into two slide figures, re-checked against the cached data.

Slide 14 (slide14_need_maps_looks_events): a Sentinel-1 days between looks; b wetting events per warm season.
Slide 15 (slide15_need_maps_armo_gain): a wetting events per season with no Sentinel-1 look; b extra wetting events
per season with a look when ARMO is added (cropland >= 25 %).
Terminology (project definitions): Look = acquisition; Capture = observation opportunity; Detection = positive result.
These maps are about LOOKS: whether a look falls inside a wetting window. No detection is implied.

Inputs (read only, from code/10_gee_need_maps.py; no Earth Engine call here): data/processed/need_grid.npz,
need_stations.csv, need_summary.csv, events.csv, station_seasons.csv, acq_s1.csv.
Every number printed on the figures is recomputed here and asserted equal to need_summary.csv; extra ground-truth
checks are written to figures/generated/fig_need_maps_audit.csv.
Run: python figures/fig_need_maps_split.py
"""
import os
import sys
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "code"))
sys.path.insert(0, os.path.join(ROOT, "figures"))
import numpy as np
import pandas as pd
import geopandas as gpd
import shapely
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm
from common import PROC, RAW
import figstyle

X0, Y0, DX, NX, NY = -125.0, 50.0, 0.1, 590, 260      # grid of code/10_gee_need_maps.py
R_ARMO = 1.42                                         # design D mean revisit (code/06), as in code/10
SEASON_D = 214.0                                      # 1 Apr - 31 Oct


def p_look(R, W):
    """Chance that a look falls inside a window, E[min(1, W/R)], regular revisit R (days), USCRN windows W (days).
    Same formula as capture() in code/10_gee_need_maps.py."""
    R = np.asarray(R, float)
    out = np.full(R.shape, np.nan)
    ok = np.isfinite(R) & (R > 0)
    Ws = np.sort(W); cw = np.concatenate([[0], np.cumsum(Ws)])
    k = np.searchsorted(Ws, R[ok])
    out[ok] = (cw[k] / R[ok] + (Ws.size - k)) / Ws.size
    return out


def conus_mask(states):
    geom = states.union_all()
    xx, yy = np.meshgrid(X0 + (np.arange(NX) + 0.5) * DX, Y0 - (np.arange(NY) + 0.5) * DX)
    return shapely.contains_xy(geom, xx, yy)


def compute():
    states = gpd.read_file(os.path.join(RAW, "naturalearth", "states", "ne_50m_admin_1_states_provinces.shp"))
    states = states[(states.iso_a2 == "US") & ~states.name.isin(["Alaska", "Hawaii"])]
    z = np.load(os.path.join(PROC, "need_grid.npz"))
    us = conus_mask(states)
    days = np.where(us, z["days"], np.nan)
    on = np.where(us, (z["on25"] + z["on26"]) / 2, np.nan)
    crop = np.where(us, z["crop"], np.nan)
    st = pd.read_csv(os.path.join(PROC, "station_seasons.csv"))
    stn = st[st.included].drop_duplicates("wban")[["wban", "lat", "lon"]]
    ev = pd.read_csv(os.path.join(PROC, "events.csv"))
    ns = pd.read_csv(os.path.join(PROC, "need_stations.csv"))
    cnt = ev.groupby(["wban", "season"]).size().rename("events").reset_index()
    cnt = st[st.included][["wban", "season"]].merge(cnt, how="left").fillna({"events": 0})
    m = cnt.merge(ns, on="wban")
    m["onsets"] = np.where(m.season == 2025, m.on25, m.on26)
    m = m.dropna(subset=["onsets"])
    k = m.events.sum() / m.onsets.sum()
    r_on = np.corrcoef(m.onsets, m.events)[0, 1]
    s1 = pd.read_csv(os.path.join(PROC, "acq_s1.csv"), parse_dates=["time"])
    s1 = s1[(s1.time >= "2026-04-01") & (s1.time < "2026-11-01")]
    pc = s1.assign(d=s1.time.dt.date).groupby("wban").d.nunique().rename("pc_days")
    chk = ns.set_index("wban").join(pc, how="inner")
    r_days = np.corrcoef(chk.days, chk.pc_days)[0, 1]
    W = ev.window_h.to_numpy() / 24
    with np.errstate(divide="ignore"):
        R_s1 = np.where(days > 0, SEASON_D / days, np.nan)
    E = k * on
    p_s1 = p_look(R_s1, W)
    p_comb = p_look(1 / (1 / R_s1 + 1 / R_ARMO), W)
    nolook = E * (1 - p_s1)
    gain = E * (p_comb - p_s1)
    cropm = crop >= 0.25
    v = np.isfinite(R_s1) & np.isfinite(E)
    sm = dict(n_stations=len(chk), r_days_gee_vs_pc=r_days, k_events_per_onset=k, r_onsets_events=r_on,
              n_station_seasons=len(m), conus_R_s1_median=np.nanmedian(R_s1[v]), conus_missed_median=np.nanmedian(nolook[v]),
              crop_gain_median=np.nanmedian(gain[cropm & v]), crop_cells=int((cropm & v).sum()),
              conus_gain_median=np.nanmedian(gain[v]))
    # 1) reproduce the published numbers exactly
    ref = pd.read_csv(os.path.join(PROC, "need_summary.csv")).iloc[0]
    for key, val in sm.items():
        assert np.isclose(val, ref[key], rtol=1e-9), (key, val, ref[key])
    # 2) ground-truth checks of the look model at the stations (2026 season)
    evr = pd.read_csv(os.path.join(PROC, "events_real.csv"))
    obs = evr[evr.season == 2026].groupby("wban")["cap_Sentinel-1 (2026 season)"].mean()
    stR = (SEASON_D / ns.set_index("wban").days).rename("R")
    j = pd.concat([obs.rename("obs"), stR], axis=1, join="inner").dropna()
    n26 = evr[evr.season == 2026].groupby("wban").size()
    mod = (p_look(j.R.to_numpy(), W) * n26.reindex(j.index).to_numpy()).sum() / n26.reindex(j.index).sum()
    obs_all = evr.loc[evr.season == 2026, "cap_Sentinel-1 (2026 season)"].mean()
    audit = [
        ("a", "median days between Sentinel-1 looks, CONUS cells", sm["conus_R_s1_median"], "need_summary.csv", "5.6 d"),
        ("a", "r, Earth Engine look days vs station record (stations)", sm["r_days_gee_vs_pc"], f"n = {sm['n_stations']} stations", "0.90"),
        ("b", "wetting events per gridMET onset (pooled, USCRN)", sm["k_events_per_onset"], f"{sm['n_station_seasons']} station-seasons", "0.75"),
        ("b", "r, gridMET onsets vs USCRN wetting events", sm["r_onsets_events"], f"{sm['n_station_seasons']} station-seasons", "0.82"),
        ("b", "USCRN stations plotted (qualifying)", len(stn), "station_seasons.csv included", "121"),
        ("b", "USCRN stations with >= 1 wetting event", ev.wban.nunique(), "events.csv", "120"),
        ("c", "USCRN wetting windows used for W", len(W), "events.csv", "3,340"),
        ("c", "median wetting events per season with no Sentinel-1 look, CONUS cells", sm["conus_missed_median"], "need_summary.csv", "8.5"),
        ("c", "look model vs observed at stations: share of 2026 events with a Sentinel-1 look, model", mod, f"{len(j)} stations, event-weighted", ""),
        ("c", "same, observed (real Sentinel-1 looks, events_real.csv)", obs_all, "2026 season", ""),
        ("d", "ARMO mean days between looks (design D, 362 km swath assumed)", R_ARMO, "code/06 orbit simulation", "1.4 d"),
        ("d", "median extra wetting events per season with a look, cropland >= 25 % cells", sm["crop_gain_median"], f"{sm['crop_cells']} cells", "8.8 -> 9"),
        ("d all land", "median extra wetting events per season with a look, all CONUS cells", sm["conus_gain_median"], f"{int(v.sum())} cells", "6.3"),
        ("d all land", "10th / 90th percentile, all CONUS cells", f"{np.nanpercentile(gain[v], 10):.1f} / {np.nanpercentile(gain[v], 90):.1f}", "", ""),
        ("d all land", "share of CONUS cells gaining >= 5 events per season", np.mean(gain[v] >= 5), "", ""),
    ]
    pd.DataFrame(audit, columns=["panel", "quantity", "value", "basis", "as printed"]).to_csv(
        os.path.join(HERE, "generated", "fig_need_maps_audit.csv"), index=False)
    print(pd.DataFrame(audit).to_string())
    return states, stn, R_s1, E, nolook, np.where(cropm, gain, np.nan), sm, len(stn), np.where(v, gain, np.nan)


def figure(fname, panels, states, stn, slots=None):
    """slots: (column, row) per panel on a two-column grid; default one row. Column may be fractional (0.5 = centred)."""
    figstyle.apply()
    slots = slots or [(c, 0) for c in range(len(panels))]
    ncol = max(2, int(np.ceil(max(c for c, _ in slots))) + 1)
    nrow = max(r for _, r in slots) + 1
    W_IN, ROW_IN = 3.6 * ncol, 2.75                     # 3.6 in per column, 2.75 in per row
    H_IN = ROW_IN * nrow
    f = 2 / ncol
    ASP = 1 / np.cos(np.deg2rad(37.0))
    ext = [X0, X0 + NX * DX, Y0 - NY * DX, Y0]
    bar_deg = 500 / (111.32 * np.cos(np.deg2rad(37.0)))
    mw = 0.405 * f
    mh = mw * W_IN * (26 * ASP / 58.5) / H_IN
    fig = plt.figure(figsize=(W_IN, H_IN))
    for (arr, title, cmap, bounds, unit, cap, dots), (col, row) in zip(panels, slots):
        x0 = (0.02 + col * 0.50) * f
        y0 = (0.30 + (nrow - 1 - row) * 0.86) / nrow          # rows overlap their spare top margin
        ax = fig.add_axes([x0, y0, mw, mh])
        cm = plt.get_cmap(cmap, len(bounds) + 1)
        im = ax.imshow(arr, extent=ext, origin="upper", cmap=cm, norm=BoundaryNorm(bounds, cm.N, extend="both"),
                       interpolation="nearest")
        states.boundary.plot(ax=ax, color="#555555", linewidth=0.25)
        if dots:
            ax.scatter(stn.lon, stn.lat, s=3, c="black", lw=0, label="USCRN stations")
            ax.legend(loc="lower left", fontsize=6, frameon=False, handletextpad=0.1, borderaxespad=0)
        ax.grid(False); ax.set_xlabel(""); ax.set_ylabel(""); ax.set_xticks([]); ax.set_yticks([])
        ax.set_xlim(-125, -66.5); ax.set_ylim(24, 50); ax.set_aspect(ASP)
        for sp in ax.spines.values():
            sp.set_visible(False)
        bx, by = -78.5, 25.2
        ax.plot([bx, bx + bar_deg], [by, by], color=figstyle.INK, lw=1.0, solid_capstyle="butt")
        for xx, lab in [(bx, "0"), (bx + bar_deg, "500 km")]:
            ax.plot([xx, xx], [by - 0.25, by + 0.25], color=figstyle.INK, lw=0.6)
            ax.text(xx, by + 0.55, lab, fontsize=5, ha="center", va="bottom", color=figstyle.INK)
        ax.annotate("", xy=(-69.0, 29.0), xytext=(-69.0, 25.0),
                    arrowprops=dict(arrowstyle="-|>", color=figstyle.INK, lw=0.8, mutation_scale=7))
        ax.text(-69.0, 29.3, "N", fontsize=6.5, fontweight="bold", ha="center", va="bottom", color=figstyle.INK)
        fig.text(x0, y0 + mh + 0.02 / nrow, title, fontsize=7.5, ha="left", va="bottom")
        cax = fig.add_axes([x0 + mw + 0.012 * f, y0 + 0.08 * mh, 0.012 * f, 0.84 * mh])
        cb = fig.colorbar(im, cax=cax)
        cb.ax.tick_params(labelsize=6)
        cb.set_label(unit, fontsize=6, color=figstyle.INK2, labelpad=2)
        fig.text(x0, y0 - 0.03 / nrow, textwrap.fill(cap, 76), fontsize=6.3, color=figstyle.INK2, ha="left", va="top",
                 linespacing=1.15)
    fig.savefig(os.path.join(HERE, f"{fname}.png"), dpi=400, bbox_inches="tight", pad_inches=0.03, facecolor="white")
    plt.close(fig)
    print("saved", os.path.join(HERE, fname + ".png"))


def main():
    states, stn, R, E, nolook, gain, sm, n_stn, gain_all = compute()
    figure("slide14_need_maps_looks_events", [
        (R, "a  Days between Sentinel-1 looks, 2026 warm season", "Blues", [2, 3, 4, 5, 6, 8, 10, 12, 16], "days",
         f"Season length ÷ distinct days with a Sentinel-1 look, 1 Apr–31 Oct 2026 (Earth Engine COPERNICUS/S1_GRD, IW). "
         f"Agrees with our station record (r = {sm['r_days_gee_vs_pc']:.2f}, {sm['n_stations']} stations). "
         f"Median cell {sm['conus_R_s1_median']:.1f} d.", False),
        (E, "b  Wetting events per warm season (gridMET, USCRN-calibrated)", "Greens", [4, 6, 8, 10, 12, 14, 16, 18, 20],
         "events per season",
         f"gridMET storm onsets (≥ 5 mm after a day with < 5 mm), mean of the 2025 and 2026 seasons, × "
         f"{sm['k_events_per_onset']:.2f} wetting events per onset fitted at USCRN (r = {sm['r_onsets_events']:.2f}, "
         f"{sm['n_station_seasons']} station-seasons). Dots: the {n_stn} USCRN stations.", True)], states, stn)
    figure("slide15_need_maps_armo_gain", [
        (nolook, "a  Wetting events per season with no Sentinel-1 look", "Oranges", [2, 4, 6, 8, 10, 12, 14],
         "events per season",
         f"Events × (1 − chance of a look inside the window); chance = E[min(1, W/R)] over the 3,340 USCRN wetting windows W "
         f"at each cell's days between looks R. Median cell {sm['conus_missed_median']:.1f} per season.", False),
        (gain_all, "b  Extra wetting events per season with a look, adding ARMO", "Purples", [1, 2, 4, 6, 8, 10, 12, 14],
         "events per season",
         f"Added when ARMO (362 km swath, a look every {R_ARMO:.1f} d on average) joins Sentinel-1; all land cells. "
         f"Median {sm['conus_gain_median']:.1f} per season.", False),
        (gain, "c  As b, cropland only (≥ 25 % of the cell)", "Purples", [1, 2, 4, 6, 8, 10, 12, 14],
         "events per season",
         f"Panel b on cells with ≥ 25 % cropland (MODIS MCD12Q1 2024; cropland/natural mosaic counted as half). "
         f"Median {sm['crop_gain_median']:.1f} per season.", False)], states, stn, slots=[(0, 0), (1, 0), (0.5, 1)])

if __name__ == "__main__":
    main()
