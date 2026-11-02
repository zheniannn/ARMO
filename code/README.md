# ARMO proof of concept: code

Reproduces every number, figure and table in `report/ARMO_Proposal_ES4304.pdf` and `slides/ARMO_Slides_ES4304.pdf`.

## Setup
Python 3.14 with: `numpy pandas scipy matplotlib requests pystac-client planetary-computer rasterio pyproj geopandas pyogrio h5py fsspec aiohttp python-docx python-pptx pillow pypdf pymupdf earthengine-api reportlab`.

NISAR downloads (script 07 only) need a free NASA Earthdata account, with credentials in `~/.netrc`
(`machine urs.earthdata.nasa.gov login <user> password <pass>`). Never commit credentials.
Scripts 14, 18 and 23 need Google Earth Engine: run `earthengine authenticate` once and set `EE_PROJECT` to a Cloud project registered for Earth Engine (non-commercial use is free). Everything else is anonymous.

## Run order
| Script | Does | Output (data/processed) |
|---|---|---|
| 01_parse_uscrn.py | Parse and QC NOAA USCRN hourly02 (NUL-byte repair, frozen mask, >= 70 % valid) | uscrn_hourly.pkl, station_seasons.csv |
| 02_events_revisit.py | Wetting events (O1); capture vs regular revisit, bootstrap CI, sensitivity (O2) | events.csv, capture_synthetic.csv, sensitivity.csv |
| 03_real_schedules.py | Actual Sentinel-1 (STAC) and NISAR (CMR) pass times; real capture; ARMO marginal value (O4) | acq_*.csv, capture_real.csv, revisit_real.csv, marginal_value.csv |
| 04_extract_s1_backscatter.py | Sentinel-1 RTC VV/VH 11x11 px windows via COG range reads | s1_cache/, s1_backscatter.csv |
| 05_era5land_baseline.py | ERA5-Land (Open-Meteo) event POD/FAR and continuous skill | era5_*.csv |
| 06_s1_observability.py | C-band sensitivity, noise floor, P(detect given sampled) (O3) | s1_*.csv |
| 07_extract_nisar_sme2.py | NISAR L3 SME2 soil moisture and L-band sigma0 via HDF5 range reads | nisar_cache/, nisar_sme2_points.csv |
| 08_nisar_eval.py | NISAR accuracy and change detection vs ground truth (O3) | nisar_*.csv |
| 09_armo_orbit_sim.py | J2 orbit simulation of ARMO designs A-E against the real fleet | armo_designs.csv |
| 14_gee_extract.py | Earth Engine: SMAP L3E 9 km, MODIS NDVI, ESA WorldCover, USDA CDL at each station | gee_*.csv |
| 15_smap_eval.py | SMAP capture, accuracy and detection (same tests as 06/08) | smap_*.csv |
| 16_detection_strata.py | Detection by NDVI, land cover and event size for all sensors | detection_strata.csv, station_vegetation.csv |
| 17_snr_requirement.py | Calibrated detection model; ARMO change-noise requirement | snr_requirement.csv, snr_summary.csv |
| 18_optical_clouds.py | Earth Engine MODIS cloud mask at each overpass: could optical sensors see the events? | optical_*.csv |
| 19_market_report.py | Market and niche review | market.pdf |
| 21_armo_performance.py | ARMO vs NISAR vs ROSE-L on the same events; 10 cm depth test (P-band / UHF proxy) | performance_headtohead.csv, depth_summary.csv |
| 22_armo_sizing.py | Spacecraft sizing: antenna, radar power, data, mass budget and mission cost | armo_sizing.csv, armo_mass.csv, armo_cost.csv |
| 23_gee_need_maps.py | Earth Engine CONUS maps: Sentinel-1 revisit, wetting events, missed events, ARMO gain (report Figure 1) | need_*.npy, need_summary.csv |
| 10-13_fig_*.py | Figures 2-6 | figures/ |
| 20_build_report.py (+ report_text.py) | Proposal docx from the course template; numbers read from results | report/ |
| 30_build_slides.py | Slide deck | slides/ |
| 40_review_and_qa.py | Panel self-review and Q&A | notes/review_and_QA.md |
| 50_rebuild_outputs.py | Re-run 06, 08, 15-17, figures, report, slides, PDFs and guide | all outputs |
| 60_build_team_guide.py | Step-by-step team guide | notes/ARMO_Team_Guide.pdf |

PDF export uses Microsoft Word / PowerPoint: `to_pdf.ps1`, `pptx_to_pdf.ps1`.

## Data sources
- NOAA USCRN hourly02: https://www.ncei.noaa.gov/pub/data/uscrn/products/hourly02/
- Sentinel-1 GRD / RTC: Microsoft Planetary Computer STAC (`sentinel-1-grd`, `sentinel-1-rtc`)
- NISAR: NASA CMR / ASF (`NISAR_L2_GCOV_*_V1`, `NISAR_L3_SME2_PROVISIONAL_V1`)
- SMAP, MODIS, WorldCover, CDL: Google Earth Engine catalogue
- ERA5-Land: Open-Meteo archive API (`models=era5_land`; rainfall from `models=era5`)
- Boundaries: Natural Earth 1:50m
