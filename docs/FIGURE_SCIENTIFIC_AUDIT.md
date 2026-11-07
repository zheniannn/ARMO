# ARMO figure and evidence audit (3 November 2026)

Scope: every scientific figure in `figures/`, the report figures, the slide assets and native slide charts, and the
numbers behind them. All analyses here run **offline** from `data/processed/`; nothing was downloaded. Every number below
is written by a script to `figures/generated/*.csv`; the figure inventory is `figures/figure_manifest.csv`.
Evidence classes: **OBSERVED** (ground truth or real acquisitions), **SIMULATED** (orbit model or idealised sampler),
**MODEL-BASED** (calibrated statistical model or proxy), **REQUIREMENT** (a target), **UNVALIDATED** (not yet shown).

## 1. Reproduction of the anchor values

`figures/reproduce_anchors.py` recomputed 36 anchors from the processed tables; **all 36 match** (`generated/anchor_check.csv`):
3,340 events at 120 stations; matched cohort 979 events / 107 stations (storms 17 Jun–31 Oct 2026); looks S1 30.2 %,
NISAR 37.9 %, fleet 51.6 %; partition 474 none / 134 S1 only / 209 NISAR only / 162 both; 212 of 474 missed events
rose ≥ 0.09 m³/m³; duration bins 16.3 / 50.8 / 61.1 / 75.3 / 85.3 % (n 257 / 266 / 185 / 162 / 109); regular revisit
for 80 % = 1.46 d (1.31–1.64); design D mean gap 1.416 d, fleet + ARMO 81.5 %, gain +29.9 pp, ARMO alone 76.1 %;
SMAP era capture 76.6 % (any quality) vs 26.7 % (recommended); mission cost US$ 149.8 M. The event key (wban, t_ws) is unique.

The per-event ARMO export added to `code/06_mission_design.py` (`event_flags`) reproduces the published design results
exactly (fleet + ARMO A–E 71.1 / 70.1 / 77.2 / 81.5 / 77.4 %; ARMO alone 76.1 %), and its baseline gap distribution
reproduces the claim audit (longest ARMO gap 5.49 d).

## 2. High-priority analyses (P0)

### P0-1 Which real events are missed? — `figS07_event_capture_severity.png` (OBSERVED)
- Look categories on the 979 events: none 474 (48.4 %), S1 only 134, NISAR only 209, both 162.
- Look rate by window duration, station-bootstrap 95 % CI: < 1 d 16.3 % (11.3–22.6), 1–2 d 50.8 % (43.6–58.1),
  2–3 d 61.1 % (53.4–68.5), 3–5 d 75.3 % (67.9–82.0), ≥ 5 d 85.3 % (79.0–91.4).
- Amplitude: crudely, rises ≥ 0.09 m³/m³ were looked at 9.9 pp more often (CI 2.8–17.2), but they also last longer
  (Spearman ρ(amp, window) = 0.19). **Standardised to the cohort's duration mix the difference is +3.4 pp (CI −2.9 to
  +10.3): no detectable amplitude effect once duration is held fixed.** Missing an event is a timing problem.

### P0-2 Paired gain from ARMO — `figS11_capture_gain_paired_ci.png` (OBSERVED baseline, SIMULATED ARMO)
- Design D: **+29.9 pp** paired gain on the same events. 95 % CI **27.2–32.6** (station bootstrap, phases averaged);
  range over the 8 orbital phases 29.0–30.4; station + phase bootstrap 26.6–33.4. On average 293 events (284–298 by
  phase) are newly given a look.
- Other designs: A +19.5 (17.5–21.5), B +18.6 (16.6–20.5), C +25.6 (23.3–28.0), E +25.8 (23.4–28.2).
- By duration (design D): < 1 d 16 → 42 %, 1–2 d 51 → 90 %, 2–3 d 61 → 98 %, ≥ 3 d → 100 %. Even with ARMO, events
  shorter than a day are mostly missed.

### P0-3 From a look to a detected change — `figS08_quality_attrition.png` (OBSERVED)
Same 979 events, same denominator (events reaching each stage):

