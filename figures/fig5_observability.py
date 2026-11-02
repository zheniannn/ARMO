"""Figure 5: observability when sampled (C-band Sentinel-1, L-band NISAR, L-band radiometer SMAP),
detection by vegetation, the end-to-end detection chain, and the noise requirement curve."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "code"))
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from common import FIG, rd
import figstyle as fs

fs.apply()
LILAC = "#a99be8"



pr = rd("s1_pairs.csv")
sm = rd("s1_summary.csv", index_col=0).iloc[:, 0]
nis = rd("nisar_summary.csv", index_col=0).iloc[:, 0]
smap = rd("smap_summary.csv", index_col=0)["all"]
real = rd("capture_real.csv").set_index("fleet")
era = rd("era5_summary.csv").set_index("a_min")
strata = rd("detection_strata.csv")
snr = rd("snr_requirement.csv").set_index("sensor")
req = rd("snr_summary.csv", index_col=0).iloc[:, 0]
ev = rd("events.csv")

fig, axs = plt.subplots(2, 2, figsize=(7.6, 5.9), gridspec_kw=dict(wspace=0.55, hspace=0.62, width_ratios=[1, 1.1]))
a, b, c, d = axs.ravel()

# (a) change detection physics: same-geometry backscatter change vs ground-truth change, C vs L band
xs = np.linspace(-0.15, 0.3, 10)
c1 = pr[(pr.dsm.abs() < 0.35)]
a.scatter(c1.dsm, c1.dvv, s=3, color=fs.ORANGE, alpha=0.18, lw=0, rasterized=True)
k1 = np.polyfit(c1.dsm, c1.dvv, 1)
a.plot(xs, np.polyval(k1, xs), color=fs.ORANGE, lw=2, label=f"C-band S1 VV: {k1[0] / 10:.2f} dB per 0.1 m³/m³")
n2 = rd("nisar_pairs.csv").dropna(subset=["dhh"])
a.scatter(n2.dsm, n2.dhh, s=9, color=fs.VIOLET, alpha=0.7, lw=0)
k2 = np.polyfit(n2.dsm, n2.dhh, 1)
a.plot(xs, np.polyval(k2, xs), color=fs.VIOLET, lw=2, label=f"L-band NISAR HH: {k2[0] / 10:.2f} dB per 0.1 m³/m³")
a.axhline(0, color=fs.MUTED, lw=0.6); a.axvline(0, color=fs.MUTED, lw=0.6)
a.set_xlim(-0.15, 0.3); a.set_ylim(-6, 8)
a.set_xlabel("ΔSM ground truth (m³/m³)"); a.set_ylabel("Δσ⁰ same geometry (dB)")
a.legend(fontsize=5.8, loc="upper left", handlelength=1.2, frameon=True, framealpha=0.95, edgecolor="none")
a.set_title("Change sensitivity", loc="left", fontsize=8.5)
fs.panel_label(a, "a")

# (b) detection when sampled, by vegetation greenness at the event (MODIS NDVI via Earth Engine)
sens = [("Sentinel-1 VV (C-band SAR)", "S1 VV", fs.ORANGE), ("NISAR HH (L-band SAR)", "NISAR HH", fs.VIOLET),
        ("NISAR SME2 (L-band SAR)", "NISAR SME2", LILAC), ("SMAP (L-band radiometer)", "SMAP 9 km", fs.MAGENTA)]
levels = ["NDVI < 0.35 (sparse)", "0.35-0.6", "NDVI >= 0.6 (dense)"]
w = 0.19
for i, (key, lab, col) in enumerate(sens):
    g = strata[(strata.sensor == key) & (strata.dimension == "ndvi_bin")].set_index("level").reindex(levels)
    x = np.arange(3) + (i - 1.5) * w
    b.bar(x, g.p_detect * 100, w * 0.92, color=col, label=lab)
    b.errorbar(x, g.p_detect * 100, yerr=[(g.p_detect - g.ci_lo) * 100, (g.ci_hi - g.p_detect) * 100],
               fmt="none", ecolor=fs.INK2, elinewidth=0.7, capsize=1.5)
b.set_xticks(range(3)); b.set_xticklabels(["Sparse\nNDVI < 0.35", "Moderate\n0.35–0.6", "Dense\nNDVI ≥ 0.6"], fontsize=7)
b.set_ylim(0, 100); b.set_ylabel("Sampled events detected (%)")
b.grid(axis="x", visible=False)
b.legend(fontsize=5.8, ncol=2, loc="upper right", handlelength=1, columnspacing=0.8, frameon=True, framealpha=0.95, edgecolor="none")
b.set_title("Detection falls with vegetation", loc="left", fontsize=8.5)
fs.panel_label(b, "b")

# (c) detection chain (horizontal bars)
# matched-cohort chain (same 979 NISAR-era events for every row; figures/fig_quality_attrition.py). Revised 3 Nov 2026:
# the earlier "end-to-end" bars multiplied rates from different cohorts and overstated what the same events achieve.
import pandas as pd
qa = pd.read_csv(os.path.join(FIG, "generated", "quality_attrition_stats.csv"))
q = lambda sensor, stage: qa[(qa.sensor == sensor) & (qa.stage.str.startswith(stage))].value.iloc[0]
rows = [("S1 look in window", q("S1 VV", "Real look"), fs.ORANGE),
        ("S1 detected change (same events)", q("S1 VV", "Change"), fs.ORANGE),
        ("NISAR look in window", q("NISAR HH", "Real look"), fs.VIOLET),
        ("NISAR HH detected (same events)", q("NISAR HH", "Change"), fs.VIOLET),
        ("SME2 detected (same events)", q("NISAR SME2", "Change"), LILAC),
        ("Any radar detected (same events)", q("Field-scale radar fleet (S1 VV or NISAR HH or SME2)", "detected"), fs.INK2),
        ("SMAP any-quality look", q("SMAP all quality", "Real look"), fs.MAGENTA),
        ("SMAP any-quality detected", q("SMAP all quality", "Change"), fs.MAGENTA),
        ("SMAP recommended detected", q("SMAP recommended", "Change"), fs.MAGENTA),
        ("ERA5-Land POD", era.loc[0.02, "POD"], fs.AQUA), ("ERA5-Land false-alarm ratio", era.loc[0.02, "FAR"], fs.AQUA)]
y = np.arange(len(rows))[::-1]
for yi, (lab, v, col) in zip(y, rows):
    e2e = "detected" in lab
    c.barh(yi, v * 100, color=col, height=0.62, hatch="////" if e2e else None,
           edgecolor="white" if e2e else col, alpha=0.5 if "false" in lab else 1)
    c.text(v * 100 + 2, yi, f"{v * 100:.0f}%", va="center", fontsize=6.5)
c.set_yticks(y); c.set_yticklabels([r[0] for r in rows], fontsize=6.3)
c.set_xlim(0, 100); c.set_xlabel("% of 979 matched events (ERA5: all events)")
c.grid(axis="y", visible=False)
c.set_title("Same 979 events: look vs detected change", loc="left", fontsize=8.2)
fs.panel_label(c, "c")

# (d) requirement curve: calibrated detection model vs noise (soil-moisture units)
amps = ev.amp.to_numpy(); K = req["k_calibration"]
nn = np.geomspace(0.01, 0.2, 80)
d.plot(nn, [stats.norm.cdf(K * amps / n - 1).mean() * 100 for n in nn], color=fs.INK2, lw=1.6, label="Calibrated model")
for (key, lab, col) in [("Sentinel-1 VV", "S1 VV", fs.ORANGE), ("NISAR HH", "NISAR HH", fs.VIOLET),
                        ("NISAR SME2", "NISAR SME2", LILAC), ("SMAP", "SMAP", fs.MAGENTA)]:
    r = snr.loc[key]
    d.scatter(r.noise_sm_equiv, r.p_observed * 100, s=34, color=col, edgecolor="white", lw=1, zorder=3, label=lab)
d.axhline(70, color=fs.MUTED, lw=0.8, ls="--"); d.axvline(req["noise_req_70"], color=fs.BLUE, lw=1.2, ls=":")
d.text(req["noise_req_70"] * 1.07, 6, f"ARMO\nrequirement\n≤ {req['noise_req_70']:.3f}", color=fs.BLUE, fontsize=6.3, ha="left")
d.text(0.19, 72, "70 % target", fontsize=6.3, ha="right", color=fs.INK2)
d.xaxis.set_minor_formatter(plt.NullFormatter())
d.set_xscale("log"); d.set_xlim(0.01, 0.2); d.set_ylim(0, 100)
d.set_xticks([0.01, 0.02, 0.04, 0.1, 0.2]); d.set_xticklabels(["0.01", "0.02", "0.04", "0.1", "0.2"])
d.xaxis.set_minor_formatter(plt.NullFormatter())
d.set_xlabel("Change noise, soil-moisture equivalent (m³/m³)"); d.set_ylabel("Sampled events detected (%)")
d.legend(fontsize=5.8, loc="lower left", handlelength=1, frameon=True, framealpha=0.95, edgecolor="none")
d.set_title("MODEL-BASED: noise for 70 % detection", loc="left", fontsize=8.2)
fs.panel_label(d, "d")
fig.savefig(os.path.join(FIG, "fig5_observability.png"))
print("ok")
