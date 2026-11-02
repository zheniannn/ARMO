"""ARMO mission design: orbit simulation of designs A-E, head-to-head against NISAR and ROSE-L with the 10 cm depth
test, and spacecraft sizing, mass and cost.

Run: python 06_mission_design.py  (parts run in this order: orbit_designs, performance, sizing)
"""
import os
import geopandas as gpd
import importlib
import numpy as np
import pandas as pd
import shapely
from common import PROC, RAW, to_hours, captured, load_uscrn, station_seasons, synthetic_schedule, cluster_boot_ci


# ====================================================================================================
# orbit_designs
# ====================================================================================================

MU, RE, J2, WE = 398600.4418, 6378.137, 1.08263e-3, 7.2921159e-5

T0, T1 = pd.Timestamp("2026-06-01", tz="UTC"), pd.Timestamp("2026-11-10", tz="UTC")

DT = 10.0

ERA = (pd.Timestamp("2026-06-17", tz="UTC"), pd.Timestamp("2026-11-01", tz="UTC"))


def gmst(t):
    jd = t.to_julian_date()
    d = jd - 2451545.0
    return np.deg2rad((280.46061837 + 360.98564736629 * d) % 360)


def sun_ra(t):
    d = t.to_julian_date() - 2451545.0
    L = np.deg2rad((280.460 + 0.9856474 * d) % 360); g = np.deg2rad((357.528 + 0.9856003 * d) % 360)
    lam = L + np.deg2rad(1.915) * np.sin(g) + np.deg2rad(0.020) * np.sin(2 * g)
    eps = np.deg2rad(23.439)
    return np.arctan2(np.cos(eps) * np.sin(lam), np.cos(lam))


def orbit(h_km, ltan_h, u0):
    a = RE + h_km
    n = np.sqrt(MU / a ** 3)
    rdot = 2 * np.pi / (365.2422 * 86400)
    inc = np.arccos(-rdot / (1.5 * n * J2 * (RE / a) ** 2))
    t = np.arange(0, (T1 - T0).total_seconds(), DT)
    raan = sun_ra(T0) + np.deg2rad((ltan_h - 12) * 15) + rdot * t
    u = u0 + n * t
    cu, su, cO, sO, ci, si = np.cos(u), np.sin(u), np.cos(raan), np.sin(raan), np.cos(inc), np.sin(inc)
    x = a * (cO * cu - sO * su * ci); y = a * (sO * cu + cO * su * ci); z = a * su * si
    th = gmst(T0) + WE * t
    xe = np.cos(th) * x + np.sin(th) * y; ye = -np.sin(th) * x + np.cos(th) * y
    r = np.stack([xe, ye, z], 1)
    v = np.gradient(r, DT, axis=0)
    rev = np.floor(u / (2 * np.pi)).astype(int)
    return t, r, v, np.rad2deg(inc), a, rev


def ground_range_km(eta_deg, a):
    eta = np.deg2rad(eta_deg)
    return RE * (np.arcsin(np.clip(a / RE * np.sin(eta), -1, 1)) - eta)


def accesses(t, r, v, lat, lon, eta_min, eta_max, sides, rev=None):
    """sides: "R" right only; "ALT" = roll to right on even and left on odd revolutions
    (a SAR images one side at a time, so both-sides-at-once is not allowed)."""
    la, lo = np.deg2rad(lat), np.deg2rad(lon)
    st = RE * np.array([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)])
    d = np.linalg.norm(r - st, axis=1)
    m = (d[1:-1] < d[:-2]) & (d[1:-1] <= d[2:]) & (d[1:-1] < 2500)
    idx = np.flatnonzero(m) + 1
    los = st - r[idx]
    nad = -r[idx] / np.linalg.norm(r[idx], axis=1)[:, None]
    eta = np.rad2deg(np.arccos(np.sum(los * nad, 1) / np.linalg.norm(los, axis=1)))
    right = np.cross(v[idx], r[idx])
    side = np.where(np.sum(los * right, 1) > 0, "R", "L")
    if sides == "ALT":
        want = np.where(rev[idx] % 2 == 0, "R", "L")
        ok = (eta >= eta_min) & (eta <= eta_max) & (side == want)
    else:
        ok = (eta >= eta_min) & (eta <= eta_max) & np.isin(side, list(sides))
    return t[idx[ok]]


