# ARMO method notes and limitations

These notes give the numbers behind the supplementary figures and the limits of each analysis. Everything here runs
offline from `data/processed/`. Every number is written by a script to `figures/generated/*.csv`, and
`figures/figure_manifest.csv` lists each figure with its inputs, cohort, uncertainty and placement.

Evidence classes: **OBSERVED** (ground truth or real acquisitions), **SIMULATED** (orbit model or idealised sampler),
**MODEL-BASED** (calibrated statistical model or proxy), **UNVALIDATED** (not yet shown).

## 1. Headline numbers

`figures/reproduce_anchors.py` recomputes 36 headline values from the processed tables; all 36 match
(`generated/anchor_check.csv`). `code/15_slide_numbers.py` does the same for the 76 analysis numbers on the slides.

- 3,340 wetting events at 120 stations (2025–2026). Matched cohort: 979 events at 107 stations, storms 17 Jun–31 Oct 2026.
- Looks in the window: Sentinel-1 30.2 %, NISAR 37.9 %, fleet 51.6 %. Partition: 474 none, 134 Sentinel-1 only,
  209 NISAR only, 162 both.
- Regular revisit for 80 % capture: 1.46 d (95 % band 1.31–1.64).
- Design D: mean gap between ARMO looks 1.416 d; fleet + ARMO 81.5 %; gain +29.9 points; ARMO alone 76.1 %.
- SMAP retrieval in the window: 76.6 % (any quality), 26.7 % (recommended quality).
- Bottom-up mission cost: US$ 149.8 M.
- The event key (station, window start) is unique.

The per-event ARMO export (`code/06_mission_design.py event_flags`) reproduces the design results exactly (fleet +
ARMO A–E 71.1 / 70.1 / 77.2 / 81.5 / 77.4 %; ARMO alone 76.1 %).

## 2. Ground truth (slides 4 and 8)

**Representativeness — `figS02_vegetation_representativeness.png` (OBSERVED).** 121 stations are classified (120 have
events; station 4125 has none). ESA WorldCover at the probe: cropland 9 (7 by USDA CDL), grassland 60, tree cover 36.
Cropland detection groups are too small for Sentinel-1 (n 17) and NISAR HH (n 24) and are flagged; SMAP cropland 56 %
(n 192). No national crop-specific inference is possible.

**Event definition — `figS03_sampling_robustness.png` (OBSERVED events, SIMULATED sampling).** Across a 3 × 3 grid of
rain and rise thresholds: 2,522–3,807 events; median window 40–48 h; 2-day capture 69.7–74.8 %; 6-day capture
34.0–40.5 %. The 80 %-capture revisit is computed for the main definition only.

**Probe depth — `figS04_depth_comparison.png` (OBSERVED).** 2,433 storms produce events at both 5 and 10 cm (117
stations). Paired median window difference 0 h (CI 0 to +2 h); paired capture difference +0.6 (1 d), +0.9 (2 d), +1.5
(3 d) and +2.0 points (6 d, CI 0.2–4.0). This concerns probe depth only, not radar penetration.

**Capture against revisit — `figS05_capture_vs_revisit.png` (SIMULATED sampling on OBSERVED windows).** An ideal
regular sampler, phase-swept, on the 3,340 measured windows; the real fleets are plotted at their mean gap between looks.

## 3. Why radar (slide 9)

**Optical cloud penalty — `figS06_optical_cloud_penalty.png` (MODEL-BASED proxy).** Clear-sky optical against
all-weather sampling at the same cadence: 1 d 47.0 vs 86.3 % (−39 points, CI 37–42); 2 d 32.9 vs 72.2 %; 3 d 24.8 vs
59.8 %; 5 d 16.4 vs 42.8 %; 8 d 10.6 vs 28.5 %. Clouds remove 46–63 % of opportunities. MODIS cloud mask as a proxy.

## 4. What the fleet misses (slide 10)

**Missed events — `figS07_event_capture_severity.png` (OBSERVED).**
- No look in 474 of 979 events (48.4 %).
- Look rate by window duration (station-bootstrap 95 % CI): < 1 d 16.3 % (11.3–22.6), 1–2 d 50.8 % (43.6–58.1),
  2–3 d 61.1 % (53.4–68.5), 3–5 d 75.3 % (67.9–82.0), ≥ 5 d 85.3 % (79.0–91.4).
- Large rises (≥ 0.09 m³/m³) are looked at 9.9 points more often (CI 2.8–17.2) but also last longer (Spearman ρ 0.19).
  Standardised to the cohort's duration mix the difference is +3.4 points (CI −2.9 to +10.3): once duration is held
  fixed there is no detectable amplitude effect. Missing an event is a timing problem.

