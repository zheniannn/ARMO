"""Independent cross-checks of the inputs, each against a second provider of the same data.

1. Sentinel-1 passes, 2026 season: Microsoft Planetary Computer (used, step 02) vs the Copernicus Data Space Ecosystem
   catalogue (ESA, OData API), one look per pass (frames < 1 h apart merged), per USCRN station.
2. NISAR passes, NISAR era: NASA CMR (used, step 02) vs the ASF search API, one look per pass, per station.
3. ERA5-Land 0-7 cm soil moisture: Open-Meteo archive (used, step 04) vs Google Earth Engine ECMWF/ERA5_LAND/HOURLY
   (volumetric_soil_water_layer_1), hourly, at 12 stations, 2026 season.
4. Rainfall: USCRN gauge totals per station-season vs gridMET daily totals (Earth Engine), the rain source of step 10.
Output: data/processed/cross_checks.csv (one row per check) and cross_check_*.csv (per-station detail).
"""
import os
import numpy as np
import pandas as pd
import requests
import ee
from concurrent.futures import ThreadPoolExecutor
from common import PROC, RAW

ee.Initialize(project=os.environ.get("EE_PROJECT", "my-ee-project-ntu-512914"))
S1_SEASON = ("2026-04-01", "2026-11-01")
NI_ERA = ("2026-06-17", "2026-11-01")


def passes(times):
    t = np.sort(pd.to_datetime(pd.Series(times), utc=True).to_numpy())
    if not t.size:
        return 0
    return int(1 + (np.diff(t) > np.timedelta64(1, "h")).sum())


def cdse_s1(r):
    url = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
    f = (f"Collection/Name eq 'SENTINEL-1' and OData.CSC.Intersects(area=geography'SRID=4326;POINT({r.lon} {r.lat})') "
         f"and ContentDate/Start ge {S1_SEASON[0]}T00:00:00.000Z and ContentDate/Start lt {S1_SEASON[1]}T00:00:00.000Z "
         f"and contains(Name,'_IW_GRDH_')")
    for k in range(4):
        try:
            v = requests.get(url, params={"$filter": f, "$top": 1000}, timeout=120).json()["value"]
            return passes([x["ContentDate"]["Start"] for x in v])
        except Exception:
            pass
    return np.nan


def asf_nisar(r):
    for k in range(4):
        try:
            j = requests.get("https://api.daac.asf.alaska.edu/services/search/param",
                             params=dict(platform="NISAR", intersectsWith=f"POINT({r.lon} {r.lat})",
                                         start=f"{NI_ERA[0]}T00:00:00Z", end=f"{NI_ERA[1]}T00:00:00Z",
                                         output="json", maxResults=5000), timeout=180).json()
            return passes([x["startTime"] for x in j[0]])
        except Exception:
            pass
    return np.nan


