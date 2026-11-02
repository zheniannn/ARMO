"""Mission feasibility: fly candidate ARMO orbits and test them against ground truth.

Orbit model: circular sun-synchronous orbit, J2 secular nodal precession (RAAN rate fixed
to the SSO value), spherical Earth, GMST rotation; 10 s steps over the NISAR era
(17 Jun - 31 Oct 2026). Access model: a side-looking SAR images a station at broadside
(closest approach) if the station lies on the looking side(s) with off-nadir angle within
[eta_min, eta_max]. Every CONUS access is assumed imaged (duty cycle reported).

For each design the simulated ARMO pass times are added to the REAL Sentinel-1 + NISAR
pass times and event capture is scored against USCRN ground truth (979 events), averaging
over 8 initial orbital phases. Outputs: data/processed/armo_designs.csv, armo_access_*.csv
"""
import os
import numpy as np
import pandas as pd
import geopandas as gpd
import shapely
from common import PROC, RAW, to_hours, captured

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


if __name__ == "__main__":
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
