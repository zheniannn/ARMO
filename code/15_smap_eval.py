"""Objective 3c: SMAP Enhanced L3 (L-band radiometer, 9 km, AM + PM) vs USCRN ground truth.

Answers "why not SMAP?" with the same tests used for Sentinel-1 (06) and NISAR (08):
capture of wetting-event windows by retrievals, absolute accuracy, and detection of sampled events
by change between consecutive retrievals of the same overpass (AM-AM or PM-PM).
Overpass time: SMAP has no per-pixel time band in Earth Engine, so the nominal local solar times
06:00 (AM, descending) and 18:00 (PM, ascending) are used, converted to UTC by longitude.
Recommended quality = retrieval_qual_flag 0 (as in NISAR's recommended flag); all retrievals as a check.
Outputs: data/processed/smap_summary.csv, smap_capture.csv, smap_sampled_events.csv, smap_pairs.csv
"""
import os
import numpy as np
import pandas as pd
from common import PROC, load_uscrn, to_hours, captured

NISAR_ERA = ("2026-06-17", "2026-11-01")
s = pd.read_csv(os.path.join(PROC, "gee_smap.csv"))
rows = []
for ov, h in (("am", 6), ("pm", 18)):
    d = s[["wban", "date", "longitude", f"soil_moisture_{ov}", f"retrieval_qual_flag_{ov}", f"vegetation_water_content_{ov}"]].copy()
    d.columns = ["wban", "date", "lon", "sm_sat", "flag", "vwc"]
    d["time"] = (pd.to_datetime(d.date, utc=True) + pd.to_timedelta(h - d.lon / 15, unit="h")).dt.round("min")
    rows.append(d.assign(overpass=ov.upper()))
sm = pd.concat(rows, ignore_index=True).dropna(subset=["sm_sat"])
sm["recommended"] = sm.flag == 0

df = load_uscrn()[["wban", "time_utc", "sm5", "precip"]]
df["p3"] = df.groupby("wban").precip.transform(lambda x: x.rolling(3, min_periods=1).sum())
sm["hour"] = sm.time.dt.ceil("h")
m_all = sm.merge(df, left_on=["wban", "hour"], right_on=["wban", "time_utc"], how="left")
m_all = m_all[m_all.sm5.notna()]                     # in a QC'd warm-season USCRN hour

ev = pd.read_csv(os.path.join(PROC, "events.csv"), parse_dates=["t_start", "t_ws", "t_we"])
era = (ev.t_start >= pd.Timestamp(NISAR_ERA[0], tz="UTC")) & (ev.t_start < pd.Timestamp(NISAR_ERA[1], tz="UTC"))


def evaluate(m, label):
    """Capture, accuracy and sampled-event detection for one quality subset."""
    # ---- capture: any retrieval inside the window (no rain screen: a look is a look) ----
    cap = []
    for w, g in ev.groupby("wban"):
        obs = np.sort(to_hours(sm.loc[(sm.wban == w) & (m.attrs["mask"](sm)), "time"]))
        for r in g.itertuples():
            cap.append(dict(wban=w, season=r.season, era=bool(era[r.Index]),
                            cap=captured(obs, to_hours(pd.DatetimeIndex([r.t_ws]))[0], to_hours(pd.DatetimeIndex([r.t_we]))[0]) if len(obs) else 0.0))
    cap = pd.DataFrame(cap)
    # ---- matched looks for accuracy / change (rain screen as in 06 and 08) ----
    v = m[m.p3.fillna(0) < 0.2]
    e = v.sm_sat - v.sm5
    per = []
    for w, g in v.groupby("wban"):
        if len(g) >= 20 and g.sm5.std() > 0.01:
            ee_ = g.sm_sat - g.sm5
            per.append(dict(wban=w, n=len(g), r=g.sm_sat.corr(g.sm5), bias=ee_.mean(), ubrmse=ee_.std(ddof=0)))
    per = pd.DataFrame(per)
    pairs = []
    for (w, ov), g in v.groupby(["wban", "overpass"]):
        g = g.sort_values("time")
        g = g.assign(dsm=g.sm5.diff(), dsat=g.sm_sat.diff(), dt_d=g.time.diff().dt.total_seconds() / 86400)
        pairs.append(g.dropna(subset=["dsm"]))
    pr = pd.concat(pairs, ignore_index=True)
    pr = pr[pr.dt_d <= 3.5]
    nochg = pr[pr.dsm.abs() < 0.01]
    noise = nochg.dsat.std()
    det = []
    for r in ev[ev.wban.isin(pr.wban.unique())].itertuples():
        g = pr[(pr.wban == r.wban) & (pr.time >= r.t_ws) & (pr.time < r.t_we)]
        if len(g):
            x = g.sort_values("time").iloc[0]
            det.append(dict(wban=r.wban, t_ws=r.t_ws, amp=r.amp, dsm=x.dsm, dsat=x.dsat, vwc=x.vwc))
    det = pd.DataFrame(det)
    S = dict(subset=label, n_retrievals=int(m.attrs["mask"](sm).sum()), n_matched=len(v), n_stations=v.wban.nunique(),
             capture_2025=cap[cap.season == 2025].cap.mean(), capture_2026=cap[cap.season == 2026].cap.mean(),
             capture_era=cap[cap.era].cap.mean(), n_era=int(cap.era.sum()),
             bias=e.mean(), ubrmse=e.std(ddof=0), r_pooled=v.sm_sat.corr(v.sm5),
             median_station_r=per.r.median(), median_station_ubrmse=per.ubrmse.median(),
             frac_station_ubrmse_le_004=(per.ubrmse <= 0.04).mean(), n_station_stats=len(per),
             n_pairs=len(pr), r_change=pr.dsat.corr(pr.dsm), noise_nochange=noise,
             n_sampled_events=len(det), P_detect_1sigma=(det.dsat > noise).mean(),
             false_alarm_1sigma=(nochg.dsat > noise).mean(), P_detect_2sigma=(det.dsat > 2 * noise).mean(),
             false_alarm_2sigma=(nochg.dsat > 2 * noise).mean())
    S["end_to_end_era"] = S["capture_era"] * S["P_detect_1sigma"]
    return S, cap, det, pr


rec = m_all[m_all.recommended].copy(); rec.attrs["mask"] = lambda d: d.recommended
alls = m_all.copy(); alls.attrs["mask"] = lambda d: d.sm_sat.notna()
S_rec, cap_rec, det_rec, pr_rec = evaluate(rec, "recommended")
S_all, cap_all, det_all, pr_all = evaluate(alls, "all")

summ = pd.DataFrame([S_rec, S_all]).set_index("subset").T
summ.to_csv(os.path.join(PROC, "smap_summary.csv"))
cap_rec.to_csv(os.path.join(PROC, "smap_capture.csv"), index=False)
det_rec.to_csv(os.path.join(PROC, "smap_sampled_events.csv"), index=False)
det_all.to_csv(os.path.join(PROC, "smap_sampled_events_all.csv"), index=False)
pr_rec.to_csv(os.path.join(PROC, "smap_pairs.csv"), index=False)
pr_all.to_csv(os.path.join(PROC, "smap_pairs_all.csv"), index=False)
print(summ.to_string(float_format=lambda x: f"{x:.3f}"))