def conus_duty(t, r, v, a, eta_min, eta_max, sides, conus, rev=None):
    """Fraction of time the access swath (any part) overlaps CONUS land: imaging duty cycle."""
    rh = r / np.linalg.norm(r, axis=1)[:, None]
    right = np.cross(v, r); right /= np.linalg.norm(right, axis=1)[:, None]
    over = np.zeros(len(t), bool)
    sgn = np.where(rev % 2 == 0, 1, -1) if sides == "ALT" else np.ones(len(t))
    for _ in [0]:
        for eta in np.linspace(eta_min, eta_max, 3):
            lam = ground_range_km(eta, a) / RE
            g = np.cos(lam) * rh + sgn[:, None] * np.sin(lam) * right
            glat = np.rad2deg(np.arcsin(g[:, 2])); glon = np.rad2deg(np.arctan2(g[:, 1], g[:, 0]))
            over |= shapely.contains_xy(conus, glon, glat)
    return over.mean()


def orbit_designs():
    """Mission feasibility: fly candidate ARMO orbits and test them against ground truth.

    Orbit model: circular sun-synchronous orbit, J2 secular nodal precession (RAAN rate fixed
    to the SSO value), spherical Earth, GMST rotation; 10 s steps over the NISAR era
    (17 Jun - 31 Oct 2026). Access model: a side-looking SAR images a station at broadside
    (closest approach) if the station lies on the looking side(s) with off-nadir angle within
    [eta_min, eta_max]. Every CONUS access is assumed imaged (duty cycle reported).

    For each design the simulated ARMO pass times are added to the REAL Sentinel-1 + NISAR
    pass times and event capture is scored against USCRN ground truth (979 events), averaging
    over 8 initial orbital phases. Outputs: data/processed/armo_designs.csv, armo_access_*.csv"""
    st = pd.read_csv(os.path.join(PROC, "station_seasons.csv"))
    st = st[st.included & (st.season == 2026)].drop_duplicates("wban")[["wban", "lat", "lon"]]
    ev = pd.read_csv(os.path.join(PROC, "events.csv"), parse_dates=["t_start", "t_ws", "t_we"])
    ev = ev[(ev.t_start >= ERA[0]) & (ev.t_start < ERA[1])].reset_index(drop=True)
    ws, we = to_hours(ev.t_ws), to_hours(ev.t_we)
    s1 = pd.read_csv(os.path.join(PROC, "acq_s1.csv"), parse_dates=["time"])
    ni = pd.read_csv(os.path.join(PROC, "acq_nisar.csv"), parse_dates=["time"])
    fleet = {w: np.sort(to_hours(pd.concat([s1[s1.wban == w].time, ni[ni.wban == w].time]))) for w in st.wban}
    t0h = to_hours(pd.DatetimeIndex([T0]))[0]

    states = gpd.read_file(os.path.join(RAW, "naturalearth", "states", "ne_50m_admin_1_states_provinces.shp"))
    conus = states[(states.iso_a2 == "US") & ~states.name.isin(["Alaska", "Hawaii"])].union_all()
    shapely.prepare(conus)

    def score(times_by_w):
        c = np.zeros(len(ev))
        for w, idx in ev.groupby("wban").groups.items():
            i = ev.index.get_indexer(idx)
            obs = np.sort(np.concatenate([fleet.get(w, np.array([])), times_by_w.get(w, np.array([]))]))
            c[i] = captured(obs, ws[i], we[i]) if obs.size else 0
        return c

    base = score({})
    designs = [  # name, altitude, LTAN (asc node, h), off-nadir range, look sides, n satellites
        ("A  1 sat, right-looking, 25-45 deg, dawn-dusk", 620, 18.0, 25, 45, "R", 1),
        ("B  1 sat, roll left/right on alternate orbits, dawn-dusk", 620, 18.0, 25, 45, "ALT", 1),
        ("C  1 sat, roll alternate, wider 20-50 deg access", 620, 18.0, 20, 50, "ALT", 1),
        ("D  2 sats (180 deg apart), right-looking, dawn-dusk", 620, 18.0, 25, 45, "R", 2),
        ("E  2 sats, roll alternate, dawn-dusk", 620, 18.0, 25, 45, "ALT", 2),
    ]
    rows = []
    for name, h, ltan, e0, e1, sides, nsat in designs:
        caps, gaps, ns, duties = [], [], [], []
        for k, u0 in enumerate(np.linspace(0, 2 * np.pi, 8, endpoint=False)):
            tb = {w: [] for w in st.wban}
            for s in range(nsat):
                t, r, v, inc, a, rev = orbit(h, ltan, u0 + s * np.pi)
                if k == 0 and s == 0:
                    duties.append(conus_duty(t, r, v, a, e0, e1, sides, conus, rev))
                for row in st.itertuples():
                    tb[row.wban].append(t0h + accesses(t, r, v, row.lat, row.lon, e0, e1, sides, rev) / 3600)
            tb = {w: np.sort(np.concatenate(x)) for w, x in tb.items()}
            caps.append(score(tb).mean())
            era_h = to_hours(pd.DatetimeIndex(list(ERA)))
            for w, x in tb.items():
                x = x[(x >= era_h[0]) & (x < era_h[1])]
                ns.append(len(x))
                if len(x) > 1:
                    gaps.append(np.diff(np.r_[era_h[0], x, era_h[1]]).mean() / 24)
        swath = ground_range_km(e1, a) - ground_range_km(e0, a)
        rows.append(dict(design=name, altitude_km=h, inclination_deg=round(inc, 2), ltan_asc=ltan,
                         off_nadir=f"{e0}-{e1}", access_swath_km=round(swath), sides=sides, n_sat=nsat,
                         armo_mean_gap_d=np.mean(gaps), armo_looks_per_station=np.mean(ns),
                         capture_fleet_plus_armo=np.mean(caps), capture_min=np.min(caps), capture_max=np.max(caps),
                         gain_pts=(np.mean(caps) - base.mean()) * 100, imaging_duty_conus=duties[0]))
        print(rows[-1], flush=True)
    out = pd.DataFrame(rows)
    out["capture_current_fleet"] = base.mean()
    out.to_csv(os.path.join(PROC, "armo_designs.csv"), index=False)
    print(out.round(3).to_string())


