"""Report Figures 3, 4 and 6: example station, capture vs revisit, and marginal value of ARMO."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "code"))
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from common import PROC, FIG, load_uscrn, season_series
import figstyle as fs

fs.apply()
ev = pd.read_csv(os.path.join(PROC, "events_real.csv"), parse_dates=["t_start", "t_peak", "t_ws", "t_we"])
s1 = pd.read_csv(os.path.join(PROC, "acq_s1.csv"), parse_dates=["time"])
ni = pd.read_csv(os.path.join(PROC, "acq_nisar.csv"), parse_dates=["time"])

# ---------------- Figure 3: Stillwater 2 W, NISAR era ----------------
W = 53926
t0, t1 = pd.Timestamp("2026-06-17", tz="UTC"), pd.Timestamp("2026-10-31", tz="UTC")
df = load_uscrn()
s = season_series(df, W, 2026)
s = s[(s.index >= t0) & (s.index < t1)]
e = ev[(ev.wban == W) & (ev.t_start >= t0) & (ev.t_start < t1)]
a1 = s1[(s1.wban == W) & (s1.time >= t0) & (s1.time < t1)].time.drop_duplicates()
a2 = ni[(ni.wban == W) & (ni.time >= t0) & (ni.time < t1)].time
a2 = a2[a2.diff().abs().fillna(pd.Timedelta(days=1)) > pd.Timedelta(hours=1)]

fig, (axp, ax) = plt.subplots(2, 1, figsize=(7.2, 3.9), sharex=True, gridspec_kw=dict(height_ratios=[1, 3], hspace=0.08))
daily = s.precip.resample("D").sum()
axp.bar(daily.index + pd.Timedelta(hours=12), daily.values, width=0.8, color=fs.INK2)
axp.set_ylabel("Rain\n(mm/day)")
axp.set_title("Stillwater 2 W, Oklahoma: hourly 5 cm soil moisture (ground truth) vs actual radar looks, "
              "17 Jun–31 Oct 2026", loc="left", fontsize=9)
for r in e.itertuples():
    hit = r._asdict().get("_25", None)
    ax.axvspan(r.t_ws, min(r.t_we, t1), color=fs.YELLOW, alpha=0.28, lw=0)
ax.plot(s.index, s.sm5, color=fs.BLUE, lw=1.4, label="USCRN 5 cm soil moisture")
yl = (s.sm5.min() - 0.06, s.sm5.max() + 0.02)
ax.set_ylim(*yl)
ax.vlines(a1, yl[0], yl[0] + 0.025, color=fs.ORANGE, lw=1.6, label="Sentinel-1C/1D acquisition")
ax.vlines(a2, yl[0] + 0.03, yl[0] + 0.055, color=fs.VIOLET, lw=1.6, label="NISAR L-band acquisition")
ax.fill_between([], [], color=fs.YELLOW, alpha=0.28, label="Wetting-event window (≥ 50 % of rise)")
both = pd.concat([a1, a2]).sort_values()
obs_h = np.ceil(((both - pd.Timestamp("1970-01-01", tz="UTC")) / pd.Timedelta(hours=1)).to_numpy())
n_cap = sum(np.any((obs_h >= ((r.t_ws - pd.Timestamp("1970-01-01", tz="UTC")) / pd.Timedelta(hours=1))) &
                   (obs_h < ((r.t_we - pd.Timestamp("1970-01-01", tz="UTC")) / pd.Timedelta(hours=1)))) for r in e.itertuples())
ax.text(0.99, 0.97, f"{len(e)} wetting events; {n_cap} seen by S1 or NISAR inside the window",
        transform=ax.transAxes, ha="right", va="top", fontsize=8, color=fs.INK)
ax.set_ylabel("Soil moisture (m³/m³)")
ax.legend(loc="upper center", ncol=4, fontsize=7, bbox_to_anchor=(0.5, -0.12), handlelength=1.5, columnspacing=1.2)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
ax.set_xlim(t0, t1)
fig.savefig(os.path.join(FIG, "fig3_stillwater_example.png"))
plt.close(fig)
print("Stillwater events", len(e), "captured", n_cap, "S1 looks", len(a1), "NISAR looks", len(a2))

# ---------------- Figure 4: event durations + capture vs revisit ----------------
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

for wn, col, lab in [("half-amplitude", fs.BLUE, "Regular revisit (half-amplitude)"), ("abs0.03", fs.AQUA, "Regular revisit (≥ 0.03 m³/m³)")]:
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
fig.savefig(os.path.join(FIG, "fig4_capture_vs_revisit.png"))
plt.close(fig)

# ---------------- Figure 6: marginal value of ARMO ----------------
mv = pd.read_csv(os.path.join(PROC, "marginal_value.csv"))
order = ["Current fleet (S1C/D + NISAR)", "Current fleet + ARMO 4-day", "Current fleet + ARMO 3-day",
         "Current fleet + ARMO 2-day", "Current fleet + ARMO 1-day", "Future fleet (+ROSE-L 6-day)",
         "Future fleet + ARMO 3-day", "Future fleet + ARMO 2-day"]
mv = mv.set_index("scenario").loc[order].reset_index()
labels = ["Current\nfleet", "+ ARMO\n4-day", "+ ARMO\n3-day", "+ ARMO\n2-day", "+ ARMO\n1-day",
          "Future\nfleet†", "+ ARMO\n3-day", "+ ARMO\n2-day"]
x = np.array([0, 1.25, 2.5, 3.75, 5.0, 7.0, 8.25, 9.5])
cols = [fs.INK2] + [fs.BLUE] * 4 + [fs.INK2] + [fs.BLUE] * 2
fig, ax = plt.subplots(figsize=(7.2, 3.0))
ax.bar(x, mv.capture * 100, width=0.62, color=cols)
ax.errorbar(x, mv.capture * 100, yerr=[(mv.capture - mv.ci_lo) * 100, (mv.ci_hi - mv.capture) * 100],
            fmt="none", ecolor=fs.INK, elinewidth=1, capsize=3)
for xi, v in zip(x, mv.capture * 100):
    ax.text(xi, 3, f"{v:.0f}%", ha="center", va="bottom", fontsize=8, color="white", fontweight="bold")
ax.axhline(80, color=fs.MUTED, lw=0.8, ls=":")
ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=7.4)
ax.set_ylabel("Events captured (%)"); ax.set_ylim(0, 100)
ax.set_title("Marginal value of a dedicated revisit mission (ARMO) on top of the real 2026 fleet "
             "(979 events, 17 Jun–31 Oct 2026)", loc="left", fontsize=9)
ax.grid(axis="x", visible=False)
fig.text(0.01, -0.07, "Current fleet = actual Sentinel-1C/1D + NISAR looks. †Future fleet adds ROSE-L at ESA's documented two-satellite "
         "revisit over global land (6 days; 3 days is Europe only); launch ≥ 2030 (WMO OSCAR).\nARMO = regular dawn/dusk revisit added at "
         "random phase. Error bars = 95 % station-bootstrap CI. Dotted line = 80 % capture target.", fontsize=6.8, color=fs.INK2)
fig.savefig(os.path.join(FIG, "fig6_marginal_value.png"))
print(mv.round(3))
