"""Can an optical (multispectral/hyperspectral/thermal) sensor see wetting events? Cloud test against USCRN events.

Rain causes the events, and rain comes with cloud. For every event window [t_ws, t_we] we ask whether a clear-sky
optical look exists at the real overpass time:
  MODIS Terra (~10:30 local solar; the same morning slot as Sentinel-2 and Landsat) and Aqua (~13:30), daily,
  Google Earth Engine MODIS/061/MOD09GA and MYD09GA 'state_1km'. Clear = cloud-state bits 0-1 == 0 and cloud-shadow
  bit 2 == 0 at the station pixel.
A look counts only if its overpass time (local solar 10:30 / 13:30 -> UTC via longitude) falls inside the window.
Results: (a) daily optical (Terra+Aqua) = best case for any optical sensor; (b) a morning optical sensor with
regular revisit R = 1, 2, 3, 5, 8 days at random phase (Terra days subsampled), compared with an all-weather
sensor (radar) of the same revisit. Needs `earthengine authenticate`. Outputs: data/processed/optical_state.csv,
optical_capture.csv
"""
import os
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd
import ee
from common import PROC

ee.Initialize(project=os.environ.get("EE_PROJECT", "my-ee-project-ntu-512914"))
SEASONS = [("2025-04-01", "2025-11-01"), ("2026-04-01", "2026-11-01")]
LST = {"terra": 10.5, "aqua": 13.5}


def state(r):
    out = []
    for cid, sat in (("MODIS/061/MOD09GA", "terra"), ("MODIS/061/MYD09GA", "aqua")):
        for t0, t1 in SEASONS:
            for k in range(3):
                try:
                    rows = ee.ImageCollection(cid).filterDate(t0, t1).select("state_1km").getRegion(
                        ee.Geometry.Point([r.lon, r.lat]), 1000).getInfo()
                    d = pd.DataFrame(rows[1:], columns=rows[0])
                    out.append(pd.DataFrame(dict(wban=r.wban, sat=sat, date=pd.to_datetime(d.time, unit="ms").dt.normalize(),
                                                 state=d.state_1km)))
                    break
                except Exception:
                    pass
    return pd.concat(out) if out else pd.DataFrame()


if __name__ == "__main__":
    ev = pd.read_csv(os.path.join(PROC, "events.csv"))
    for c in ("t_ws", "t_we"):
        ev[c] = pd.to_datetime(ev[c], utc=True)
    stn = ev.groupby("wban")[["lat", "lon"]].first().reset_index()
    f = os.path.join(PROC, "optical_state.csv")
    if not os.path.exists(f):
        with ThreadPoolExecutor(8) as ex:
            pd.concat(list(ex.map(state, stn.itertuples())), ignore_index=True).to_csv(f, index=False)
    st = pd.read_csv(f).dropna(subset=["state"])
    s = st.state.astype(int); st["clear"] = ((s & 0b11) == 0) & ((s & 0b100) == 0)
    st["date"] = pd.to_datetime(st.date, utc=True)
    lon = stn.set_index("wban").lon
    st["t_obs"] = st.date + pd.to_timedelta(st.sat.map(LST) - st.wban.map(lon) / 15.0, unit="h")   # local solar -> UTC
    print(f"stations {st.wban.nunique()}; clear-sky share of all overpasses {st.clear.mean():.1%}")
    by = {k: v for k, v in st.groupby("wban")}
    rng = np.random.default_rng(7)
    rows = []
    for e in ev.itertuples():
        x = by.get(e.wban)
        if x is None:
            continue
        inw = x[(x.t_obs >= e.t_ws) & (x.t_obs <= e.t_we)]
        terra = inw[inw.sat == "terra"]
        r = dict(wban=e.wban, season=e.season, window_h=e.window_h, daily_any=bool(inw.clear.any()),
                 terra_any=bool(terra.clear.any()), n_days=terra.date.nunique())
        # regular morning sensor with revisit R (days), random phase: optical needs clear; radar just needs the pass
        days = terra.date.dt.floor("D").to_numpy().astype("datetime64[D]").astype(np.int64)
        clr = terra.clear.to_numpy()
        for R in (1, 2, 3, 5, 8):
            ph = rng.integers(0, R, 200)
            sel = (days[None, :] - ph[:, None]) % R == 0
            r[f"opt_R{R}"] = float(np.mean((sel & clr[None, :]).any(1))) if days.size else 0.0
            r[f"sar_R{R}"] = float(np.mean(sel.any(1))) if days.size else 0.0
        rows.append(r)
    o = pd.DataFrame(rows)
    o.to_csv(os.path.join(PROC, "optical_events.csv"), index=False)
    summ = [dict(sensor="Daily optical, Terra + Aqua (best case)", revisit_d=0.5, capture=o.daily_any.mean())]
    for R in (1, 2, 3, 5, 8):
        summ.append(dict(sensor=f"Morning optical, {R}-day", revisit_d=R, capture=o[f"opt_R{R}"].mean(),
                         same_revisit_all_weather=o[f"sar_R{R}"].mean()))
    sm = pd.DataFrame(summ); sm.to_csv(os.path.join(PROC, "optical_capture.csv"), index=False)
    print(f"events {len(o)}"); print(sm.round(3).to_string(index=False))
