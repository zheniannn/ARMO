"""Sensor tests (O3): Sentinel-1, NISAR and SMAP against ground truth; detection by vegetation; and the calibrated
detection model that sets ARMO's noise requirement.

Run: python 08_sensor_tests.py  (parts run in this order: s1_observability, nisar_eval, smap_eval, detection_strata, snr_requirement)
"""
import os
import numpy as np
import pandas as pd
from scipy import stats, optimize
from common import PROC, load_uscrn, to_hours, captured, rd


# ====================================================================================================
# s1_observability
# ====================================================================================================


def s1_observability():
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
    Outputs: data/processed/s1_matched.csv, s1_station_stats.csv, s1_summary.csv"""
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


# ====================================================================================================
# nisar_eval
# ====================================================================================================


def nisar_eval():
    """Objective 3b: NISAR SME2 (L-band, 200 m) and L-band backscatter vs USCRN ground truth.
    
    Same matching rules as the Sentinel-1 test (06): hour-ending USCRN value after the pass,
    no rain in the 3 h before, unfrozen soil; change detection only between consecutive
    looks on the SAME track (identical geometry), <= 13 days apart.
    Outputs: data/processed/nisar_matched.csv, nisar_summary.csv, nisar_sampled_events.csv"""
    n = pd.read_csv(os.path.join(PROC, "nisar_sme2_points.csv"))
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
    for (w, _), g in m.groupby(["wban", "track"]):
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
            summ[f"false_alarm_sat_{k:g}sigma"] = (nochg.dsat.dropna() > k * noise_sat).mean()   # valid retrievals only, as for detection
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


# ====================================================================================================
# smap_eval
# ====================================================================================================


def smap_eval():
    """Objective 3c: SMAP Enhanced L3 (L-band radiometer, 9 km, AM + PM) vs USCRN ground truth.
    
    Answers "why not SMAP?" with the same tests used for Sentinel-1 (06) and NISAR (08):
    capture of wetting-event windows by retrievals, absolute accuracy, and detection of sampled events
    by change between consecutive retrievals of the same overpass (AM-AM or PM-PM).
    Overpass time: SMAP has no per-pixel time band in Earth Engine, so the nominal local solar times
    06:00 (AM, descending) and 18:00 (PM, ascending) are used, converted to UTC by longitude.
    Recommended quality = retrieval_qual_flag 0 (as in NISAR's recommended flag); all retrievals as a check.
    Outputs: data/processed/smap_summary.csv, smap_capture.csv, smap_sampled_events.csv, smap_pairs.csv"""
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
    S_all, _, det_all, pr_all = evaluate(alls, "all")

    summ = pd.DataFrame([S_rec, S_all]).set_index("subset").T
    summ.to_csv(os.path.join(PROC, "smap_summary.csv"))
    cap_rec.to_csv(os.path.join(PROC, "smap_capture.csv"), index=False)
    det_rec.to_csv(os.path.join(PROC, "smap_sampled_events.csv"), index=False)
    det_all.to_csv(os.path.join(PROC, "smap_sampled_events_all.csv"), index=False)
    pr_rec.to_csv(os.path.join(PROC, "smap_pairs.csv"), index=False)
    pr_all.to_csv(os.path.join(PROC, "smap_pairs_all.csv"), index=False)
    print(summ.to_string(float_format=lambda x: f"{x:.3f}"))


# ====================================================================================================
# detection_strata
# ====================================================================================================


def detection_strata():
    """Why do sampled events go undetected? Detection rate by vegetation (MODIS NDVI at the event,
    from Earth Engine), by land cover (ESA WorldCover at the probe) and by event size, for
    Sentinel-1 VV, NISAR SME2, NISAR HH and SMAP (all retrievals). Each sensor keeps its own
    1-sigma no-change noise threshold from the three sensor tests above.
    Outputs: data/processed/detection_strata.csv, station_vegetation.csv"""
    s1s = rd("s1_summary.csv", index_col=0).iloc[:, 0]
    nis = rd("nisar_summary.csv", index_col=0).iloc[:, 0]
    sms = rd("smap_summary.csv", index_col=0)["all"]
    sensors = {
        "Sentinel-1 VV (C-band SAR)": (rd("s1_sampled_events.csv"), "dvv", s1s["noise_db_nochange"]),
        "NISAR SME2 (L-band SAR)": (rd("nisar_sampled_events.csv"), "dsat", nis["noise_sat_nochange"]),
        "NISAR HH (L-band SAR)": (rd("nisar_sampled_events.csv"), "dhh", nis["noise_hh_db"]),
        "SMAP (L-band radiometer)": (rd("smap_sampled_events_all.csv"), "dsat", sms["noise_nochange"]),
    }

    # ---- NDVI at each event: nearest good-quality MODIS 16-day composite within 16 days ----
    nd = rd("gee_ndvi.csv")
    nd = nd[nd.SummaryQA <= 1].dropna(subset=["NDVI"])
    nd = nd.assign(ndvi=nd.NDVI * 1e-4, date=pd.to_datetime(nd.date, utc=True) + pd.Timedelta(days=8))  # composite centre
    lc = rd("gee_landcover.csv")
    WC = {10: "Tree cover", 20: "Shrubland", 30: "Grassland", 40: "Cropland"}
    lc["cover"] = lc.worldcover.map(WC).fillna("Other")
    CROPS_CDL = set(range(1, 62)) | set(range(66, 78)) | set(range(204, 255))
    lc["cdl_crop"] = lc.cdl.isin(CROPS_CDL)


    def ndvi_at(det):
        det = det.copy()
        det["t_ws"] = pd.to_datetime(det.t_ws, utc=True, format="ISO8601")
        out = np.full(len(det), np.nan)
        for i, r in enumerate(det.itertuples()):
            g = nd[nd.wban == r.wban]
            if len(g):
                dt = (g.date - r.t_ws).abs()
                j = dt.idxmin()
                if dt[j] <= pd.Timedelta(days=16):
                    out[i] = g.ndvi[j]
        det["ndvi"] = out
        return det.merge(lc[["wban", "cover", "cdl_crop"]], on="wban", how="left")


    def ci(k, n):
        """Wilson 95 % interval for a proportion."""
        if n == 0:
            return np.nan, np.nan
        p, z = k / n, 1.96
        c = (p + z * z / (2 * n)) / (1 + z * z / n); h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
        return c - h, c + h


    rows = []
    for name, (det, col, noise) in sensors.items():
        d = ndvi_at(det.dropna(subset=[col]))
        d["hit"] = d[col] > noise
        d["ndvi_bin"] = pd.cut(d.ndvi, [-1, 0.35, 0.6, 1], labels=["NDVI < 0.35 (sparse)", "0.35-0.6", "NDVI >= 0.6 (dense)"])
        d["amp_bin"] = pd.cut(d.amp, [0, 0.06, 0.12, 1], labels=["rise < 0.06", "0.06-0.12", "rise >= 0.12"])
        for dim in ("all", "ndvi_bin", "cover", "amp_bin"):
            groups = [("all", d)] if dim == "all" else list(d.groupby(dim, observed=True))
            for lev, g in groups:
                lo, hi = ci(int(g.hit.sum()), len(g))
                rows.append(dict(sensor=name, dimension=dim, level=str(lev), n=len(g), p_detect=g.hit.mean(), ci_lo=lo, ci_hi=hi,
                                 median_ndvi=g.ndvi.median()))
    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(PROC, "detection_strata.csv"), index=False)

    # station vegetation summary (for the report's limitation on cropland representativeness)
    sv = nd[nd.date.dt.month.isin([6, 7, 8])].groupby("wban").ndvi.median().rename("ndvi_summer").reset_index().merge(lc, on="wban", how="right")
    sv.to_csv(os.path.join(PROC, "station_vegetation.csv"), index=False)
    print(out.round(3).to_string(index=False))
    print("\nstations by WorldCover class:", lc.cover.value_counts().to_dict(), "| CDL crop at probe:", int(lc.cdl_crop.sum()),
          "| median summer NDVI:", round(sv.ndvi_summer.median(), 2), "| median crop fraction in 9 km:", round(lc.crop_frac_9km.median(), 3))


# ====================================================================================================
# snr_requirement
# ====================================================================================================


def snr_requirement():
    """Derive ARMO's event-sensitivity (noise) requirement from the four sensors tested.
    
    Model: a sampled event of size A changes the sensor by s*A plus Gaussian noise sigma (the no-change
    spread of same-geometry pairs). With a 1-sigma threshold, P(detect | A) = Phi(A / n - 1), where
    n = sigma / s is the noise in soil-moisture units. The model is checked against the observed detection
    rates of Sentinel-1, NISAR (HH and SME2) and SMAP, then solved for the n that detects 70 % of the
    observed event-size distribution. n is converted to backscatter (dB) with the measured L- and C-band
    sensitivities; if the noise is speckle-dominated, noise falls as 1/sqrt(looks).
    Outputs: data/processed/snr_requirement.csv (sensor table), snr_summary.csv"""
    ev = rd("events.csv")
    s1 = rd("s1_summary.csv", index_col=0).iloc[:, 0]
    ni = rd("nisar_summary.csv", index_col=0).iloc[:, 0]
    sm = rd("smap_summary.csv", index_col=0)["all"]
    s1p, nip, smp = rd("s1_pairs.csv"), rd("nisar_pairs.csv"), rd("smap_pairs_all.csv")


    def slope(x, y):
        ok = np.isfinite(x) & np.isfinite(y)
        return stats.linregress(x[ok], y[ok]).slope


    cases = [  # name, change column, pairs, sampled events, noise
        ("Sentinel-1 VV", "dvv", s1p, rd("s1_sampled_events.csv"), s1["noise_db_nochange"]),
        ("NISAR HH", "dhh", nip, rd("nisar_sampled_events.csv"), ni["noise_hh_db"]),
        ("NISAR SME2", "dsat", nip, rd("nisar_sampled_events.csv"), ni["noise_sat_nochange"]),
        ("SMAP", "dsat", smp, rd("smap_sampled_events_all.csv"), sm["noise_nochange"]),
    ]
    rows = []
    for name, col, pr, det, sig in cases:
        s = slope(pr.dsm.to_numpy(float), pr[col].to_numpy(float))
        n = sig / s
        d = det.dropna(subset=[col])
        rows.append(dict(sensor=name, slope_per_m3m3=s, noise=sig, noise_sm_equiv=n, n_events=len(d),
                         p_observed=(d[col] > sig).mean(), p_model=stats.norm.cdf(d.amp / n - 1).mean(),
                         snr_median_event=ev.amp.median() / n))
    tab = pd.DataFrame(rows)
    amps = ev.amp.to_numpy()


    # The ideal model is optimistic for every sensor (events vary more than one slope and noise capture).
    # Calibrate with ONE factor k shared by all sensors (effective sensitivity = k x slope), fitted to the
    # observed rates weighted by events, and use the calibrated model for the requirement.
    det_amps = {r[0]: r[3].dropna(subset=[r[1]]).amp.to_numpy() for r in cases}


    def p_k(n, a, k): return stats.norm.cdf(k * a / n - 1).mean()


    def loss(k):
        return sum(r.n_events * (p_k(r.noise_sm_equiv, det_amps[r.sensor], k) - r.p_observed) ** 2 for r in tab.itertuples())


    K = optimize.minimize_scalar(loss, bounds=(0.1, 2), method="bounded").x
    tab["p_calibrated"] = [p_k(r.noise_sm_equiv, det_amps[r.sensor], K) for r in tab.itertuples()]


    def p_of(n, k=K): return stats.norm.cdf(k * amps / n - 1).mean()


    n70 = optimize.brentq(lambda n: p_of(n) - 0.70, 0.002, 0.5)
    n50 = optimize.brentq(lambda n: p_of(n) - 0.50, 0.002, 0.5)
    n70_ideal = optimize.brentq(lambda n: p_of(n, 1.0) - 0.70, 0.002, 0.5)
    L = tab.set_index("sensor").loc["NISAR HH"]; C = tab.set_index("sensor").loc["Sentinel-1 VV"]
    summ = dict(k_calibration=K, noise_req_70=n70, noise_req_50=n50, noise_req_70_ideal=n70_ideal, snr_req_median=np.median(amps) / n70,
                req_db_L=n70 * L.slope_per_m3m3, req_db_C=n70 * C.slope_per_m3m3,
                now_db_L=L.noise, now_db_C=C.noise,
                looks_factor_L=(L.noise / (n70 * L.slope_per_m3m3)) ** 2,
                model_mae_pts=(tab.p_model - tab.p_observed).abs().mean() * 100,
                calibrated_mae_pts=(tab.p_calibrated - tab.p_observed).abs().mean() * 100)
    tab.to_csv(os.path.join(PROC, "snr_requirement.csv"), index=False)
    pd.Series(summ).to_csv(os.path.join(PROC, "snr_summary.csv"))
    print(tab.round(3).to_string(index=False)); print(pd.Series(summ).round(3).to_string())


if __name__ == "__main__":
    s1_observability()
    nisar_eval()
    smap_eval()
    detection_strata()
    snr_requirement()
