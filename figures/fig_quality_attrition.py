"""P0-3  From a real look to a detected wetting change: where events are lost, sensor by sensor (OBSERVED).

(a) Matched NISAR-era cohort (979 events, 107 stations): for each sensor, the number of the SAME 979 events that reach each
    stage. Stages: real look inside the window -> valid same-geometry pair (ground-matched, no rain in the 3 h before
    either look, <= 13 d apart; SMAP same overpass <= 3.5 d) -> valid retrieval in the pair -> change > 1 sigma of the
    sensor's own no-change noise. SMAP has no acquisition list: its "look" is a retrieval inside the window, either of
    any quality or recommended quality (retrieval_qual_flag 0) - two policies with different stations and denominators.
    The chain is not perfectly nested: a few events have a valid pair but no catalogue look (time rounding at the window
    edge / catalogue vs granule lists); these are counted and reported, not hidden.
(b) Detection when sampled with the published, full-period denominators (S1 and SMAP: 2025-2026 seasons; NISAR: 2026),
    station-cluster bootstrap 95 % CI. Different sensors = different event cohorts: not a same-cohort comparison.
(c) False-alarm rate on unchanged pairs (|dSM| < 0.01 m3/m3), its own denominator; NOT part of the wetting-event chain.
Outputs: figures/figS08_quality_attrition.png, figures/generated/quality_attrition_stats.csv
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import armo_evidence as ae
import figstyle as fs
from common import rd, PROC, to_hours, captured

fs.apply()
c = ae.era_cohort()
c["k"] = c.wban.astype(str) + "|" + c.t_ws.dt.strftime("%Y-%m-%dT%H")
N = len(c)


def keyed(f):
    d = rd(f)
    d["t_ws"] = pd.to_datetime(d.t_ws, utc=True, format="ISO8601")
    d["k"] = d.wban.astype(str) + "|" + d.t_ws.dt.strftime("%Y-%m-%dT%H")
    return d


s1s = rd("s1_summary.csv", index_col=0).iloc[:, 0]
nis = rd("nisar_summary.csv", index_col=0).iloc[:, 0]
sms = rd("smap_summary.csv", index_col=0)
NOISE = {"S1 VV": s1s["noise_db_nochange"], "NISAR HH": nis["noise_hh_db"], "NISAR SME2": nis["noise_sat_nochange"],
         "SMAP all quality": sms.loc["noise_nochange", "all"], "SMAP recommended": sms.loc["noise_nochange", "recommended"]}

# SMAP looks per event (recomputed from gee_smap.csv with the 08_sensor_tests.py rule; any quality and recommended)
g = rd("gee_smap.csv")
parts = []
for ov, h in (("am", 6), ("pm", 18)):
    d = g[["wban", "date", "longitude", f"soil_moisture_{ov}", f"retrieval_qual_flag_{ov}"]].copy()
    d.columns = ["wban", "date", "lon", "sm", "flag"]
    d["time"] = (pd.to_datetime(d.date, utc=True) + pd.to_timedelta(h - d.lon / 15, unit="h")).dt.round("min")
    parts.append(d)
sm = pd.concat(parts).dropna(subset=["sm"])
smap_look = {}
for pol, mask in (("all", sm.sm.notna()), ("recommended", sm.flag == 0)):
    obs = {w: np.sort(to_hours(x.time)) for w, x in sm[mask].groupby("wban")}
    f = np.zeros(N, bool)
    for w, idx in c.groupby("wban").groups.items():
        i = c.index.get_indexer(idx)
        o = obs.get(w, np.array([]))
        f[i] = captured(o, to_hours(c.t_ws.iloc[i]), to_hours(c.t_we.iloc[i])) if o.size else False
    smap_look[pol] = f

S = {"S1 VV": (keyed("s1_sampled_events.csv"), "dvv", c.s1.to_numpy()),
     "NISAR HH": (keyed("nisar_sampled_events.csv"), "dhh", c.ni.to_numpy()),
     "NISAR SME2": (keyed("nisar_sampled_events.csv"), "dsat", c.ni.to_numpy()),
     "SMAP all quality": (keyed("smap_sampled_events_all.csv"), "dsat", smap_look["all"]),
     "SMAP recommended": (keyed("smap_sampled_events.csv"), "dsat", smap_look["recommended"])}
stats, chain, EVHIT = [], {}, {}
for name, (det, col, look) in S.items():
    d = det[det.k.isin(c.k)].set_index("k").reindex(c.k)
    pair = d.amp.notna().to_numpy()                    # a valid same-geometry pair exists for this event
    valid = d[col].notna().to_numpy()                  # retrieval present in both looks of the pair
    hit = (d[col] > NOISE[name]).fillna(False).to_numpy()
    st = [("Real look\nin window", look), ("Valid same-\ngeometry pair", pair), ("Valid retrieval\nin pair", valid),
          ("Change > 1σ of\nno-change noise", hit)]
    EVHIT[name] = hit
    chain[name] = st
    for lab, m in st:
        lo, hi = ae.ci95(ae.boot_stat(c.wban, lambda i, m=m: m[i].mean(), n=1000))
        stats.append(dict(panel="a", sensor=name, stage=lab.replace("\n", " "), n=int(m.sum()), denominator=N, value=m.mean(), ci_lo=lo, ci_hi=hi,
                          cohort="979 NISAR-era events, 107 stations"))
    stats.append(dict(panel="a", sensor=name, stage="valid pair WITHOUT a catalogue look (non-nested)",
                      n=int((pair & ~look).sum()), denominator=int(pair.sum()), value=np.nan))
radar = EVHIT["S1 VV"] | EVHIT["NISAR HH"] | EVHIT["NISAR SME2"]
lo, hi = ae.ci95(ae.boot_stat(c.wban, lambda i: radar[i].mean()))
stats.append(dict(panel="a", sensor="Field-scale radar fleet (S1 VV or NISAR HH or SME2)", stage="detected change (union)",
                  n=int(radar.sum()), denominator=N, value=radar.mean(), ci_lo=lo, ci_hi=hi, cohort="979 NISAR-era events, 107 stations"))

# (b) detection when sampled, published denominators
B = {"S1 VV": ("s1_sampled_events.csv", "dvv", "2025–2026"), "NISAR HH": ("nisar_sampled_events.csv", "dhh", "2026"),
     "NISAR SME2": ("nisar_sampled_events.csv", "dsat", "2026"), "SMAP all quality": ("smap_sampled_events_all.csv", "dsat", "2025–2026"),
     "SMAP recommended": ("smap_sampled_events.csv", "dsat", "2025–2026")}
bres = {}
for name, (f, col, per) in B.items():
    d = rd(f).dropna(subset=[col]).reset_index(drop=True)
    hit = (d[col] > NOISE[name]).to_numpy()
    lo, hi = ae.ci95(ae.boot_stat(d.wban, lambda i: hit[i].mean()))
    bres[name] = (hit.mean(), lo, hi, len(d), d.wban.nunique(), per)
    stats.append(dict(panel="b", sensor=name, stage="detected | sampled (published denominator)", n=int(hit.sum()), denominator=len(d),
                      value=hit.mean(), ci_lo=lo, ci_hi=hi, cohort=f"{per}; {d.wban.nunique()} stations"))

# (c) false alarms on unchanged pairs
C = {"S1 VV": ("s1_pairs.csv", "dvv"), "NISAR HH": ("nisar_pairs.csv", "dhh"), "NISAR SME2": ("nisar_pairs.csv", "dsat"),
     "SMAP all quality": ("smap_pairs_all.csv", "dsat"), "SMAP recommended": ("smap_pairs.csv", "dsat")}
cres = {}
for name, (f, col) in C.items():
    p = rd(f)
    p = p[p.dsm.abs() < 0.01].dropna(subset=[col]).reset_index(drop=True)
    fa = (p[col] > NOISE[name]).to_numpy()
    lo, hi = ae.ci95(ae.boot_stat(p.wban, lambda i: fa[i].mean(), n=1000))
    cres[name] = (fa.mean(), lo, hi, len(p))
    stats.append(dict(panel="c", sensor=name, stage="false alarm | unchanged pair", n=int(fa.sum()), denominator=len(p),
                      value=fa.mean(), ci_lo=lo, ci_hi=hi, cohort="all unchanged same-geometry pairs"))
ae.write_stats("quality_attrition_stats", stats)

# ---------------------------------------------------------------- figure
COL = {"S1 VV": fs.ORANGE, "NISAR HH": fs.VIOLET, "NISAR SME2": "#a99be8", "SMAP all quality": fs.MAGENTA, "SMAP recommended": "#b0476f"}
fig = plt.figure(figsize=(7.6, 6.4))
gs = fig.add_gridspec(2, 2, height_ratios=[1.25, 1], hspace=0.42, wspace=0.5)
a = fig.add_subplot(gs[0, :]); b = fig.add_subplot(gs[1, 0]); cc = fig.add_subplot(gs[1, 1])
stages = [s for s, _ in next(iter(chain.values()))]
x = np.arange(len(stages)); w = 0.16
for j, (name, st) in enumerate(chain.items()):
    v = np.array([m.sum() for _, m in st])
    xx = x + (j - 2) * w
    a.bar(xx, v / N * 100, w * 0.92, color=COL[name], label=name)
    for xi, k in zip(xx, v):
        a.text(xi, k / N * 100 + 1.2, str(k), ha="center", fontsize=5.6, rotation=90)
a.set_xticks(x); a.set_xticklabels(stages, fontsize=7.4); a.set_ylim(0, 100)
a.set_ylabel("% of the 979 matched events")
a.grid(axis="x", visible=False)
a.legend(ncol=5, fontsize=6.8, loc="upper right", handlelength=1, columnspacing=0.9)
a.set_title(f"Same 979 events: a radar-detected change in only {radar.sum()} ({radar.mean() * 100:.1f} %, any field-scale radar); numbers = events",
            loc="left", fontsize=8.4)
fs.panel_label(a, "a")

names = list(B)
y = np.arange(len(names))[::-1]
for yi, nm in zip(y, names):
    p, lo, hi, n, ns, per = bres[nm]
    b.barh(yi, p * 100, color=COL[nm], height=0.6)
    b.errorbar(p * 100, yi, xerr=[[(p - lo) * 100], [(hi - p) * 100]], fmt="none", ecolor=fs.INK, capsize=2, lw=0.9)
    b.text(hi * 100 + 2, yi, f"{p * 100:.0f} %  (n={n}, {per})", va="center", fontsize=6.2)
b.axvline(70, color=fs.BLUE, ls=":", lw=1); None
b.set_yticks(y); b.set_yticklabels(names, fontsize=7); b.set_xlim(0, 130); b.set_xticks([0, 25, 50, 75, 100])
b.set_xlabel("Detected when sampled (%)\n(dotted: ARMO 70 % target, UNVALIDATED)", fontsize=8); b.grid(axis="y", visible=False)
b.set_title("Detection, published denominators", loc="left", fontsize=8.6)
fs.panel_label(b, "b")
for yi, nm in zip(y, names):
    p, lo, hi, n = cres[nm]
    cc.barh(yi, p * 100, color=COL[nm], height=0.6, alpha=0.55)
    cc.errorbar(p * 100, yi, xerr=[[(p - lo) * 100], [(hi - p) * 100]], fmt="none", ecolor=fs.INK, capsize=2, lw=0.9)
    cc.text(hi * 100 + 0.6, yi, f"{p * 100:.1f} %  (n={n:,})", va="center", fontsize=6.2)
cc.axvline(10, color=fs.BLUE, ls=":", lw=1)
cc.set_yticks(y); cc.set_yticklabels([]); cc.set_xlim(0, 22)
cc.set_xlabel("False alarms on unchanged pairs (%)\n(dotted: 10 % target)", fontsize=8); cc.grid(axis="y", visible=False)
cc.set_title("False alarms, own denominator", loc="left", fontsize=8.6)
fs.panel_label(cc, "c")
nn = {k: [r for r in stats if r["sensor"] == k and "non-nested" in r["stage"]][0]["n"] for k in chain}
fig.text(0.01, -0.06,
         "OBSERVED. (a) 979 USCRN wetting events, 107 stations, storms 17 Jun–31 Oct 2026; S1/NISAR looks = real acquisitions; SMAP look = "
         "retrieval in the window (any quality vs recommended,\nretrieval_qual_flag 0). Pair = same orbit/track/overpass, ground-matched, no rain "
         "in the 3 h before. Non-nested events (valid pair, no catalogue look): "
         + ", ".join(f"{k} {v}" for k, v in nn.items() if v) + ".\n(b, c) Different cohorts and periods per sensor; "
         "95 % CIs = station-cluster bootstrap. False alarm = probability of a > 1σ rise on an unchanged pair (not a false-alarm ratio).",
         fontsize=6.1, color=fs.INK2)
ae.save(fig, "figS08_quality_attrition")
print(pd.DataFrame(stats).round(4).to_string(index=False))
