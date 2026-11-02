"""Objective 3a: Sentinel-1 C-band backscatter at every USCRN station (field scale).

Product: Sentinel-1 Radiometrically Terrain Corrected (RTC) gamma0, 10 m, VV and VH,
Microsoft Planetary Computer collection `sentinel-1-rtc` (anonymous SAS token).
Only the 11 x 11 pixel (~110 m) window around each station is read (HTTP range
requests on cloud-optimised GeoTIFFs), so no full scenes are downloaded.
Output: data/processed/s1_backscatter.csv
"""
import os
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd
import pystac_client
import planetary_computer as pc
import rasterio
from rasterio.windows import Window
from pyproj import Transformer
from common import PROC

SEASONS = ["2025-04-01/2025-10-31", "2026-04-01/2026-10-31"]
HALF = 5  # 11 x 11 window
OUT = os.path.join(PROC, "s1_backscatter.csv")
GDAL_ENV = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MULTIRANGE="YES",
                CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.tiff", GDAL_HTTP_MAX_RETRY="4", GDAL_HTTP_RETRY_DELAY="2",
                GDAL_HTTP_TIMEOUT="45", GDAL_HTTP_CONNECTTIMEOUT="20")


def window_stats(href, lon, lat):
    with rasterio.open(href) as src:
        x, y = Transformer.from_crs(4326, src.crs, always_xy=True).transform(lon, lat)
        r, c = src.index(x, y)
        a = src.read(1, window=Window(c - HALF, r - HALF, 2 * HALF + 1, 2 * HALF + 1), boundless=True,
                     fill_value=np.nan).astype(float)
        a[(a <= 0) | (a == src.nodata)] = np.nan
    if np.isfinite(a).sum() < 0.5 * a.size:
        return np.nan, np.nan, np.nan
    core = a[HALF - 1:HALF + 2, HALF - 1:HALF + 2]
    # spatial coefficient of variation of linear power: heterogeneity around the probe
    return 10 * np.log10(np.nanmean(a)), 10 * np.log10(np.nanmean(core)), np.nanstd(a) / np.nanmean(a)


def search(row):
    cat = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")
    items = []
    for season in SEASONS:
        items += list(cat.search(collections=["sentinel-1-rtc"], datetime=season,
                                 intersects={"type": "Point", "coordinates": [row.lon, row.lat]}).items())
    return items


def scene(args):
    row, it = args
    rec = dict(wban=row.wban, time=it.datetime, platform=str(it.properties.get("platform", "")).lower(),
               orbit_state=it.properties.get("sat:orbit_state"), rel_orbit=it.properties.get("sat:relative_orbit"))
    try:
        with rasterio.Env(**GDAL_ENV):
            # sign at read time: planetary_computer caches and refreshes the SAS token
            rec["vv_db"], rec["vv_db_3x3"], rec["vv_cv"] = window_stats(pc.sign(it.assets["vv"].href), row.lon, row.lat)
            rec["vh_db"], rec["vh_db_3x3"], rec["vh_cv"] = window_stats(pc.sign(it.assets["vh"].href), row.lon, row.lat)
    except Exception as e:
        rec["error"] = str(e)[:120]
    return rec


if __name__ == "__main__":
    cache = os.path.join(PROC, "s1_cache")
    os.makedirs(cache, exist_ok=True)
    st = pd.read_csv(os.path.join(PROC, "station_seasons.csv"))
    st = st[st.included].drop_duplicates("wban")[["wban", "name", "lat", "lon"]]
    todo = [r for r in st.itertuples() if not os.path.exists(os.path.join(cache, f"{r.wban}.csv"))]
    with ThreadPoolExecutor(24) as ex:
        for i in range(0, len(todo), 6):
            chunk = todo[i:i + 6]
            found = list(ex.map(search, chunk))
            jobs = [(r, it) for r, its in zip(chunk, found) for it in its]
            recs = list(ex.map(scene, jobs))
            for r in chunk:
                pd.DataFrame([x for x in recs if x["wban"] == r.wban]).to_csv(os.path.join(cache, f"{r.wban}.csv"), index=False)
            print(f"done {i + len(chunk)}/{len(todo)} stations, {len(jobs)} scenes", flush=True)
    df = pd.concat([pd.read_csv(os.path.join(cache, f)) for f in os.listdir(cache)
                    if os.path.getsize(os.path.join(cache, f)) > 10], ignore_index=True)
    df.to_csv(OUT, index=False)
    print(len(df), "rows;", df.vv_db.notna().sum(), "valid VV")
