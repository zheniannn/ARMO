"""Slide figure: change detection scored against ground truth as a confusion matrix per sensor (like the TP/FP/TN/FN
validation of the course's SAR tutorial).
Truth "wetting": a ground-truth wetting event with a look inside its window (the sampled events).
Truth "no change": a same-geometry pair whose 5 cm soil moisture changed by < 0.01 m3/m3.
Detected: the satellite change exceeds 1 sigma of its own no-change noise (the rule used throughout the report).
Missing retrievals are excluded. Inputs: the pair, sampled-event and summary tables from code/08_sensor_tests.py.
Output: figures/fig_detection_matrix.png
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "code"))
import matplotlib.pyplot as plt
from common import FIG, rd
import figstyle as fs

fs.apply()
s1s = rd("s1_summary.csv", index_col=0).iloc[:, 0]
ns = rd("nisar_summary.csv", index_col=0).iloc[:, 0]
ss = rd("smap_summary.csv", index_col=0)["all"]
cases = [("Sentinel-1 VV\n(C-band SAR, 10 m)", rd("s1_pairs.csv"), "dvv", rd("s1_sampled_events.csv"), s1s["noise_db_nochange"], "dB"),
         ("NISAR HH\n(L-band SAR backscatter)", rd("nisar_pairs.csv"), "dhh", rd("nisar_sampled_events.csv"), ns["noise_hh_db"], "dB"),
         ("NISAR SME2\n(L-band soil moisture, 200 m)", rd("nisar_pairs.csv"), "dsat", rd("nisar_sampled_events.csv"), ns["noise_sat_nochange"], "m³/m³"),
         ("SMAP L3E\n(L-band radiometer, 9 km)", rd("smap_pairs_all.csv"), "dsat", rd("smap_sampled_events_all.csv"), ss["noise_nochange"], "m³/m³")]

fig, axes = plt.subplots(1, 4, figsize=(11.0, 3.3))
for ax, (name, pr, col, ev, noise, unit) in zip(axes, cases):
    nc = pr[pr.dsm.abs() < 0.01][col].dropna(); e = ev[col].dropna()
    tp = int((e > noise).sum()); fn = len(e) - tp; fp = int((nc > noise).sum()); tn = len(nc) - fp
    cells = [[tp, fn], [fp, tn]]
    rate = [[tp / len(e), fn / len(e)], [fp / len(nc), tn / len(nc)]]
    good = [[True, False], [False, True]]
    for i in range(2):
        for j in range(2):
            c = fs.SEQ[1 + int(round(rate[i][j] * 5))] if good[i][j] else ["#fde3d6", "#f9c3a9", "#f39d78", "#eb6834", "#c4501f", "#9a3c14"][int(round(rate[i][j] * 5))]
            ax.add_patch(plt.Rectangle((j, 1 - i), 1, 1, fc=c, ec="white", lw=2))
            ink = "white" if rate[i][j] > 0.55 else fs.INK
            ax.text(j + 0.5, 1.5 - i + 0.12, f"{rate[i][j] * 100:.0f} %", ha="center", va="center", fontsize=12, fontweight="bold", color=ink)
            ax.text(j + 0.5, 1.5 - i - 0.2, f"n = {cells[i][j]:,}", ha="center", va="center", fontsize=7.5, color=ink)
    ax.set_xlim(0, 2); ax.set_ylim(0, 2); ax.set_aspect("equal"); ax.grid(False)
    ax.set_xticks([0.5, 1.5], ["detected", "not detected"], fontsize=7.5); ax.tick_params(length=0)
    ax.set_yticks([1.5, 0.5], ["wetting\nevent", "no\nchange"], fontsize=7.5)
    ax.xaxis.set_ticks_position("top")
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_xlabel(f"{name}\nthreshold 1σ = {noise:.2f} {unit}", fontsize=8, labelpad=6)
fig.text(0.5, -0.04, "Rows: ground truth (USCRN). ARMO's requirement: detect ≥ 70 % of wetting events with ≤ 10 % false alarms.",
         ha="center", fontsize=8.5, color=fs.INK2)
fig.subplots_adjust(wspace=0.45)
out = os.path.join(FIG, "fig_detection_matrix.png")
fig.savefig(out, dpi=250, bbox_inches="tight", pad_inches=0.05); print("saved", out)
