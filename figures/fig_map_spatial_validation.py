"""Do the national need maps hold at stations they were not fitted on?  (MODEL-BASED maps vs OBSERVED stations)

The maps (code/10_gee_need_maps.py, figures/figS13_need_maps_report.png) convert gridMET storm onsets to wetting events with ONE
pooled factor k = events / onsets fitted at all USCRN station-seasons (in-sample r ~ 0.8), then estimate events missed by
Sentinel-1 as events x (1 - c(R_S1)), with c(R) = E[min(1, W/R)] from the USCRN windows and R_S1 from Earth Engine.
Here, offline from need_stations.csv / station_seasons.csv / events_real.csv:
  (1) refit k on TRAINING stations only and predict wetting events per station-season at held-out stations;
      folds = 5 longitude blocks (spatially held out) and 5 random station folds;
  (2) validate the map's "missed by Sentinel-1" layer at held-out stations against the events each station actually had
      without a real Sentinel-1 look in the 2026 season (events_real.csv, cap_Sentinel-1 (2026 season)).
The maps' gain layer is Sentinel-1-only; the mission claims use Sentinel-1 + NISAR. Maps are screening estimates, not
observed per-field misses.
Outputs: figures/figS14_map_spatial_validation.png, figures/generated/map_spatial_validation_stats.csv
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import armo_evidence as ae
import figstyle as fs
from common import rd

fs.apply()
st = rd("station_seasons.csv"); st = st[st.included]
ns = rd("need_stations.csv")
ev = ae.events_real()
cnt = ev.groupby(["wban", "season"]).size().rename("events").reset_index()
m = st[["wban", "season", "lon", "lat"]].merge(cnt, how="left").fillna({"events": 0}).merge(ns, on="wban")
m["onsets"] = np.where(m.season == 2025, m.on25, m.on26)
m = m.dropna(subset=["onsets"]).reset_index(drop=True)
k_all = m.events.sum() / m.onsets.sum()
W = ev.window_h.to_numpy() / 24


def cap(R):
    R = np.asarray(R, float); out = np.full(R.shape, np.nan); ok = np.isfinite(R) & (R > 0)
    Ws = np.sort(W); cw = np.concatenate([[0], np.cumsum(Ws)]); kk = np.searchsorted(Ws, R[ok])
    out[ok] = (cw[kk] / R[ok] + (Ws.size - kk)) / Ws.size
    return out


stations = np.sort(m.wban.unique())
lon_st = m.drop_duplicates("wban").set_index("wban").lon.reindex(stations).to_numpy()
schemes = {"longitude blocks": np.array_split(stations[np.argsort(lon_st)], 5)}
rng = np.random.default_rng(ae.SEED)
schemes["random stations"] = np.array_split(rng.permutation(stations), 5)
pred = {}
for name, folds in schemes.items():
    p = np.full(len(m), np.nan)
    for f in folds:
        tr = ~m.wban.isin(f)
        k = m.events[tr].sum() / m.onsets[tr].sum()
        p[~tr.to_numpy()] = k * m.onsets[~tr].to_numpy()
    pred[name] = p
m["pred_in"] = k_all * m.onsets
rows = []


def metrics(o, p, label, extra=""):
    r = np.corrcoef(o, p)[0, 1]
    rows.append(dict(test=label, subset=extra, n=len(o), r=r, r2_1to1=1 - ((o - p) ** 2).sum() / ((o - o.mean()) ** 2).sum(),
                     mae=np.abs(o - p).mean(), bias=(p - o).mean(), mean_observed=o.mean()))


crop = (m.crop >= 0.25).to_numpy()
metrics(m.events.to_numpy(), m.pred_in.to_numpy(), "events/station-season, IN-SAMPLE k")
for name, p in pred.items():
    metrics(m.events.to_numpy(), p, f"events/station-season, held-out k ({name})")
    for lab, msk in (("cropland cell >= 25 %", crop), ("other cells", ~crop)):
        if msk.sum() > 5:
            metrics(m.events.to_numpy()[msk], p[msk], f"events/station-season, held-out k ({name})", lab)

# (2) missed-by-Sentinel-1 layer, 2026 season, held-out k (longitude blocks)
e26 = ev[ev.season == 2026].copy()
e26["s1"] = e26["cap_Sentinel-1 (2026 season)"].astype(float) > 0
obs_miss = e26.groupby("wban").apply(lambda g: (~g.s1).sum()).rename("obs_missed")
m26 = m[m.season == 2026].copy()
m26["pred_events"] = pred["longitude blocks"][m.season.to_numpy() == 2026]
m26["R_s1"] = np.where(m26.days > 0, 214.0 / m26.days, np.nan)
m26["pred_missed"] = m26.pred_events * (1 - cap(m26.R_s1))
m26 = m26.merge(obs_miss, left_on="wban", right_index=True, how="left").fillna({"obs_missed": 0}).dropna(subset=["pred_missed"])
metrics(m26.obs_missed.to_numpy(), m26.pred_missed.to_numpy(), "S1-missed events, 2026, held-out k (longitude blocks)")
boot = ae.boot_stat(m26.wban.to_numpy(), lambda i: np.corrcoef(m26.obs_missed.to_numpy()[i], m26.pred_missed.to_numpy()[i])[0, 1])
rows[-1].update(r_ci_lo=ae.ci95(boot)[0], r_ci_hi=ae.ci95(boot)[1])
S = ae.write_stats("map_spatial_validation_stats", rows)

fig, axs = plt.subplots(1, 3, figsize=(7.8, 2.9), gridspec_kw=dict(wspace=0.5))
a, b, c = axs
pl = pred["longitude blocks"]
a.scatter(m.pred_in, m.events, s=8, color=fs.MUTED, alpha=0.6, lw=0, label="in-sample k")
a.scatter(pl, m.events, s=8, color=fs.BLUE, alpha=0.6, lw=0, label="held-out k (longitude blocks)")
mx = max(m.events.max(), np.nanmax(pl)) * 1.05
a.plot([0, mx], [0, mx], color=fs.INK2, ls="--", lw=0.8)
a.set_xlabel("Predicted events per station-season", fontsize=7); a.set_ylabel("Observed USCRN events")
a.legend(fontsize=6, loc="upper left")
r_in = S[S.test.str.contains("IN-SAMPLE")].r.iloc[0]; r_lb = S[(S.test.str.contains("longitude")) & (S.subset == "") & S.test.str.startswith("events")].r.iloc[0]
a.set_title(f"Counts: r {r_in:.2f} in-sample, {r_lb:.2f} held out", loc="left", fontsize=7.2)
fs.panel_label(a, "a")
res = m.events - pl
for lab, msk, col in (("cropland cells", crop, fs.YELLOW), ("other cells", ~crop, fs.AQUA)):
    b.hist(res[msk], bins=np.arange(-20, 21, 2), color=col, alpha=0.7, label=f"{lab} (n={msk.sum()})")
b.axvline(0, color=fs.INK2, lw=0.8)
b.set_xlabel("Observed − predicted (held out)", fontsize=7); b.set_ylabel("Station-seasons")
b.legend(fontsize=6); b.set_title("Residuals by cropland", loc="left", fontsize=7.2)
fs.panel_label(b, "b")
rr = S.iloc[-1]
c.scatter(m26.pred_missed, m26.obs_missed, s=10, color=fs.ORANGE, alpha=0.7, lw=0)
mx = max(m26.obs_missed.max(), m26.pred_missed.max()) * 1.05
c.plot([0, mx], [0, mx], color=fs.INK2, ls="--", lw=0.8)
c.set_xlabel("Map: missed by S1, 2026", fontsize=7); c.set_ylabel("Observed: no S1 look", fontsize=7)
c.set_title(f"Missed layer: r {rr.r:.2f} ({rr.r_ci_lo:.2f}–{rr.r_ci_hi:.2f})", loc="left", fontsize=7.2)
fs.panel_label(c, "c")
fig.text(0.01, -0.14, "MODEL-BASED map quantities validated against OBSERVED USCRN stations. Held-out: the events-per-onset factor is refitted "
         "without the test stations (5 longitude blocks). (c) Sentinel-1-only layer, 2026 season,\nGEE revisit + held-out k vs real "
         "acquisition looks; CI = station bootstrap. Maps are screening estimates at 0.1°, not observed per-field misses.", fontsize=6, color=fs.INK2)
ae.save(fig, "figS14_map_spatial_validation")
print(S.round(3).to_string(index=False)); print("k (all) =", round(k_all, 3))
