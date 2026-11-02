"""Write figures/figure_manifest.csv: one row per figure in figures/ (and the private slide assets / native charts),
with source script, exact inputs, cohort, numerator/denominator, time window, assumptions, uncertainty, finding and
suggested placement. Findings are filled from figures/generated/*.csv where a statistic exists.
Run: python figures/build_manifest.py
"""
import os
import pandas as pd
import armo_evidence as ae

G = lambda f: pd.read_csv(os.path.join(ae.GEN, f))
qa = G("quality_attrition_stats.csv"); gain = G("capture_gain_paired_stats.csv").set_index("design")
sw = G("swath_sensitivity_stats.csv").set_index("scenario"); roc = G("detection_operating_curve_stats.csv").set_index("sensor")
mapv = G("map_spatial_validation_stats.csv"); sev = G("event_capture_severity_stats.csv").set_index("quantity")
dep = G("depth_comparison_stats.csv").set_index("quantity"); opt = G("optical_cloud_penalty_stats.csv").set_index("revisit_d")
radar = qa[qa.stage == "detected change (union)"].iloc[0]
E979 = "979 NISAR-era events, 107 USCRN stations"
T26 = "storms 17 Jun–31 Oct 2026"
rows = [
    # ------------------------------------------------------------------ new evidence figures
    ("fig_event_capture_severity.png", "Which real events the fleet misses", "NEW · OBSERVED", "figures/fig_event_capture_severity.py",
     "data/processed/events_real.csv", E979, "events with ≥1 real S1/NISAR look / 979", T26,
     "look = acquisition inside half-amplitude window; not a detection", "station-cluster bootstrap 95 % CI (2,000)",
     f"474/979 no look; <1 d windows {sev.loc['fleet look | duration < 1 d', 'value'] * 100:.1f} % vs ≥5 d {sev.loc['fleet look | duration ≥ 5 d', 'value'] * 100:.1f} %; "
     f"duration-standardised rise effect {sev.loc['duration-standardised difference (big - small), pp', 'value']:+.1f} pp (CI "
     f"{sev.loc['duration-standardised difference (big - small), pp', 'ci_lo']:+.1f} to {sev.loc['duration-standardised difference (big - small), pp', 'ci_hi']:+.1f})",
     "report Figure S1; slide 9 text"),
    ("fig_capture_gain_paired_ci.png", "Paired gain from simulated ARMO on the same events", "NEW · OBSERVED baseline + SIMULATED",
     "figures/fig_capture_gain_paired_ci.py; code/06_mission_design.py event_flags", "data/processed/armo_event_capture_by_phase.csv, events_real.csv",
     E979, "per-event combined − fleet look, mean over events", T26, "ARMO orbit model, 8 phases, whole access swath imaged",
     "paired station bootstrap; phase range; station+phase bootstrap",
     f"D +{gain.loc['D', 'gain_pp']:.1f} pp (CI {gain.loc['D', 'gain_ci_station_lo']:.1f}–{gain.loc['D', 'gain_ci_station_hi']:.1f}; with phase "
     f"{gain.loc['D', 'gain_ci_station_and_phase_lo']:.1f}–{gain.loc['D', 'gain_ci_station_and_phase_hi']:.1f}); {gain.loc['D', 'newly_looked_events_mean']:.0f} events newly looked",
     "report Figure S2; slide 15 text"),
    ("fig_quality_attrition.png", "From a look to a detected change, per sensor", "NEW · OBSERVED", "figures/fig_quality_attrition.py",
     "events_real.csv, s1/nisar/smap sampled events and pairs, gee_smap.csv, *_summary.csv", E979 + "; panels b–c published per-sensor cohorts",
     "events reaching each stage / 979; detections / sampled; false alarms / unchanged pairs", "2026 (a); 2025–2026 (b, c for S1/SMAP)",
     "1σ no-change noise threshold per sensor; SMAP look = retrieval in window", "station-cluster bootstrap",
     f"any field-scale radar detected change in {int(radar.n)}/979 = {radar.value * 100:.1f} % (CI {radar.ci_lo * 100:.1f}–{radar.ci_hi * 100:.1f})",
     "report Figure S3; Figure 5c revised"),
    ("fig_swath_capture_sensitivity.png", "Usable imaging strip vs ARMO benefit", "NEW · SIMULATED (hypothetical)",
     "figures/fig_swath_capture_sensitivity.py; code/06_mission_design.py event_flags", "data/processed/armo_swath_event_capture.csv, armo_swath_gaps.csv",
     E979, "events with a look (fleet + ARMO D) / 979", T26, "deterministic strip models (fixed, cycled); data volume ∝ width",
     "paired station bootstrap vs baseline; 8-phase range",
     f"362 km 81.5 %; 300 km {sw.loc['300 km cycled', 'combined'] * 100:.1f}–{sw.loc['300 km fixed', 'combined'] * 100:.1f} %; 200 km "
     f"{sw.loc['200 km cycled', 'combined'] * 100:.1f}–{sw.loc['200 km fixed', 'combined'] * 100:.1f} %; none below 362 km reaches 80 %",
     "report Figure S4; backup A3"),
    ("fig_detection_operating_curve.png", "Detection vs false alarms, held-out operating points", "NEW · OBSERVED (target UNVALIDATED)",
     "figures/fig_detection_operating_curve.py", "s1/nisar/smap sampled events and pairs, *_summary.csv",
     "per-sensor sampled events and unchanged pairs (S1 624/2,376; NISAR HH 216/511; SME2 139/372; SMAP 2,200/27,190 and 693/13,527)",
     "detected / sampled events; false alarms / unchanged pairs", "S1, SMAP 2025–2026; NISAR 2026",
     "threshold swept in σ units; FPR = probability of false detection", "station bootstrap; 5-fold held-out stations; 2025→2026 split",
     f"held-out detection at 10 % FPR: S1 {roc.loc['Sentinel-1 VV (C, 10 m)', 'station_cv_tpr'] * 100:.0f} %, NISAR HH "
     f"{roc.loc['NISAR HH (L, 200 m)', 'station_cv_tpr'] * 100:.0f} %, SME2 {roc.loc['NISAR SME2 (L, 200 m)', 'station_cv_tpr'] * 100:.0f} %, SMAP rec "
     f"{roc.loc['SMAP recommended (9 km)', 'station_cv_tpr'] * 100:.0f} %; none field-scale reaches 70 %",
     "report Figure S5; slide 10 text"),
    ("fig_map_spatial_validation.png", "Held-out validation of the need maps", "NEW · MODEL-BASED vs OBSERVED",
     "figures/fig_map_spatial_validation.py", "need_stations.csv, station_seasons.csv, events_real.csv",
     "227 station-seasons (events); 111 stations (2026 missed layer)", "observed vs predicted events per station-season", "2025–2026",
     "one pooled events-per-onset factor refitted without test stations", "longitude-block and random 5-fold; station bootstrap on r",
     f"held-out r {mapv.iloc[1].r:.2f} (in-sample {mapv.iloc[0].r:.2f}); cropland cells r {mapv.iloc[2].r:.2f}; S1-missed layer r {mapv.iloc[-1].r:.2f}",
     "report Figure S6"),
    ("fig_vegetation_representativeness.png", "Station cover and detection by cover", "NEW · OBSERVED", "figures/fig_vegetation_representativeness.py",
     "station_vegetation.csv, events.csv, sampled events", "121 classified / 120 event stations; sampled events per sensor",
     "share of stations/events; detected / sampled by cover", "2025–2026", "WorldCover class at the probe", "station bootstrap; n<30 or <5 stations flagged",
     "9 of 121 stations cropland; cropland detection groups too small for S1/NISAR", "report Figure S7"),
    ("fig_sampling_robustness.png", "Event-definition sensitivity (3×3)", "NEW · OBSERVED events, SIMULATED sampling", "figures/fig_sampling_robustness.py",
     "data/processed/sensitivity.csv", "all 120 stations, 2025–2026", "events; capture = phase-averaged regular sampler", "Apr–Oct 2025–2026",
     "80 %-revisit not recomputed per definition", "none (deterministic counts)", "2,522–3,807 events; 6-day capture 34.0–40.5 %", "report Figure S8; backup A1"),
    ("fig_depth_comparison.png", "5 cm vs 10 cm, paired storms", "NEW · OBSERVED", "figures/fig_depth_comparison.py", "data/processed/depth_events.csv",
     "2,433 storms with events at both depths, 117 stations", "paired window difference; paired capture", "2025–2026",
     "probe depth only, not radar penetration", "station bootstrap",
     f"paired median window difference {dep.loc['paired median of (10 cm - 5 cm) window (d)', 'value'] * 24:+.0f} h; 6-day capture "
     f"{dep.loc['paired capture at 6-day revisit: 5 cm / 10 cm / diff pp', 'value']:+.1f} pp", "report Figure S9; backup A6 text"),
    ("fig_optical_cloud_penalty.png", "Clear-sky optical vs all-weather sampling", "NEW · MODEL-BASED proxy", "figures/fig_optical_cloud_penalty.py",
     "data/processed/optical_events.csv", "3,340 events, 120 stations", "phase-averaged per-event opportunity", "2025–2026",
     "MODIS cloud mask proxy; morning overpass", "station bootstrap of paired difference",
     f"1 d: {opt.loc[1, 'optical_clear'] * 100:.1f} % vs {opt.loc[1, 'all_weather'] * 100:.1f} %; 3 d: {opt.loc[3, 'optical_clear'] * 100:.1f} % vs "
     f"{opt.loc[3, 'all_weather'] * 100:.1f} %", "report Figure S10"),
    ("fig_mission_decision_frontier.png", "Build / buy / coordinate / fuse evidence matrix", "NEW · mixed classes (UNKNOWN shown)",
     "figures/fig_mission_decision_frontier.py", "performance_headtohead.csv, armo_designs.csv, armo_sizing.csv, smap_summary.csv, generated stats, market report",
     "as each cell", "as each cell", "market facts dated 3 Nov 2026", "no Pareto frontier; costs ± 40 %", "as source cells",
     "no option yet demonstrated to meet ARMO's requirements; Spire UNKNOWN", "report Figure S11; slide 17 consistent"),
    # ------------------------------------------------------------------ existing figures (audited)
    ("fig1_need_maps.png", "National need maps", "KEPT · MODEL-BASED (screening)", "code/10_gee_need_maps.py (needs Earth Engine to regenerate)",
     "need_grid.npz, need_stations.csv, events.csv", "0.1° CONUS cells; calibrated at 227 station-seasons", "events per season; S1-only misses and ARMO gain",
     "2025–2026 (gridMET), 2026 (S1)", "S1-only baseline (not S1+NISAR); regular-sampler capture model", "none on map; validated in fig_map_spatial_validation",
     "held-out validation r 0.78 for missed layer; screening, not per-field observation", "report Figure 1 (caption should say screening estimate)"),
    ("fig2_workflow.png", "Analysis workflow", "REVISED · diagram", "figures/fig2_workflow.py", "none", "—", "—", "—",
     "decision box now: CONDITIONAL, Stage 1 now, Stage 2 only through gates", "—", "workflow → gated decision", "report Figure 2"),
    ("fig3_stillwater_example.png", "Stillwater example", "KEPT · OBSERVED (single site, illustrative)", "figures/fig3_4_6_results.py",
     "uscrn_hourly.pkl, events_real.csv, acq_s1.csv, acq_nisar.csv", "1 station, NISAR era", "events with a look at one station", T26,
     "illustration only", "none", "single-site illustration", "report Figure 3"),
    ("fig4_capture_vs_revisit.png", "Capture vs regular revisit", "REVISED legend · SIMULATED sampling on OBSERVED windows", "figures/fig3_4_6_results.py",
     "capture_synthetic.csv, capture_real.csv, revisit_real.csv, events.csv", "3,340 events", "captured / events", "2025–2026",
     "ideal phase-swept regular sampler; real fleets plotted at mean gap", "station bootstrap bands", "80 % needs 1.46 d (1.31–1.64)", "report Figure 4"),
    ("fig5_observability.png", "Observability when sampled", "REVISED panel c (matched cohort) · OBSERVED + MODEL-BASED (d)", "figures/fig5_observability.py",
     "s1/nisar pairs, detection_strata.csv, snr_requirement.csv, snr_summary.csv, generated/quality_attrition_stats.csv", "per panel",
     "per panel", "2025–2026 / 2026", "panel d noise requirement is MODEL-BASED", "Wilson CIs (b)", "end-to-end bars replaced by same-event chain (11 % any radar)",
     "report Figure 5"),
    ("fig6_marginal_value.png", "Marginal value of idealised ARMO revisits", "REVISED caption · OBSERVED baseline + SIMULATED", "figures/fig3_4_6_results.py",
     "marginal_value.csv", "979 events", "captured / 979", T26, "ARMO bars are idealised regular samplers, not design D; ROSE-L ~2030 or later",
     "bar CIs only (gain CI in fig_capture_gain_paired_ci)", "idealised 2-day ARMO → 80 %", "report Figure 6"),
    ("fig_armo_coverage.png", "Revisit maps S1 / ARMO / combined", "REVISED caveat · SIMULATED access", "figures/fig_armo_coverage.py",
     "need_grid.npz, armo_revisit_grid.npz", "CONUS 0.5° grid, one orbital phase", "mean revisit", "1 Jun–10 Nov 2026",
     "access opportunities, whole corridor imaged; combined = rate sum", "none", "not event capture or imaging coverage", "backup A4 footer reference only"),
    ("fig_detection_matrix.png", "Confusion matrices", "KEPT · OBSERVED", "figures/fig_detection_matrix.py", "*_pairs.csv, *_sampled_events.csv",
     "per-sensor cohorts", "counts", "2025–2026 / 2026", "1σ rule; missing retrievals excluded", "counts shown (no CI)",
     "technical detail; complements fig_detection_operating_curve", "backup A2"),
    ("fig_market_niche.png", "Soil-moisture source niche map", "KEPT · dated source table (private generator)",
     "Assignment (Do Not Push)/19_market_report.py (source table SYS, references S1–S26 dated 2–3 Nov 2026)", "in-script dated table",
     "products as published", "—", "accessed 2–3 Nov 2026", "Spire D-HSSM 100 m and ROSE-L ~2030+ updated 3 Nov 2026", "—",
     "only open, direct systems are in the ARMO niche; Spire's 100 m is downscaled", "market.pdf (not in the proposal)"),
    ("fig_resolution_ladder.png", "Resolution ladder (real imagery)", "KEPT · OBSERVED imagery", "figures/fig_resolution_ladder.py",
     "data/processed/imagery/*", "one 24 × 24 km scene, Aug 2026", "—", "23–25 Aug 2026", "product pixels ≠ independent footprints", "—",
     "illustration of frequency vs detail", "slide 4 asset"),
    ("fig_sar_wetting_event.png", "Sentinel-1 before/after wetting", "KEPT · OBSERVED (single case)", "figures/fig_sar_wetting_event.py",
     "imagery/*, gridMET", "one scene pair", "Δσ⁰ vs rain", "13 and 25 Aug 2026", "backscatter change has non-unique causes", "—",
     "r 0.73 with rain at 4 km; one case, not validation", "backup A8"),
    ("fig_sar_wetting_event_oakley.png", "Sentinel-1 before/after wetting, Oakley KS", "NEW · OBSERVED (single case)",
     "figures/fig_sar_wetting_event.py oakley; code/12_extract_imagery.py oakley", "imagery/oakley_*.npz, uscrn_hourly.pkl",
     "one same-orbit pair (orbit 85, descending), 60 × 60 km", "Δσ⁰ vs gridMET rain at 4 km cells", "4–16 Aug 2026",
     "single case; gridMET under-resolves convective rain; part of box outside the swath (67 % valid)", "—",
     "probe 0.10 → 0.36 m³/m³, +5.7 dB at the station; widespread +2 to +6 dB; r(rain, Δσ⁰) 0.16 (little rain contrast)", "optional backup / report supplement"),
    ("fig_sar_wetting_event_champaign.png", "Sentinel-1 before/after wetting, Champaign IL (cropland)", "NEW · OBSERVED (single case)",
     "figures/fig_sar_wetting_event.py champaign; code/12_extract_imagery.py champaign", "imagery/champaign_*.npz, uscrn_hourly.pkl",
     "one same-orbit pair (orbit 19, ascending), 60 × 60 km", "Δσ⁰ vs gridMET rain at 4 km cells", "4–16 Sep 2026",
     "single case; near harvest, so crop changes also alter σ⁰", "—",
     "probe 0.14 → 0.26 m³/m³, +5.0 dB at the station; r(rain, Δσ⁰) 0.55; +0.7 dB (< 20 mm) vs +1.4 dB (≥ 20 mm)", "optional backup / report supplement"),
    ("fig_study_area.png", "Study area", "REVISED · OBSERVED", "figures/fig_study_area.py", "events.csv, station_vegetation.csv", "120 event / 121 classified stations",
     "—", "2025–2026", "WorldCover cropland at the probe outlined (9)", "—", "cropland under-represented", "slide 6 asset (via make_assets)"),
]
cols = ["figure_file", "title", "status", "source_script", "inputs", "cohort", "numerator_denominator", "time_window", "assumptions",
        "uncertainty", "finding", "placement"]
