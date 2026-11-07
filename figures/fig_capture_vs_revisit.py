"""Supplementary Figure S05 (supports slides 8 and 17): wetting-event window durations and event capture against revisit interval."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "code"))
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import PROC, FIG
import figstyle as fs

fs.apply()

cap = pd.read_csv(os.path.join(PROC, "capture_synthetic.csv"))
real = pd.read_csv(os.path.join(PROC, "capture_real.csv"))
rv = pd.read_csv(os.path.join(PROC, "revisit_real.csv"))
evs = pd.read_csv(os.path.join(PROC, "events.csv"))
fig, (a, b) = plt.subplots(1, 2, figsize=(7.2, 3.1), gridspec_kw=dict(width_ratios=[1, 1.35], wspace=0.28))
w = np.sort(evs.window_h.to_numpy() / 24)
a.plot(w, np.arange(1, w.size + 1) / w.size, color=fs.BLUE, label="Half-amplitude window")
wa = np.sort(evs.window_abs_h.to_numpy() / 24)
a.plot(wa, np.arange(1, wa.size + 1) / wa.size, color=fs.AQUA, label="Anomaly ≥ 0.03 m³/m³")
a.set_xlim(0, 10); a.set_ylim(0, 1)
a.set_xlabel("Event window duration (days)"); a.set_ylabel("Cumulative fraction of events")
a.axvline(np.median(w), color=fs.MUTED, lw=0.8, ls=":")
a.text(np.median(w) + 0.15, 0.92, f"median {np.median(w):.1f} d", fontsize=7.5, color=fs.INK2)
a.legend(loc="center right", fontsize=7.2)
a.set_title(f"{len(evs):,} wetting events, 120 stations", loc="left", fontsize=9)
fs.panel_label(a, "a")

for wn, col, lab in [("half-amplitude", fs.BLUE, "Ideal regular sampler on measured windows (half-amplitude)"),
                     ("abs0.03", fs.AQUA, "Ideal regular sampler (≥ 0.03 m³/m³ windows)")]:
    c = cap[cap.window == wn]
    b.fill_between(c.R, c.ci_lo * 100, c.ci_hi * 100, color=col, alpha=0.18, lw=0)
    b.plot(c.R, c.capture * 100, color=col, marker="o", ms=4, label=lab)
c = cap[cap.window == "half-amplitude"]
b.plot(c.R, c.analytic * 100, color=fs.INK2, lw=1, ls="--", label="Analytic E[min(1, W/R)]")
era = real[real.fleet.str.contains("NISAR era")]
gap = rv.groupby("fleet").mean_gap_d.median()
for (lab, key, col, mk) in [("Sentinel-1C/1D (actual)", "S1", fs.ORANGE, "s"), ("NISAR (actual)", "NISAR", fs.VIOLET, "D"),
                            ("S1 + NISAR (actual)", "S1+NISAR", fs.INK, "*")]:
    row = era[era.fleet.str.startswith({"S1": "Sentinel-1 (", "NISAR": "NISAR", "S1+NISAR": "Sentinel-1 + NISAR"}[key])].iloc[0]
    b.scatter(gap[key], row.capture * 100, color=col, marker=mk, s=60 if mk == "*" else 34, zorder=5, label=lab,
              edgecolor="white", linewidth=0.6)
b.axhline(80, color=fs.MUTED, lw=0.8, ls=":")
b.text(11.9, 81.5, "80 % capture target", ha="right", fontsize=7.5, color=fs.INK2)
b.set_xlabel("Revisit interval / actual mean gap between looks (days)")
b.set_ylabel("Events captured (%)")
b.set_xticks([1, 2, 3, 4, 6, 8, 10, 12]); b.set_ylim(0, 100)
b.legend(fontsize=6.8, loc="upper center", bbox_to_anchor=(0.45, -0.2), ncol=2, handlelength=1.6)
b.set_title("Capture vs revisit, 95 % station-bootstrap CI", loc="left", fontsize=9)
fs.panel_label(b, "b")
fig.savefig(os.path.join(FIG, "figS05_capture_vs_revisit.png"))
plt.close(fig)
