"""Objective 3a: is the wetting signal observable by field-scale C-band SAR when it IS sampled?

Matches Sentinel-1 RTC backscatter (11 x 11 px window, ~110 m) to USCRN 5 cm soil moisture
at the acquisition hour. Exclusions: frozen/unknown soil, rain in the 3 h before the pass
(wet canopy / ponding), invalid windows. Geometry is controlled by working within each
station x relative-orbit group (same incidence angle and look direction).

Metrics
  r_temporal   : per station-orbit Pearson r(sigma0_VV dB, SM5)  [n >= 10]
  sensitivity  : OLS slope, dB per 0.1 m3/m3
  noise_sm     : std(d sigma0 | |dSM| < 0.01) / slope -> SM-equivalent noise of a single
                 change-detection pair (speckle + vegetation + roughness change)
  P(detect|sampled): fraction of events with an S1 look inside the window whose backscatter
                 rose by > k*noise relative to the previous same-orbit look
Outputs: data/processed/s1_matched.csv, s1_station_stats.csv, s1_summary.csv
"""
import os
import numpy as np
import pandas as pd
from scipy import stats
from common import PROC, load_uscrn, to_hours

cache = os.path.join(PROC, "s1_cache")
s1 = pd.concat([pd.read_csv(os.path.join(cache, f)) for f in os.listdir(cache)
                if os.path.getsize(os.path.join(cache, f)) > 10], ignore_index=True)  # skip stations with no scenes
s1["time"] = pd.to_datetime(s1.time, utc=True, format="ISO8601")
s1 = s1.dropna(subset=["vv_db", "vh_db"])
s1 = s1.sort_values(["wban", "time"]).drop_duplicates(["wban", "time"])

df = load_uscrn()[["wban", "time_utc", "sm5", "precip"]]
df["p3"] = df.groupby("wban").precip.transform(lambda x: x.rolling(3, min_periods=1).sum())
s1["hour"] = s1.time.dt.ceil("h")
m = s1.merge(df, left_on=["wban", "hour"], right_on=["wban", "time_utc"], how="left")
m["season"] = m.time.dt.year
m["xpol"] = m.vh_db - m.vv_db                      # cross-pol ratio (dB): vegetation volume proxy
ok = m.sm5.notna() & (m.p3.fillna(0) < 0.2)
m = m[ok].copy()
m.to_csv(os.path.join(PROC, "s1_matched.csv"), index=False)
print("matched S1-ground pairs:", len(m), "stations:", m.wban.nunique())

# vegetation class per station-season by cross-pol ratio terciles
veg = m.groupby(["wban", "season"]).xpol.mean().rename("xpol_mean").reset_index()
veg["veg_class"] = pd.qcut(veg.xpol_mean, 3, labels=["low", "medium", "high"])
m = m.merge(veg, on=["wban", "season"])

rows = []
pairs = []
for (w, orb), g in m.groupby(["wban", "rel_orbit"]):
    g = g.sort_values("time")
    if len(g) < 10 or g.sm5.std() < 0.01:
        continue
    r, p = stats.pearsonr(g.vv_db, g.sm5)
    sl = stats.linregress(g.sm5, g.vv_db).slope * 0.1
    rows.append(dict(wban=w, rel_orbit=orb, n=len(g), r=r, p=p, slope_db_per_0p1=sl,
                     sm_range=g.sm5.max() - g.sm5.min(), veg_class=g.veg_class.mode()[0],
                     xpol=g.xpol.mean(), vv_cv=g.vv_cv.mean()))
    d = g.assign(dvv=g.vv_db.diff(), dsm=g.sm5.diff(), dt_d=g.time.diff().dt.total_seconds() / 86400,
                 prev_time=g.time.shift(), prev_sm=g.sm5.shift())
    pairs.append(d.dropna(subset=["dvv", "dsm"]).assign(rel_orbit=orb))