# ====================================================================================================
# performance
# ====================================================================================================

evr = importlib.import_module("01_events")

rng = np.random.default_rng(3)


def head_to_head():
    st = pd.read_csv(os.path.join(PROC, "station_seasons.csv"))
    st = st[st.included & (st.season == 2026)].drop_duplicates("wban")[["wban", "lat", "lon"]]
    ev = pd.read_csv(os.path.join(PROC, "events.csv"), parse_dates=["t_start", "t_ws", "t_we"])
    ev = ev[(ev.t_start >= ERA[0]) & (ev.t_start < ERA[1])].reset_index(drop=True)
    ws, we = to_hours(ev.t_ws), to_hours(ev.t_we)
    s1 = pd.read_csv(os.path.join(PROC, "acq_s1.csv"), parse_dates=["time"])
    ni = pd.read_csv(os.path.join(PROC, "acq_nisar.csv"), parse_dates=["time"])
    real = {"s1": {w: np.sort(to_hours(s1[s1.wban == w].time)) for w in st.wban},
            "ni": {w: np.sort(to_hours(ni[ni.wban == w].time)) for w in st.wban}}
    t0h = to_hours(pd.DatetimeIndex([T0]))[0]
    t_first, t_last = pd.Timestamp("2026-06-01", tz="UTC"), pd.Timestamp("2026-11-10", tz="UTC")

    # ARMO design D passes for 8 orbital phases (2 satellites 180 deg apart, right-looking 25-45 deg)
    armo = []
    for u0 in np.linspace(0, 2 * np.pi, 8, endpoint=False):
        tb = {w: [] for w in st.wban}
        for s in range(2):
            t, r, v, inc, a, rev = orbit(620, 18.0, u0 + s * np.pi)
            for row in st.itertuples():
                tb[row.wban].append(t0h + accesses(t, r, v, row.lat, row.lon, 25, 45, "R", rev) / 3600)
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
        lo, hi = cluster_boot_ci(p, ev.wban, rng)
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


