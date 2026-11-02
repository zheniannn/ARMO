"""Shared definitions: paths, wetting-event detection and schedule capture tests.

Definitions (fixed before looking at satellite data; see report Section 3.2):
  storm      : run of hours with P >= 0.2 mm, storms closer than STORM_GAP_H dry hours merged
  event      : storm with total P >= P_MIN_MM whose 5 cm soil moisture rises by
               A = peak - pre >= A_MIN (m3/m3)
  pre        : mean SM5 over the 3 h before the storm starts
  window     : hours during which the wetting anomaly (SM5 - pre) >= FRAC * A, from the
               first such hour after onset until the anomaly first falls below
               FRAC * A after the peak (or the next event starts: censoring)
  captured   : at least one satellite acquisition falls inside the window
"""
import os
import sys
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(ROOT, "data", "processed")
RAW = os.path.join(ROOT, "data", "raw")
FIG = os.path.join(ROOT, "figures")
# report and slide generators (20, 30, report_text) are kept out of the repository in "Assignment (Do Not Push)/"
GEN = os.path.join(ROOT, "Assignment (Do Not Push)")
if GEN not in sys.path:
    sys.path.append(GEN)
# figure scripts and their shared style (figstyle.py) live in figures/
if FIG not in sys.path:
    sys.path.append(FIG)
os.makedirs(FIG, exist_ok=True)

P_MIN_MM = 5.0
A_MIN = 0.03
FRAC = 0.5
STORM_GAP_H = 24
WET_HOUR_MM = 0.2


def rd(f, **kw):
    """Read a result table from data/processed."""
    return pd.read_csv(os.path.join(PROC, f), **kw)


def cluster_boot_ci(values, groups, rng, n=2000):
    """95 % CI of a mean by cluster bootstrap over stations (events at one station are not independent)."""
    values, groups = np.asarray(values), np.asarray(groups)
    keys = np.unique(groups)
    by = {k: values[groups == k] for k in keys}
    means = [np.concatenate([by[k] for k in rng.choice(keys, keys.size)]).mean() for _ in range(n)]
    return np.percentile(means, [2.5, 97.5])


def load_uscrn():
    return pd.read_pickle(os.path.join(PROC, "uscrn_hourly.pkl"))


def station_seasons():
    st = pd.read_csv(os.path.join(PROC, "station_seasons.csv"))
    return st[st.included].reset_index(drop=True)


def season_series(df, wban, season, pad_days=10):
    """Hourly series on a complete UTC grid for one station-season (Apr 1 - Oct 31)."""
    t0 = pd.Timestamp(f"{season}-04-01", tz="UTC") - pd.Timedelta(days=pad_days)
    t1 = pd.Timestamp(f"{season}-11-01", tz="UTC") + pd.Timedelta(days=pad_days)
    s = df[(df.wban == wban) & (df.time_utc >= t0) & (df.time_utc < t1)].set_index("time_utc")
    grid = pd.date_range(t0, t1, freq="h", inclusive="left")
    s = s.reindex(grid)
    s["sm5"] = s.sm5.interpolate(limit=3, limit_area="inside")  # bridge <=3 h gaps only
    s["precip"] = s.precip.fillna(0.0)
    return s


