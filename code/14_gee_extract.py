"""Google Earth Engine extraction at every USCRN station (needs `earthengine authenticate` and a
Cloud project registered for Earth Engine; set EE_PROJECT or edit the default below).

  SMAP Enhanced L3 (NASA/SMAP/SPL3SMP_E/006): 9 km soil moisture, AM (06:00) and PM (18:00)
      local overpasses, vegetation water content and retrieval quality flag
  MODIS MOD13Q1 v6.1: 250 m 16-day NDVI (vegetation greenness at each station)
  ESA WorldCover v200 (2021) and USDA NASS Cropland Data Layer (2025): land cover / crop type
      within 100 m of the probe, and crop fraction over the ~9 km SMAP cell

Outputs: data/processed/gee_smap.csv, gee_ndvi.csv, gee_landcover.csv
"""
import os
from concurrent.futures import ThreadPoolExecutor
import ee
import pandas as pd
from common import PROC

ee.Initialize(project=os.environ.get("EE_PROJECT", "my-ee-project-ntu-512914"))
T0, T1 = "2025-03-01", "2026-11-01"
st = pd.read_csv(os.path.join(PROC, "station_seasons.csv"))
st = st[st.included].drop_duplicates("wban")[["wban", "name", "lat", "lon"]].reset_index(drop=True)
print("stations:", len(st))


def region(coll, bands, lon, lat, scale):
    rows = coll.filterDate(T0, T1).select(bands).getRegion(ee.Geometry.Point([lon, lat]), scale).getInfo()
    return pd.DataFrame(rows[1:], columns=rows[0])


def smap(r):
    bands = ["soil_moisture_am", "soil_moisture_pm", "retrieval_qual_flag_am", "retrieval_qual_flag_pm",
             "vegetation_water_content_am", "vegetation_water_content_pm"]
    d = region(ee.ImageCollection("NASA/SMAP/SPL3SMP_E/006"), bands, r.lon, r.lat, 9000)
    return d.assign(wban=r.wban)


def ndvi(r):
    d = region(ee.ImageCollection("MODIS/061/MOD13Q1"), ["NDVI", "SummaryQA"], r.lon, r.lat, 250)
    return d.assign(wban=r.wban)


def cached(name, fn):
    f = os.path.join(PROC, name)
    if os.path.exists(f):
        return pd.read_csv(f)
    with ThreadPoolExecutor(8) as ex:
        d = pd.concat(list(ex.map(fn, st.itertuples())), ignore_index=True)
    d["date"] = pd.to_datetime(d.time, unit="ms", utc=True).dt.strftime("%Y-%m-%d")
    d.drop(columns=["id", "time"]).to_csv(f, index=False)
    print("saved", f, len(d))
    return d


cached("gee_smap.csv", smap)
cached("gee_ndvi.csv", ndvi)

# ---------------------------------------------------------------- land cover
f = os.path.join(PROC, "gee_landcover.csv")
if not os.path.exists(f):
    pts = ee.FeatureCollection([ee.Feature(ee.Geometry.Point([r.lon, r.lat]), {"wban": int(r.wban)}) for r in st.itertuples()])
    wc = ee.Image("ESA/WorldCover/v200/2021").select("Map")
    cdl = ee.Image("USDA/NASS/CDL/2025").select("cropland")
    crop = cdl.lte(61).Or(cdl.gte(66).And(cdl.lte(77))).Or(cdl.gte(204).And(cdl.lte(254))).rename("crop")
    near = pts.map(lambda p: p.buffer(100))
    wc_h = wc.reduceRegions(near, ee.Reducer.frequencyHistogram(), 10).getInfo()
    cdl_h = cdl.reduceRegions(near, ee.Reducer.frequencyHistogram(), 30).getInfo()
    crop9 = crop.reduceRegions(pts.map(lambda p: p.buffer(4500)), ee.Reducer.mean(), 30, tileScale=4).getInfo()
    out = {}
    for ft in wc_h["features"]:
        h = ft["properties"]["histogram"]; w = ft["properties"]["wban"]
        out.setdefault(w, {})["worldcover"] = int(max(h, key=h.get)) if h else None
    for ft in cdl_h["features"]:
        h = ft["properties"]["histogram"]; w = ft["properties"]["wban"]
        out.setdefault(w, {})["cdl"] = int(max(h, key=h.get)) if h else None
    for ft in crop9["features"]:
        out.setdefault(ft["properties"]["wban"], {})["crop_frac_9km"] = ft["properties"].get("mean")
    lc = pd.DataFrame.from_dict(out, orient="index").rename_axis("wban").reset_index()
    lc.to_csv(f, index=False)
    print("saved", f, len(lc))