def performance():
    """ARMO head-to-head against NISAR and ROSE-L, and a ground-truth test of deeper-sensing (P-band / UHF) options.

    (a) Head-to-head, each system ON ITS OWN, on the same 979 NISAR-era wetting events (17 Jun - 31 Oct 2026):
        Sentinel-1 and NISAR = real acquisition times; ROSE-L = regular 6-day (ESA, global land) and 3-day (Europe /
        eoPortal) samplers, phase- and dawn/dusk-averaged as in step 02; ARMO = design D flown in the orbit model above
        (2 satellites, 8 orbital phases). Also: ARMO D added to the future fleet (real S1 + NISAR + ROSE-L 6-day).
    (b) Sensing depth. Shen et al. (2021) find P-band retrieves soil moisture over ~7 cm (vs ~5 cm at L-band), and
        > 10 cm below 0.5 GHz (UHF). USCRN also reports 10 cm soil moisture, so we rerun the SAME event definition on
        the 10 cm series: how many events, how long they last, and what regular revisits would capture.
    Outputs: data/processed/performance_headtohead.csv, depth_events.csv, depth_summary.csv"""
    head_to_head()
    depth_test()


# ====================================================================================================
# sizing
# ====================================================================================================

MU, RE_MEAN, C, KB = 398600.4418, 6371.0, 2.998e8, 1.380649e-23

H_KM, F_HZ = 620.0, 1.2575e9                  # orbit altitude; L-band centre (EESS 1215-1300 MHz)

LAM = C / F_HZ

ASSUME = dict(
    nesz_req_db=-25.0,       # 2 dB better than NISAR's ~-23 dB requirement (NISAR team, Fringe 2026)
    bandwidth_hz=20e6,       # range bandwidth: ~7.5 m slant resolution, multi-looked to 100-200 m products
    noise_fig_loss_db=6.0,   # receiver noise figure + system/processing losses (assumption)
    scansar_margin_db=3.0,   # extra margin for ScanSAR bursts and scalloping (assumption)
    tx_duty=0.10,            # transmit duty cycle (assumption, typical solid-state SAR)
    sspa_eff=0.35,           # GaN power-amplifier DC-to-RF efficiency (assumption)
    radar_elec_w=150.0,      # receivers, digital electronics, data storage while imaging (assumption)
    bus_w=150.0,             # bus orbit-average power: ADCS, C&DH, thermal, comms standby (assumption)
    xband_w=60.0, xband_rate_bps=400e6,   # downlink transmitter power and rate (assumption, commercial X-band radio)
    bits=4, rx_duty=0.7, n_pol=2,         # BAQ 4-bit samples, receive-window duty, HH + HV
    array_eff=0.28, packing=0.85, degr=0.85, margin_power=1.3,   # solar cells, packing, end-of-life, margin
    max_pass_min=10.0, dod=0.3,           # longest CONUS imaging pass; battery depth of discharge (assumption)
    reflector_kg_ref=8.0, reflector_d_ref=3.35,   # mesh reflector < 8 kg at 3.35 m (Sushko et al., EUSAR 2021)
    mass_margin=0.30,        # mass growth allowance at concept stage (assumption)
    dv_ms=120.0, isp_s=220.0,  # phasing to 180 deg, drag make-up, de-orbit within 5 years (estimate); hydrazine Isp
)


def geom(eta_deg, h=H_KM):
    """Slant range (m) and incidence angle (rad) for off-nadir angle eta on a spherical Earth."""
    r, e = RE_MEAN + h, np.deg2rad(eta_deg)
    R = r * np.cos(e) - np.sqrt(RE_MEAN ** 2 - (r * np.sin(e)) ** 2)
    th = np.arcsin(r * np.sin(e) / RE_MEAN)
    return R * 1e3, th


