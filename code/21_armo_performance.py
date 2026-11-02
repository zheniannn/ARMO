"""ARMO head-to-head against NISAR and ROSE-L, and a ground-truth test of deeper-sensing (P-band / UHF) options.

(a) Head-to-head, each system ON ITS OWN, on the same 979 NISAR-era wetting events (17 Jun - 31 Oct 2026):
    Sentinel-1 and NISAR = real acquisition times; ROSE-L = regular 6-day (ESA, global land) and 3-day (Europe /
    eoPortal) samplers, phase- and dawn/dusk-averaged as in step 03; ARMO = design D flown in the step-09 orbit model
    (2 satellites, 8 orbital phases). Also: ARMO D added to the future fleet (real S1 + NISAR + ROSE-L 6-day).
(b) Sensing depth. Shen et al. (2021) find P-band retrieves soil moisture over ~7 cm (vs ~5 cm at L-band), and
    > 10 cm below 0.5 GHz (UHF). USCRN also reports 10 cm soil moisture, so we rerun the SAME event definition on
    the 10 cm series: how many events, how long they last, and what regular revisits would capture.
Outputs: data/processed/performance_headtohead.csv, depth_events.csv, depth_summary.csv
"""
import os
import importlib
import numpy as np
import pandas as pd
from common import PROC, load_uscrn, station_seasons, to_hours, captured, synthetic_schedule

orb = importlib.import_module("09_armo_orbit_sim")
evr = importlib.import_module("02_events_revisit")
rng = np.random.default_rng(3)


def boot(p, g, n=2000):
    g = np.asarray(g); keys = np.unique(g); by = {k: p[g == k] for k in keys}
    s = [np.concatenate([by[k] for k in rng.choice(keys, keys.size)]).mean() for _ in range(n)]
    return np.percentile(s, [2.5, 97.5])


def head_to_head():
    st = pd.read_csv(os.path.join(PROC, "station_seasons.csv"))
    st = st[st.included & (st.season == 2026)].drop_duplicates("wban")[["wban", "lat", "lon"]]
    ev = pd.read_csv(os.path.join(PROC, "events.csv"), parse_dates=["t_start", "t_ws", "t_we"])
    ev = ev[(ev.t_start >= orb.ERA[0]) & (ev.t_start < orb.ERA[1])].reset_index(drop=True)
    ws, we = to_hours(ev.t_ws), to_hours(ev.t_we)
    s1 = pd.read_csv(os.path.join(PROC, "acq_s1.csv"), parse_dates=["time"])
    ni = pd.read_csv(os.path.join(PROC, "acq_nisar.csv"), parse_dates=["time"])
    real = {"s1": {w: np.sort(to_hours(s1[s1.wban == w].time)) for w in st.wban},
            "ni": {w: np.sort(to_hours(ni[ni.wban == w].time)) for w in st.wban}}
    t0h = to_hours(pd.DatetimeIndex([orb.T0]))[0]
    t_first, t_last = pd.Timestamp("2026-06-01", tz="UTC"), pd.Timestamp("2026-11-10", tz="UTC")

    # ARMO design D passes for 8 orbital phases (2 satellites 180 deg apart, right-looking 25-45 deg)
    armo = []
    for u0 in np.linspace(0, 2 * np.pi, 8, endpoint=False):
        tb = {w: [] for w in st.wban}
        for s in range(2):
            t, r, v, inc, a, rev = orb.orbit(620, 18.0, u0 + s * np.pi)
            for row in st.itertuples():
                tb[row.wban].append(t0h + orb.accesses(t, r, v, row.lat, row.lon, 25, 45, "R", rev) / 3600)
        armo.append({w: np.sort(np.concatenate(x)) for w, x in tb.items()})

    def score(parts, rose=None, armo_on=False):
        """Per-event capture probability. parts: list of real fleets; rose: ROSE-L interval (regular, phase-
        and dawn/dusk-averaged); armo_on: average over the 8 ARMO phases."""
        p = np.zeros(len(ev))
        for w, idx in ev.groupby("wban").groups.items():
            i = ev.index.get_indexer(idx)
            off = int(ev.utc_off.iloc[i[0]])
            base = [real[k].get(w, np.array([])) for k in parts]
            roses = [synthetic_schedule(t_first, t_last, rose, ph, hh, off) for ph in range(rose) for hh in (6, 18)] \
                if rose else [np.array([])]
            arms = [a_.get(w, np.array([])) for a_ in armo] if armo_on else [np.array([])]
            acc, n = 0.0, 0
            for rs in roses:
                for am in arms:
                    obs = np.sort(np.concatenate(base + [rs, am]))
                    acc = acc + (captured(obs, ws[i], we[i]) if obs.size else 0); n += 1
            p[i] = acc / n
        return p

    rows = []
    for name, kw in [("Sentinel-1 alone", dict(parts=["s1"])),
                     ("NISAR alone", dict(parts=["ni"])),
                     ("ROSE-L alone, 6-day", dict(parts=[], rose=6)),
                     ("ROSE-L alone, 3-day", dict(parts=[], rose=3)),
                     ("ARMO alone (design D)", dict(parts=[], armo_on=True)),
                     ("Sentinel-1 + NISAR", dict(parts=["s1", "ni"])),
                     ("Sentinel-1 + NISAR + ARMO", dict(parts=["s1", "ni"], armo_on=True)),
                     ("Sentinel-1 + NISAR + ROSE-L 6-day", dict(parts=["s1", "ni"], rose=6)),
                     ("Sentinel-1 + NISAR + ROSE-L 6-day + ARMO", dict(parts=["s1", "ni"], rose=6, armo_on=True)),
                     ("Sentinel-1 + NISAR + ROSE-L 3-day + ARMO", dict(parts=["s1", "ni"], rose=3, armo_on=True))]:
        p = score(**kw)
        lo, hi = boot(p, ev.wban)
        rows.append(dict(system=name, capture=p.mean(), ci_lo=lo, ci_hi=hi, n_events=len(ev)))
        print(rows[-1], flush=True)
    pd.DataFrame(rows).to_csv(os.path.join(PROC, "performance_headtohead.csv"), index=False)


