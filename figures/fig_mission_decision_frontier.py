"""P1-11  Build, buy, coordinate or fuse? An evidence matrix, not an economic Pareto frontier.

Rows = options; columns = the criteria the Stage 1 gates use. Every cell carries its evidence class. Numbers come from the
project tables (performance_headtohead.csv, armo_designs.csv, armo_sizing.csv, smap_summary.csv, and the outputs of
fig_quality_attrition.py / fig_detection_operating_curve.py / fig_swath_capture_sensitivity.py). Market facts are from
Submission (Do Not Push)/ARMO_ES4304_Market_and_Prior_Art.md (research cutoff 3 Nov 2026). Unknown values (Spire accuracy,
event timing, price) are shown as UNKNOWN, never as zero or "weak". Costs are first-order estimates (+-40 %) except where
stated. A no-launch option that meets ARMO's requirements in Stage 1 ends ARMO (Gate 1/2).
Outputs: figures/fig_mission_decision_frontier.png/.pdf, figures/generated/decision_options.csv
"""
import os
import textwrap
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import armo_evidence as ae
import figstyle as fs
from common import rd

fs.apply()
hh = rd("performance_headtohead.csv").set_index("system")
sz = rd("armo_sizing.csv").iloc[0]
sm = rd("smap_summary.csv", index_col=0)
D = rd("armo_designs.csv"); D = D.set_index(D.design.str[0])
dop = pd.read_csv(os.path.join(ae.GEN, "detection_operating_curve_stats.csv")).set_index("sensor")
sw = pd.read_csv(os.path.join(ae.GEN, "swath_sensitivity_stats.csv")).set_index("scenario")
pc = lambda x: f"{x * 100:.1f} %"
COLS = ["Independent field-scale\nmeasurement cadence", "Observation opportunity\n(979 events)", "Detection at 10 % FPR\n(held-out stations)",
        "Field scale\n(≤ 200 m)", "Cost / access", "Main open risk"]
rows = [
    ("Coordinate today's fleet\n(S1C/D + NISAR)", [("median gap 2.0 d, longest 20 d", "OBSERVED"), (pc(hh.loc["Sentinel-1 + NISAR", "capture"]), "OBSERVED"),
     (f"S1 {pc(dop.loc['Sentinel-1 VV (C, 10 m)', 'station_cv_tpr'])}; NISAR HH {pc(dop.loc['NISAR HH (L, 200 m)', 'station_cv_tpr'])}", "OBSERVED"),
     ("yes", "OBSERVED"), ("free", "OBSERVED"), ("looks miss short events", "OBSERVED")]),
    ("+ ROSE-L, 6 d (2 sats)", [("6 d, from ~2030 or later", "PLANNED"), (pc(hh.loc["Sentinel-1 + NISAR + ROSE-L 6-day", "capture"]), "SIMULATED"),
     ("assumed as NISAR", "UNVALIDATED"), ("yes", "PLANNED"), ("free", "PLANNED"), ("launch date uncertain", "PLANNED")]),
    ("Buy: Spire D-HSSM\n(100 m daily estimate)", [("daily estimate; S1 looks ~6 d beneath", "VENDOR CLAIM"), ("UNKNOWN (product is daily)", "UNKNOWN"),
     ("UNKNOWN — Stage 1 benchmark", "UNKNOWN"), ("100 m, downscaled", "VENDOR CLAIM"), ("price on request", "UNKNOWN"), ("event timing never scored", "UNKNOWN")]),
    ("Fuse: SMAP (+ NISAR + S1)", [("SMAP 2–3 d at 9 km", "OBSERVED"),
     (f"{pc(sm.loc['capture_era', 'all'])} any quality; {pc(sm.loc['capture_era', 'recommended'])} recommended", "OBSERVED"),
     (f"SMAP rec. {pc(dop.loc['SMAP recommended (9 km)', 'station_cv_tpr'])} (9 km)", "OBSERVED"), ("no (9 km)", "OBSERVED"),
     ("free + research", "ESTIMATE"), ("fusion method untested on events", "UNVALIDATED")]),
    ("Build: ARMO, 1 satellite (C)", [(f"mean gap {D.loc['C', 'armo_mean_gap_d']:.1f} d", "SIMULATED"), (pc(D.loc["C", "capture_fleet_plus_armo"]), "SIMULATED"),
     ("target 70 %", "REQUIREMENT"), ("100–200 m target", "REQUIREMENT"), (f"≈ US$ {sz.cost_threshold:.0f} M ± 40 %", "ESTIMATE"), ("misses 80 % even if fully imaged", "SIMULATED")]),
    ("Build: ARMO, 2 satellites (D)", [(f"mean gap {D.loc['D', 'armo_mean_gap_d']:.1f} d (longest 5.5)", "SIMULATED"),
     (f"{pc(D.loc['D', 'capture_fleet_plus_armo'])} (362 km corridor imaged); {pc(sw.loc['200 km fixed', 'combined'])} (200 km strip)", "SIMULATED"),
     ("target 70 %", "REQUIREMENT"), ("100–200 m target", "REQUIREMENT"), (f"≈ US$ {sz.cost_total:.0f} M ± 40 %", "ESTIMATE"),
     ("needs ~full-corridor imaging + 70 % retrieval", "UNVALIDATED")]),
]
COL = {"OBSERVED": "#d6ecf2", "SIMULATED": "#f8e7c3", "PLANNED": "#eeeeee", "REQUIREMENT": "#ffffff", "UNVALIDATED": "#fbe3e0",
       "ESTIMATE": "#f1f1ea", "VENDOR CLAIM": "#ececf6", "UNKNOWN": "#ffffff"}
