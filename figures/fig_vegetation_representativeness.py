"""How representative are the stations of farmland, and does detection depend on cover?  (OBSERVED)
Sources: station_vegetation.csv (ESA WorldCover at the probe, USDA CDL crop flag; 121 classified stations), events.csv
(3,340 events at 120 event stations), s1/nisar/smap sampled events + the published 1-sigma noise.
(a) composition: classified stations (121) vs event stations (120) vs events, by WorldCover class at the probe.
(b) detection when sampled by cover class, station-cluster bootstrap 95 % CI; classes with < 30 sampled events or < 5
    stations are marked "n too small" and must not be interpreted. No national crop-performance inference is possible:
    only 9 classified stations are WorldCover cropland (7 by USDA CDL at the probe).
Outputs: figures/figS02_vegetation_representativeness.png, figures/generated/vegetation_representativeness_stats.csv
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import armo_evidence as ae
import figstyle as fs
from common import rd

fs.apply()
sv = rd("station_vegetation.csv")
ev = rd("events.csv")
COV = ["Cropland", "Grassland", "Shrubland", "Tree cover", "Other"]
comp = pd.DataFrame({"Classified stations (121)": sv.cover.value_counts(normalize=True),
                     "Event stations (120)": sv[sv.wban.isin(ev.wban)].cover.value_counts(normalize=True),
                     "Events (3,340)": ev.merge(sv[["wban", "cover"]], on="wban").cover.value_counts(normalize=True)}).reindex(COV).fillna(0)
counts = {"stations": sv.cover.value_counts().reindex(COV).fillna(0).astype(int),
          "events": ev.merge(sv[["wban", "cover"]], on="wban").cover.value_counts().reindex(COV).fillna(0).astype(int)}
s1s = rd("s1_summary.csv", index_col=0).iloc[:, 0]
nis = rd("nisar_summary.csv", index_col=0).iloc[:, 0]
sms = rd("smap_summary.csv", index_col=0)
SENS = [("Sentinel-1 VV", "s1_sampled_events.csv", "dvv", s1s["noise_db_nochange"], fs.ORANGE),
        ("NISAR HH", "nisar_sampled_events.csv", "dhh", nis["noise_hh_db"], fs.VIOLET),
        ("SMAP all quality", "smap_sampled_events_all.csv", "dsat", sms.loc["noise_nochange", "all"], fs.MAGENTA)]
rows = []
for cov in COV:
    rows.append(dict(kind="composition", cover=cov, stations=int(counts["stations"][cov]), events=int(counts["events"][cov]),
                     share_classified=comp.loc[cov].iloc[0], share_event_stations=comp.loc[cov].iloc[1], share_events=comp.loc[cov].iloc[2]))
det = {}
for name, f, col, sig, colr in SENS:
    d = rd(f).dropna(subset=[col]).merge(sv[["wban", "cover"]], on="wban")
    for cov in COV:
        g = d[d.cover == cov].reset_index(drop=True)
        if len(g) == 0:
            continue
        hit = (g[col] > sig).to_numpy()
        lo, hi = ae.ci95(ae.boot_stat(g.wban, lambda i: hit[i].mean(), n=1000))
        small = len(g) < 30 or g.wban.nunique() < 5
        det[(name, cov)] = (hit.mean(), lo, hi, len(g), g.wban.nunique(), small)
        rows.append(dict(kind="detection", sensor=name, cover=cov, n=len(g), stations=g.wban.nunique(), p_detect=hit.mean(),
                         ci_lo=lo, ci_hi=hi, too_small=small))
S = ae.write_stats("vegetation_representativeness_stats", rows)

fig, (a, b) = plt.subplots(1, 2, figsize=(7.6, 3.2), gridspec_kw=dict(width_ratios=[1, 1.5], wspace=0.35))
cc = {"Cropland": fs.YELLOW, "Grassland": fs.AQUA, "Shrubland": "#b9a26b", "Tree cover": fs.GREEN, "Other": fs.MUTED}
left = np.zeros(3)
for cov in COV:
    v = comp.loc[cov].to_numpy() * 100
    a.barh(np.arange(3)[::-1], v, left=left, color=cc[cov], label=cov, height=0.6, edgecolor="white", lw=0.8)
    for k, (l_, w_) in enumerate(zip(left, v)):
        if w_ >= 6:
            a.text(l_ + w_ / 2, 2 - k, f"{w_:.0f}", ha="center", va="center", fontsize=6.4)
    left += v
a.set_yticks(np.arange(3)[::-1]); a.set_yticklabels(comp.columns, fontsize=7); a.set_xlim(0, 100)
a.set_xlabel("Share (%), WorldCover class at the probe"); a.grid(axis="y", visible=False)
a.legend(fontsize=6, ncol=5, loc="upper center", bbox_to_anchor=(0.4, -0.2), handlelength=1, columnspacing=0.6)
a.set_title(f"Only {counts['stations']['Cropland']} cropland stations", loc="left", fontsize=8.4)
fs.panel_label(a, "a")
x = np.arange(len(COV)); w = 0.26
for j, (name, *_ , colr) in enumerate(SENS):
    for xi, cov in zip(x, COV):
        if (name, cov) not in det:
            continue
        p, lo, hi, n, ns, small = det[(name, cov)]
        xx = xi + (j - 1) * w
        b.bar(xx, p * 100, w * 0.9, color=colr, alpha=0.3 if small else 1, hatch="///" if small else None,
              edgecolor=colr, label=name if cov == "Grassland" else None)
        b.errorbar(xx, p * 100, yerr=[[(p - lo) * 100], [(hi - p) * 100]], fmt="none", ecolor=fs.INK, capsize=1.5, lw=0.8)
        b.text(xx, 2, f"{n}", ha="center", fontsize=5, rotation=90, color=fs.INK)
b.set_xticks(x); b.set_xticklabels(COV, fontsize=7); b.set_ylim(0, 118); b.set_yticks(range(0, 101, 20))
b.set_ylabel("Sampled events detected (%)"); b.grid(axis="x", visible=False)
b.legend(fontsize=6.2, loc="upper center", ncol=3, handlelength=1, columnspacing=0.8)
b.set_title("Detection by cover (hatched = n too small)", loc="left", fontsize=8.4)
fs.panel_label(b, "b")
fig.text(0.01, -0.24, "OBSERVED. WorldCover class at the USCRN probe (121 classified stations; 120 with wetting events; station 4125 has none). "
         "Numbers in bars = sampled events. 95 % CIs: station-cluster bootstrap.\nHatched/pale: < 30 sampled events or < 5 stations — "
         "not interpretable. Too few cropland sites for any national crop-performance inference.", fontsize=6, color=fs.INK2)
ae.save(fig, "figS02_vegetation_representativeness")
print(S.round(3).to_string(index=False))
