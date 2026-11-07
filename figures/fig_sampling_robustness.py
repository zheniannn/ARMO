"""P1-9  Does the event definition drive the result?  3 x 3 rain-threshold x rise-threshold grid (OBSERVED events; ideal
regular-revisit sampling SIMULATED on them).  Source: data/processed/sensitivity.csv (code/01_events.py sensitivity()).
Only the quantities actually rerun for each definition are shown (event count, median window, capture at 2/3/6-day
regular revisits). The 80 %-capture revisit was NOT recomputed per definition and is not shown.
Outputs: figures/figS03_sampling_robustness.png, figures/generated/sampling_robustness_stats.csv
"""
import numpy as np
import matplotlib.pyplot as plt
import armo_evidence as ae
import figstyle as fs
from common import rd

fs.apply()
s = rd("sensitivity.csv")
P, A = [2.0, 5.0, 10.0], [0.02, 0.03, 0.05]
panels = [("n_events", "Wetting events", "{:,.0f}", "Blues"), ("median_window_h", "Median window (h)", "{:.0f}", "Purples"),
          ("cap_R2", "Capture, 2-day revisit", "{:.1%}", "Oranges"), ("cap_R6", "Capture, 6-day revisit", "{:.1%}", "Oranges")]
fig, axs = plt.subplots(1, 4, figsize=(7.8, 2.5), gridspec_kw=dict(wspace=0.35))
for ax, (col, ttl, fmt, cmap) in zip(axs, panels):
    M = np.array([[s[(s.p_min == p) & (s.a_min == a)][col].iloc[0] for a in A] for p in P])
    ax.imshow(M, cmap=cmap, aspect="auto", alpha=0.75)
    for i in range(3):
        for j in range(3):
            base = P[i] == 5.0 and A[j] == 0.03
            ax.text(j, i, fmt.format(M[i, j]), ha="center", va="center", fontsize=7, fontweight="bold" if base else "normal",
                    bbox=dict(boxstyle="square,pad=0.25", fc="none", ec=fs.INK, lw=1.2) if base else None)
    ax.set_xticks(range(3)); ax.set_xticklabels([f"{a:g}" for a in A], fontsize=7)
    ax.set_yticks(range(3)); ax.set_yticklabels([f"{p:g}" for p in P] if ax is axs[0] else [], fontsize=7)
    ax.set_xlabel("Rise threshold (m³/m³)", fontsize=7); ax.grid(False)
    ax.set_title(ttl, fontsize=7.4, loc="left")
axs[0].set_ylabel("Storm total ≥ (mm)", fontsize=7)
fig.text(0.01, -0.16, f"OBSERVED events (USCRN, 120 stations, Apr–Oct 2025–2026) under 9 definitions; capture = ideal regular revisit (SIMULATED sampling, phase- and "
         f"dawn/dusk-averaged). Boxed = definition used throughout.\nRange: {s.n_events.min():,}–{s.n_events.max():,} events; median window "
         f"{s.median_window_h.min():.0f}–{s.median_window_h.max():.0f} h; 2-day capture {s.cap_R2.min():.1%}–{s.cap_R2.max():.1%}; 6-day "
         f"{s.cap_R6.min():.1%}–{s.cap_R6.max():.1%}. The 80 %-capture revisit was not recomputed per definition.", fontsize=6, color=fs.INK2)
ae.save(fig, "figS03_sampling_robustness")
ae.write_stats("sampling_robustness_stats", [dict(metric=c, min=s[c].min(), max=s[c].max(), baseline=s[(s.p_min == 5) & (s.a_min == 0.03)][c].iloc[0])
                                              for c in ["n_events", "median_window_h", "cap_R2", "cap_R3", "cap_R6", "cap_R12"]])
print(s.round(3).to_string(index=False))