## 5. Capture is not detection

**From a look to a detected change — `figS08_quality_attrition.png` (OBSERVED).** Same 979 events and denominator:

| Sensor | Look in window | Valid same-geometry pair | Valid retrieval in pair | Change > 1σ |
|---|---|---|---|---|
| Sentinel-1 VV | 296 (30.2 %) | 174 | 174 | **60 (6.1 %)** |
| NISAR HH | 371 (37.9 %) | 240 | 216 | **49 (5.0 %)** |
| NISAR SME2 | 371 | 240 | 139 | **51 (5.2 %)** |
| SMAP any quality (9 km) | 750 (76.6 %) | 647 | 647 | 334 (34.1 %) |
| SMAP recommended (9 km) | 261 (26.7 %) | 221 | 221 | 142 (14.5 %) |

- Any field-scale radar (Sentinel-1 VV, NISAR HH or SME2) registered a detected change in 111 of 979 events:
  **11.3 % (CI 9.0–14.0)**.
- The chain is not perfectly nested: 1 (Sentinel-1), 4 (NISAR), 8 (SMAP any) and 4 (SMAP recommended) events have a
  valid pair but no catalogue look (window-edge time rounding; catalogue against granule lists). They are counted.
- Detection on each sensor's own sampled events and false alarms on unchanged pairs are separate cohorts: Sentinel-1
  33 % (n 624) / 8.8 % (n 2,376); NISAR HH 23 % (216) / 3.9 % (511); SME2 37 % (139) / 8.6 % (372); SMAP any 53 %
  (2,200) / 8.1 % (27,190); SMAP recommended 65 % (693) / 8.6 % (13,527).

**Detection against false alarms — `figS09_detection_operating_curve.png` (OBSERVED).** Positives are sampled-event
changes; negatives are unchanged pairs (|ΔSM| < 0.01). FPR is the probability of a false detection. Thresholds are swept
in units of each sensor's no-change σ.

| Sensor | AUC | 1σ rule: detected / FPR | Held-out stations, threshold for 10 % FPR: detected (FPR) | 2025 → 2026 |
|---|---|---|---|---|
| Sentinel-1 VV | 0.65 | 33 % / 8.8 % | 34 % (9.8 %) | 35 % (9.0 %) |
| NISAR HH | 0.74 | 23 % / 3.9 % | **50 %** (10.2 %) | one season only |
| NISAR SME2 | 0.66 | 37 % / 8.6 % | 42 % (9.9 %) | one season only |
| SMAP any quality | 0.77 | 53 % / 8.1 % | 57 % (10.0 %) | 58 % (10.5 %) |
| SMAP recommended | 0.80 | 65 % / 8.6 % | 67 % (10.0 %) | 68 % (10.1 %) |

NISAR HH's 23 % reflects a conservative operating point (heavy-tailed no-change noise; 1σ gives only 4 % false alarms).
At a held-out 10 % threshold it detects 50 %. No field-scale sensor reaches ≥ 70 % detection at ≤ 10 % false alarms.

**Confusion matrices — `figS10_detection_matrix.png` (OBSERVED).** Counts per sensor at the 1σ rule; missing
retrievals excluded.

## 6. ARMO (slides 11–13)

**Orbit simulator — `figS11_orbit_simulation.png` (SIMULATED looks).** `code/06_mission_design.py` flies each candidate
design and turns it into look times at every station:
- Orbit: circular, 620 km, sun-synchronous (inclination 97.9° from the J2 condition; ascending node at 18:00 local, a
  dawn–dusk orbit), J2 nodal precession, spherical Earth, Earth rotation by GMST; positions every 10 s from 1 June to
  10 November 2026. Period 97 min.
- Look rule: a side-looking SAR sees a station at closest approach if the station is on the looking side and 25–45°
  off-nadir (362 km access swath). Design B/C/E satellites roll left and right on alternate revolutions; a SAR images
  one side at a time.
- Designs: A one satellite; B one satellite rolling; C one satellite rolling with 20–50° access; D two satellites 180°
  apart; E two satellites rolling.
- Scoring: simulated looks are merged with the real Sentinel-1 and NISAR look times and scored on the 979 events,
  averaged over 8 initial orbital phases.
- Example (design D, phase 0): 93 looks at Stillwater between 17 June and 31 October 2026, median gap 1.5 d.

