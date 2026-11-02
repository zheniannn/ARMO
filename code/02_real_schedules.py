"""Objective 2b: event capture by the ACTUAL field-scale radar fleet.

Acquisition times over every USCRN station are taken from the public catalogues
(no login needed for metadata):
  Sentinel-1 IW GRD : Microsoft Planetary Computer STAC, collection sentinel-1-grd
  NISAR L-band      : NASA CMR, NISAR_L2_GCOV_{BETA,PROVISIONAL}_V1 granules (each GCOV
                      granule has a matching L3 SME2 soil-moisture granule)
Outputs: data/processed/acq_s1.csv, acq_nisar.csv, capture_real.csv, revisit_real.csv
"""
import os
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd
import requests
import pystac_client
from common import PROC, to_hours, captured, cluster_boot_ci

NISAR_ERA = ("2026-06-17", "2026-11-01")  # continuous provisional NISAR record
CMR = "https://cmr.earthdata.nasa.gov/search/granules.json"


def s1_times(lon, lat):
    cat = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")
    items = cat.search(collections=["sentinel-1-grd"], intersects={"type": "Point", "coordinates": [lon, lat]},
                       datetime="2025-03-15/2026-11-01").items()
    rows = {(it.datetime.replace(microsecond=0)): (it.properties.get("platform", "").lower(),
                                                    it.properties.get("sat:orbit_state"),
                                                    it.properties.get("sat:relative_orbit")) for it in items}
    return [dict(time=t, platform=p, orbit_state=o, rel_orbit=r) for t, (p, o, r) in rows.items()]


def nisar_times(lon, lat):
    out = []
    for sn in ("NISAR_L2_GCOV_BETA_V1", "NISAR_L2_GCOV_PROVISIONAL_V1"):
        r = requests.get(CMR, params={"short_name": sn, "point": f"{lon},{lat}", "page_size": 500,
                                      "temporal": "2025-03-15T00:00:00Z,2026-11-01T00:00:00Z"}, timeout=60)
        for e in r.json()["feed"]["entry"]:
            parts = e["title"].split("_")
            out.append(dict(time=pd.Timestamp(e["time_start"]), product=sn, track=parts[5],
                            direction=parts[6], granule=e["title"]))
    return out


def fetch(row):
    s1 = [dict(wban=row.wban, **d) for d in s1_times(row.lon, row.lat)]
    ni = [dict(wban=row.wban, **d) for d in nisar_times(row.lon, row.lat)]
    return s1, ni