def main():
    st = pd.read_csv(os.path.join(PROC, "station_seasons.csv"))
    stn = st[st.included].drop_duplicates("wban")[["wban", "lat", "lon"]].reset_index(drop=True)
    rows = []
    # 1 + 2: pass counts
    s1 = pd.read_csv(os.path.join(PROC, "acq_s1.csv"), parse_dates=["time"])
    ni = pd.read_csv(os.path.join(PROC, "acq_nisar.csv"), parse_dates=["time"])
    with ThreadPoolExecutor(6) as ex:
        stn["s1_cdse"] = list(ex.map(cdse_s1, stn.itertuples()))
        stn["ni_asf"] = list(ex.map(asf_nisar, stn.itertuples()))
    s1w = s1[(s1.time >= S1_SEASON[0]) & (s1.time < S1_SEASON[1])]
    niw = ni[(ni.time >= NI_ERA[0]) & (ni.time < NI_ERA[1])]
    stn["s1_pc"] = stn.wban.map(lambda w: passes(s1w[s1w.wban == w].time))
    stn["ni_cmr"] = stn.wban.map(lambda w: passes(niw[niw.wban == w].time))
    stn.to_csv(os.path.join(PROC, "cross_check_passes.csv"), index=False)
    for a, b, name in [("s1_pc", "s1_cdse", "Sentinel-1 passes 2026: Planetary Computer vs Copernicus Data Space"),
                       ("ni_cmr", "ni_asf", "NISAR passes, NISAR era: NASA CMR vs ASF search")]:
        x = stn.dropna(subset=[a, b])
        rows.append(dict(check=name, n=len(x), r=np.corrcoef(x[a], x[b])[0, 1], median_used=x[a].median(),
                         median_independent=x[b].median(), frac_within_10pct=np.mean(abs(x[a] - x[b]) <= 0.1 * x[b])))
    # 3: ERA5-Land, Open-Meteo vs Earth Engine, 12 stations
    sub = stn.sample(12, random_state=1)
    det = []
    for r in sub.itertuples():
        om = pd.read_csv(os.path.join(RAW, "era5land", f"{r.wban}.csv"), parse_dates=["time"])
        om = om[(om.time >= "2026-06-01") & (om.time < "2026-09-01")].set_index("time").sm
        col = ee.ImageCollection("ECMWF/ERA5_LAND/HOURLY").filterDate("2026-06-01", "2026-09-01") \
            .select("volumetric_soil_water_layer_1")
        reg = col.getRegion(ee.Geometry.Point([r.lon, r.lat]), 11000).getInfo()
        g = pd.DataFrame(reg[1:], columns=reg[0])
        g = pd.Series(g.volumetric_soil_water_layer_1.to_numpy(float), index=pd.to_datetime(g.time, unit="ms"))
        m = pd.concat([om.rename("om"), g.rename("gee")], axis=1).dropna()
        det.append(dict(wban=r.wban, n=len(m), r=m.om.corr(m.gee), bias=(m.om - m.gee).mean()))
    det = pd.DataFrame(det); det.to_csv(os.path.join(PROC, "cross_check_era5.csv"), index=False)
    rows.append(dict(check="ERA5-Land 0-7 cm SM (Jun-Aug 2026): Open-Meteo vs Earth Engine", n=len(det),
                     r=det.r.median(), median_used=np.nan, median_independent=np.nan,
                     frac_within_10pct=np.mean(det.bias.abs() <= 0.01)))
    # 4: rainfall, USCRN gauge vs gridMET per station-season
    df = pd.read_pickle(os.path.join(PROC, "uscrn_hourly.pkl"))
    pts = ee.FeatureCollection([ee.Feature(ee.Geometry.Point([r.lon, r.lat]), dict(wban=int(r.wban))) for r in stn.itertuples()])
    rr = []
    for yr, (t0, t1) in {2025: ("2025-04-01", "2025-11-01"), 2026: ("2026-04-01", "2026-10-27")}.items():
        tot = ee.ImageCollection("IDAHO_EPSCOR/GRIDMET").filterDate(t0, t1).select("pr").sum()
        fc = tot.reduceRegions(pts, ee.Reducer.first(), 4000).getInfo()
        gm = pd.Series({f["properties"]["wban"]: f["properties"].get("first") for f in fc["features"]})
        w = df[(df.time_utc >= t0) & (df.time_utc < t1)].groupby("wban").precip.agg(["sum", "count"])
        inc = st[st.included & (st.season == yr)].wban
        for wb in inc:
            if wb in w.index and wb in gm.index and gm[wb] is not None and w.loc[wb, "count"] > 0.9 * 24 * 200:
                rr.append(dict(wban=wb, season=yr, uscrn=w.loc[wb, "sum"], gridmet=gm[wb]))
    rr = pd.DataFrame(rr); rr.to_csv(os.path.join(PROC, "cross_check_rain.csv"), index=False)
    rows.append(dict(check="Warm-season rain: USCRN gauge vs gridMET", n=len(rr), r=np.corrcoef(rr.uscrn, rr.gridmet)[0, 1],
                     median_used=rr.gridmet.median(), median_independent=rr.uscrn.median(),
                     frac_within_10pct=np.mean(abs(rr.gridmet - rr.uscrn) <= 0.1 * rr.uscrn)))
    out = pd.DataFrame(rows); out.to_csv(os.path.join(PROC, "cross_checks.csv"), index=False)
    print(out.round(3).to_string())


if __name__ == "__main__":
    main()