| Sensor | Look in window | Valid same-geometry pair | Valid retrieval in pair | Change > 1σ |
|---|---|---|---|---|
| Sentinel-1 VV | 296 (30.2 %) | 174 | 174 | **60 (6.1 %)** |
| NISAR HH | 371 (37.9 %) | 240 | 216 | **49 (5.0 %)** |
| NISAR SME2 | 371 | 240 | 139 | **51 (5.2 %)** |
| SMAP any quality (9 km) | 750 (76.6 %) | 647 | 647 | 334 (34.1 %) |
| SMAP recommended (9 km) | 261 (26.7 %) | 221 | 221 | 142 (14.5 %) |

- **Any field-scale radar (S1 VV or NISAR HH or SME2) registered a detected change in 111 of 979 events: 11.3 %
  (CI 9.0–14.0).**
- The chain is not perfectly nested: 1 (S1), 4 (NISAR), 8 (SMAP any) and 4 (SMAP recommended) events have a valid pair
  but no catalogue look (window-edge time rounding; catalogue vs granule lists). They are counted, not hidden.
- Published detection denominators (panel b) and false alarms on unchanged pairs (panel c) are shown separately because
  they are different cohorts: S1 33 % (n 624) / FA 8.8 % (n 2,376); NISAR HH 23 % (216) / 3.9 % (511); SME2 37 % (139) /
  8.6 % (372); SMAP any 53 % (2,200) / 8.1 % (27,190); SMAP recommended 65 % (693) / 8.6 % (13,527).

### P0-4 Usable imaging swath — `figS12_swath_capture_sensitivity.png` (SIMULATED, hypothetical) — **negative result**
Design D's 81.5 % assumes the whole 25–45° access corridor (≈ 362 km) is imaged on every pass. Narrower usable strips,
two station-agnostic tasking rules, same 979 events, 8 phases:

| Usable strip | Fleet + ARMO D | Paired gain over fleet (95 % CI) | ARMO-only gap median / p90 / longest |
|---|---|---|---|
| 362 km (baseline) | **81.5 %** | +29.9 (27.2–32.6) | 1.5 / 2.5 / 5.5 d |
| 300 km, cycled / fixed | 78.6 / 78.9 % | +27.0 / +27.3 | 1.5 / 3.0 / 11–13 d |
| 250 km | 76.1 / 76.3 % | +24.5 / +24.7 | 1.5 / 3.0 / 11–17 d |
| 200 km | 72.2 / 72.7 % | +20.6 / +21.1 | 2.5 / 3.0–5.1 / 11–23 d |
| 100 km | 64.2 / 63.4 % | +12.6 / +11.8 | 3.0–4.5 / 9–14 d / 29–35 d |
| 50 km | 57.9 / 58.0 % | +6.3 / +6.4 | 3.0–6.0 / 24–27 d / 41–79 d |

**No strip narrower than the full corridor reaches 80 %.** The 80 % target therefore requires imaging essentially the
whole 362 km access swath at 100–200 m on every pass, which no design yet shows. This is stated as a limitation in the README. Data volume was assumed proportional to imaged width (MODEL-BASED); power, radiometry and
polarimetry for any width are UNVALIDATED. Earlier tiling of the "cycled" rule left a partial last strip and was
corrected to evenly spaced overlapping strips before these results were taken.

### P0-5 Detection vs false alarms — `figS09_detection_operating_curve.png` (OBSERVED; target UNVALIDATED)
Positives = sampled-event changes; negatives = unchanged pairs (|ΔSM| < 0.01). FPR = probability of false detection,
not false-alarm ratio. Thresholds swept in units of each sensor's no-change σ.

| Sensor | AUC | 1σ rule: detected / FPR | Held-out stations, threshold for 10 % FPR: detected (FPR) | 2025 → 2026 |
|---|---|---|---|---|
| Sentinel-1 VV | 0.65 | 33 % / 8.8 % | 34 % (9.8 %) | 35 % (9.0 %) |
| NISAR HH | 0.74 | 23 % / 3.9 % | **50 %** (10.2 %) | BLOCKED (one season) |
| NISAR SME2 | 0.66 | 37 % / 8.6 % | 42 % (9.9 %) | BLOCKED |
| SMAP any quality | 0.77 | 53 % / 8.1 % | 57 % (10.0 %) | 58 % (10.5 %) |
| SMAP recommended | 0.80 | 65 % / 8.6 % | 67 % (10.0 %) | 68 % (10.1 %) |

