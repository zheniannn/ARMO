"""5 cm vs 10 cm: the same storms seen at two probe depths (OBSERVED; ideal revisit sampling SIMULATED).
Source: data/processed/depth_events.csv (code/06_mission_design.py depth_test). Storms are paired by (station, storm start):
only storms that produced an event at BOTH depths enter the paired comparison, so the depth contrast is not confounded by
which storms qualify. This is about how long wetting lasts at each probe depth; it says nothing about the electromagnetic
sensing depth of any radar band.
Outputs: figures/figS04_depth_comparison.png, figures/generated/depth_comparison_stats.csv
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import armo_evidence as ae
import figstyle as fs
from common import rd

fs.apply()
d = rd("depth_events.csv")
e5, e10 = d[d.depth == "sm5"], d[d.depth == "sm10"]
m = e5.merge(e10, on=["wban", "t_start"], suffixes=("_5", "_10"))
assert not m.duplicated(["wban", "t_start"]).any()
w5, w10 = m.window_h_5.to_numpy() / 24, m.window_h_10.to_numpy() / 24
diff = w10 - w5
dmed = ae.boot_stat(m.wban, lambda i: np.median(diff[i]))
caps = {}
for R in (1, 2, 3, 6):
    a, b = m[f"p_R{R}_5"].to_numpy(), m[f"p_R{R}_10"].to_numpy()
    caps[R] = (a.mean(), b.mean(), (b - a).mean(), ae.ci95(ae.boot_stat(m.wban, lambda i: (b[i] - a[i]).mean())))
rows = [dict(quantity="events at 5 cm", value=len(e5)), dict(quantity="events at 10 cm", value=len(e10)),
        dict(quantity="paired storms (both depths)", value=len(m)), dict(quantity="stations in paired set", value=m.wban.nunique()),
        dict(quantity="median window 5 cm, all events (d)", value=e5.window_h.median() / 24),
        dict(quantity="median window 10 cm, all events (d)", value=e10.window_h.median() / 24),
        dict(quantity="paired median of (10 cm - 5 cm) window (d)", value=float(np.median(diff)), ci_lo=ae.ci95(dmed)[0], ci_hi=ae.ci95(dmed)[1]),
        dict(quantity="paired: share of storms lasting longer at 10 cm", value=float((diff > 0).mean()))]
for R, (a, b, g, ci) in caps.items():
    rows.append(dict(quantity=f"paired capture at {R}-day revisit: 5 cm / 10 cm / diff pp", value=g * 100, ci_lo=ci[0] * 100, ci_hi=ci[1] * 100,
                     note=f"{a:.3f} / {b:.3f}"))
S = ae.write_stats("depth_comparison_stats", rows)

fig, (a, b) = plt.subplots(1, 2, figsize=(7.2, 2.9), gridspec_kw=dict(wspace=0.35))
lim = 10
a.scatter(np.clip(w5, 0, lim), np.clip(w10, 0, lim), s=4, alpha=0.25, color=fs.BLUE, lw=0, rasterized=True)
a.plot([0, lim], [0, lim], color=fs.INK2, lw=0.8, ls="--")
a.set_xlim(0, lim); a.set_ylim(0, lim)
a.set_xlabel("Window at 5 cm (days)"); a.set_ylabel("Window at 10 cm (days)")
a.set_title(f"{len(m):,} storms with an event at both depths", loc="left", fontsize=8.4)
a.text(0.4, 9.3, f"median difference {np.median(diff) * 24:+.0f} h\n(95 % CI {ae.ci95(dmed)[0] * 24:+.0f} to {ae.ci95(dmed)[1] * 24:+.0f} h)", fontsize=7)
fs.panel_label(a, "a")
x = np.arange(4)
b.bar(x - 0.18, [caps[R][0] * 100 for R in (1, 2, 3, 6)], 0.34, color=fs.BLUE, label="5 cm")
b.bar(x + 0.18, [caps[R][1] * 100 for R in (1, 2, 3, 6)], 0.34, color=fs.AQUA, label="10 cm")
for xi, R in zip(x, (1, 2, 3, 6)):
    b.text(xi, max(caps[R][0], caps[R][1]) * 100 + 3, f"{caps[R][2] * 100:+.1f} pp", ha="center", fontsize=6.6)
b.set_xticks(x); b.set_xticklabels(["1 d", "2 d", "3 d", "6 d"]); b.set_ylim(0, 105)
b.set_xlabel("Regular revisit"); b.set_ylabel("Same storms captured (%)"); b.legend(fontsize=7)
b.grid(axis="x", visible=False)
b.set_title("Deeper probe barely relaxes revisit", loc="left", fontsize=8.4)
fs.panel_label(b, "b")
fig.text(0.01, -0.12, "OBSERVED windows (USCRN 5 cm and 10 cm probes, same event rule); capture = ideal regular revisit (SIMULATED sampling). "
         "Paired by station and storm start; CIs = station-cluster bootstrap.\nAbout probe-depth wetting duration only, not radar penetration depth.",
         fontsize=6.2, color=fs.INK2)
ae.save(fig, "figS04_depth_comparison")
print(S.round(4).to_string(index=False))
