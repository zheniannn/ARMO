# ARMO proof of concept: code

Reproduces every number, figure and table in the proposal and slides (kept locally in `Assignment (Do Not Push)/`, not in this repository).

## Setup
Python 3.14 with: `numpy pandas scipy matplotlib requests pystac-client planetary-computer rasterio pyproj geopandas pyogrio shapely h5py fsspec aiohttp earthengine-api`.

NISAR downloads (script 05 only) need a free NASA Earthdata account, with credentials in `~/.netrc`
(`machine urs.earthdata.nasa.gov login <user> password <pass>`). Never commit credentials.
Scripts 07, 09 and 10 need Google Earth Engine: run `earthengine authenticate` once and set `EE_PROJECT` to a Cloud project registered for Earth Engine (non-commercial use is free). Everything else is anonymous.

## Run order
Scripts that download data cache what they fetch, so a re-run reuses the cache. Figure scripts live in `../figures/`.

| Script | Does | Internet | Output (data/processed) |
|---|---|---|---|
| 00_download_raw.py | Download NOAA USCRN hourly02 (2025, 2026; all stations except AK, HI) and Natural Earth outlines | yes | data/raw/ |
| 01_events.py | Parse and QC USCRN (NUL-byte repair, frozen mask, >= 70 % valid); wetting events (O1); capture vs regular revisit, bootstrap CI, sensitivity (O2) | no | uscrn_hourly.pkl, station_seasons.csv, events.csv, capture_synthetic.csv, sensitivity.csv |
| 02_real_schedules.py | Actual Sentinel-1 (STAC) and NISAR (CMR) pass times; real capture; ARMO marginal value (O4) | yes | acq_*.csv, capture_real.csv, revisit_real.csv, marginal_value.csv |
| 03_extract_s1_backscatter.py | Sentinel-1 RTC VV/VH 11x11 px windows via COG range reads | yes | s1_cache/, s1_backscatter.csv |
| 04_era5land_baseline.py | ERA5-Land (Open-Meteo) event POD/FAR and continuous skill | yes | era5_*.csv |
| 05_extract_nisar_sme2.py | NISAR L3 SME2 soil moisture and L-band HH sigma0 via HDF5 range reads | yes (Earthdata) | nisar_cache/, nisar_sme2_points.csv |
| 06_mission_design.py | J2 orbit simulation of ARMO designs A-E; ARMO vs NISAR vs ROSE-L on the same events and the 10 cm depth test; spacecraft sizing, mass and cost. Optional `event_flags` argument: per-event look flags by design and orbital phase, and usable-swath scenarios | no | armo_designs.csv, performance_headtohead.csv, depth_*.csv, armo_sizing.csv, armo_mass.csv, armo_cost.csv; event_flags: armo_event_capture_by_phase.csv, armo_swath_event_capture.csv, armo_swath_gaps.csv |
| 07_gee_extract.py | Earth Engine: SMAP L3E 9 km, MODIS NDVI, ESA WorldCover, USDA CDL at each station | yes (Earth Engine) | gee_*.csv |
| 08_sensor_tests.py | Sentinel-1, NISAR and SMAP accuracy and P(detect given sampled) (O3); detection by NDVI, land cover and event size; calibrated detection model and ARMO noise requirement | no | s1_*.csv, nisar_*.csv, smap_*.csv, detection_strata.csv, station_vegetation.csv, snr_*.csv |
| 09_optical_clouds.py | Earth Engine MODIS cloud mask at each overpass: could optical sensors see the events? | yes (Earth Engine) | optical_*.csv |
| 10_gee_need_maps.py | Earth Engine CONUS maps: Sentinel-1 revisit, wetting events, missed events, ARMO gain (report Figure 1) | yes (Earth Engine) | need_*.npy, need_summary.csv, ../figures/fig1_need_maps.png |
| 11_cross_checks.py | Independent checks: S1 passes (Copernicus Data Space), NISAR passes (ASF), ERA5-Land (Earth Engine), rain (gridMET vs USCRN) | yes | cross_check*.csv |
| 12_extract_imagery.py | Imagery subsets for the slide figures: Sentinel-1 VV before/after two storms at Stillwater, OK (Aug 2026), gridMET rain, SMAP 9 km and NISAR 200 m soil moisture | yes (Earthdata, Earth Engine) | imagery/ |
| ../figures/*.py | Report Figures 2-6 (file numbers match the report) and the slide figures (study area, SAR wetting event, resolution ladder, ARMO coverage, detection matrices); `figstyle.py` is the shared style | no | ../figures/ |

The proposal, slides, market review, self-review and team guide, and the scripts that build them (including the one-step rebuild `50_rebuild_outputs.py`), are kept locally in `Assignment (Do Not Push)/` and are not in this repository.

## Data sources
- NOAA USCRN hourly02: https://www.ncei.noaa.gov/pub/data/uscrn/products/hourly02/
- Sentinel-1 GRD / RTC: Microsoft Planetary Computer STAC (`sentinel-1-grd`, `sentinel-1-rtc`)
- NISAR: NASA CMR / ASF (`NISAR_L2_GCOV_*_V1`, `NISAR_L3_SME2_PROVISIONAL_V1`)
- SMAP, MODIS, WorldCover, CDL: Google Earth Engine catalogue
- ERA5-Land: Open-Meteo archive API (`models=era5_land`; rainfall from `models=era5`)
- Boundaries: Natural Earth 1:50m
