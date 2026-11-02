"""Download the raw inputs that the analysis scripts read from data/raw (no login needed).

  NOAA USCRN hourly02, 2025 and 2026 station files, all stations except Alaska and Hawaii (133 per year),
      plus HEADERS.txt, README.txt and the station list (stations.tsv).
      https://www.ncei.noaa.gov/pub/data/uscrn/products/hourly02/
  Natural Earth 1:50m admin-1 states and lakes (map outlines, CONUS mask).  https://www.naturalearthdata.com/
ERA5-Land (step 04), Sentinel-1 (02, 03), NISAR (05) and Earth Engine data (07, 09, 10) are fetched by those scripts.
Re-running refreshes the 2026 files, which NOAA may have extended or corrected since the original download.
"""
import os
import re
import io
import zipfile
import requests
from concurrent.futures import ThreadPoolExecutor
from common import RAW

BASE = "https://www.ncei.noaa.gov/pub/data/uscrn/products/hourly02/"
NE = {"states": "https://naciscdn.org/naturalearth/50m/cultural/ne_50m_admin_1_states_provinces.zip",
      "lakes": "https://naciscdn.org/naturalearth/50m/physical/ne_50m_lakes.zip"}
S = requests.Session()


def get(url, path):
    for k in range(4):
        try:
            r = S.get(url, timeout=120)
            r.raise_for_status()
            open(path, "wb").write(r.content)
            return len(r.content)
        except requests.RequestException as e:
            err = e
    raise err


def main():
    u = os.path.join(RAW, "uscrn")
    os.makedirs(u, exist_ok=True)
    get(BASE + "HEADERS.txt", os.path.join(u, "HEADERS.txt"))
    get(BASE + "README.txt", os.path.join(u, "README.txt"))
    get("https://www.ncei.noaa.gov/pub/data/uscrn/products/stations.tsv", os.path.join(u, "stations.tsv"))
    for yr in (2025, 2026):
        names = sorted(set(re.findall(rf'href="(CRNH0203-{yr}-[^"/]+\.txt)"', S.get(BASE + f"{yr}/", timeout=60).text)))
        keep = [n for n in names if not re.match(rf"CRNH0203-{yr}-(AK|HI)_", n)]
        d = os.path.join(u, str(yr)); os.makedirs(d, exist_ok=True)
        open(os.path.join(u, f"conus{yr}.txt"), "w").write("\n".join(keep) + "\n")
        with ThreadPoolExecutor(8) as ex:
            sizes = list(ex.map(lambda n: get(BASE + f"{yr}/{n}", os.path.join(d, n)), keep))
        print(f"USCRN {yr}: {len(keep)} of {len(names)} station files, {sum(sizes) / 1e6:.0f} MB", flush=True)
    for name, url in NE.items():
        r = S.get(url, timeout=120); r.raise_for_status()
        zipfile.ZipFile(io.BytesIO(r.content)).extractall(os.path.join(RAW, "naturalearth", name))
        print("Natural Earth", name, "ok", flush=True)


if __name__ == "__main__":
    main()