**Paired gain — `figS12_capture_gain_paired_ci.png` (OBSERVED baseline, SIMULATED ARMO).**
- Design D: **+29.9 points** on the same events, 95 % CI **27.2–32.6** (station bootstrap, phases averaged); range over
  the 8 orbital phases 29.0–30.4; station + phase bootstrap 26.6–33.4. On average 293 events (284–298 by phase) gain a
  look.
- Other designs: A +19.5 (17.5–21.5), B +18.6 (16.6–20.5), C +25.6 (23.3–28.0), E +25.8 (23.4–28.2).
- By duration (design D): < 1 d 16 → 42 %, 1–2 d 51 → 90 %, 2–3 d 61 → 98 %, ≥ 3 d → 100 %. Events shorter than a day
  are still mostly missed.

**Usable imaging swath — `figS13_swath_capture_sensitivity.png` (SIMULATED, hypothetical).** Design D's 81.5 % assumes
the whole 25–45° access corridor (≈ 362 km) is imaged on every pass. Narrower usable strips, two station-agnostic
tasking rules ('fixed': one central strip; 'cycled': strips stepped across the corridor every revolution), same 979 events and 8 phases:

| Usable strip | Fleet + ARMO D | Paired gain over fleet (95 % CI) | ARMO-only gap median / p90 / longest |
|---|---|---|---|
| 362 km | **81.5 %** | +29.9 (27.2–32.6) | 1.5 / 2.5 / 5.5 d |
| 300 km, cycled / fixed | 78.6 / 78.9 % | +27.0 / +27.3 | 1.5 / 3.0 / 11–13 d |
| 250 km | 76.1 / 76.3 % | +24.5 / +24.7 | 1.5 / 3.0 / 11–17 d |
| 200 km | 72.2 / 72.7 % | +20.6 / +21.1 | 2.5 / 3.0–5.1 / 11–23 d |
| 100 km | 64.2 / 63.4 % | +12.6 / +11.8 | 3.0–4.5 / 9–14 d / 29–35 d |
| 50 km | 57.9 / 58.0 % | +6.3 / +6.4 | 3.0–6.0 / 24–27 d / 41–79 d |

No strip narrower than the full corridor reaches 80 %, so the 80 % result requires imaging essentially the whole
362 km access swath at 100–200 m on every pass. Data volume is assumed proportional to imaged width (MODEL-BASED);
power, radiometry and polarimetry for any width are UNVALIDATED.

## 7. Need maps (slides 14 and 15)

**Validation — `figS15_map_spatial_validation.png` (MODEL-BASED against OBSERVED).** Refitting the single
events-per-onset factor without the test stations (5 longitude blocks) leaves skill unchanged: r 0.82 held out against
0.82 in sample (227 station-seasons); weaker on cropland cells (r 0.69, n 37). The map's Sentinel-1 missed-event layer
against each station's actual 2026 misses: **r 0.78 (CI 0.71–0.84)**, bias −0.9 events per season. The maps are 0.1°
screening estimates with a Sentinel-1-only baseline, not per-field observations. `figS14_need_maps_report.png` is drawn
by `code/10_gee_need_maps.py` and needs Earth Engine to regenerate.

## 8. Limitations

- **ARMO change detection needs same-geometry pairs; not evaluated.** All detection numbers come from same-orbit /
  same-track pairs of existing sensors. ARMO's consecutive looks at a station fall at different off-nadir angles within
  25–45°, so its own same-geometry repeat interval is longer than its 1.4-day look cadence. The orbit model does not
  design a repeat ground track.
- Usable-swath scenarios are station-agnostic rules, not an imaging-mode design; data volume ∝ width is an assumption.
- Detection cohorts differ between sensors (periods, stations); only the look-to-detection chain (section 5) is a
  same-cohort comparison.
- NISAR products are provisional and cover one season.
- Only 9 cropland stations; cropland detection is not estimable for Sentinel-1 or NISAR.
- No commercial daily product (e.g. Spire D-HSSM) could be tested: no independent accuracy or event-timing data exist;
  a head-to-head test would need purchased data at USCRN stations.

## 9. Tests

`tests/test_evidence.py` runs 11 checks (results in `figures/generated/test_results.csv`): cohort partition; unique
event keys and a complete phase table; bootstrap reproducibility; paired-gain bounds; adding a satellite never reduces
capture (D ⊇ A, E ⊇ B per event and phase); swath monotonicity (centred strips nested, every strip ≤ the 362 km
baseline, 362 km = design D); SMAP any / recommended consistency; realistic sizing matches the slides; all 76 slide
numbers match; the figure manifest is complete; the 36 headline values match.
