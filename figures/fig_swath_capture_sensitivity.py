"""P0-4  What if ARMO can only image a strip narrower than its 362 km access corridor?  (SIMULATED, HYPOTHETICAL envelope)

Baseline design D assumes every station inside the 25-45 deg off-nadir access corridor (~362 km of ground range) is imaged
on every pass. A real ScanSAR/stripmap mode images a strip of usable width W. code/06_mission_design.py event_flags models
W = 50, 100, 200 km with two deterministic, station-agnostic tasking rules (fixed central strip; strip stepped every
revolution) and W = 362 km (baseline). Scored on the SAME 979 events and 8 orbital phases as the baseline; paired with
the real fleet (OBSERVED acquisition times). Gaps: ARMO-only looks per station in the NISAR era, gaps <= 6 h dropped
(same rule as the claim audit). Data volume: first-order assumption that volume scales with imaged width at fixed pixel
spacing (MODEL-BASED; no imaging-mode design exists). This is a feasibility envelope, NOT an imaging-mode certification.
Outputs: figures/figS12_swath_capture_sensitivity.png, figures/generated/swath_sensitivity_stats.csv
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import armo_evidence as ae
import figstyle as fs
from common import PROC

fs.apply()
s = pd.read_csv(os.path.join(PROC, "armo_swath_event_capture.csv"), parse_dates=["t_ws"])
s["key"] = s.wban.astype(str) + "|" + s.t_ws.dt.strftime("%Y-%m-%dT%H")
gp = pd.read_csv(os.path.join(PROC, "armo_swath_gaps.csv"))
coh = ae.era_cohort(); coh["key"] = coh.wban.astype(str) + "|" + coh.t_ws.dt.strftime("%Y-%m-%dT%H")
w = coh.wban.to_numpy()
fleet = coh.fleet.to_numpy(float)
order = ["baseline 362 km (whole access corridor)"] + [f"{W} km {m}" for W in sorted(s.swath_km[s.swath_km < 362].unique(), reverse=True)
                                                       for m in ("cycled", "fixed")]
mats = {}
for sc in order:
    g = s[s.scenario == sc]
    mats[sc] = (g.pivot_table(index="key", columns="phase", values="combined_look", aggfunc="first").reindex(coh.key).to_numpy(float),
                g.pivot_table(index="key", columns="phase", values="armo_look", aggfunc="first").reindex(coh.key).to_numpy(float))
    assert np.allclose(g.pivot_table(index="key", columns="phase", values="fleet_look", aggfunc="first").reindex(coh.key)[0].to_numpy(float), fleet)
base_c = mats[order[0]][0].mean(1)
rows = []
for sc in order:
    comb, alone = mats[sc]
    ce = comb.mean(1)
    assert (comb >= fleet[:, None]).all()
    gain = ae.boot_stat(w, lambda i: (ce[i] - fleet[i]).mean())
    vsb = ae.boot_stat(w, lambda i: (ce[i] - base_c[i]).mean())
    g = gp[gp.scenario == sc]
    allg = np.concatenate([np.array(x.split(";"), float) for x in g.gaps_d.dropna().astype(str) if x])
    ph_max = g.groupby("phase").apply(lambda d: max(float(v) for x in d.gaps_d.dropna().astype(str) for v in x.split(";") if v))
    W = int(g.swath_km.iloc[0])
    rows.append(dict(scenario=sc, swath_km=W, mode=g["mode"].iloc[0], combined=ce.mean(), combined_phase_min=comb.mean(0).min(),
                     combined_phase_max=comb.mean(0).max(), armo_alone=alone.mean(), gain_pp=(ce - fleet).mean() * 100,
                     gain_ci_lo=ae.ci95(gain)[0] * 100, gain_ci_hi=ae.ci95(gain)[1] * 100,
                     vs_baseline_pp=(ce - base_c).mean() * 100, vs_baseline_ci_lo=ae.ci95(vsb)[0] * 100, vs_baseline_ci_hi=ae.ci95(vsb)[1] * 100,
                     looks_per_station=g.n_looks.mean(), gap_mean_d=allg.mean(), gap_p50_d=np.percentile(allg, 50), gap_p90_d=np.percentile(allg, 90),
                     gap_max_d=allg.max(), gap_max_phase_median_d=float(ph_max.median()), gap_gt3_frac=(allg > 3).mean(),
                     relative_data_volume=W / 362, meets_80pct=ce.mean() >= 0.80))
R = ae.write_stats("swath_sensitivity_stats", rows)

# ---------------------------------------------------------------- figure
fig, (a, b, c) = plt.subplots(1, 3, figsize=(7.8, 4.0), gridspec_kw=dict(wspace=0.55, width_ratios=[1.25, 1, 1]))
lab = {o: ("362 km corridor\n(baseline)" if o.startswith("baseline") else o) for o in order}
y = np.arange(len(order))[::-1]
for yi, r in zip(y, R.itertuples()):
    col = fs.YELLOW if r.mode == "baseline" else ("#e8b04a" if r.mode == "cycled" else "#f3d38a")
    a.barh(yi, r.combined * 100, color=col, height=0.6, edgecolor="#b07a00", lw=0.6)
    a.plot([r.combined_phase_min * 100, r.combined_phase_max * 100], [yi, yi], color=fs.INK, lw=1.2)
    a.text(r.combined * 100 + 2.5, yi, f"{r.combined * 100:.1f} %", va="center", fontsize=6.6)
a.axvline(fleet.mean() * 100, color=fs.BLUE, lw=1.2)
a.text(fleet.mean() * 100 + 0.8, -1.05, f"real fleet {fleet.mean() * 100:.1f} %", color=fs.BLUE, fontsize=6, ha="left", va="center")
a.axvline(80, color=fs.MUTED, ls=":", lw=1); a.text(80.8, -1.05, "80 %", color=fs.INK2, fontsize=6, va="center")
a.set_ylim(-1.5, len(order) - 0.4)
a.set_yticks(y); a.set_yticklabels([lab[o] for o in order], fontsize=6.6); a.set_xlim(40, 100)
a.set_xlabel("Fleet + ARMO D: events with a look (%)\n(line = range over 8 orbital phases)", fontsize=7.4)
a.grid(axis="y", visible=False)
a.set_title("Look opportunity vs usable strip", loc="left", fontsize=8.2)
fs.panel_label(a, "a")
for yi, r in zip(y, R.itertuples()):
    b.errorbar(r.vs_baseline_pp, yi, xerr=[[r.vs_baseline_pp - r.vs_baseline_ci_lo], [r.vs_baseline_ci_hi - r.vs_baseline_pp]],
               fmt="o", color=fs.RED if r.mode != "baseline" else fs.INK2, ms=4, capsize=2, lw=1)
b.axvline(0, color=fs.MUTED, lw=0.8)
b.set_yticks(y); b.set_yticklabels([]); b.set_xlabel("Paired change vs baseline (pp)\n95 % station-bootstrap CI", fontsize=7.4)
b.grid(axis="y", visible=False)
b.set_title("Loss from a narrower strip", loc="left", fontsize=8.2)
fs.panel_label(b, "b")
for yi, r in zip(y, R.itertuples()):
    c.plot([r.gap_p50_d, r.gap_p90_d], [yi, yi], color=fs.INK2, lw=1.2)
    c.scatter([r.gap_p50_d], [yi], s=18, color=fs.YELLOW, edgecolor=fs.INK, zorder=3, label="median" if yi == y[0] else None)
    c.scatter([r.gap_p90_d], [yi], s=18, color=fs.ORANGE, edgecolor=fs.INK, zorder=3, label="90th pct" if yi == y[0] else None)
    c.scatter([r.gap_max_phase_median_d], [yi], s=22, marker="x", color=fs.RED, zorder=3, label="longest (median phase)" if yi == y[0] else None)
c.set_xscale("log"); c.set_xticks([1, 2, 5, 10, 20, 40]); c.set_xticklabels(["1", "2", "5", "10", "20", "40"])
c.set_yticks(y); c.set_yticklabels([]); c.set_xlabel("ARMO-only gap between looks (d)", fontsize=7.4)
c.grid(axis="y", visible=False); c.legend(fontsize=5.8, loc="lower center", ncol=3, handletextpad=0.2, columnspacing=0.6)
c.set_ylim(-1.5, len(order) - 0.4); b.set_ylim(-1.5, len(order) - 0.4)
c.set_title("ARMO-only revisit gaps", loc="left", fontsize=8.2)
fs.panel_label(c, "c")
fig.text(0.01, -0.1,
         "SIMULATED, HYPOTHETICAL. Design D (2 satellites, 620 km dawn–dusk, right-looking 25–45° access corridor ≈ 362 km). A narrower usable strip W is imaged "
         "inside the corridor: 'fixed' = one central strip every pass;\n'cycled' = overlapping strips spanning the corridor, stepped every revolution. Same 979 events "
         "(107 stations, 17 Jun–31 Oct 2026), real Sentinel-1 + NISAR looks as baseline, 8 orbital phases. Not an imaging-mode design: radiometry,\n"
         "polarimetry, 100–200 m product quality, power and downlink for any W are UNVALIDATED. Data volume assumed ∝ W at fixed pixel spacing.",
         fontsize=5.9, color=fs.INK2)
ae.save(fig, "figS12_swath_capture_sensitivity")
print(R.round(3).to_string(index=False))
