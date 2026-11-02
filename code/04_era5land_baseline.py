"""Baseline / alternative: can a land-surface reanalysis (no new satellite) see the events?

ERA5-Land (Munoz-Sabater et al., 2021): 9 km, hourly, offline land model forced by ERA5;
it does not assimilate soil-moisture observations, so it is independent of USCRN.
Access: Open-Meteo historical archive API (free, no key), variable soil_moisture_0_to_7cm.
Outputs: data/raw/era5land/<wban>.csv, data/processed/era5_events_match.csv, era5_summary.csv
"""
import os, time
import numpy as np
import pandas as pd
import requests
from common import PROC, RAW, load_uscrn, station_seasons, season_series, detect_events, to_hours

ERA_DIR = os.path.join(RAW, "era5land")
os.makedirs(ERA_DIR, exist_ok=True)
URL = "https://archive-api.open-meteo.com/v1/archive"


def _get(params):
    """Open-Meteo archive request with back-off (free API: rate limits, transient errors)."""
    for attempt in range(10):
        try:
            r = requests.get(URL, params=params, timeout=120)
            return r.json()["hourly"]
        except Exception:
            time.sleep(30 * (attempt + 1))
    raise RuntimeError(f"Open-Meteo failed: {params}")


def download(row):
    """0-7 cm soil moisture from ERA5-Land and rainfall from ERA5, its forcing (0.25 deg).
    Rain always comes from model=era5: Open-Meteo returns ERA5-Land precipitation for some points and not others,
    so taking it from ERA5 in the same pass keeps every station consistent and makes one run sufficient."""
    f = os.path.join(ERA_DIR, f"{row.wban}.csv")
    if os.path.exists(f):
        d = pd.read_csv(f, parse_dates=["time"])
        if d.precip.notna().any():
            return d
    parts = []
    for a, b in (("2025-03-20", "2025-11-05"), ("2026-03-20", "2026-10-31")):
        sm = _get(dict(latitude=row.lat, longitude=row.lon, start_date=a, end_date=b,
                       hourly="soil_moisture_0_to_7cm", models="era5_land", timezone="GMT"))
        time.sleep(1.0)
        pr = _get(dict(latitude=row.lat, longitude=row.lon, start_date=a, end_date=b,
                       hourly="precipitation", models="era5", timezone="GMT"))
        time.sleep(1.0)
        parts.append(pd.DataFrame(dict(time=pd.to_datetime(sm["time"]), sm=sm["soil_moisture_0_to_7cm"]))
                     .merge(pd.DataFrame(dict(time=pd.to_datetime(pr["time"]), precip=pr["precipitation"])),
                            on="time", how="left"))
    d = pd.concat(parts)
    d.to_csv(f, index=False)
    return d


if __name__ == "__main__":
    df = load_uscrn()
    sts = station_seasons()
    ev = pd.read_csv(os.path.join(PROC, "events.csv"), parse_dates=["t_start", "t_peak"])
    rows, cont = [], []
    for r in sts.itertuples():
        era = download(r)
        era["time"] = pd.to_datetime(era.time).dt.tz_localize("UTC")
        g = season_series(df, r.wban, r.season)
        e = era.set_index("time").reindex(g.index)
        # --- event detection on ERA5-Land with the same rules (its own rainfall) ---
        ge = ev[(ev.wban == r.wban) & (ev.season == r.season)]
        es = pd.DataFrame({"sm5": e.sm.interpolate(limit=3), "precip": e.precip.fillna(0)}, index=g.index)
        for a_min in (0.01, 0.02, 0.03):
            ee = detect_events(es, r.season, a_min=a_min)
            gt = to_hours(ge.t_start); et = to_hours(ee.t_start) if len(ee) else np.array([])
            hit = np.array([np.any(np.abs(et - x) <= 24) for x in gt]) if len(gt) else np.array([])
            fa = np.array([not np.any(np.abs(gt - x) <= 24) for x in et]) if len(et) else np.array([])
            rows.append(dict(wban=r.wban, season=r.season, a_min=a_min, n_gt=len(gt), n_era=len(et),
                             hits=int(hit.sum()), false_alarms=int(fa.sum())))
        # --- rainfall agreement: does ERA5 rain at all when the station gauge records a storm? ---
        rain_hit = []
        for x in ge.t_start:
            w = e.precip[(e.index >= x - pd.Timedelta(hours=12)) & (e.index <= x + pd.Timedelta(hours=24))]
            rain_hit.append(w.sum() >= 2.0)
        # --- continuous skill: hourly anomalies about a 31-day running mean ---
        m = pd.DataFrame({"obs": g.sm5, "era": e.sm}).loc[f"{r.season}-04-01":f"{r.season}-10-31"].dropna()
        if len(m) > 24 * 60:
            an = m - m.rolling(24 * 31, center=True, min_periods=24 * 10).mean()
            an = an.dropna()
            d = m.resample("D").mean().diff().dropna()
            cont.append(dict(wban=r.wban, season=r.season, r_raw=m.obs.corr(m.era), r_anom=an.obs.corr(an.era),
                             r_daily_change=d.obs.corr(d.era), bias=(m.era - m.obs).mean(),
                             ubrmse=np.sqrt((((m.era - m.era.mean()) - (m.obs - m.obs.mean())) ** 2).mean()),
                             rain_detect=np.mean(rain_hit) if rain_hit else np.nan))
        print(r.name, r.season, flush=True)
    det = pd.DataFrame(rows)
    det.to_csv(os.path.join(PROC, "era5_events_match.csv"), index=False)
    cs = pd.DataFrame(cont)
    cs.to_csv(os.path.join(PROC, "era5_continuous.csv"), index=False)
    s = det.groupby("a_min")[["n_gt", "n_era", "hits", "false_alarms"]].sum()
    s["POD"] = s.hits / s.n_gt
    s["FAR"] = s.false_alarms / s.n_era
    s["CSI"] = s.hits / (s.n_gt + s.false_alarms)
    s.to_csv(os.path.join(PROC, "era5_summary.csv"))
    print(s.round(3))
    print(cs.describe().round(3))