- NISAR HH's published 23 % reflects a conservative operating point (heavy-tailed no-change noise; 1σ gives only 4 %
  false alarms). At a held-out 10 % threshold it detects 50 %. **No field-scale sensor reaches the ≥ 70 % / ≤ 10 % box.**
- The model-based 0.038 m³/m³ noise requirement checked here (SMAP recommended: 71.6 % predicted vs 65.4 % observed,
  n 693) was retired on 7 Nov 2026 with `snr_requirement()`; the presentation does not use it.

## 3. Additional analyses (P1)

- **P1-6 need-map validation** (`figS14_map_spatial_validation.png`, MODEL-BASED vs OBSERVED). Refitting the single
  events-per-onset factor without the test stations (5 longitude blocks) leaves skill unchanged: r 0.82 held out vs 0.82
  in sample (227 station-seasons); weaker on cropland cells (r 0.69, n 37). The map's Sentinel-1 missed-event layer vs
  each station's actual 2026 misses: **r 0.78 (CI 0.71–0.84)**, bias −0.9 events per season (slight underestimate).
  The maps remain 0.1° screening estimates with a Sentinel-1-only baseline, not per-field observations.
- **P1-7 optical cloud penalty** (`figS06_optical_cloud_penalty.png`, MODEL-BASED proxy). Clear-sky optical vs all-weather at
  the same cadence: 1 d 47.0 vs 86.3 % (−39 pp, CI 37–42); 2 d 32.9 vs 72.2; 3 d 24.8 vs 59.8 (−35); 5 d 16.4 vs 42.8;
  8 d 10.6 vs 28.5. Clouds remove 46–63 % of opportunities. MODIS cloud mask proxy only.
- **P1-8 representativeness** (`figS02_vegetation_representativeness.png`). 121 classified stations (120 with events;
  station 4125 has none); WorldCover cropland 9 (7 by USDA CDL at the probe), grassland 60, tree cover 36. Cropland
  detection groups are too small for S1 (n 17) and NISAR HH (n 24) and are flagged; SMAP cropland 56 % (n 192). No
  national crop-performance inference is possible.
- **P1-9 event definition** (`figS03_sampling_robustness.png`). 2,522–3,807 events; median window 40–48 h; 2-day capture
  69.7–74.8 %; 6-day 34.0–40.5 %. The 80 %-capture revisit was not recomputed per definition.
- **P1-10 depth** (`figS04_depth_comparison.png`). 2,433 storms produce events at both 5 and 10 cm (117 stations). Paired
  median window difference **0 h** (CI 0 to +2 h); paired capture difference +0.6 (1 d), +0.9 (2 d), +1.5 (3 d), +2.0 pp
  (6 d, CI 0.2–4.0). The earlier unpaired medians (1.79 vs 1.88 d) overstate the depth contrast. About probe depth only.
- **P1-11 decision matrix** (`fig_mission_decision_frontier.png`): retired 7 Nov 2026; the presentation's comparison
  slide (18) replaces it. Spire's accuracy, event timing and price remain UNKNOWN.
- **P2-12 commercial benchmark: BLOCKED** — no independent accuracy or event-timing data exist for commercial daily
  soil-moisture products (e.g. Spire D-HSSM); a head-to-head test would need purchased data at USCRN stations.

## 4. Audit of existing figures