EDGE = {"UNKNOWN": fs.RED, "UNVALIDATED": fs.RED}
out = [dict(option=o.replace("\n", " "), criterion=c.replace("\n", " "), value=v, evidence=e) for o, cells in rows for c, (v, e) in zip(COLS, cells)]
pd.DataFrame(out).to_csv(os.path.join(ae.GEN, "decision_options.csv"), index=False)

fig, ax = plt.subplots(figsize=(7.8, 5.6))
ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
x0, wl = 0.0, 0.2
wc = (1 - wl) / len(COLS)
h = 0.84 / (len(rows) + 1)
for j, c in enumerate(COLS):
    ax.text(x0 + wl + (j + 0.5) * wc, 1 - h / 2, textwrap.fill(c.replace(chr(10), " "), 18), ha="center", va="center", fontsize=5.6, fontweight="bold")
for i, (o, cells) in enumerate(rows):
    y = 1 - (i + 2) * h
    ax.text(0.005, y + h / 2, textwrap.fill(o.replace(chr(10), " "), 22), va="center", fontsize=5.8, fontweight="bold")
    for j, (v, e) in enumerate(cells):
        xx = x0 + wl + j * wc
        ax.add_patch(Rectangle((xx + 0.003, y + 0.004), wc - 0.006, h - 0.008, facecolor=COL[e], edgecolor=EDGE.get(e, "none"), lw=0.9,
                               ls="--" if e == "UNKNOWN" else "-"))
        ax.text(xx + wc / 2, y + h * 0.6, textwrap.fill(v, 17), ha="center", va="center", fontsize=5.2)
        ax.text(xx + wc / 2, y + h * 0.18, e, ha="center", va="center", fontsize=4.6, color=fs.INK2, fontweight="bold")
ax.text(0.0, 0.035, textwrap.fill("Recommendation (conditional): fund Stage 1 now. Proceed to ARMO Stage 2 only if no cheaper option meets ARMO's "
        "requirements on the same events (Gate 1, interim 2027; Gate 2, 2028), L-band retrieval reaches ≥ 70 % detection at ≤ 10 % false alarms "
        "(Gate 2), and Phase A shows the imaging swath, reflector and cost close (Gate 3). Otherwise buy, fuse, stop or redesign.", 150),
        fontsize=6, color=fs.INK)
ax.text(0.0, -0.03, textwrap.fill("Evidence classes as labelled; dashed red = UNKNOWN (not zero). Not an economic Pareto frontier: costs are ± 40 % "
        "estimates and no option's benefit is monetised. Market facts dated 3 Nov 2026.", 160), fontsize=5.6, color=fs.INK2)
ae.save(fig, "fig_mission_decision_frontier")
print(pd.DataFrame(out).to_string(index=False))
