"""Is each Sentinel-1 / NISAR acquisition drawn in the case-study time series a USABLE observation at the station?

acq_s1.csv and acq_nisar.csv list passes whose footprint contains the station (metadata only). This script reads the
pixel itself:
  Sentinel-1 RTC (Planetary Computer): VV gamma0 in a 3 x 3 window (10 m pixels) at the station; valid if > 0.
  NISAR L2 GCOV (ASF, Earthdata login): `mask` at the station's 20 m / 10 m sample and in a 200 m box; valid if the
    station sample has a subswath number (1..254). 0 = partially focused / invalid, 255 = outside the swath.
Output: data/processed/acquisition_validity.csv (read by figures/fig_case_studies.py to style the acquisition lines)
Run: python code/14_check_station_validity.py   (needs an Earthdata login in ~/.netrc for the NISAR masks)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
import pandas as pd
import fsspec
import h5py
import rasterio
import pystac_client
import planetary_computer as pc
from rasterio.windows import Window
from pyproj import Transformer
from common import PROC
import importlib
_gcov = importlib.import_module("13_extract_nisar_gcov")
granule_url, G = _gcov.granule_url, _gcov.G

STATIONS = {53926: (-97.09, 36.12, "2026-08-08", "2026-08-31"), 3067: (-100.96, 38.87, "2026-07-22", "2026-08-23"),
            54808: (-88.37, 40.05, "2026-08-31", "2026-09-21")}
GDAL_ENV = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MAX_RETRY="4", GDAL_HTTP_RETRY_DELAY="2")
OUT = os.path.join(PROC, "acquisition_validity.csv")
done = pd.read_csv(OUT) if os.path.exists(OUT) else pd.DataFrame(columns=["wban", "sensor", "time", "id"])
rows = done.to_dict("records")
have = set(zip(done.wban, done.sensor, done["id"]))
cat = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")
s1 = pd.read_csv(os.path.join(PROC, "acq_s1.csv"), parse_dates=["time"])
ni = pd.read_csv(os.path.join(PROC, "acq_nisar.csv"), parse_dates=["time"])
for w, (lon, lat, a, b) in STATIONS.items():
    for _, r in s1[(s1.wban == w) & (s1.time >= a) & (s1.time < b)].iterrows():
        t = r.time
        items = [i for i in cat.search(collections=["sentinel-1-rtc"], intersects={"type": "Point", "coordinates": [lon, lat]},
                                       datetime=f"{(t - pd.Timedelta(minutes=2)):%Y-%m-%dT%H:%M:%SZ}/{(t + pd.Timedelta(minutes=2)):%Y-%m-%dT%H:%M:%SZ}").items()]
        for it in items:
            if (w, "Sentinel-1", it.id) in have:
                continue
            with rasterio.Env(**GDAL_ENV), rasterio.open(pc.sign(it.assets["vv"].href)) as src:
                x, y = Transformer.from_crs(4326, src.crs, always_xy=True).transform(lon, lat)
                rr, cc = src.index(x, y)
                v = src.read(1, window=Window(cc - 1, rr - 1, 3, 3), boundless=True, fill_value=0).astype(float)
            ok = bool((v > 0).all())
            rows.append(dict(wban=w, sensor="Sentinel-1", time=str(t), id=it.id, valid=ok, station_value_db=float(10 * np.log10(v[1, 1])) if v[1, 1] > 0 else np.nan,
                             detail="VV > 0 in 3 x 3 window" if ok else "no RTC data at station"))
            print(rows[-1]); pd.DataFrame(rows).to_csv(OUT, index=False)
    for _, r in ni[(ni.wban == w) & (ni.time >= a) & (ni.time < b)].iterrows():
        if (w, "NISAR", r.granule) in have:
            continue
        with fsspec.filesystem("https").open(granule_url(r.granule), "rb", block_size=2 * 2**20, cache_type="blockcache") as fh, h5py.File(fh, "r") as h:
            epsg = int(h[G + "projection"][()])
            x, y = h[G + "xCoordinates"][:], h[G + "yCoordinates"][:]
            dx = float(h[G + "xCoordinateSpacing"][()])
            sx, sy = Transformer.from_crs(4326, epsg, always_xy=True).transform(lon, lat)
            j, i = int(np.argmin(np.abs(x - sx))), int(np.argmin(np.abs(y - sy)))
            k = int(100 / dx)
            inside = abs(x[j] - sx) <= dx and abs(y[i] - sy) <= dx
            m = h[G + "mask"][max(i - k, 0):i + k + 1, max(j - k, 0):j + k + 1] if inside else np.array([[255]])
            hh = float(h[G + "HHHH"][i, j]) if inside else np.nan
        ms = int(m[min(k, m.shape[0] - 1), min(k, m.shape[1] - 1)]) if inside else 255
        ok = 1 <= ms <= 254
        frac = float(((m >= 1) & (m <= 254)).mean())
        rows.append(dict(wban=w, sensor="NISAR", time=str(r.time), id=r.granule, valid=ok, station_value_db=10 * np.log10(hh) if hh > 0 else np.nan,
                         detail=f"mask {ms} at station; {frac:.0%} of 200 m box valid" if inside else "station outside the frame grid"))
        print(rows[-1]); pd.DataFrame(rows).to_csv(OUT, index=False)
pd.DataFrame(rows).to_csv(OUT, index=False)
print(pd.DataFrame(rows)[["wban", "sensor", "time", "valid", "detail"]].to_string())
