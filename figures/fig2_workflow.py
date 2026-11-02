"""Figure 2: analysis workflow (data -> pre-processing -> analyses per objective -> decision)."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "code"))
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from common import FIG
import figstyle as fs

fs.apply()
fig, ax = plt.subplots(figsize=(7.2, 4.1))
ax.set_xlim(0, 100); ax.set_ylim(0, 50); ax.axis("off")


def box(x, y, w, h, title, body, fc, ec):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2", fc=fc, ec=ec, lw=1))
    ax.text(x + w / 2, y + h - 1.6, title, ha="center", va="top", fontsize=6.9, fontweight="bold", color=fs.INK)
    two_line = len(title.splitlines()) > 1
    ax.text(x + w / 2, y + h - (7.6 if two_line else 4.8), body, ha="center", va="top", fontsize=5.9,
            color=fs.INK2, linespacing=1.3)


def arrow(x0, y0, x1, y1):
    ax.annotate("", (x1, y1), (x0, y0), arrowprops=dict(arrowstyle="-|>", color=fs.INK2, lw=1))


DATA, PRE, ANA, OUT = "#eaf2fc", "#f4f3f0", "#e8f6f0", "#fdf1e3"
ax.text(10.5, 49, "Phase 1  Data", ha="center", fontsize=8, color=fs.INK)
ax.text(36, 49, "Phase 1  Pre-processing", ha="center", fontsize=8, color=fs.INK)
ax.text(64, 49, "Phase 2  Analysis (Objectives)", ha="center", fontsize=8, color=fs.INK)
ax.text(90, 49, "Phase 3  Synthesis", ha="center", fontsize=8, color=fs.INK)

box(1, 35, 19, 11, "NOAA USCRN (truth)", "hourly 5 cm SM, rain,\nsoil temp; 133 stations", DATA, fs.BLUE)
box(1, 23, 19, 10, "Sentinel-1 RTC / GRD", "10 m VV+VH backscatter;\nactual pass times (STAC)", DATA, fs.BLUE)
box(1, 11.5, 19, 9.5, "NISAR (ASF / CMR)", "L-band pass times;\nSME2 200 m soil moisture", DATA, fs.BLUE)
box(1, 1, 19, 8.5, "ERA5-Land", "9 km hourly model SM\n(no-satellite baseline)", DATA, fs.BLUE)

box(25, 27, 22, 19, "QC + event detection", "NUL-byte repair, range check,\nfrozen mask (T5 ≤ 1 °C),\n≥ 70 % valid hours\n→ 227 station-seasons\nstorm ≥ 5 mm, rise ≥ 0.03\n→ 3,340 wetting events", PRE, fs.MUTED)
box(25, 1, 22, 22, "Matching", "acquisition → hour-ending\nUSCRN value; drop rain\n< 3 h before pass;\nsame-orbit pairs for\nchange detection;\none look per pass", PRE, fs.MUTED)

box(52, 36, 24, 10, "O1  Event timescales", "window W, half-life,\namplitude per event", ANA, fs.AQUA)
box(52, 24.5, 24, 10, "O2  Sampling capture", "regular 1–12 d (all phases)\n+ actual S1 / NISAR looks", ANA, fs.AQUA)
box(52, 12.5, 24, 10.5, "O3  Observability", "S1 Δσ° vs ΔSM; NISAR SME2\nvs truth; ERA5 POD/FAR", ANA, fs.AQUA)
box(52, 1, 24, 10, "Uncertainty", "station-cluster bootstrap;\n2025 vs 2026 holdout;\nthreshold sensitivity", ANA, fs.AQUA)

box(81, 22, 18, 24, "O4  Requirement\n& marginal value", "revisit for ≥ 80 %\ncapture; ARMO added\nto real 2026 fleet and\nto future fleet\n(+ ROSE-L)", OUT, fs.ORANGE)
box(81, 1, 18, 18, "Decision", "CONDITIONAL:\nfund Stage 1 now;\nStage 2 only if\ngo/no-go gates pass", OUT, fs.ORANGE)

for y in (40.5, 28, 16, 5):
    arrow(20.6, y, 24.6, 36 if y > 30 else (12 if y < 20 else 30))
arrow(47.6, 38, 51.6, 41); arrow(47.6, 34, 51.6, 29.5); arrow(47.6, 12, 51.6, 17.5); arrow(47.6, 6, 51.6, 6)
arrow(76.6, 41, 80.6, 38); arrow(76.6, 29.5, 80.6, 33); arrow(76.6, 17.5, 80.6, 27); arrow(76.6, 6, 80.6, 10)
arrow(90, 21.6, 90, 19.4)
fig.savefig(os.path.join(FIG, "fig2_workflow.png"))
print("ok")
