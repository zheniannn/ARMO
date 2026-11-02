"""Objective 1 + 2a: wetting events from ground truth and their capture by regular revisits.

Outputs (data/processed):
  events.csv              one row per wetting event (all station-seasons)
  capture_synthetic.csv   capture probability vs revisit interval, with station-bootstrap CI
  sensitivity.csv         same headline numbers under alternative event definitions
"""
import numpy as np
import pandas as pd
from common import (PROC, load_uscrn, station_seasons, season_series, detect_events,
                    to_hours, captured, synthetic_schedule)
import os

INTERVALS = [1, 2, 3, 4, 5, 6, 8, 10, 12]
HOURS = [6, 18]          # dawn/dusk local overpasses, as flown by Sentinel-1, NISAR, SMAP
N_BOOT = 2000
rng = np.random.default_rng(42)


def all_events(df, sts, **kw):
    out = []
    for r in sts.itertuples():
        s = season_series(df, r.wban, r.season)
        off = (df[df.wban == r.wban].iloc[0][["time_lst", "time_utc"]])
        utc_off = round((off.time_lst - off.time_utc.tz_localize(None)).total_seconds() / 3600)
        ev = detect_events(s, r.season, **kw)
        if len(ev):
            ev.insert(0, "wban", r.wban); ev.insert(1, "season", r.season)
            ev["name"], ev["lat"], ev["lon"], ev["utc_off"] = r.name, r.lat, r.lon, utc_off
            out.append(ev)
    return pd.concat(out, ignore_index=True)


def capture_prob(ev, R, abs_window=False):
    """Per-event probability of capture by a regular R-day schedule, averaged over all
    start-day phases and both dawn/dusk overpass times."""
    ws = to_hours(ev["t_ws_abs" if abs_window else "t_ws"])
    we = to_hours(ev["t_we_abs" if abs_window else "t_we"])
    prob = np.zeros(len(ev))
    for (season, off), idx in ev.groupby(["season", "utc_off"]).groups.items():
        idx = ev.index.get_indexer(idx)
        t_first = pd.Timestamp(f"{season}-03-20", tz="UTC")
        t_last = pd.Timestamp(f"{season}-12-01", tz="UTC")
        acc = np.zeros(idx.size)
        n = 0
        for ph in range(R):
            for hh in HOURS:
                obs = synthetic_schedule(t_first, t_last, R, ph, hh, off)
                acc += captured(obs, ws[idx], we[idx])
                n += 1
        prob[idx] = acc / n
    return prob


def boot_ci(values, groups, n=N_BOOT):
    """Cluster bootstrap over stations: events at one station are not independent."""
    keys = np.unique(groups)
    by = {k: values[groups == k] for k in keys}
    stats = []
    for _ in range(n):
        pick = rng.choice(keys, size=keys.size, replace=True)
        v = np.concatenate([by[k] for k in pick])
        stats.append(v.mean())
    return np.percentile(stats, [2.5, 97.5])


if __name__ == "__main__":
    df = load_uscrn()
    sts = station_seasons()
    ev = all_events(df, sts)
    ev.to_csv(os.path.join(PROC, "events.csv"), index=False)
    print(f"events: {len(ev)} from {ev.wban.nunique()} stations, {len(sts)} station-seasons")
    print(ev[["rain_mm", "amp", "rise_h", "half_life_h", "window_h", "window_abs_h"]].describe().round(3).to_string())
    print("censored fraction:", ev.censored.mean().round(3))

    rows = []
    for R in INTERVALS:
        for absw in (False, True):
            p = capture_prob(ev, R, absw)
            ev[f"p_R{R}{'_abs' if absw else ''}"] = p
            lo, hi = boot_ci(p, ev.wban.to_numpy())
            # analytic expectation for a randomly phased periodic sampler: E[min(1, W/R)]
            W = (ev.window_abs_h if absw else ev.window_h).to_numpy() / 24.0
            rows.append(dict(R=R, window="abs0.03" if absw else "half-amplitude", capture=p.mean(),
                             ci_lo=lo, ci_hi=hi, analytic=np.minimum(1, W / R).mean(),
                             cap_2025=p[ev.season.to_numpy() == 2025].mean(),
                             cap_2026=p[ev.season.to_numpy() == 2026].mean()))
    cap = pd.DataFrame(rows)
    cap.to_csv(os.path.join(PROC, "capture_synthetic.csv"), index=False)
    ev.to_csv(os.path.join(PROC, "events.csv"), index=False)
    print(cap.round(3).to_string())

    # Sensitivity of headline numbers to the event definition
    srows = []
    for p_min in (2.0, 5.0, 10.0):
        for a_min in (0.02, 0.03, 0.05):
            e = all_events(df, sts, p_min=p_min, a_min=a_min)
            r = dict(p_min=p_min, a_min=a_min, n_events=len(e), median_window_h=e.window_h.median(),
                     median_half_life_h=e.half_life_h.median())
            for R in (2, 3, 6, 12):
                r[f"cap_R{R}"] = capture_prob(e, R).mean()
            srows.append(r)
            print(r)
    pd.DataFrame(srows).to_csv(os.path.join(PROC, "sensitivity.csv"), index=False)
