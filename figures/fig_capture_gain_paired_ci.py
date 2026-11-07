"""Paired gain in observation opportunity from adding simulated ARMO to the real fleet (OBSERVED baseline vs SIMULATED).

Input: data/processed/armo_event_capture_by_phase.csv (code/06_mission_design.py event_flags): one row per event x design x
orbital phase with the real-fleet look flag, the simulated ARMO-alone look flag and the combined flag, on the SAME 979
NISAR-era events (107 stations, 17 Jun-31 Oct 2026).
Paired gain per event = combined - fleet (>= 0 by construction). Point estimate averages the 8 phases. Uncertainty, stated
separately because they answer different questions:
  station : station-cluster bootstrap of the phase-averaged paired gain (sampling of stations/events; phase fixed by averaging)
  phase   : spread of the gain across the 8 simulated initial orbital phases (orbit-placement uncertainty; not sampling)
  both    : each bootstrap draw resamples stations AND picks one phase at random (covers both; wider)
No CI is derived by differencing two independent CIs.
Outputs: figures/figS12_capture_gain_paired_ci.png, figures/generated/capture_gain_paired_stats.csv
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import armo_evidence as ae
import figstyle as fs
from common import PROC

fs.apply()
f = pd.read_csv(os.path.join(PROC, "armo_event_capture_by_phase.csv"), parse_dates=["t_ws"])
f["key"] = f.wban.astype(str) + "|" + f.t_ws.dt.strftime("%Y-%m-%dT%H")
coh = ae.era_cohort()
coh["key"] = coh.wban.astype(str) + "|" + coh.t_ws.dt.strftime("%Y-%m-%dT%H")
assert set(f.key) == set(coh.key) and f.groupby(["design", "phase"]).size().eq(len(coh)).all()
rng = np.random.default_rng(ae.SEED)
stats, res = [], {}
for d in "ABCDE":
    g = f[f.design == d].pivot_table(index="key", columns="phase", values=["fleet_look", "armo_look", "combined_look"], aggfunc="first")
    g = g.reindex(coh.key)
    fleet = g["fleet_look"][0].to_numpy(float)
    comb = g["combined_look"].to_numpy(float)          # events x 8 phases
    alone = g["armo_look"].to_numpy(float)
    gain_e = comb.mean(1) - fleet
    assert (comb >= fleet[:, None]).all(), "adding a satellite reduced capture"
    w = coh.wban.to_numpy()
    st = ae.boot_stat(w, lambda i: gain_e[i].mean())
    ph = (comb - fleet[:, None]).mean(0)
    both = []
    for i in ae.cluster_draws(w, seed=ae.SEED + 1):
        k = rng.integers(8)
        both.append((comb[i, k] - fleet[i]).mean())
    both = np.array(both)
    new_ev = ((comb > 0) & (fleet[:, None] == 0)).sum(0)
    res[d] = dict(gain=gain_e.mean(), st=ae.ci95(st), ph=(ph.min(), ph.max()), ph_all=ph, both=ae.ci95(both),
                  comb=comb.mean(), fleet=fleet.mean(), alone=alone.mean(), alone_ci=ae.ci95(ae.boot_stat(w, lambda i: alone[i].mean(1).mean())),
                  comb_ci=ae.ci95(ae.boot_stat(w, lambda i: comb[i].mean(1).mean())), new=new_ev, gain_e=gain_e)
    r = res[d]
    stats.append(dict(design=d, fleet_capture=r["fleet"], combined_capture=r["comb"], armo_alone=r["alone"],
                      armo_alone_ci_lo=r["alone_ci"][0], armo_alone_ci_hi=r["alone_ci"][1],
                      combined_ci_lo=r["comb_ci"][0], combined_ci_hi=r["comb_ci"][1],
                      gain_pp=r["gain"] * 100, gain_ci_station_lo=r["st"][0] * 100, gain_ci_station_hi=r["st"][1] * 100,
                      gain_phase_min=r["ph"][0] * 100, gain_phase_max=r["ph"][1] * 100,
                      gain_ci_station_and_phase_lo=r["both"][0] * 100, gain_ci_station_and_phase_hi=r["both"][1] * 100,
                      newly_looked_events_mean=float(new_ev.mean()), newly_looked_min=int(new_ev.min()), newly_looked_max=int(new_ev.max()),
                      n_events=len(coh), n_stations=coh.wban.nunique()))
S = ae.write_stats("capture_gain_paired_stats", stats)

# gain by window duration (design D)
BINS, LAB = [0, 24, 48, 72, 120, np.inf], ["< 1 d", "1–2 d", "2–3 d", "3–5 d", "≥ 5 d"]
dur = pd.cut(coh.window_h, BINS, right=False, labels=LAB).astype(str).to_numpy()
D = res["D"]
drows = []
for lab in LAB:
    m = dur == lab
    fl = f[(f.design == "D")].pivot_table(index="key", columns="phase", values="combined_look", aggfunc="first").reindex(coh.key).to_numpy(float)
    fleet_d = coh.fleet.to_numpy(float)
    drows.append(dict(bin=lab, n=int(m.sum()), fleet=fleet_d[m].mean(), combined=fl[m].mean(1).mean()))
DR = pd.DataFrame(drows)
DR.to_csv(os.path.join(ae.GEN, "capture_gain_by_duration_D.csv"), index=False)

# ---------------------------------------------------------------- figure
fig = plt.figure(figsize=(7.6, 5.4))
gs = fig.add_gridspec(2, 2, width_ratios=[1, 1.15], hspace=0.62, wspace=0.42)
a = fig.add_subplot(gs[:, 0]); b = fig.add_subplot(gs[0, 1]); c = fig.add_subplot(gs[1, 1])
vals = [D["fleet"], D["comb"], D["alone"]]
cis = [ae.ci95(ae.boot_stat(coh.wban, lambda i: coh.fleet.to_numpy(float)[i].mean())), D["comb_ci"], D["alone_ci"]]
cols = [fs.BLUE, fs.YELLOW, "#f3d38a"]
labs = ["Real fleet\n(S1C/D + NISAR)\nOBSERVED", "Fleet + ARMO D\nSIMULATED\nopportunity", "ARMO D alone\nSIMULATED\nopportunity"]
x = np.array([0, 1, 2.15])
a.bar(x, np.array(vals) * 100, width=0.62, color=cols, edgecolor=[fs.BLUE, "#b07a00", "#b07a00"], lw=1)
a.errorbar(x, np.array(vals) * 100, yerr=[[(v - lo) * 100 for v, (lo, hi) in zip(vals, cis)], [(hi - v) * 100 for v, (lo, hi) in zip(vals, cis)]],
           fmt="none", ecolor=fs.INK, capsize=3, lw=1)
for xi, v in zip(x, vals):
    a.text(xi, 4, f"{v * 100:.1f} %", ha="center", fontsize=8, fontweight="bold", color=fs.INK)
a.annotate("", xy=(1, D["comb"] * 100 + 6), xytext=(0, D["fleet"] * 100 + 6),
           arrowprops=dict(arrowstyle="->", color=fs.INK, lw=1.2, connectionstyle="arc3,rad=-0.3"))
a.text(0.5, max(vals) * 100 + 9, f"paired +{D['gain'] * 100:.1f} pp\n95 % CI {D['st'][0] * 100:.1f}–{D['st'][1] * 100:.1f} (stations)\n"
       f"{D['both'][0] * 100:.1f}–{D['both'][1] * 100:.1f} (stations + phase)", ha="center", fontsize=6.8)
a.set_xticks(x); a.set_xticklabels(labs, fontsize=6.8); a.set_ylim(0, 122); a.set_yticks(range(0, 101, 20))
a.set_ylabel("Events with ≥ 1 look in the window (%)"); a.grid(axis="x", visible=False)
a.set_title("Look opportunity, same 979 events", loc="left", fontsize=8.8)
fs.panel_label(a, "a")

names = {"A": "A 1 sat", "B": "B 1 sat roll", "C": "C 1 sat wide", "D": "D 2 sats", "E": "E 2 sats roll"}
y = np.arange(5)[::-1]
for yi, d in zip(y, "ABCDE"):
    r = res[d]
    col = fs.YELLOW if d == "D" else "#e8cf98"
    c_ = r["gain"] * 100
    b.plot([r["both"][0] * 100, r["both"][1] * 100], [yi, yi], color=fs.MUTED, lw=5, solid_capstyle="butt", alpha=0.6)
    b.plot([r["st"][0] * 100, r["st"][1] * 100], [yi, yi], color=fs.INK, lw=1.4)
    b.scatter(r["ph_all"] * 100, np.full(8, yi + 0.22), s=6, color=fs.INK2, zorder=3)
    b.scatter([c_], [yi], s=40, color=col, edgecolor=fs.INK, zorder=4)
    b.text(36, yi, f"+{c_:.1f}", va="center", fontsize=7)
b.set_yticks(y); b.set_yticklabels([names[d] for d in "ABCDE"], fontsize=7.2); b.set_xlim(10, 40)
b.set_xlabel("Paired gain over the real fleet (pp)"); b.grid(axis="y", visible=False)
b.set_title("All designs: CI (line), + phase (grey), 8 phases (dots)", loc="left", fontsize=7.8)
fs.panel_label(b, "b")

xx = np.arange(len(LAB))
c.bar(xx - 0.18, DR.fleet * 100, 0.34, color=fs.BLUE, label="Real fleet")
c.bar(xx + 0.18, DR.combined * 100, 0.34, color=fs.YELLOW, label="+ ARMO D (simulated)")
for xi, r in zip(xx, DR.itertuples()):
    c.text(xi - 0.18, 3, f"{r.n}", ha="center", fontsize=5.8, color="white", rotation=90)
c.set_xticks(xx); c.set_xticklabels(LAB, fontsize=7); c.set_ylim(0, 128); c.set_yticks(range(0, 101, 25))
c.set_ylabel("Events with a look (%)"); c.set_xlabel("Wetting-window duration (numbers in bars = events)")
c.legend(fontsize=6.6, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.02)); c.grid(axis="x", visible=False)
c.set_title("Look opportunity by window duration (design D)", loc="left", fontsize=8.2)
fs.panel_label(c, "c")
fig.text(0.01, -0.05,
         f"979 USCRN wetting events, 107 stations, storms 17 Jun–31 Oct 2026. Fleet = actual Sentinel-1C/1D + NISAR acquisition times (OBSERVED). "
         f"ARMO = orbit-model passes (SIMULATED), 8 initial phases,\naccess corridor 25–45° off-nadir assumed fully imaged (see swath sensitivity). "
         f"A look is an opportunity, not a detection. ARMO D newly looks at {D['new'].mean():.0f} events on average "
         f"(range {D['new'].min()}–{D['new'].max()} over phases).\nCIs: station-cluster bootstrap of the paired gain (2,000 draws); 'stations + phase' "
         f"also draws one random phase per replicate.", fontsize=6.1, color=fs.INK2)
ae.save(fig, "figS12_capture_gain_paired_ci")
print(S.round(3).T.to_string())
print(DR.round(3).to_string(index=False))
