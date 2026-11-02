# Figure programme: implementation summary (3 November 2026)

Science and methods: `docs/FIGURE_SCIENTIFIC_AUDIT.md`. Figure inventory: `figures/figure_manifest.csv`.
Blocked benchmark: `docs/COMMERCIAL_BENCHMARK_BLOCKED.md`. Nothing was committed or pushed.

## New files

| Path | Purpose |
|---|---|
| `figures/armo_evidence.py` | shared helpers: event key, NISAR-era cohort, seeded station-cluster bootstrap, Wilson CI, save (PNG 300 dpi + PDF) |
| `figures/reproduce_anchors.py` | recomputes 36 anchor values → `generated/anchor_check.csv` |
| `figures/fig_event_capture_severity.py` (.png/.pdf) | P0-1 |
| `figures/fig_capture_gain_paired_ci.py` (.png/.pdf) | P0-2 |
| `figures/fig_quality_attrition.py` (.png/.pdf) | P0-3 |
| `figures/fig_swath_capture_sensitivity.py` (.png/.pdf) | P0-4 |
| `figures/fig_detection_operating_curve.py` (.png/.pdf) | P0-5 |
| `figures/fig_map_spatial_validation.py` (.png/.pdf) | P1-6 |
| `figures/fig_optical_cloud_penalty.py` (.png/.pdf) | P1-7 |
| `figures/fig_vegetation_representativeness.py` (.png/.pdf) | P1-8 |
| `figures/fig_sampling_robustness.py` (.png/.pdf) | P1-9 |
| `figures/fig_depth_comparison.py` (.png/.pdf) | P1-10 |
| `figures/fig_mission_decision_frontier.py` (.png/.pdf) | P1-11 |
| `figures/build_manifest.py`, `figures/figure_manifest.csv` | manifest (28 rows: 23 figures, 4 slide assets, native charts) |
| `figures/generated/*.csv`, `*.log` | statistics behind each figure, run logs, test results |
| `figures/previous_2026-11-03/` | previous versions of every revised figure and script |
| `tests/test_evidence.py` | 13 deterministic checks |
| `docs/FIGURE_SCIENTIFIC_AUDIT.md`, `docs/FIGURE_IMPLEMENTATION_SUMMARY.md`, `docs/COMMERCIAL_BENCHMARK_BLOCKED.md` | documentation |
| `data/processed/armo_event_capture_by_phase.csv`, `armo_swath_event_capture.csv`, `armo_swath_gaps.csv` | per-event ARMO flags (git-ignored, regenerable) |

## Revised files

| Path | Change |
|---|---|
| `code/06_mission_design.py` | optional `event_flags` entry point (`broadside_passes`, `DESIGNS`, `SWATH_KM`); default run order and outputs unchanged |
| `figures/fig2_workflow.py` | gated decision box |
| `figures/fig3_4_6_results.py` | Figure 4 legend (ideal sampler); Figure 6 caption (idealised ARMO, ROSE-L ~2030+, bar vs gain CIs) |
| `figures/fig5_observability.py` | panel c = matched-cohort chain; panel d labelled MODEL-BASED |
| `figures/fig_armo_coverage.py` | access-vs-imaging caveat |
| `figures/fig_study_area.py` | 120/121 counts; cropland stations outlined |
| `README.md`, `code/README.md` | offline rerun instructions for the evidence figures |
| `Assignment (Do Not Push)/report_text.py`, `20_build_report.py` | matched-cohort chain, held-out detection, paired gain CI, swath caveat, model check, Gate 3 swath; Supplementary Figures S1–S11; `figure(label=)` |
| `Assignment (Do Not Push)/50_rebuild_outputs.py` | runs event_flags, evidence figures, manifest and tests |
| `Submission (Do Not Push)/build_deck.py` | slides 9, 10, 13, 15, 17 text; backup A3 replaced by the swath sensitivity (need maps stay as report Figure 1) |
| `Submission (Do Not Push)/analysis/audit_claims.py` | evidence claims (128 total); `depth10_cap_R2` class corrected |
| `Submission (Do Not Push)/ARMO_ES4304_Examiner_QA.md`, `ARMO_ES4304_Red_Team.md` | Q23–25; red-team items 16–17 |

Regenerated outputs: proposal (docx/pdf, 19 pages; Sections 1–5 on pages 2–11), deck (27 slides; 18-page main PDF;
27-page full PDF; PowerPoint validator passed), speaker notes, claim audit, Q&A, red team.

## Rerun (offline, from the repository root)

```bash
python code/06_mission_design.py event_flags
cd figures
python reproduce_anchors.py
for f in fig_event_capture_severity fig_quality_attrition fig_capture_gain_paired_ci fig_swath_capture_sensitivity \
         fig_detection_operating_curve fig_map_spatial_validation fig_vegetation_representativeness fig_sampling_robustness \
         fig_depth_comparison fig_optical_cloud_penalty fig5_observability fig2_workflow fig3_4_6_results fig_study_area \
         fig_armo_coverage fig_mission_decision_frontier build_manifest; do python $f.py; done
cd ..
python tests/test_evidence.py
# private deliverables (local only)
python "Submission (Do Not Push)/analysis/audit_claims.py"
python "Submission (Do Not Push)/build_deck.py"          # then export with Assignment (Do Not Push)/pptx_to_pdf.ps1
python "Assignment (Do Not Push)/20_build_report.py"     # then export with Assignment (Do Not Push)/to_pdf.ps1
```
`Assignment (Do Not Push)/50_rebuild_outputs.py` runs all of this, including the PDF exports and the tests.
Order matters: `fig5_observability.py`, `fig_mission_decision_frontier.py`, `audit_claims.py` and the report read the
CSVs written by the evidence scripts.
