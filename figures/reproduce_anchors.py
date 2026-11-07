"""Independently recompute 36 headline values from data/processed/ and flag disagreements.

Output: figures/generated/anchor_check.csv (anchor, expected, recomputed, tolerance, status, source)
Run:    python figures/reproduce_anchors.py      (offline; a few seconds)
"""
import os
import numpy as np
import pandas as pd
import armo_evidence as ae
from common import rd

ev = ae.events_real()
c = ae.era_cohort()
rows = []


def check(name, expected, value, tol, source):
    ok = abs(value - expected) <= tol
    rows.append(dict(anchor=name, expected=expected, recomputed=round(float(value), 4), tolerance=tol,
                     status="MATCH" if ok else "DIFFERS", source=source))


check("events, all", 3340, len(ev), 0, "events_real.csv")
check("event stations", 120, ev.wban.nunique(), 0, "events_real.csv")
check("event key unique (duplicates)", 0, ev.key.duplicated().sum(), 0, "events_real.csv (wban, t_ws)")
check("NISAR-era cohort events", 979, len(c), 0, "events_real.csv, storm start 17 Jun-31 Oct 2026")
check("NISAR-era cohort stations", 107, c.wban.nunique(), 0, "events_real.csv")
check("S1 capture %", 30.2, c.s1.mean() * 100, 0.05, "cap_Sentinel-1 (NISAR era)")
check("NISAR capture %", 37.9, c.ni.mean() * 100, 0.05, "cap_NISAR (NISAR era)")
check("fleet capture %", 51.6, c.fleet.mean() * 100, 0.05, "S1 or NISAR look")
check("stored combined column agrees with S1|NISAR (mismatches)", 0,
      int(((c["cap_Sentinel-1 + NISAR (NISAR era)"] > 0) != c.fleet).sum()), 0, "events_real.csv")
for lab, m, exp in [("neither", ~c.s1 & ~c.ni, 474), ("S1 only", c.s1 & ~c.ni, 134),
                    ("NISAR only", ~c.s1 & c.ni, 209), ("both", c.s1 & c.ni, 162)]:
    check(f"partition: {lab}", exp, m.sum(), 0, "events_real.csv")
check("missed events with amp >= 0.09", 212, ((~c.fleet) & (c.amp >= 0.09)).sum(), 0, "events_real.csv amp")
bins = [0, 24, 48, 72, 120, np.inf]
lab = ["<1 d", "1-2 d", "2-3 d", "3-5 d", ">=5 d"]
c["dur"] = pd.cut(c.window_h, bins, right=False, labels=lab)
for l_, (p, n) in zip(lab, [(16.3, 257), (50.8, 266), (61.1, 185), (75.3, 162), (85.3, 109)]):
    g = c[c.dur == l_]
    check(f"duration {l_}: n", n, len(g), 0, "window_h")
    check(f"duration {l_}: fleet capture %", p, g.fleet.mean() * 100, 0.05, "window_h")
cs = rd("capture_synthetic.csv"); h = cs[cs.window == "half-amplitude"].sort_values("R")
check("R for 80 % capture (d)", 1.46, float(np.interp(-0.8, -h.capture, h.R)), 0.005, "capture_synthetic.csv")
check("R80 lower (d)", 1.31, float(np.interp(-0.8, -h.ci_lo, h.R)), 0.006, "capture_synthetic.csv")
check("R80 upper (d)", 1.64, float(np.interp(-0.8, -h.ci_hi, h.R)), 0.006, "capture_synthetic.csv")
D = rd("armo_designs.csv").set_index(rd("armo_designs.csv").design.str[0])
check("design D mean gap (d)", 1.416, D.loc["D", "armo_mean_gap_d"], 0.001, "armo_designs.csv")
check("design D fleet + ARMO %", 81.5, D.loc["D", "capture_fleet_plus_armo"] * 100, 0.05, "armo_designs.csv")
check("design D gain (pp)", 29.9, D.loc["D", "gain_pts"], 0.05, "armo_designs.csv")
hh = rd("performance_headtohead.csv").set_index("system")
check("ARMO alone %", 76.1, hh.loc["ARMO alone (design D)", "capture"] * 100, 0.05, "performance_headtohead.csv")
check("head-to-head fleet + ARMO % (= design D)", 81.5, hh.loc["Sentinel-1 + NISAR + ARMO", "capture"] * 100, 0.05,
      "performance_headtohead.csv")
sm = rd("smap_summary.csv", index_col=0)
check("SMAP all-quality era capture %", 76.6, sm.loc["capture_era", "all"] * 100, 0.05, "smap_summary.csv")
check("SMAP recommended-quality era capture %", 26.7, sm.loc["capture_era", "recommended"] * 100, 0.05, "smap_summary.csv")
smc = rd("smap_capture.csv")
check("smap_capture.csv era mean = recommended capture % (per-event table is the recommended subset)", 26.7,
      smc[smc.era.astype(str) == "True"].cap.astype(str).isin(["True", "1.0", "1"]).mean() * 100, 0.05, "smap_capture.csv")
sz = rd("armo_sizing.csv").iloc[0]
check("mission cost US$ M", 149.8, sz.cost_total, 0.05, "armo_sizing.csv")
out = pd.DataFrame(rows)
out.to_csv(os.path.join(ae.GEN, "anchor_check.csv"), index=False)
print(out.to_string(index=False))
print("\n", out.status.value_counts().to_dict())
