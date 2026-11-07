"""Imagery for the slide figures: one wetting event at Stillwater, OK, seen by Sentinel-1, NISAR, SMAP and gridMET.

The case: storms on 17 Aug 2026 (43.6 mm at the USCRN probe) and 22 Aug (31.6 mm) fell between two Sentinel-1 looks
from the same orbit (relative orbit 34, ascending): 13 Aug (dry) and 25 Aug (the second storm's tail). NISAR and SMAP
both looked on 23 Aug, near the second peak.

Downloads (small subsets only; nothing else is fetched):
  Sentinel-1 RTC VV, 13 and 25 Aug, 60 x 60 km around the station at 40 m (COG overview reads, Planetary Computer)
  Sentinel-1 RTC VV, 25 Aug, 24 x 24 km at the native 10 m (resolution ladder)
  gridMET daily rain, 13-24 Aug, summed, 60 x 60 km box (Earth Engine IDAHO_EPSCOR/GRIDMET)
  SMAP L3E 9 km soil moisture, 23 Aug AM (Earth Engine NASA/SMAP/SPL3SMP_E/006)
  NISAR L3 SME2 200 m soil moisture, 23 Aug descending granule (ASF, Earthdata login; HDF5 range reads)
Output: data/processed/imagery/*.npz
"""
import os
import numpy as np
import requests
import fsspec
import h5py
import ee
import pystac_client
import planetary_computer as pc
import rasterio
from rasterio.enums import Resampling
from rasterio.windows import from_bounds
from pyproj import Transformer
from common import PROC

import sys

# Additional wetting cases, chosen from s1_pairs.csv as strong same-orbit 2026 pairs with a large probe rise:
#   oakley    KS_Oakley_19_SSW (3067): 4 -> 16 Aug 2026, descending orbit 85, probe +0.255 m3/m3, +5.5 dB (grassland, farm region)
#   champaign IL_Champaign_9_SW (54808): 4 -> 16 Sep 2026, ascending orbit 19, probe +0.115 m3/m3, +5.2 dB (cropland, near harvest)
# Run: python 12_extract_imagery.py oakley | champaign   (Sentinel-1 pair + gridMET rain only; no SMAP / NISAR subsets)
SITES = {
    "stillwater": dict(lon=-97.09, lat=36.12, orbit=34, s1=["2026-08-13", "2026-08-25"], rain=("2026-08-13", "2026-08-25")),
    "oakley": dict(lon=-100.96, lat=38.87, orbit=85, s1=["2026-08-04", "2026-08-16"], rain=("2026-08-04", "2026-08-16")),
    "champaign": dict(lon=-88.37, lat=40.05, orbit=19, s1=["2026-09-04", "2026-09-16"], rain=("2026-09-04", "2026-09-17")),
}
SITE = sys.argv[1] if len(sys.argv) > 1 else "stillwater"
CFG = SITES[SITE]
LON, LAT = CFG["lon"], CFG["lat"]              # default: USCRN OK_Stillwater_2_W (WBAN 53926)
OUT = os.path.join(PROC, "imagery")
os.makedirs(OUT, exist_ok=True)
S1_DATES = CFG["s1"]
REL_ORBIT = CFG["orbit"]
PREFIX = "" if SITE == "stillwater" else SITE + "_"   # Stillwater keeps its original file names
NISAR_GRANULE = "NISAR_L3_PR_SME2_028_142_D_070_4005_DHDH_A_20260823T012505_20260823T012540_P05023_N_F_J_001"
GDAL_ENV = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MULTIRANGE="YES",
                CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.tiff", GDAL_HTTP_MAX_RETRY="4", GDAL_HTTP_RETRY_DELAY="2")
ee.Initialize(project=os.environ.get("EE_PROJECT", "my-ee-project-ntu-512914"))


def lonlat_box(half_km):
    dlat = half_km / 111.32
    dlon = half_km / (111.32 * np.cos(np.deg2rad(LAT)))
    return LON - dlon, LAT - dlat, LON + dlon, LAT + dlat


def s1_vv(date, half_km, res_m, name):
    f = os.path.join(OUT, name)
    if os.path.exists(f):
        return
    cat = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")
    items = [i for i in cat.search(collections=["sentinel-1-rtc"], datetime=date,
                                   intersects={"type": "Point", "coordinates": [LON, LAT]}).items()
             if i.properties.get("sat:relative_orbit") == REL_ORBIT]
    assert len(items) == 1, (date, len(items))
    it = items[0]
    with rasterio.Env(**GDAL_ENV), rasterio.open(pc.sign(it.assets["vv"].href)) as src:
        x, y = Transformer.from_crs(4326, src.crs, always_xy=True).transform(LON, LAT)
        h = half_km * 1000
        win = from_bounds(x - h, y - h, x + h, y + h, src.transform)
        n = int(round(2 * h / res_m))
        a = src.read(1, window=win, out_shape=(n, n), boundless=True, fill_value=0,
                     resampling=Resampling.average).astype("float32")
        crs = src.crs.to_epsg()
    a[a <= 0] = np.nan
    np.savez_compressed(f, vv_db=10 * np.log10(a), x0=x - h, x1=x + h, y0=y - h, y1=y + h, epsg=crs,
                        station_x=x, station_y=y, time=str(it.datetime), item=it.id)
    print("saved", name, a.shape, it.id)


