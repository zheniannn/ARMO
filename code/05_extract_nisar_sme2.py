"""Objective 3b: NISAR L-band soil moisture (L3 SME2, PROVISIONAL V1, 200 m EASE-Grid 2.0)
and L-band backscatter at every USCRN station, 17 Jun - 31 Oct 2026.

Access: NASA Earthdata Login (credentials read by `requests` from the user's ~/.netrc;
nothing is stored in this repository). Only 3 x 3 pixel windows are read from each
~120 MB HDF5 granule using HTTP range requests (fsspec + h5py).
HDF5 paths (from the product itself):
  /science/LSAR/SME2/grids/soilMoisture            averaged recommended retrieval (m3/m3)
  /science/LSAR/SME2/grids/retrievalQualityFlag    bit0: 0 = recommended
  /science/LSAR/SME2/grids/radarData/frequencyA/sigma0HH (linear; HV is not used)
  /science/LSAR/SME2/grids/latitude, longitude     1-D (EASE-2 is cylindrical)
Output: data/processed/nisar_sme2_points.csv
"""
import os
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import numpy as np
import pandas as pd
import requests
import fsspec
import h5py
from common import PROC

CMR = "https://cmr.earthdata.nasa.gov/search/granules.umm_json"
G = "science/LSAR/SME2/grids/"
OUT = os.path.join(PROC, "nisar_sme2_points.csv")
CACHE = os.path.join(PROC, "nisar_cache")
os.makedirs(CACHE, exist_ok=True)


def granules(row):
    r = requests.get(CMR, params={"short_name": "NISAR_L3_SME2_PROVISIONAL_V1", "point": f"{row.lon},{row.lat}",
                                  "temporal": "2026-06-17T00:00:00Z,2026-11-01T00:00:00Z", "page_size": 200}, timeout=60)
    out = []
    for it in r.json()["items"]:
        u = it["umm"]
        url = [x["URL"] for x in u["RelatedUrls"] if x.get("Type") == "GET DATA" and x["URL"].startswith("https")
               and x["URL"].endswith(".h5") and "QA_STATS" not in x["URL"]]
        if url:
            out.append(dict(wban=row.wban, lat=row.lat, lon=row.lon, granule=u["GranuleUR"], url=url[0],
                            time=u["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"]))
    return out


def window(ds, i, j):
    i0, j0 = max(i - 1, 0), max(j - 1, 0)
    return ds[i0:i + 2, j0:j + 2].astype(float)


def read_granule(args):
    gid, rows = args
    f_out = os.path.join(CACHE, gid + ".csv")
    if os.path.exists(f_out):
        return pd.read_csv(f_out)
    recs = []
    try:
        s = requests.Session()
        r0 = s.get(rows[0]["url"], headers={"Range": "bytes=0-0"}, timeout=120)
        r0.raise_for_status()                              # fail clearly (e.g. 400/401) instead of opening an error page
        signed = r0.url
        f = fsspec.filesystem("https", client_kwargs={"timeout": __import__("aiohttp").ClientTimeout(total=300)}).open(signed, "rb", block_size=2 * 2**20, cache_type="blockcache")
        with h5py.File(f, "r") as h:
            lat, lon = h[G + "latitude"][:], h[G + "longitude"][:]
            for r in rows:
                i, j = int(np.argmin(np.abs(lat - r["lat"]))), int(np.argmin(np.abs(lon - r["lon"])))
                if abs(lat[i] - r["lat"]) > 0.01 or abs(lon[j] - r["lon"]) > 0.01:
                    continue  # station outside this granule's grid
                sm = window(h[G + "soilMoisture"], i, j)
                fl = window(h[G + "retrievalQualityFlag"], i, j)
                hh = window(h[G + "radarData/frequencyA/sigma0HH"], i, j)
                for a in (sm, hh):
                    a[a <= -9999] = np.nan
                good = (fl >= 0) & ((fl.astype(int) & 1) == 0) & np.isfinite(sm)
                c = sm.shape[0] // 2, sm.shape[1] // 2
                recs.append(dict(wban=r["wban"], granule=gid, time=r["time"],
                                 sm_center=sm[c], flag_center=fl[c], recommended_center=bool(good[c]),
                                 sm_3x3_rec=np.nanmean(np.where(good, sm, np.nan)) if good.any() else np.nan,
                                 sm_3x3_all=np.nanmean(sm), n_rec=int(good.sum()),
                                 hh_db=10 * np.log10(np.nanmean(hh)) if np.isfinite(hh).any() else np.nan))
    except Exception as e:
        # failures are returned but NOT cached, so a re-run retries them
        return pd.DataFrame([dict(wban=rows[0]["wban"], granule=gid, time=rows[0]["time"],
                                  error=f"{type(e).__name__}: {e}"[:300])])
    d = pd.DataFrame(recs)
    d.to_csv(f_out, index=False)
    return d


if __name__ == "__main__":
    st = pd.read_csv(os.path.join(PROC, "station_seasons.csv"))
    st = st[st.included & (st.season == 2026)][["wban", "lat", "lon"]]
    with ThreadPoolExecutor(8) as ex:
        g = pd.DataFrame([x for xs in ex.map(granules, st.itertuples()) for x in xs])
    print("station-granule pairs:", len(g), "unique granules:", g.granule.nunique())
    jobs = [(gid, grp.to_dict("records")) for gid, grp in g.groupby("granule")]
    # h5py serialises HDF5 calls behind a global lock, so use processes, not threads.
    # Few workers and small batches: bursts of range requests trip ASF's rate limit (HTTP 400 from CloudFront).
    # If a whole batch is refused, stop at once (successes stay cached) rather than send thousands of failing requests.
    nw = int(os.environ.get("NISAR_WORKERS", 3))
    res = []
    with ProcessPoolExecutor(nw) as ex:
        for b in range(0, len(jobs), 4 * nw):
            batch = list(ex.map(read_granule, jobs[b:b + 4 * nw]))
            res += batch
            if all("error" in d and str(d.error.iloc[0]).startswith("HTTPError: 400") for d in batch):
                raise SystemExit(f"ASF refused a whole batch at {b}/{len(jobs)} granules (HTTP 400, rate limit); "
                                 f"{len(os.listdir(CACHE))} granules cached; re-run later")
            if b % 120 == 0:
                print(f"{b}/{len(jobs)} granules", flush=True)
    out = pd.concat(res, ignore_index=True)
    err = out["error"].notna().mean() if "error" in out else 0.0
    if err > 0.5:
        raise SystemExit(f"{err:.0%} of granules failed (first error: {out.error.dropna().iloc[0]}); not writing {OUT}")
    out.to_csv(OUT, index=False)
    print(out.describe(include="all").T.head(14))