def sizing():
    """ARMO spacecraft sizing: antenna, radar power, data volume, power and mass budgets, launch and a rough-order cost.

    Physics (first-order, conservative; Ulaby et al. 2014; Freeman et al. 2000):
      antenna area   A >= 4 v lambda R tan(theta_i) / c            (range/azimuth ambiguity constraint, single beam)
      noise floor    NESZ = 16 pi R^3 v k T F L B lambda sin(theta_i) / (P_avg A^2 c)
                     (SAR radar equation for a distributed target, G = 4 pi A / lambda^2; solved for P_avg)
    Orbit and imaging time come from the orbit model above (design D: 620 km dawn-dusk SSO, 25-45 deg off-nadir, CONUS
    imaging duty from armo_designs.csv). Every engineering assumption is listed in ASSUME and printed; values without a
    public source are our estimates, not facts. Outputs: data/processed/armo_sizing.csv, armo_mass.csv, armo_cost.csv"""
    a = ASSUME
    v = np.sqrt(MU / (RE_MEAN + H_KM)) * 1e3
    D = pd.read_csv(os.path.join(PROC, "armo_designs.csv"))
    duty_conus = float(D[D.design.str.startswith("D")].imaging_duty_conus.iloc[0])
    rows = {}
    for eta in (25, 35, 45):
        R, th = geom(eta)
        rows[eta] = dict(R_km=R / 1e3, inc_deg=np.rad2deg(th), A_min_m2=4 * v * LAM * R * np.tan(th) / C)
    A_min = rows[45]["A_min_m2"]                      # worst case: far edge of the access range
    D_refl = np.ceil(np.sqrt(4 * A_min / np.pi) * 10) / 10   # reflector diameter meeting it, rounded up 0.1 m
    A = np.pi * D_refl ** 2 / 4
    FL = 10 ** ((a["noise_fig_loss_db"] + a["scansar_margin_db"]) / 10); nesz = 10 ** (a["nesz_req_db"] / 10)
    R45, th45 = geom(45)
    P_avg = 16 * np.pi * R45 ** 3 * v * KB * 290 * FL * a["bandwidth_hz"] * LAM * np.sin(th45) / (nesz * A ** 2 * C)
    P_peak = P_avg / a["tx_duty"]
    radar_dc = P_avg / a["sspa_eff"] + a["radar_elec_w"]
    # data
    rate = a["n_pol"] * 1.2 * a["bandwidth_hz"] * 2 * a["bits"] * a["rx_duty"]       # bit/s while imaging
    img_s_day = duty_conus * 86400
    vol_bits = rate * img_s_day
    dl_s = vol_bits / a["xband_rate_bps"]
    # power
    orbit_avg = a["bus_w"] + radar_dc * duty_conus + a["xband_w"] * dl_s / 86400
    array_m2 = orbit_avg * a["margin_power"] / (1361 * a["array_eff"] * a["packing"] * a["degr"])
    batt_wh = (radar_dc + a["bus_w"]) * a["max_pass_min"] / 60 / a["dod"]
    siz = dict(v_ms=v, lambda_m=LAM, **{f"R_{k}_km": r["R_km"] for k, r in rows.items()},
               **{f"inc_{k}_deg": r["inc_deg"] for k, r in rows.items()}, **{f"Amin_{k}_m2": r["A_min_m2"] for k, r in rows.items()},
               reflector_d_m=D_refl, antenna_area_m2=A, P_avg_rf_w=P_avg, P_peak_rf_w=P_peak, radar_dc_w=radar_dc,
               data_rate_mbps=rate / 1e6, imaging_min_day=img_s_day / 60, data_gb_day=vol_bits / 8e9,
               downlink_min_day=dl_s / 60, orbit_avg_w=orbit_avg, array_m2=array_m2, battery_wh=batt_wh,
               duty_conus=duty_conus)
    # mass budget per satellite (current best estimate, kg)
    refl = a["reflector_kg_ref"] * (D_refl / a["reflector_d_ref"]) ** 2
    m = [("L-band mesh reflector (scaled by area from < 8 kg at 3.35 m)", refl, "Sushko et al. (2021), scaled"),
         ("Deployable boom and dual-pol L-band feed array", 18.0, "estimate"),
         ("SAR electronics: GaN amplifiers, receivers, digital, storage", 25.0, "estimate"),
         ("Structure and mechanisms", 45.0, "estimate"),
         (f"Power: {array_m2:.1f} m² array, {batt_wh:.0f} Wh battery, PCDU", 22.0, "estimate"),
         ("Attitude control: wheels, star trackers, magnetorquers", 18.0, "estimate"),
         ("Command and data handling; X-band downlink; S-band TT&C", 10.0, "estimate"),
         ("Thermal, harness", 12.0, "estimate"),
         ("Propulsion (dry)", 8.0, "estimate")]
    dry_cbe = sum(x[1] for x in m)
    dry = dry_cbe * (1 + a["mass_margin"])
    prop = dry * (np.exp(a["dv_ms"] / (9.80665 * a["isp_s"])) - 1)
    wet = dry + prop
    mass = pd.DataFrame(m, columns=["item", "kg", "basis"])
    mass = pd.concat([mass, pd.DataFrame([
        ("Dry mass, current best estimate", dry_cbe, "sum"),
        (f"Dry mass with {a['mass_margin']:.0%} growth margin", dry, "AIAA-style concept margin (assumption)"),
        (f"Propellant ({a['dv_ms']:.0f} m/s, Isp {a['isp_s']:.0f} s)", prop, "rocket equation"),
        ("Wet mass per satellite", wet, ""),
        ("Two satellites at launch", 2 * wet, "")], columns=["item", "kg", "basis"])], ignore_index=True)
    siz.update(dry_cbe_kg=dry_cbe, dry_kg=dry, prop_kg=prop, wet_kg=wet, launch_kg=2 * wet)
    # cost (FY2026 US$ M), rough order of magnitude (+-40 %)
    sal, idc = 101_920, 0.62                                   # BLS median geoscientist; MIT F&A rate (Section 5)
    fte = lambda n, yrs: n * sal * (1 + idc) * yrs / 1e6
    gs_min_day = 2 * siz["downlink_min_day"] * 1.5            # both satellites, 50 % pass-overhead margin
    cost = [("A-D", "PI, science team and algorithm development (3 FTE, 5 yr)", fte(3, 5), "BLS salary + 62 % F&A"),
            ("A-D", "Flight system: 2 spacecraft with L-band SAR (first unit incl. development 45, second 25)", 70.0,
             "Analogy: NovaSAR-1 ≈ £45 M build + launch (2011); CYGNSS US$ 102 M excl. launch (8 microsats)"),
            ("A-D", "Project management, systems engineering, mission assurance, integration and test (20 %)", 14.0, "estimate"),
            ("A-D", "Ground and science data systems", 6.0, "estimate"),
            ("A-D", "Launch: one dedicated small launcher for both satellites", 15.0, "Firefly Alpha class (≈ US$ 15 M, secondary sources)"),
            ("E", "Mission operations team (6 FTE, 3 yr)", fte(6, 3), "BLS salary + 62 % F&A"),
            ("E", "Sustaining engineering, software and ground-system maintenance (3 yr)", 3.0, "estimate"),
            ("E", f"Ground-station contacts ({gs_min_day:.0f} min/day at ≈ US$ 20/min, 3 yr)", gs_min_day * 365 * 3 * 20 / 1e6, "estimate (commercial ground-station pricing)"),
            ("E", "Science team, processing and open data distribution (3 FTE + cloud, 3 yr)", fte(3, 3) + 0.3, "BLS salary + 62 % F&A; AWS")]
    cost = pd.DataFrame(cost, columns=["phase", "item", "usd_m", "basis"])
    ad = cost[cost.phase == "A-D"].usd_m.sum(); e = cost[cost.phase == "E"].usd_m.sum()
    cost = pd.concat([cost, pd.DataFrame([("A-D", "Reserve, 30 % of Phases A-D", 0.30 * ad, "assumption (EVM-3 AO sets reserve rules)"),
                                          ("E", "Reserve, 15 % of Phase E", 0.15 * e, "assumption")],
                                         columns=cost.columns)], ignore_index=True)
    siz.update(cost_AD=cost[cost.phase == "A-D"].usd_m.sum(), cost_E=cost[cost.phase == "E"].usd_m.sum())
    siz["cost_total"] = siz["cost_AD"] + siz["cost_E"]
    # threshold mission (design C, one satellite): drop the second flight unit, its 20 % wrap and its 30 % reserve
    siz["cost_threshold"] = siz["cost_total"] - 25.0 * 1.2 * 1.3
    siz["flight_share"] = 70.0 / siz["cost_total"]
    siz["evm_cap"] = 190.0
    pd.DataFrame([siz]).to_csv(os.path.join(PROC, "armo_sizing.csv"), index=False)
    mass.to_csv(os.path.join(PROC, "armo_mass.csv"), index=False)
    cost.to_csv(os.path.join(PROC, "armo_cost.csv"), index=False)
    print(pd.Series(siz).round(3).to_string()); print(mass.round(1).to_string()); print(cost.round(2).to_string())


