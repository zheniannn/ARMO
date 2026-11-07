"""NISAR L2 GCOV (L-band, RTC gamma0) subsets around the three case-study stations, for before/after comparison.

Pairs are the same track and frame (identical imaging geometry), chosen from data/processed/acq_nisar.csv as the
closest acquisitions before the storm and inside the station's wetting window:
  stillwater  track 142 D frame 070: 11 Aug 2026 (dry) -> 23 Aug 2026 (wetting window 2)   NB modes differ: 20 MHz QP vs 40 MHz DH
  oakley      track  62 A frame 021: 24 Jul 2026 (dry) -> 17 Aug 2026 (wetting window)     24 days, both 40 MHz DH; the track 70 D
              pair (25 Jul -> 18 Aug) was rejected: mask = 0 (invalid) at the station on both dates (check_station_validity.py)
  champaign   track 148 A frame 022: 04 Sep 2026 (dry) -> 16 Sep 2026 (wetting window)     same mode, 12-day repeat; NB the
              station lies in an invalid (mask 0) stripe on 16 Sep, so the pair is used for the scene, not the station

Access: NASA CMR -> ASF Earthdata Cloud HTTPS; Earthdata login from ~/.netrc (never printed); HDF5 chunk reads only
(512 x 512 gzip chunks), so a 60 x 60 km subset is ~50 MB per layer instead of the 8 GB granule.
Read: HHHH, HVHV (and VVVV where the granule is quad-pol), mask, numberOfLooks.
Valid sample: mask in 1..254 (subswath number; 0 = partially focused / invalid, 255 = outside the swath) and gamma0 > 0.
Resampling: block mean of LINEAR gamma0 to 40 m (2 x 2 for 20 m products, 4 x 4 for 10 m 40-MHz products), valid samples
only (>= half valid), on a 40 m lattice shared by both dates; dB taken afterwards.
Output: data/processed/imagery/nisar_gcov/<site>_nisar_<yyyymmdd>_60km_40m.npz (gitignored data folder)
Run: python code/13_extract_nisar_gcov.py [site ...]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
import pandas as pd
import requests
import fsspec
import h5py
from pyproj import Transformer
from common import PROC

OUT = os.path.join(PROC, "imagery", "nisar_gcov")
os.makedirs(OUT, exist_ok=True)
SITES = {"stillwater": dict(wban=53926, lon=-97.09, lat=36.12, track=142, dates=("2026-08-11", "2026-08-23")),
         "oakley": dict(wban=3067, lon=-100.96, lat=38.87, track=62, dates=("2026-07-24", "2026-08-17")),
         "champaign": dict(wban=54808, lon=-88.37, lat=40.05, track=148, dates=("2026-09-04", "2026-09-16"))}
HALF = 30_000       # m, 60 x 60 km box as the Sentinel-1 subsets
G = "science/LSAR/GCOV/grids/frequencyA/"
ID = "science/LSAR/identification/"


def granule_url(name):
    r = requests.get("https://cmr.earthdata.nasa.gov/search/granules.umm_json",
                     params={"readable_granule_name": name, "short_name": "NISAR_L2_GCOV_PROVISIONAL_V1"}, timeout=60)
    r.raise_for_status()
    url = [u["URL"] for u in r.json()["items"][0]["umm"]["RelatedUrls"] if u["URL"].endswith(".h5") and u["URL"].startswith("https")][0]
    r0 = requests.Session().get(url, headers={"Range": "bytes=0-0"}, timeout=120)   # Earthdata redirect -> signed URL
    r0.raise_for_status()
    return r0.url


def extract(site, date, name):
    f = os.path.join(OUT, f"{site}_nisar_{date.replace('-', '')}_60km_40m.npz")
    if os.path.exists(f):
        print("exists", f); return
    c = SITES[site]
    with fsspec.filesystem("https").open(granule_url(name), "rb", block_size=8 * 2**20, cache_type="blockcache") as fh, \
            h5py.File(fh, "r") as h:
        epsg = int(h[G + "projection"][()])
        x, y = h[G + "xCoordinates"][:], h[G + "yCoordinates"][:]
        dx = float(h[G + "xCoordinateSpacing"][()]); dy = float(h[G + "yCoordinateSpacing"][()])
        assert dx in (10.0, 20.0) and dy == -dx, (dx, dy)      # 20 MHz modes post at 20 m, 40 MHz modes at 10 m
        sx, sy = Transformer.from_crs(4326, epsg, always_xy=True).transform(c["lon"], c["lat"])
        # box on a 40 m lattice (multiples of 40 m), so 10 m and 20 m products of a pair share the same 40 m cells
        X0, Y1 = np.floor((sx - HALF) / 40) * 40, np.ceil((sy + HALF) / 40) * 40
        N, F = int(2 * HALF / dx), int(40 / dx)
        j0 = int(round((X0 + dx / 2 - x[0]) / dx)); i0 = int(round((y[0] - (Y1 - dx / 2)) / dx))
        assert abs(x[j0] - dx / 2 - X0) < 1e-6 and abs(y[i0] + dx / 2 - Y1) < 1e-6, "grid not on the 40 m lattice"
        assert 0 <= j0 and j0 + N <= x.size and 0 <= i0 and i0 + N <= y.size, "box leaves the frame"
        sl = (slice(i0, i0 + N), slice(j0, j0 + N))
        pols = [p.decode() for p in h[G + "listOfPolarizations"][:]]
        terms = [t.decode() for t in h[G + "listOfCovarianceTerms"][:]]
        mask = h[G + "mask"][sl]
        nlooks = h[G + "numberOfLooks"][sl]
        valid = (mask >= 1) & (mask <= 254)
        out = {}
        for t in ("HHHH", "HVHV", "VVVV"):
            if t in terms:
                a = h[G + t][sl].astype("float64")
                a[~(valid & (a > 0))] = np.nan
                b = a.reshape(1500, F, 1500, F)
                n = np.isfinite(b).sum(axis=(1, 3))
                m = np.nansum(b, axis=(1, 3)) / np.where(n > 0, n, 1)
                m[n < F * F / 2] = np.nan                                      # need >= half of the native samples valid
                out[t[:2].lower() + "_db"] = (10 * np.log10(m)).astype("float32")
                del a, b
        meta = {k: h[ID + k][()].decode() if isinstance(h[ID + k][()], bytes) else h[ID + k][()]
                for k in ("zeroDopplerStartTime", "productVersion", "trackNumber", "frameNumber", "orbitPassDirection")
                if ID + k in h}
    np.savez_compressed(f, **out, x0=X0, x1=X0 + 2 * HALF, y0=Y1 - 2 * HALF, y1=Y1, epsg=epsg, native_spacing_m=dx,
                        station_x=sx, station_y=sy, granule=name, pols=",".join(pols),
                        frac_valid=float(valid.mean()), nlooks_median=float(np.nanmedian(nlooks[valid])) if valid.any() else np.nan,
                        meta=str(meta))
    print("saved", f, {k: v.shape for k, v in out.items()}, "valid", round(float(valid.mean()), 3), meta)


if __name__ == "__main__":
    ni = pd.read_csv(os.path.join(PROC, "acq_nisar.csv"), parse_dates=["time"])
    for site in (sys.argv[1:] or SITES):
        c = SITES[site]
        mode = None
        for d in c["dates"]:
            g = ni[(ni.wban == c["wban"]) & (ni.track == c["track"]) & (ni.time.dt.strftime("%Y-%m-%d") == d)]
            if len(g) > 1 and mode:   # two products of one pass (e.g. Oakley 17 Aug: 20 and 40 MHz): keep the before-date mode
                g = g[g.granule.str.split("_").str[8] == mode]
            assert len(g) == 1, (site, d, len(g))
            mode = mode or g.granule.iloc[0].split("_")[8]
            extract(site, d, g.granule.iloc[0])
