"""Recompute every number quoted in the submitted presentation (Group2_FinalProjectSlides.pptx, 20 slides) from the
processed data, and check it against the value printed on the slide.

Run after the analysis (00-14) and the figure scripts; offline. Writes figures/generated/slide_numbers.csv
(slide, claim, value on the slide, recomputed value, source) and exits with status 1 if any value disagrees.
Numbers that come from the literature or from NASA/ESA documents (slides 3, 9, 18, 19) are listed in the README,
not here.
"""
import importlib
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import PROC, ROOT, to_hours, P_MIN_MM, A_MIN, FRAC, STORM_GAP_H, WET_HOUR_MM  # noqa: E402

GEN = os.path.join(ROOT, "figures", "generated")
rd = lambda f: pd.read_csv(os.path.join(PROC, f))
rows = []


def check(slide, claim, shown, value, tol, source):
    ok = abs(float(value) - float(shown)) <= tol
    rows.append(dict(slide=slide, claim=claim, on_slide=shown, recomputed=round(float(value), 4), tolerance=tol,
                     status="MATCH" if ok else "MISMATCH", source=source))


# ------------------------------------------------------------------ slides 4 and 8: ground truth
ev = rd("events_real.csv")
win_d = ev.window_h / 24
check(4, "wetting events", 3340, len(ev), 0, "code/01_events.py events.csv")
check(4, "stations with events", 120, ev.wban.nunique(), 0, "events.csv")
check(4, "storm total >= mm", 5, P_MIN_MM, 0, "code/common.py")
check(4, "wet hour >= mm", 0.2, WET_HOUR_MM, 0, "code/common.py")
check(4, "storms separated by dry hours", 24, STORM_GAP_H, 0, "code/common.py")
check(4, "soil-moisture rise >= m3/m3", 0.03, A_MIN, 0, "code/common.py")
check(4, "wet window = share of peak rise", 0.5, FRAC, 0, "code/common.py")
check(8, "median window (days)", 1.8, win_d.median(), 0.05, "events.csv")
check(8, "windows shorter than 48 h (%)", 55, (ev.window_h < 48).mean() * 100, 0.5, "events.csv")
hist = np.histogram(np.clip(win_d, 0, 7.49), bins=np.arange(0, 7.51, 0.5))[0] / len(ev) * 100
labels = [f"{a:g}–{a + 0.5:g}" for a in np.arange(0, 7, 0.5)] + ["7+"]
shown = [12.5, 15.3, 13.4, 13.8, 9.9, 8.2, 5.6, 4.3, 3.6, 2.9, 2.2, 1.7, 1.1, 0.8, 4.6]
for lab, s_, h in zip(labels, shown, hist):
    check(8, f"window histogram {lab} d (%)", s_, h, 0.05, "events.csv")

# ------------------------------------------------------------------ slide 5: Stillwater
sw = ev[ev.wban == 53926].copy()
sw["t_start"] = pd.to_datetime(sw.t_start, utc=True)
aug = sw[(sw.t_start >= "2026-08-10") & (sw.t_start < "2026-08-30")].sort_values("t_start")
check(5, "first window (h)", 68, aug.window_h.iloc[0], 0.5, "events_real.csv, WBAN 53926")
check(5, "second window (h)", 41, aug.window_h.iloc[1], 0.5, "events_real.csv, WBAN 53926")
col = "cap_Sentinel-1 + NISAR (NISAR era)"
era_sw = sw[sw[col].notna()]
check(5, "NISAR-era wetting events at Stillwater", 11, len(era_sw), 0, "events_real.csv")
check(5, "...sampled by any radar look", 5, era_sw[col].sum(), 0, "code/02_real_schedules.py")
check(5, "17 Aug event captured (0 = missed)", 0, aug[col].iloc[0], 0, "code/02_real_schedules.py")
check(5, "22 Aug event captured (1 = captured)", 1, aug[col].iloc[1], 0, "code/02_real_schedules.py")

# ------------------------------------------------------------------ slides 6 and 7: case studies
cs = pd.read_csv(os.path.join(GEN, "case_study_stats.csv"), index_col=0)["stillwater"]
cn = pd.read_csv(os.path.join(GEN, "case_study_nisar_stats.csv"), index_col=0)["stillwater"]
check(6, "Sentinel-1 ΔVV vs rain, r", 0.74, float(cs["main_r"]), 0.005, "figures/fig_case_studies.py")
check(6, "high-rain cells ΔVV (dB)", 0.9, float(cs["dvv_high"]), 0.05, "figures/fig_case_studies.py")
check(6, "low-rain cells ΔVV (dB)", -0.4, float(cs["dvv_low"]), 0.05, "figures/fig_case_studies.py")
check(7, "NISAR ΔHH vs rain, r", 0.57, float(cn["n_main_r"]), 0.005, "figures/fig_case_studies.py")
check(7, "high-rain cells ΔHH (dB)", 2.2, float(cn["n_dvv_high"]), 0.05, "figures/fig_case_studies.py")
check(7, "low-rain cells ΔHH (dB)", 0.5, float(cn["n_dvv_low"]), 0.05, "figures/fig_case_studies.py")