def detect_events(s, season, p_min=P_MIN_MM, a_min=A_MIN, frac=FRAC, gap_h=STORM_GAP_H):
    """Return a DataFrame of wetting events for one station-season series `s`."""
    sm = s.sm5.to_numpy()
    p = s.precip.to_numpy()
    t = s.index
    wet = np.flatnonzero(p >= WET_HOUR_MM)
    if wet.size == 0:
        return pd.DataFrame()
    # group wet hours into storms
    breaks = np.flatnonzero(np.diff(wet) > gap_h)
    starts = np.r_[wet[0], wet[breaks + 1]]
    ends = np.r_[wet[breaks], wet[-1]]
    totals = np.array([p[a:b + 1].sum() for a, b in zip(starts, ends)])
    keep = totals >= p_min
    starts, ends, totals = starts[keep], ends[keep], totals[keep]
    lo = np.searchsorted(t, pd.Timestamp(f"{season}-04-01", tz="UTC"))
    hi = np.searchsorted(t, pd.Timestamp(f"{season}-11-01", tz="UTC"))
    rows = []
    for k, (a, b, tot) in enumerate(zip(starts, ends, totals)):
        if a < lo or a >= hi or a < 3:
            continue
        pre = np.nanmean(sm[a - 3:a]) if np.isfinite(sm[a - 3:a]).any() else np.nan
        if not np.isfinite(pre):
            continue
        nxt = starts[k + 1] if k + 1 < len(starts) else len(sm)
        seg_end = min(b + 24, nxt)
        seg = sm[a:seg_end + 1]
        if not np.isfinite(seg).any():
            continue
        ip = a + int(np.nanargmax(seg))
        A = sm[ip] - pre
        if A < a_min:
            continue
        lim = min(nxt, ip + 30 * 24, len(sm))
        thr = pre + frac * A
        # window start: first hour after onset with anomaly >= frac*A
        ws = a + int(np.flatnonzero(np.nan_to_num(sm[a:ip + 1], nan=-1) >= thr)[0])
        after = sm[ip:lim]
        below = np.flatnonzero(np.nan_to_num(after, nan=np.inf) < thr)
        censored = below.size == 0
        we = ip + (int(below[0]) if not censored else len(after))
        # absolute-threshold window (anomaly >= A_MIN), used as a sensitivity test
        thr_abs = pre + a_min
        ws_abs = a + int(np.flatnonzero(np.nan_to_num(sm[a:ip + 1], nan=-1) >= thr_abs)[0])
        below_abs = np.flatnonzero(np.nan_to_num(after, nan=np.inf) < thr_abs)
        we_abs = ip + (int(below_abs[0]) if below_abs.size else len(after))
        rows.append(dict(t_start=t[a], t_peak=t[ip], t_ws=t[ws], t_we=t[min(we, len(t) - 1)],
                         t_ws_abs=t[ws_abs], t_we_abs=t[min(we_abs, len(t) - 1)],
                         rain_mm=tot, rain_hours=b - a + 1, pre=pre, peak=sm[ip], amp=A,
                         rise_h=ip - a, half_life_h=(we - ip), censored=censored,
                         window_h=we - ws, window_abs_h=we_abs - ws_abs, i_start=a, i_lim=lim))
    return pd.DataFrame(rows)


def to_hours(times):
    """Timestamps -> float hours since epoch (UTC)."""
    if not len(times):
        return np.array([])
    idx = pd.DatetimeIndex(times).tz_convert("UTC")
    return ((idx - pd.Timestamp("1970-01-01", tz="UTC")) / pd.Timedelta(hours=1)).to_numpy(dtype=float)


def captured(obs_h, ws_h, we_h):
    """Boolean per event: any observation time in [ws, we). obs_h must be sorted.
    USCRN hourly values are labelled at hour END, so an acquisition at hh:mm is
    compared with the value labelled hh+1:00 (ceil)."""
    obs_lab = np.ceil(np.asarray(obs_h))
    i = np.searchsorted(obs_lab, ws_h, side="left")
    return (i < obs_lab.size) & (obs_lab[np.minimum(i, obs_lab.size - 1)] < we_h)


def synthetic_schedule(t_first, t_last, interval_days, phase_days, local_hour, utc_offset_h):
    """Regular schedule every `interval_days` at a fixed local standard time."""
    day0 = pd.Timestamp(t_first).tz_convert("UTC").floor("D")
    start = day0 + pd.Timedelta(hours=local_hour - utc_offset_h) + pd.Timedelta(days=phase_days)
    n = int((pd.Timestamp(t_last) - start) / pd.Timedelta(days=interval_days)) + 1
    times = start + pd.to_timedelta(np.arange(max(n, 0)) * interval_days, unit="D")
    return to_hours(times)