m = pd.DataFrame(rows, columns=cols)
extra = pd.DataFrame([
    ("[slide asset] title_bg.png", "Title background (Sentinel-1D VV)", "KEPT · OBSERVED imagery", "Submission (Do Not Push)/analysis/make_assets.py",
     "imagery", "1 scene", "—", "25 Aug 2026", "decorative", "—", "—", "slide 1"),
    ("[slide asset] s3_stillwater_aug2026.png", "Hourly timeline, Stillwater", "KEPT · OBSERVED", "Submission (Do Not Push)/analysis/make_assets.py",
     "uscrn_hourly.pkl, acq_*.csv, gee_smap.csv", "1 station", "—", "10–29 Aug 2026", "single site, illustrative", "—", "—", "slide 3"),
    ("[slide asset] s4_ladder.png", "Resolution ladder", "KEPT · OBSERVED imagery", "Submission (Do Not Push)/analysis/make_assets.py", "imagery",
     "1 scene", "—", "Aug 2026", "pixels ≠ footprints", "—", "—", "slide 4"),
    ("[slide asset] s6_study_area.png", "Study area (slide)", "KEPT · OBSERVED", "Submission (Do Not Push)/analysis/make_assets.py", "events.csv",
     "120 stations", "—", "2025–2026", "—", "—", "—", "slide 6"),
    ("[native chart] slides 8, 9, 10, 11, 14, 15, A4", "Native PowerPoint charts", "REVISED labels/text where noted",
     "Submission (Do Not Push)/build_deck.py", "analysis/values.json", "as slide", "as slide", "as slide",
     "slide 11 = SIMULATED sampling on OBSERVED events; slide 15 paired CI", "as slide", "—", "main deck / A4"),
], columns=cols)
m = pd.concat([m, extra], ignore_index=True)
m.to_csv(os.path.join(os.path.dirname(ae.GEN), "figure_manifest.csv"), index=False)
print(len(m), "manifest rows")