| Figure | Action | Reason |
|---|---|---|
| figS13_need_maps_report | kept; validated (P1-6); report caption issue noted | S1-only screening estimate; regenerating needs Earth Engine |
| fig2_workflow | retired 7 Nov 2026 | gated two-stage decision no longer the narrative |
| fig3_stillwater_example | retired 7 Nov 2026 | replaced by fig_wetting_window (slide 5) |
| figS05_capture_vs_revisit | revised legend; own script 7 Nov 2026 | "ideal regular sampler on measured windows" (SIMULATED sampling) |
| fig5_observability | retired 7 Nov 2026 | panel d's noise requirement retired; detection shown by figS08_quality_attrition and figS09_detection_operating_curve |
| fig6_marginal_value | retired 7 Nov 2026 | idealised regular samplers, not design D; replaced by figS11_capture_gain_paired_ci and slides 12–13 |
| figS10_detection_matrix | kept | technical backup; complemented by P0-5 |
| slide09_resolution_ladder, case_studies/stillwater_* | kept | real imagery; single case; backscatter change has non-unique causes |
| figS01_study_area | revised | 120 event / 121 classified stations; 9 cropland outlined |
| deck figures (title background, ladder, wetting window, need maps, case studies) | kept | scripts in figures/ (see figure_manifest.csv) |

Earlier figure versions are in the git history.

## 5. Differences from previously reported claims

1. "End to end, today's radars register roughly 12–19 %" (capture × detection) → traced on the same events, **11.3 %
   (9.0–14.0)**; Sentinel-1 6 % rather than ≈ 10 %. The proposal's Table 4 "events registered" column is now labelled an
   upper bound.
2. SMAP "41 % end to end" (product) → 34 % of the same events (any quality), 15 % with recommended quality.
3. NISAR HH "23 % detection" is at the 1σ rule (4 % false alarms); at a held-out 10 % false-alarm threshold it is 50 %.
4. The 81.5 % / +29.9 pp result requires imaging the whole 362 km access swath; with 200 km it is 72–73 %.
5. The ≤ 0.038 m³/m³ noise requirement was model-based and, on an out-of-sample check, optimistic (65 % observed vs 72 %
   predicted at that noise); it was retired on 7 Nov 2026.
6. Paired CI for the gain now reported (27.2–32.6) instead of two separate capture CIs.
7. Claim-audit evidence class corrected: `depth10_cap_R2` was labelled OBSERVED; it is simulated sampling on observed
   events (caught by `tests/test_evidence.py`).
8. Depth: the paired median window difference is 0 h, smaller than the unpaired 1.79 vs 1.88 d suggested.

None of the 36 anchor values changed; the conclusions above are additions and corrections of interpretation.

## 6. Unresolved limitations

- **ARMO change detection needs same-geometry pairs. NOT EVALUATED.** All detection numbers come from same-orbit /
  same-track pairs of existing sensors. ARMO's consecutive looks at a station fall at different off-nadir angles within
  25–45°, so its own same-geometry repeat interval (and hence change-detection cadence) is longer than its 1.4-day look
  cadence. The orbit model does not yet design a repeat ground track; this is a Phase A / Stage 1 item.
- Usable-swath scenarios are station-agnostic deterministic rules, not an imaging-mode design; data volume ∝ width is
  an assumption.
- Detection cohorts differ between sensors (periods, stations); only the P0-3 chain is a same-cohort comparison.
- NISAR results are provisional and from one season (year split BLOCKED).
- Only 9 cropland stations; cropland detection is not estimable for S1 / NISAR.
- Spire / fusion benchmark BLOCKED (no data).
- `figS13_need_maps_report.png` was not regenerated (needs Earth Engine credentials); its limitation is documented here and in
  the manifest.

## 7. Tests

`tests/test_evidence.py` (13 checks; all PASS on 3 Nov 2026; results in `figures/generated/test_results.csv`): cohort
partition; unique event keys and complete phase table; bootstrap reproducibility; paired-gain bounds; adding a satellite
never reduces capture (D ⊇ A, E ⊇ B per event and phase); swath monotonicity (centred strips nested; every strip ≤ the
baseline; 362 km = design D); SMAP any / recommended consistency; no simulated capture labelled OBSERVED in the claim
audit; manifest complete; figure scripts ran without tracebacks; anchors match; 27 slides / 18-page main PDF / 27-page
full PDF; proposal Sections 1–5 within pages 2–11.