if __name__ == "__main__":
    st = pd.read_csv(os.path.join(PROC, "station_seasons.csv"))
    st = st[st.included].drop_duplicates("wban")[["wban", "name", "lat", "lon"]]
    if not os.path.exists(os.path.join(PROC, "acq_s1.csv")):
        with ThreadPoolExecutor(8) as ex:
            res = list(ex.map(fetch, st.itertuples()))
        s1 = pd.DataFrame([d for a, _ in res for d in a])
        ni = pd.DataFrame([d for _, b in res for d in b])
        s1["time"] = pd.to_datetime(s1.time, utc=True)
        ni["time"] = pd.to_datetime(ni.time, utc=True)
        s1.to_csv(os.path.join(PROC, "acq_s1.csv"), index=False)
        ni.to_csv(os.path.join(PROC, "acq_nisar.csv"), index=False)
    s1 = pd.read_csv(os.path.join(PROC, "acq_s1.csv"), parse_dates=["time"])
    ni = pd.read_csv(os.path.join(PROC, "acq_nisar.csv"), parse_dates=["time"])

    def one_per_pass(a):
        # adjacent frames / reprocessed versions of the same pass are a single look
        a = a.sort_values(["wban", "time"])
        new = (a.wban != a.wban.shift()) | (a.time.diff() > pd.Timedelta(hours=1))
        return a[new].reset_index(drop=True)
    n0 = (len(s1), len(ni))
    s1, ni = one_per_pass(s1), one_per_pass(ni)
    print(f"acquisitions (after one-per-pass de-duplication): S1 {n0[0]} -> {len(s1)}, NISAR {n0[1]} -> {len(ni)}")
    print(s1.groupby([s1.time.dt.year, "platform"]).size())

    ev = pd.read_csv(os.path.join(PROC, "events.csv"), parse_dates=["t_start", "t_peak", "t_ws", "t_we", "t_ws_abs", "t_we_abs"])
    ws, we = to_hours(ev.t_ws), to_hours(ev.t_we)
    ws_a, we_a = to_hours(ev.t_ws_abs), to_hours(ev.t_we_abs)

    def cap_with(times_by_station, mask):
        c = np.full(len(ev), np.nan)
        ca = np.full(len(ev), np.nan)
        for w, idx in ev[mask].groupby("wban").groups.items():
            i = ev.index.get_indexer(idx)
            obs = np.sort(to_hours(times_by_station.get(w, pd.Series([], dtype="datetime64[ns, UTC]"))))
            if obs.size == 0:
                c[i] = 0; ca[i] = 0
                continue
            c[i] = captured(obs, ws[i], we[i])
            ca[i] = captured(obs, ws_a[i], we_a[i])
        return c, ca

    s1_by = {w: g.time for w, g in s1.groupby("wban")}
    ni_by = {w: g.time for w, g in ni.groupby("wban")}
    both_by = {w: pd.concat([s1_by.get(w, pd.Series(dtype="datetime64[ns, UTC]")),
                             ni_by.get(w, pd.Series(dtype="datetime64[ns, UTC]"))]) for w in set(s1_by) | set(ni_by)}

    rows = []
    era = (ev.t_start >= pd.Timestamp(NISAR_ERA[0], tz="UTC")) & (ev.t_start < pd.Timestamp(NISAR_ERA[1], tz="UTC"))
    for label, by, mask in [("Sentinel-1 (2025 season)", s1_by, ev.season == 2025),
                            ("Sentinel-1 (2026 season)", s1_by, ev.season == 2026),
                            ("Sentinel-1 (NISAR era)", s1_by, era),
                            ("NISAR (NISAR era)", ni_by, era),
                            ("Sentinel-1 + NISAR (NISAR era)", both_by, era)]:
        c, ca = cap_with(by, mask)
        ev[f"cap_{label}"] = c
        g = ev[mask].assign(c=c[mask], ca=ca[mask])
        stn = g.groupby("wban").c.mean()
        rows.append(dict(fleet=label, n_events=int(mask.sum()), n_stations=g.wban.nunique(),
                         capture=np.nanmean(c[mask]), capture_abs=np.nanmean(ca[mask]),
                         station_median=stn.median(), station_p10=stn.quantile(0.1), station_p90=stn.quantile(0.9)))
    cap = pd.DataFrame(rows)
    cap.to_csv(os.path.join(PROC, "capture_real.csv"), index=False)
    ev.to_csv(os.path.join(PROC, "events_real.csv"), index=False)
    print(cap.round(3).to_string())

    # Actual revisit statistics per station in the NISAR era (gaps between consecutive looks)
    t0, t1 = pd.Timestamp(NISAR_ERA[0], tz="UTC"), pd.Timestamp(NISAR_ERA[1], tz="UTC")
    rrows = []
    for w in st.wban:
        for label, by in [("S1", s1_by), ("NISAR", ni_by), ("S1+NISAR", both_by)]:
            t = by.get(w, pd.Series(dtype="datetime64[ns, UTC]"))
            t = np.sort(t[(t >= t0) & (t < t1)].to_numpy())
            gaps = np.diff(np.r_[np.datetime64(t0.tz_localize(None)), t.astype("datetime64[ns]") if t.size else [], np.datetime64(t1.tz_localize(None))].astype("datetime64[ns]")) / np.timedelta64(1, "D") if t.size else np.array([(t1 - t0).days])
            rrows.append(dict(wban=w, fleet=label, n_acq=t.size, mean_gap_d=gaps.mean(), max_gap_d=gaps.max(),
                              median_gap_d=np.median(gaps)))
    rv = pd.DataFrame(rrows)
    rv.to_csv(os.path.join(PROC, "revisit_real.csv"), index=False)
    print(rv.groupby("fleet")[["n_acq", "mean_gap_d", "median_gap_d", "max_gap_d"]].median().round(2))

    # ---- Decisive test: marginal value of a NEW regular-revisit mission (ARMO) ----
    # existing fleet = real S1 + NISAR looks; future fleet adds ROSE-L, simulated as a
    # regular 6-day L-band sampler (ESA's documented two-satellite revisit over global land; 3 d is Europe only,
    # tested as an optimistic case).
    from common import synthetic_schedule
    sub = ev[era].copy()
    ws_e, we_e = to_hours(sub.t_ws), to_hours(sub.t_we)
    t_first, t_last = pd.Timestamp("2026-06-01", tz="UTC"), pd.Timestamp("2026-11-10", tz="UTC")

    def fleet_plus(R_list, base_by):
        """Mean capture when regular samplers with intervals R_list (phase-averaged,
        dawn/dusk) are added to the real base fleet."""
        prob = np.zeros(len(sub))
        for w, idx in sub.groupby("wban").groups.items():
            i = sub.index.get_indexer(idx)
            off = int(sub.utc_off.iloc[i[0]])
            base = to_hours(base_by.get(w, pd.Series(dtype="datetime64[ns, UTC]"))) if base_by else np.array([])
            combos = [[]]
            for R in R_list:  # independent random phase for each added mission
                combos = [c + [(R, ph, hh)] for c in combos for ph in range(R) for hh in (6, 18)]
            acc = 0.0
            for c in combos:
                obs = np.concatenate([base] + [synthetic_schedule(t_first, t_last, R, ph, hh, off) for R, ph, hh in c])
                acc += captured(np.sort(obs), ws_e[i], we_e[i])
            prob[i] = acc / len(combos)
        return prob

    mrows = []
    base_now = fleet_plus([], both_by)
    for name, R_list, base in [("Current fleet (S1C/D + NISAR)", [], both_by),
                               ("Current fleet + ARMO 1-day", [1], both_by),
                               ("Current fleet + ARMO 2-day", [2], both_by),
                               ("Current fleet + ARMO 3-day", [3], both_by),
                               ("Current fleet + ARMO 4-day", [4], both_by),
                               ("Future fleet (+ROSE-L 6-day)", [6], both_by),
                               ("Future fleet + ARMO 2-day", [6, 2], both_by),
                               ("Future fleet + ARMO 3-day", [6, 3], both_by),
                               ("Optimistic future (+ROSE-L 3-day)", [3], both_by),
                               ("Optimistic future + ARMO 2-day", [3, 2], both_by)]:
        p = base_now if not R_list else fleet_plus(R_list, base)
        lo, hi = cluster_boot_ci(p, sub.wban, np.random.default_rng(1))
        mrows.append(dict(scenario=name, capture=p.mean(), ci_lo=lo, ci_hi=hi))
        print(mrows[-1])
    pd.DataFrame(mrows).to_csv(os.path.join(PROC, "marginal_value.csv"), index=False)