def depth_test():
    df = load_uscrn()
    sts = station_seasons()
    out = {}
    for depth in ("sm5", "sm10"):
        d = df.copy()
        x = d[depth].where(~d.frozen_or_unknown.astype(bool) & d[depth].between(0, 0.6))
        d["sm5"] = x          # the event code reads column sm5
        ev = evr.all_events(d, sts)
        for R in (1, 2, 3, 6):
            ev[f"p_R{R}"] = evr.capture_prob(ev, R)
        ev["depth"] = depth
        out[depth] = ev
        print(depth, len(ev), ev.window_h.median() / 24, flush=True)
    e5, e10 = out["sm5"], out["sm10"]
    # same storm seen at both depths (storm start identical)
    k5 = set(zip(e5.wban, e5.t_start)); k10 = set(zip(e10.wban, e10.t_start))
    both = len(k5 & k10)
    pd.concat([e5, e10]).to_csv(os.path.join(PROC, "depth_events.csv"), index=False)
    rows = []
    for depth, e in out.items():
        rows.append(dict(depth_cm=5 if depth == "sm5" else 10, n_events=len(e), n_stations=e.wban.nunique(),
                         win_med_d=e.window_h.median() / 24, win_q1_d=e.window_h.quantile(.25) / 24,
                         win_q3_d=e.window_h.quantile(.75) / 24, amp_med=e.amp.median(),
                         cap_R1=e.p_R1.mean(), cap_R2=e.p_R2.mean(), cap_R3=e.p_R3.mean(), cap_R6=e.p_R6.mean(),
                         n_same_storm=both, frac_5cm_also_10cm=both / len(e5)))
    s = pd.DataFrame(rows)
    s.to_csv(os.path.join(PROC, "depth_summary.csv"), index=False)
    print(s.round(3).to_string())


if __name__ == "__main__":
    head_to_head()
    depth_test()
