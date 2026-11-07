"""Cloud penalty: clear-sky optical opportunities vs all-weather sampling at the SAME cadence (MODEL-BASED proxy).
Source: data/processed/optical_events.csv (code/09_optical_clouds.py): for every wetting event, the phase-averaged chance
that a regular morning optical sampler at R days sees a CLEAR pixel inside the window (MODIS cloud mask at the station),
and the same sampler ignoring clouds (all-weather). Paired per event -> paired differences with station-cluster CIs.
Caveat: MODIS cloud mask as a proxy for clear-sky optical acquisition; not an evaluation of any specific optical system.
Outputs: figures/figS06_optical_cloud_penalty.png, figures/generated/optical_cloud_penalty_stats.csv
"""
import numpy as np
import matplotlib.pyplot as plt
import armo_evidence as ae
import figstyle as fs
from common import rd

fs.apply()
o = rd("optical_events.csv")
RS = [1, 2, 3, 5, 8]
rows = []
for R in RS:
    op, sa = o[f"opt_R{R}"].to_numpy(), o[f"sar_R{R}"].to_numpy()
    ci_o = ae.ci95(ae.boot_stat(o.wban, lambda i: op[i].mean(), n=1000))
    ci_s = ae.ci95(ae.boot_stat(o.wban, lambda i: sa[i].mean(), n=1000))
    ci_d = ae.ci95(ae.boot_stat(o.wban, lambda i: (sa[i] - op[i]).mean(), n=1000))
    rows.append(dict(revisit_d=R, optical_clear=op.mean(), optical_lo=ci_o[0], optical_hi=ci_o[1], all_weather=sa.mean(),
                     all_weather_lo=ci_s[0], all_weather_hi=ci_s[1], penalty_pp=(sa - op).mean() * 100, penalty_lo=ci_d[0] * 100,
                     penalty_hi=ci_d[1] * 100, n_events=len(o), n_stations=o.wban.nunique()))
S = ae.write_stats("optical_cloud_penalty_stats", rows)
fig, ax = plt.subplots(figsize=(5.2, 3.0))
for col, lo, hi, c, lab in [("all_weather", "all_weather_lo", "all_weather_hi", fs.BLUE, "All-weather sampler (same cadence)"),
                            ("optical_clear", "optical_lo", "optical_hi", fs.YELLOW, "Clear-sky optical (MODIS cloud proxy)")]:
    ax.fill_between(S.revisit_d, S[lo] * 100, S[hi] * 100, color=c, alpha=0.2, lw=0)
    ax.plot(S.revisit_d, S[col] * 100, marker="o", color=c, label=lab)
for r in S.itertuples():
    ax.text(r.revisit_d + 0.12, (r.all_weather + r.optical_clear) * 50, f"−{r.penalty_pp:.0f} pp", fontsize=6.6, color=fs.INK2)
ax.set_xticks(RS); ax.set_xlabel("Regular revisit (days)"); ax.set_ylabel("Events with a usable look (%)"); ax.set_ylim(0, 100)
ax.legend(fontsize=7, loc="upper right")
loss = 1 - S.optical_clear / S.all_weather
ax.set_title(f"Clouds remove {loss.min() * 100:.0f}–{loss.max() * 100:.0f} % of same-cadence opportunities", loc="left", fontsize=8.6)
fig.text(0.01, -0.1, f"MODEL-BASED proxy on OBSERVED windows: {len(o):,} USCRN events, {o.wban.nunique()} stations, 2025–2026; morning overpass, phase-averaged. "
         "Bands = 95 % station-bootstrap CI;\nlabels = paired difference. Not an evaluation of any specific optical satellite.", fontsize=6.1, color=fs.INK2)
ae.save(fig, "figS06_optical_cloud_penalty")
print(S.round(3).to_string(index=False))