ss = pd.DataFrame(rows)
pr = pd.concat(pairs, ignore_index=True)
pr = pr[(pr.dt_d > 0.5) & (pr.dt_d <= 13)]          # consecutive same-orbit looks only; drops duplicate frames of one pass
ss.to_csv(os.path.join(PROC, "s1_station_stats.csv"), index=False)
pr.to_csv(os.path.join(PROC, "s1_pairs.csv"), index=False)

# pooled temporal anomalies (remove each station-orbit mean)
a = m.copy()
a["vv_a"] = a.vv_db - a.groupby(["wban", "rel_orbit"]).vv_db.transform("mean")
a["sm_a"] = a.sm5 - a.groupby(["wban", "rel_orbit"]).sm5.transform("mean")
pooled = {c: stats.pearsonr(g.vv_a, g.sm_a)[0] for c, g in a.groupby("veg_class")}
pooled["all"] = stats.pearsonr(a.vv_a, a.sm_a)[0]

# change-detection: noise floor and event detection
# SM-equivalent noise uses the pooled same-orbit pair regression (identical method to the NISAR test)
sl_med = stats.linregress(pr.dsm, pr.dvv).slope        # dB per m3/m3
nochg = pr[pr.dsm.abs() < 0.01]
noise_db = nochg.dvv.std()
wet = pr[pr.dsm >= 0.03]
auc = stats.mannwhitneyu(wet.dvv, pr[pr.dsm < 0.03].dvv).statistic / (len(wet) * (pr.dsm < 0.03).sum())

# P(detect | sampled) for ground-truth events with an S1 look inside the window
ev = pd.read_csv(os.path.join(PROC, "events.csv"), parse_dates=["t_ws", "t_we"])
ev = ev[ev.wban.isin(m.wban.unique())]
det = []
for r in ev.itertuples():
    g = pr[(pr.wban == r.wban) & (pr.time >= r.t_ws) & (pr.time < r.t_we)]
    if len(g):
        x = g.iloc[0]
        det.append(dict(wban=r.wban, t_ws=r.t_ws, amp=r.amp, dvv=x.dvv, dsm=x.dsm, veg_class=m[m.wban == r.wban].veg_class.mode()[0]))
det = pd.DataFrame(det)
summ = dict(n_pairs_matched=len(m), n_station_orbits=len(ss), n_stations=ss.wban.nunique(),
            median_r=ss.r.median(), frac_r_sig_pos=((ss.r > 0) & (ss.p < 0.05)).mean(),
            median_slope_db_per_0p1=ss.slope_db_per_0p1.median(), pooled_r_all=pooled["all"],
            pooled_r_low=pooled.get("low"), pooled_r_medium=pooled.get("medium"), pooled_r_high=pooled.get("high"),
            noise_db_nochange=noise_db, noise_sm_equiv=noise_db / sl_med if sl_med > 0 else np.nan,
            pair_slope_db_per_0p1=sl_med * 0.1,
            r_change_vv=pr.dvv.corr(pr.dsm), n_change_pairs=len(pr),
            auc_wetup=auc, n_sampled_events=len(det))
for k in (1.0, 2.0):
    thr = k * noise_db
    summ[f"P_detect_given_sampled_{k:g}sigma"] = (det.dvv > thr).mean() if len(det) else np.nan
    summ[f"false_alarm_nochange_{k:g}sigma"] = (nochg.dvv > thr).mean()
for c in ("low", "medium", "high"):
    d = det[det.veg_class == c]
    summ[f"P_detect_1sigma_{c}"] = (d.dvv > noise_db).mean() if len(d) else np.nan
    summ[f"median_r_{c}"] = ss[ss.veg_class == c].r.median()
pd.Series(summ).to_csv(os.path.join(PROC, "s1_summary.csv"))
det.to_csv(os.path.join(PROC, "s1_sampled_events.csv"), index=False)
print(pd.Series(summ).round(3).to_string())