# ====================================================================================================
# event_flags (optional; added 3 Nov 2026 for the evidence figures; does not change the outputs above)
# ====================================================================================================

def broadside_passes(t, r, v, lat, lon, rev):
    """Every closest approach (< 2,500 km) of one orbit to one station: time (s), off-nadir angle (deg), side, revolution.
    Same geometry as accesses(); the design filters (angle range, side) are applied afterwards."""
    la, lo = np.deg2rad(lat), np.deg2rad(lon)
    st = RE * np.array([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)])
    d = np.linalg.norm(r - st, axis=1)
    m = (d[1:-1] < d[:-2]) & (d[1:-1] <= d[2:]) & (d[1:-1] < 2500)
    idx = np.flatnonzero(m) + 1
    los = st - r[idx]
    nad = -r[idx] / np.linalg.norm(r[idx], axis=1)[:, None]
    eta = np.rad2deg(np.arccos(np.sum(los * nad, 1) / np.linalg.norm(los, axis=1)))
    side = np.where(np.sum(los * np.cross(v[idx], r[idx]), 1) > 0, "R", "L")
    return t[idx], eta, side, rev[idx]


DESIGNS = {"A": (25, 45, "R", 1), "B": (25, 45, "ALT", 1), "C": (20, 50, "ALT", 1), "D": (25, 45, "R", 2), "E": (25, 45, "ALT", 2)}
SWATH_KM = (50, 100, 200, 250, 300)


