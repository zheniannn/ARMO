# P2-12 Commercial / fusion benchmark — BLOCKED

**Status (3 Nov 2026): BLOCKED.** No event-level commercial soil-moisture product data exist in this repository or in
`data/`. No vendor comparison is plotted anywhere; `figures/fig_commercial_benchmark.py` was deliberately **not** written,
because any figure would be fictional. Every place the project mentions Spire D-HSSM or a fused product labels its
accuracy, event timing and price **UNKNOWN**.

## Question the benchmark must answer

Does any no-launch option (purchased commercial daily product, or a fusion of NISAR + Sentinel-1 + SMAP) meet ARMO's own
requirements on the same ground-truth wetting events? This is the Stage 1 Gate 1 (interim, end 2027) / Gate 2 (end 2028)
test. If one does, ARMO is not built.

## Data that are missing

| Item | Needed for | How to obtain |
|---|---|---|
| Spire D-HSSM (100 m, daily) time series at ≥ 20 USCRN stations including all cropland sites, 2026–2027 warm seasons | the commercial contender | purchase / research licence from Spire (custom regions only; product page https://developers.smi.spire.com/product-100m/) |
| Per-retrieval timestamp (valid time and production time), quality flag, and the D-MSSM 6 km parent value | latency and quality screening; separating downscaled detail from independent information | request with the purchase |
| Sentinel-1 scene list used for downscaling at each pixel | to test whether a "daily" change follows a new radar look or only the 6 km field | vendor documentation or reconstruction from acq_s1.csv |
| A documented NISAR + Sentinel-1 + SMAP fusion (algorithm + code) | the fusion contender | Stage 1 work package (not yet built) |
| Field campaign probes on irrigated and rain-fed cropland | cropland representativeness (only 9 classified USCRN stations are cropland) | Stage 1 field campaign |

## Required input schema (one row per product value)

`source, product_version, wban, lat, lon, spatial_support_m, valid_time_utc, production_time_utc, latency_h, sm_m3m3,
quality_flag, parent_sm_m3m3 (if downscaled), contributing_sensors, licence`

Ground truth comes from the existing `data/processed/events.csv` windows and `uscrn_hourly.pkl` (5 cm, hour-ending).

## Protocol (pre-registered; identical for every contender, ARMO-like sampling included)

1. **Events:** the same USCRN wetting-event rule (`code/common.py`), same matched cohort and period for every contender.
2. **Availability:** an "update inside the window" = a product value whose valid time lies in [t_ws, t_we) **and**
   whose production time is ≤ t_we + 24 h (latency requirement).
3. **Detection:** change between the last value before the window and the first value inside it, compared with the
   1σ no-change noise estimated on unchanged pairs (|ΔSM| < 0.01 m³/m³) **from training stations only**.
4. **False alarms:** the same rule on unchanged pairs at held-out stations (probability of false detection, not
   false-alarm ratio).
5. **Spatial support:** report the product's stated grid and, separately, whether the change coincides with a new
   independent field-scale radar acquisition (to distinguish a 100 m estimate from a 100 m measurement).
6. **Uncertainty:** station-cluster bootstrap; held-out stations (5 folds) and held-out season.

## Acceptance criteria (ARMO's requirements, applied to every option)

An option **passes** if, on held-out stations: update inside ≥ 80 % of event windows; ≥ 70 % of those detected; ≤ 10 %
false alarms; ≤ 200 m spatial support; ≤ 24 h latency. A pass by any no-launch option ends ARMO (Gate 1 or 2).

## Experimental controls

- Same events, same stations, same period for all contenders; no threshold tuned on test stations.
- Report all contenders, including failures; no selective reporting.
- Record product versions and access dates; freeze inputs before scoring.
