"""Parse NOAA USCRN hourly02 station files into one quality-controlled table.

Ground truth for the whole project. Source:
https://www.ncei.noaa.gov/pub/data/uscrn/products/hourly02/  (no login)
Column layout: data/raw/uscrn/HEADERS.txt (38 fixed fields).

QC applied (each documented in the report, Section 3.1):
  - NOAA missing sentinels (-9999, -99.000) -> NaN
  - SOIL_MOISTURE_5 outside [0, 0.6] m3/m3 -> NaN (physically implausible)
  - frozen flag: SOIL_TEMP_5 <= 1 C (dielectric of frozen water ~ ice; probe
    and radar both invalid) -> SM5 set NaN
"""
import glob, io, os
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw", "uscrn")
OUT = os.path.join(ROOT, "data", "processed")
os.makedirs(OUT, exist_ok=True)

names = open(os.path.join(RAW, "HEADERS.txt")).read().splitlines()[1].split()
keep = ["WBANNO", "UTC_DATE", "UTC_TIME", "LST_DATE", "LST_TIME", "LONGITUDE",
        "LATITUDE", "T_CALC", "P_CALC", "SUR_TEMP", "SOIL_MOISTURE_5",
        "SOIL_MOISTURE_10", "SOIL_TEMP_5"]


def parse(path):
    # Some NOAA files contain runs of NUL bytes that overwrite a few records.
    # Strip them and keep only well-formed 38-field records; lost hours become gaps.
    text = open(path, "rb").read().replace(b"\x00", b"").decode("ascii", "ignore")
    good = [ln for ln in text.splitlines() if len(ln.split()) == len(names) and ln.split()[0].isdigit()]
    df = pd.read_csv(io.StringIO("\n".join(good)), sep=r"\s+", header=None, names=names, usecols=keep,
                     dtype={"WBANNO": "int64", "UTC_DATE": str, "UTC_TIME": str, "LST_DATE": str, "LST_TIME": str})
    df["time_utc"] = pd.to_datetime(df.UTC_DATE + df.UTC_TIME.str.zfill(4), format="%Y%m%d%H%M", utc=True)
    df["time_lst"] = pd.to_datetime(df.LST_DATE + df.LST_TIME.str.zfill(4), format="%Y%m%d%H%M")
    for c in ["T_CALC", "P_CALC", "SUR_TEMP", "SOIL_MOISTURE_5", "SOIL_MOISTURE_10", "SOIL_TEMP_5"]:
        df.loc[df[c] <= -99, c] = np.nan
    for c in ["SOIL_MOISTURE_5", "SOIL_MOISTURE_10"]:
        df.loc[(df[c] < 0) | (df[c] > 0.6), c] = np.nan
    frozen = ~(df.SOIL_TEMP_5 > 1.0)  # NaN soil temperature counts as not-verified-unfrozen
    df["frozen_or_unknown"] = frozen
    df.loc[frozen, "SOIL_MOISTURE_5"] = np.nan
    df["station_file"] = os.path.basename(path)
    return df.drop(columns=["UTC_DATE", "UTC_TIME", "LST_DATE", "LST_TIME"])


if __name__ == "__main__":
    files = sorted(glob.glob(os.path.join(RAW, "2025", "*.txt")) + glob.glob(os.path.join(RAW, "2026", "*.txt")))
    df = pd.concat([parse(f) for f in files], ignore_index=True)
    df = df.rename(columns={"WBANNO": "wban", "SOIL_MOISTURE_5": "sm5", "SOIL_MOISTURE_10": "sm10",
                            "SOIL_TEMP_5": "st5", "P_CALC": "precip", "LONGITUDE": "lon", "LATITUDE": "lat"})
    df["name"] = df.station_file.str.replace(r"CRNH0203-20\d\d-", "", regex=True).str.replace(".txt", "")
    df = df.drop(columns="station_file").sort_values(["wban", "time_utc"]).drop_duplicates(["wban", "time_utc"])
    df.to_pickle(os.path.join(OUT, "uscrn_hourly.pkl"))

    # Station summary per warm season (1 Apr - 31 Oct); a station-season enters the
    # analysis only if >= 70 % of its hours have valid, unfrozen 5 cm soil moisture.
    rows = []
    for yr in (2025, 2026):
        w = df[(df.time_utc >= f"{yr}-04-01") & (df.time_utc < f"{yr}-11-01")]
        st = w.groupby("wban").agg(name=("name", "first"), lat=("lat", "median"), lon=("lon", "median"),
                                   sm5_valid=("sm5", "count"), precip_mm=("precip", "sum"),
                                   sm5_mean=("sm5", "mean"), sm5_std=("sm5", "std"))
        st["season"] = yr
        st["sm5_frac"] = st.sm5_valid / (214 * 24)
        rows.append(st.reset_index())
    st = pd.concat(rows, ignore_index=True)
    st["included"] = st.sm5_frac >= 0.7
    st.to_csv(os.path.join(OUT, "station_seasons.csv"), index=False)
    print(st.groupby("season").included.agg(["size", "sum"]))
    print("unique stations included in >=1 season:", st[st.included].wban.nunique())