def event_flags():
    """Per-event, per-orbital-phase ARMO look flags on the matched 979-event cohort, for paired statistics, plus a
    usable-swath sensitivity for design D.

    Geometry, phases and the capture rule are identical to orbit_designs()/head_to_head(): each of the 8 initial
    phases u0 flies satellite 1 at u0 and (designs D, E) satellite 2 at u0 + pi. A pass "looks" at a station when
    the station is on an allowed side within the design's off-nadir range at closest approach.
    Swath sensitivity (design D, HYPOTHETICAL): the 25-45 deg off-nadir range is an ACCESS corridor (~362 km of ground
    range). A real SAR images only a strip of usable width W inside it on each pass. Two deterministic tasking rules:
      fixed  - one strip of width W centred in the corridor on every pass (no tasking);
      cycled - ceil(362/W) overlapping strips whose centres are evenly spaced so together they just span the corridor;
               each satellite steps to the next strip every revolution (station-agnostic tasking).
    A station is imaged only if its ground-range offset lies inside the active strip. W = 362 km equals the baseline.
    This is a feasibility envelope, not a demonstrated imaging mode.
    Outputs: data/processed/armo_event_capture_by_phase.csv, armo_swath_event_capture.csv, armo_swath_gaps.csv"""
    st = pd.read_csv(os.path.join(PROC, "station_seasons.csv"))
    st = st[st.included & (st.season == 2026)].drop_duplicates("wban")[["wban", "lat", "lon"]]
    ev = pd.read_csv(os.path.join(PROC, "events.csv"), parse_dates=["t_start", "t_ws", "t_we"])
    ev = ev[(ev.t_start >= ERA[0]) & (ev.t_start < ERA[1])].reset_index(drop=True)
    ws, we = to_hours(ev.t_ws), to_hours(ev.t_we)
    s1 = pd.read_csv(os.path.join(PROC, "acq_s1.csv"), parse_dates=["time"])
    ni = pd.read_csv(os.path.join(PROC, "acq_nisar.csv"), parse_dates=["time"])
    fleet = {w: np.sort(to_hours(pd.concat([s1[s1.wban == w].time, ni[ni.wban == w].time]))) for w in st.wban}
    t0h = to_hours(pd.DatetimeIndex([T0]))[0]
    e0, e1 = to_hours(pd.DatetimeIndex(list(ERA)))
    groups = {w: ev.index.get_indexer(ix) for w, ix in ev.groupby("wban").groups.items()}

    def flags(times_by_w, with_fleet):
        out = np.zeros(len(ev), bool)
        for w, i in groups.items():
            obs = times_by_w.get(w, np.array([]))
            if with_fleet:
                obs = np.concatenate([fleet.get(w, np.array([])), obs])
            obs = np.sort(obs)
            out[i] = captured(obs, ws[i], we[i]) if obs.size else False
        return out

    base = flags({}, True)                    # real fleet only (ARMO times empty)
    phases = np.linspace(0, 2 * np.pi, 8, endpoint=False)
    a_km = RE + 620
    g_lo, g_hi = ground_range_km(25, a_km), ground_range_km(45, a_km)
    rows, srows, grows = [], [], []
    for k, u0 in enumerate(phases):
        passes = {}                            # (sat, wban) -> (t_h, eta, side, rev)
        for s in (0, 1):
            t, r, v, inc, a, rev = orbit(620, 18.0, u0 + s * np.pi)
            for row in st.itertuples():
                tt, eta, side, rv = broadside_passes(t, r, v, row.lat, row.lon, rev)
                passes[(s, row.wban)] = (t0h + tt / 3600, eta, side, rv)
        for name, (lo, hi, sides, nsat) in DESIGNS.items():
            tb = {}
            for w in st.wban:
                keep = []
                for s in range(nsat):
                    tt, eta, side, rv = passes[(s, w)]
                    ok = (eta >= lo) & (eta <= hi)
                    ok &= (side == np.where(rv % 2 == 0, "R", "L")) if sides == "ALT" else np.isin(side, list(sides))
                    keep.append(tt[ok])
                tb[w] = np.sort(np.concatenate(keep))
            alone, comb = flags(tb, False), flags(tb, True)
            rows.append(pd.DataFrame(dict(wban=ev.wban, t_ws=ev.t_ws, design=name, phase=k, fleet_look=base,
                                          armo_look=alone, combined_look=comb)))
        # usable-swath sensitivity, design D
        for W in SWATH_KM + (362,):
            for mode in ("fixed", "cycled"):
                if W == 362 and mode == "cycled":
                    continue
                nstrip = int(np.ceil((g_hi - g_lo) / W - 1e-9))
                tb = {}
                for w in st.wban:
                    keep = []
                    for s in range(2):
                        tt, eta, side, rv = passes[(s, w)]
                        ok = (eta >= 25) & (eta <= 45) & (side == "R")
                        g = ground_range_km(eta, a_km)
                        if W < 362:
                            if mode == "fixed":
                                c = (g_lo + g_hi) / 2
                                ok &= (g >= c - W / 2) & (g <= c + W / 2)
                            else:   # nstrip overlapping strips, centres evenly spaced so the strips just span the corridor
                                j = (rv + s) % nstrip
                                cj = np.linspace(g_lo + W / 2, g_hi - W / 2, nstrip)[j]
                                ok &= (g >= cj - W / 2) & (g <= cj + W / 2)
                        keep.append(tt[ok])
                    tb[w] = np.sort(np.concatenate(keep))
                lab = "baseline 362 km (whole access corridor)" if W == 362 else f"{W} km {mode}"
                srows.append(pd.DataFrame(dict(wban=ev.wban, t_ws=ev.t_ws, swath_km=W, mode="baseline" if W == 362 else mode,
                                               scenario=lab, phase=k, fleet_look=base, armo_look=flags(tb, False),
                                               combined_look=flags(tb, True))))
                for w, x in tb.items():
                    x = x[(x >= e0) & (x < e1)]
                    d = np.diff(np.r_[e0, x, e1]) / 24 if len(x) else np.array([(e1 - e0) / 24])
                    d = d[d > 0.25]
                    grows.append(dict(scenario=lab, swath_km=W, mode="baseline" if W == 362 else mode, phase=k, wban=w,
                                      n_looks=len(x), gaps_d=";".join(f"{g_:.4f}" for g_ in d)))
        print("phase", k, "done", flush=True)
    out = pd.concat(rows, ignore_index=True)
    out.to_csv(os.path.join(PROC, "armo_event_capture_by_phase.csv"), index=False)
    pd.concat(srows, ignore_index=True).to_csv(os.path.join(PROC, "armo_swath_event_capture.csv"), index=False)
    pd.DataFrame(grows).to_csv(os.path.join(PROC, "armo_swath_gaps.csv"), index=False)
    print(out.groupby("design")[["fleet_look", "armo_look", "combined_look"]].mean().round(4).to_string())


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "event_flags":
        event_flags()          # optional: python 06_mission_design.py event_flags
    else:
        orbit_designs()
        performance()
        sizing()