def ee_grid(img, half_km, scale_deg, band):
    x0, y0, x1, y1 = lonlat_box(half_km)
    nx, ny = int(np.ceil((x1 - x0) / scale_deg)), int(np.ceil((y1 - y0) / scale_deg))
    req = dict(expression=img.select(band), fileFormat="NUMPY_NDARRAY",
               grid=dict(dimensions=dict(width=nx, height=ny),
                         affineTransform=dict(scaleX=scale_deg, shearX=0, translateX=x0, shearY=0, scaleY=-scale_deg, translateY=y1),
                         crsCode="EPSG:4326"))
    a = ee.data.computePixels(req)[band].astype("float32")
    return a, (x0, x0 + nx * scale_deg, y1 - ny * scale_deg, y1)


def gridmet_rain():
    r0, r1 = CFG["rain"]
    last = (np.datetime64(r1) - np.timedelta64(1, "D")).astype(str)
    f = os.path.join(OUT, f"{PREFIX}gridmet_rain_{r0.replace('-', '')}_{last.replace('-', '')}.npz")
    if os.path.exists(f):
        return
    img = ee.ImageCollection("IDAHO_EPSCOR/GRIDMET").filterDate(r0, r1).select("pr").sum()
    a, ext = ee_grid(img, 30, 0.01, "pr")
    np.savez_compressed(f, rain_mm=a, extent=np.array(ext))
    print("saved gridMET rain", a.shape, np.nanmax(a))


def smap():
    f = os.path.join(OUT, "smap_20260823_am.npz")
    if os.path.exists(f):
        return
    img = ee.ImageCollection("NASA/SMAP/SPL3SMP_E/006").filterDate("2026-08-23", "2026-08-24").first()
    a, ext = ee_grid(img, 12, 0.002, "soil_moisture_am")
    a[a <= 0] = np.nan
    np.savez_compressed(f, sm=a, extent=np.array(ext))
    print("saved SMAP", a.shape, np.nanmin(a), np.nanmax(a))


def nisar():
    f = os.path.join(OUT, "nisar_sme2_20260823.npz")
    if os.path.exists(f):
        return
    r = requests.get("https://cmr.earthdata.nasa.gov/search/granules.umm_json",
                     params={"readable_granule_name": NISAR_GRANULE, "short_name": "NISAR_L3_SME2_PROVISIONAL_V1"}, timeout=60)
    r.raise_for_status()
    urls = [u["URL"] for u in r.json()["items"][0]["umm"]["RelatedUrls"] if u["URL"].endswith(".h5") and u["URL"].startswith("https")]
    s = requests.Session()
    r0 = s.get(urls[0], headers={"Range": "bytes=0-0"}, timeout=120)   # Earthdata login (~/.netrc) -> signed URL
    r0.raise_for_status()
    G = "science/LSAR/SME2/grids/"
    x0, y0, x1, y1 = lonlat_box(12)
    with fsspec.filesystem("https").open(r0.url, "rb", block_size=2 * 2**20, cache_type="blockcache") as fh, h5py.File(fh, "r") as h:
        lat, lon = h[G + "latitude"][:], h[G + "longitude"][:]
        iy = np.where((lat >= y0) & (lat <= y1))[0]; ix = np.where((lon >= x0) & (lon <= x1))[0]
        sl = (slice(iy.min(), iy.max() + 1), slice(ix.min(), ix.max() + 1))
        sm = h[G + "soilMoisture"][sl].astype("float32"); fl = h[G + "retrievalQualityFlag"][sl]
    sm[sm <= -9999] = np.nan
    np.savez_compressed(f, sm=sm, flag=fl, lat=lat[sl[0]], lon=lon[sl[1]], granule=NISAR_GRANULE)
    print("saved NISAR", sm.shape, np.nanmin(sm), np.nanmax(sm))


if __name__ == "__main__":
    for d in S1_DATES:
        s1_vv(d, 30, 40, f"{PREFIX}s1_vv_{d.replace('-', '')}_60km_40m.npz")
    gridmet_rain()
    if SITE == "stillwater":                 # slide-only extras for the original case
        s1_vv("2026-08-25", 12, 10, "s1_vv_20260825_24km_10m.npz")
        smap()
        nisar()