# ------------------------------------------------------------------ slides 10, 12, 13, 18, 20: capture
hh = rd("performance_headtohead.csv").set_index("system")
era = ev[ev[col].notna()]
check(10, "NISAR-era events", 979, len(era), 0, "events_real.csv")
check(10, "NISAR-era stations", 107, era.wban.nunique(), 0, "events_real.csv")
check(10, "Sentinel-1 capture (%)", 30.2, hh.capture["Sentinel-1 alone"] * 100, 0.05, "code/06 performance_headtohead.csv")
check(10, "NISAR capture (%)", 37.9, hh.capture["NISAR alone"] * 100, 0.05, "performance_headtohead.csv")
check(10, "Sentinel-1 + NISAR capture (%)", 51.6, hh.capture["Sentinel-1 + NISAR"] * 100, 0.05, "performance_headtohead.csv")
check(12, "fleet + ARMO capture (%)", 81.5, hh.capture["Sentinel-1 + NISAR + ARMO"] * 100, 0.05, "performance_headtohead.csv")
check(12, "ARMO alone (%)", 76.1, hh.capture["ARMO alone (design D)"] * 100, 0.05, "performance_headtohead.csv")
de = rd("armo_designs.csv")
de["key"] = de.design.str.strip().str[0]
de = de.set_index("key")
check(12, "gain (percentage points)", 29.9, de.gain_pts["D"], 0.05, "code/06 armo_designs.csv")
for k, cap, gap in [("A", 71.1, 2.8), ("B", 70.1, 2.8), ("C", 77.2, 1.8), ("D", 81.5, 1.4), ("E", 77.4, 1.4)]:
    check(13, f"design {k}: fleet + ARMO capture (%)", cap, de.capture_fleet_plus_armo[k] * 100, 0.05, "armo_designs.csv")
    check(13, f"design {k}: mean gap between ARMO looks (d)", gap, de.armo_mean_gap_d[k], 0.05, "armo_designs.csv")
check(13, "D over best one-satellite design (points)", 4.3,
      (de.capture_fleet_plus_armo["D"] - de.capture_fleet_plus_armo[["A", "B", "C"]].max()) * 100, 0.05, "armo_designs.csv")
check(18, "fleet + ROSE-L 6-day capture (%)", 63.7, hh.capture["Sentinel-1 + NISAR + ROSE-L 6-day"] * 100, 0.05, "performance_headtohead.csv")
sm = rd("smap_summary.csv").set_index(rd("smap_summary.csv").columns[0])
check(18, "SMAP retrieval in windows, all quality (%)", 77, float(sm.loc["capture_era", "all"]) * 100, 0.5, "code/08 smap_summary.csv")
check(18, "SMAP retrieval in windows, recommended (%)", 27, float(sm.loc["capture_era", "recommended"]) * 100, 0.5, "smap_summary.csv")
md = importlib.import_module("06_mission_design")
e0, e1 = to_hours(pd.DatetimeIndex([md.ERA[0], md.ERA[1]]))
acq = pd.concat([rd("acq_s1.csv"), rd("acq_nisar.csv")])
acq["h"] = to_hours(pd.to_datetime(acq.time, utc=True))
gaps = []
for _, g in acq[(acq.h >= e0) & (acq.h < e1)].groupby("wban"):
    d = np.diff(np.sort(g.h.to_numpy())) / 24
    gaps += list(d[d > 0.25])                         # looks < 6 h apart are one overpass
check(18, "fleet median gap between looks (d)", 2.0, np.median(gaps), 0.05, "acq_s1.csv, acq_nisar.csv")

# ------------------------------------------------------------------ slide 17: revisit requirement
cs_ = rd("capture_synthetic.csv")
cur = cs_[cs_.window == "half-amplitude"].sort_values("R")
for r_, v in [(1, 86.7), (2, 72.2), (3, 59.5), (4, 50.0), (5, 42.6), (6, 36.9)]:
    check(17, f"capture at {r_}-day revisit (%)", v, cur.set_index("R").capture[r_] * 100, 0.05, "code/01 capture_synthetic.csv")
r80 = lambda c: float(np.interp(-0.80, -cur[c].to_numpy(), cur.R.to_numpy()))
check(17, "revisit for 80 % capture (d)", 1.46, r80("capture"), 0.005, "capture_synthetic.csv")
check(17, "...lower bound (d)", 1.31, r80("ci_lo"), 0.005, "capture_synthetic.csv")
check(17, "...upper bound (d)", 1.64, r80("ci_hi"), 0.005, "capture_synthetic.csv")

# ------------------------------------------------------------------ slides 11 and 19: spacecraft and cost
D = de.loc["D"]
sz = rd("armo_sizing.csv").iloc[0]
rl = rd("armo_sizing_realistic.csv").set_index("parameter").value
check(11, "satellites", 2, D.n_sat, 0, "armo_designs.csv")
check(11, "orbit altitude (km)", 620, D.altitude_km, 0, "armo_designs.csv")
check(11, "access swath (km)", 362, D.access_swath_km, 0, "armo_designs.csv")
check(11, "radar frequency (GHz)", 1.26, 299792458 / float(sz.lambda_m) / 1e9, 0.005, "code/06 armo_sizing.csv")
check(11, "reflector diameter (m)", 5.9, float(sz.reflector_d_m), 0.05, "armo_sizing.csv")
check(11, "wet mass per satellite (kg)", 316, rl["wet_mass_per_satellite"], 0.5, "code/06 realistic_sizing()")
check(19, "peak RF power (kW)", 2.8, rl["rf_power_peak"] / 1e3, 0.05, "realistic_sizing()")
check(19, "earlier mission estimate (US$ M)", 149.8, rd("armo_cost.csv").usd_m.sum(), 0.05, "code/06 armo_cost.csv")

out = pd.DataFrame(rows)
out.to_csv(os.path.join(GEN, "slide_numbers.csv"), index=False)
bad = out[out.status != "MATCH"]
print(f"{len(out)} slide numbers checked: {len(out) - len(bad)} MATCH, {len(bad)} MISMATCH")
if len(bad):
    print(bad.to_string(index=False))
sys.exit(1 if len(bad) else 0)
