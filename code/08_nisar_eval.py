"""Objective 3b: NISAR SME2 (L-band, 200 m) and L-band backscatter vs USCRN ground truth.

Same matching rules as the Sentinel-1 test (06): hour-ending USCRN value after the pass,
no rain in the 3 h before, unfrozen soil; change detection only between consecutive
looks on the SAME track (identical geometry), <= 13 days apart.
Outputs: data/processed/nisar_matched.csv, nisar_summary.csv, nisar_sampled_events.csv
"""
import os
import numpy as np
import pandas as pd
from scipy import stats
from common import PROC, load_uscrn

f_all = os.path.join(PROC, "nisar_sme2_points.csv")
if os.path.exists(f_all):
    n = pd.read_csv(f_all)
else:  # extraction still running: use the per-granule cache
    cdir = os.path.join(PROC, "nisar_cache")
    n = pd.concat([pd.read_csv(os.path.join(cdir, f)) for f in os.listdir(cdir)
                   if os.path.getsize(os.path.join(cdir, f)) > 10], ignore_index=True)
if "error" in n:
    print("granule errors:", n.error.notna().sum())
    n = n[n.error.isna()]
n["time"] = pd.to_datetime(n.time, utc=True, format="ISO8601")
parts = n.granule.str.split("_")
n["track"] = parts.str[5] + parts.str[6]          # relative orbit + A/D
n = n.sort_values(["wban", "time", "n_rec"]).drop_duplicates(["wban", "time"], keep="last")
n["sm_sat"] = n.sm_3x3_rec

df = load_uscrn()[["wban", "time_utc", "sm5", "precip"]]
df["p3"] = df.groupby("wban").precip.transform(lambda x: x.rolling(3, min_periods=1).sum())
n["hour"] = n.time.dt.ceil("h")
m = n.merge(df, left_on=["wban", "hour"], right_on=["wban", "time_utc"], how="left")
m = m[m.sm5.notna() & (m.p3.fillna(0) < 0.2)].copy()
m.to_csv(os.path.join(PROC, "nisar_matched.csv"), index=False)
v = m.dropna(subset=["sm_sat"])
print("matched looks:", len(m), "with recommended SM:", len(v), "stations:", v.wban.nunique())

# ---- absolute accuracy (provisional product) ----
d = v.sm_sat - v.sm5
per = []
for w, g in v.groupby("wban"):
    if len(g) >= 6 and g.sm5.std() > 0.01:
        e = g.sm_sat - g.sm5
        per.append(dict(wban=w, n=len(g), r=g.sm_sat.corr(g.sm5), bias=e.mean(), ubrmse=e.std(ddof=0)))
per = pd.DataFrame(per)

# ---- change detection on same-track pairs: SME2 and L-band HH backscatter ----
pairs = []
for (w, tr), g in m.groupby(["wban", "track"]):
    g = g.sort_values("time")
    g = g.assign(dsm=g.sm5.diff(), dsat=g.sm_sat.diff(), dhh=g.hh_db.diff(),
                 dt_d=g.time.diff().dt.total_seconds() / 86400)
    pairs.append(g.dropna(subset=["dsm"]))
pr = pd.concat(pairs, ignore_index=True)
pr = pr[(pr.dt_d > 0.5) & (pr.dt_d <= 13)]   # drop adjacent frames of the same pass (dt ~ 30 s)
nochg = pr[pr.dsm.abs() < 0.01]
noise_sat = nochg.dsat.std()
noise_hh = nochg.dhh.std()
okh = pr.dropna(subset=["dhh"])
slope_hh = stats.linregress(okh.dsm, okh.dhh).slope * 0.1 if len(okh) > 10 else np.nan

ev = pd.read_csv(os.path.join(PROC, "events.csv"), parse_dates=["t_ws", "t_we"])
det = []
for r in ev[ev.wban.isin(pr.wban.unique())].itertuples():
    g = pr[(pr.wban == r.wban) & (pr.time >= r.t_ws) & (pr.time < r.t_we)]
    if len(g):
        x = g.iloc[0]
        det.append(dict(wban=r.wban, t_ws=r.t_ws, amp=r.amp, dsm=x.dsm, dsat=x.dsat, dhh=x.dhh))
det = pd.DataFrame(det)

ok = pr.dropna(subset=["dsat"])
summ = dict(n_matched=len(m), n_rec=len(v), n_stations=v.wban.nunique(),
            bias=d.mean(), rmse=np.sqrt((d ** 2).mean()), ubrmse=d.std(ddof=0), r_pooled=v.sm_sat.corr(v.sm5),
            median_station_r=per.r.median() if len(per) else np.nan,
            median_station_ubrmse=per.ubrmse.median() if len(per) else np.nan,
            frac_station_ubrmse_le_006=(per.ubrmse <= 0.06).mean() if len(per) else np.nan,
            n_pairs=len(pr), r_change_sat=ok.dsat.corr(ok.dsm), noise_sat_nochange=noise_sat,
            r_change_hh=okh.dhh.corr(okh.dsm), slope_hh_db_per_0p1=slope_hh, noise_hh_db=noise_hh,
            noise_hh_sm_equiv=noise_hh / (slope_hh * 10) if slope_hh and slope_hh > 0 else np.nan,
            n_sampled_events=len(det))
if len(det):
    for k in (1.0, 2.0):
        summ[f"P_detect_sat_{k:g}sigma"] = (det.dsat > k * noise_sat).mean()
        summ[f"P_detect_hh_{k:g}sigma"] = (det.dhh > k * noise_hh).mean()
        summ[f"false_alarm_sat_{k:g}sigma"] = (nochg.dsat > k * noise_sat).mean()
    # the rates above count a look with no recommended retrieval as a miss (availability x sensitivity);
    # these count only events with a valid retrieval pair (sensitivity alone, comparable to S1 and SMAP)
    summ["n_sampled_sat_valid"] = int(det.dsat.notna().sum())
    summ["P_detect_sat_valid_1sigma"] = (det.dsat.dropna() > noise_sat).mean()
    summ["n_sampled_hh_valid"] = int(det.dhh.notna().sum())
    summ["P_detect_hh_valid_1sigma"] = (det.dhh.dropna() > noise_hh).mean()
pd.Series(summ).to_csv(os.path.join(PROC, "nisar_summary.csv"))
per.to_csv(os.path.join(PROC, "nisar_station_stats.csv"), index=False)
det.to_csv(os.path.join(PROC, "nisar_sampled_events.csv"), index=False)
pr.to_csv(os.path.join(PROC, "nisar_pairs.csv"), index=False)
print(pd.Series(summ).round(3).to_string())
