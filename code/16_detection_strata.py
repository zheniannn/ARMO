"""Why do sampled events go undetected? Detection rate by vegetation (MODIS NDVI at the event,
from Earth Engine), by land cover (ESA WorldCover at the probe) and by event size, for
Sentinel-1 VV, NISAR SME2, NISAR HH and SMAP (all retrievals). Each sensor keeps its own
1-sigma no-change noise threshold from scripts 06, 08 and 15.
Outputs: data/processed/detection_strata.csv, station_vegetation.csv
"""
import os
import numpy as np
import pandas as pd
from common import PROC


def rd(f, **k): return pd.read_csv(os.path.join(PROC, f), **k)


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
