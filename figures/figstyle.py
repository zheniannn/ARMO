"""Shared figure style (print figures for the PDF report and slides).
Categorical slots follow a validated CVD-safe order; text stays in ink colours."""
import matplotlib as mpl

BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = (
    "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948")
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8984", "#e4e3df"
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]


def apply():
    mpl.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
        "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
        "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
        "axes.spines.top": False, "axes.spines.right": False, "axes.axisbelow": True,
        "legend.frameon": False, "legend.fontsize": 8, "lines.linewidth": 2,
        "savefig.dpi": 300, "savefig.bbox": "tight", "figure.dpi": 110,
    })


def panel_label(ax, s):
    ax.text(-0.01, 1.02, s, transform=ax.transAxes, fontsize=11, fontweight="bold", va="bottom", ha="right")
