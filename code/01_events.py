"""Ground truth: parse NOAA USCRN, detect wetting events, and test capture by regular revisits (O1, O2).

Run: python 01_events.py  (parts run in this order: parse_uscrn, events_and_revisit)
"""
import glob, io, os
import numpy as np
import pandas as pd
from common import PROC, load_uscrn, station_seasons, season_series, detect_events, to_hours, captured, synthetic_schedule, cluster_boot_ci


# ====================================================================================================
# parse_uscrn
# ====================================================================================================

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RAW = os.path.join(ROOT, "data", "raw", "uscrn")

OUT = os.path.join(ROOT, "data", "processed")

os.makedirs(OUT, exist_ok=True)

names = open(os.path.join(RAW, "HEADERS.txt")).read().splitlines()[1].split()

keep = ["WBANNO", "UTC_DATE", "UTC_TIME", "LST_DATE", "LST_TIME", "LONGITUDE",
        "LATITUDE", "T_CALC", "P_CALC", "SUR_TEMP", "SOIL_MOISTURE_5",
        "SOIL_MOISTURE_10", "SOIL_TEMP_5"]


def parse(path):
    # Some NOAA files contain runs of NUL bytes that overwrite a few records.
    # Strip them and keep only well-formed 38-field records; lost hours become gaps.
    text = open(path, "rb").read().replace(b"\x00", b"").decode("ascii", "ignore")
    good = [ln for ln in text.splitlines() if len(ln.split()) == len(names) and ln.split()[0].isdigit()]
    df = pd.read_csv(io.StringIO("\n".join(good)), sep=r"\s+", header=None, names=names, usecols=keep,
                     dtype={"WBANNO": "int64", "UTC_DATE": str, "UTC_TIME": str, "LST_DATE": str, "LST_TIME": str})
    df["time_utc"] = pd.to_datetime(df.UTC_DATE + df.UTC_TIME.str.zfill(4), format="%Y%m%d%H%M", utc=True)
    df["time_lst"] = pd.to_datetime(df.LST_DATE + df.LST_TIME.str.zfill(4), format="%Y%m%d%H%M")
    for c in ["T_CALC", "P_CALC", "SUR_TEMP", "SOIL_MOISTURE_5", "SOIL_MOISTURE_10", "SOIL_TEMP_5"]:
        df.loc[df[c] <= -99, c] = np.nan
    for c in ["SOIL_MOISTURE_5", "SOIL_MOISTURE_10"]:
        df.loc[(df[c] < 0) | (df[c] > 0.6), c] = np.nan
    frozen = ~(df.SOIL_TEMP_5 > 1.0)  # NaN soil temperature counts as not-verified-unfrozen
    df["frozen_or_unknown"] = frozen
    df.loc[frozen, "SOIL_MOISTURE_5"] = np.nan
    df["station_file"] = os.path.basename(path)
    return df.drop(columns=["UTC_DATE", "UTC_TIME", "LST_DATE", "LST_TIME"])


def parse_uscrn():
    """Parse NOAA USCRN hourly02 station files into one quality-controlled table.
    
    Ground truth for the whole project. Source:
    https://www.ncei.noaa.gov/pub/data/uscrn/products/hourly02/  (no login)
    Column layout: data/raw/uscrn/HEADERS.txt (38 fixed fields).
    
    QC applied (each documented in the report, Section 3.1):
      - NOAA missing sentinels (-9999, -99.000) -> NaN
      - SOIL_MOISTURE_5 outside [0, 0.6] m3/m3 -> NaN (physically implausible)
      - frozen flag: SOIL_TEMP_5 <= 1 C (dielectric of frozen water ~ ice; probe
        and radar both invalid) -> SM5 set NaN"""
    files = sorted(glob.glob(os.path.join(RAW, "2025", "*.txt")) + glob.glob(os.path.join(RAW, "2026", "*.txt")))
    df = pd.concat([parse(f) for f in files], ignore_index=True)
    df = df.rename(columns={"WBANNO": "wban", "SOIL_MOISTURE_5": "sm5", "SOIL_MOISTURE_10": "sm10",
                            "SOIL_TEMP_5": "st5", "P_CALC": "precip", "LONGITUDE": "lon", "LATITUDE": "lat"})
    df["name"] = df.station_file.str.replace(r"CRNH0203-20\d\d-", "", regex=True).str.replace(".txt", "")
    df = df.drop(columns="station_file").sort_values(["wban", "time_utc"]).drop_duplicates(["wban", "time_utc"])
    df.to_pickle(os.path.join(OUT, "uscrn_hourly.pkl"))

    # Station summary per warm season (1 Apr - 31 Oct); a station-season enters the
    # analysis only if >= 70 % of its hours have valid, unfrozen 5 cm soil moisture.
    rows = []
    for yr in (2025, 2026):
        w = df[(df.time_utc >= f"{yr}-04-01") & (df.time_utc < f"{yr}-11-01")]
        st = w.groupby("wban").agg(name=("name", "first"), lat=("lat", "median"), lon=("lon", "median"),
                                   sm5_valid=("sm5", "count"), precip_mm=("precip", "sum"),
                                   sm5_mean=("sm5", "mean"), sm5_std=("sm5", "std"))
        st["season"] = yr
        st["sm5_frac"] = st.sm5_valid / (214 * 24)
        rows.append(st.reset_index())
    st = pd.concat(rows, ignore_index=True)
    st["included"] = st.sm5_frac >= 0.7
    st.to_csv(os.path.join(OUT, "station_seasons.csv"), index=False)
    print(st.groupby("season").included.agg(["size", "sum"]))
    print("unique stations included in >=1 season:", st[st.included].wban.nunique())


# ====================================================================================================
# events_and_revisit
# ====================================================================================================

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


def events_and_revisit():
    """Objective 1 + 2a: wetting events from ground truth and their capture by regular revisits.
    
    Outputs (data/processed):
      events.csv              one row per wetting event (all station-seasons)
      capture_synthetic.csv   capture probability vs revisit interval, with station-bootstrap CI
      sensitivity.csv         same headline numbers under alternative event definitions"""
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
            lo, hi = cluster_boot_ci(p, ev.wban.to_numpy(), rng, N_BOOT)
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


if __name__ == "__main__":
    parse_uscrn()
    events_and_revisit()
