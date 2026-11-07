"""Slide 5: a real wetting episode between satellite acquisitions (Stillwater 2 W, OK, 10-29 Aug 2026).
The slide version draws 5 cm soil moisture on an exponential axis (EXP_K) to stretch the wet peaks.

Events are read from data/processed/events_real.csv and re-derived with common.detect_events (asserted identical);
acquisition times are read from the processed files, not typed in.

Time convention (NOAA USCRN hourly02 README, UTC_TIME): each hourly value is labelled at the END of its hour, so the
record labelled hh:00 covers (hh-1, hh]. common.captured() already compares an acquisition at hh:mm with the record
labelled ceil(hh:mm). This figure draws the same convention: rain bars span (hh-1, hh], soil moisture (an hourly mean)
is drawn at hh-0:30, and a window with labels [t_ws, t_we) is shaded over (t_ws-1 h, t_we-1 h].

Outputs: figures/slide05_wetting_windows.png (deck slide 5; draw("B") gives fig_wetting_window_B_report.png, the
annotated report version), figures/generated/fig_wetting_window_audit.csv
Run: python figures/fig_wetting_window.py   (from the project root or anywhere)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "code"))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator
from common import PROC, load_uscrn, rd, season_series, detect_events, to_hours, captured, FRAC, A_MIN

# deck palette
NAVY, TEAL, INK, GREY, LIGHT, RAIN = "#112B43", "#167B95", "#1B2631", "#5B6770", "#D5DDE3", "#5E8FB8"
S1C, PALE, RED = "#8C98A3", "#D3E6F1", "#A33A2A"
plt.rcParams.update({"font.family": "Calibri", "font.size": 15, "axes.edgecolor": GREY, "axes.labelcolor": INK,
                     "xtick.color": INK, "ytick.color": INK, "axes.spines.top": False, "axes.spines.right": False,
                     "savefig.dpi": 300, "savefig.facecolor": "white", "svg.fonttype": "none"})
WBAN, LON = 53926, -97.09
T0, T1 = pd.Timestamp("2026-08-10", tz="UTC"), pd.Timestamp("2026-08-29", tz="UTC")
H, HALF = pd.Timedelta(hours=1), pd.Timedelta(minutes=30)
EXP_K = 9.0   # slide version: soil-moisture axis is exponential, displayed coordinate = exp(EXP_K * soil moisture)

# ------------------------------------------------------------------ data
u = load_uscrn()
raw = u[(u.wban == WBAN) & (u.time_utc >= T0) & (u.time_utc < T1 + H)].set_index("time_utc")
assert len(raw) == 19 * 24 + 1 and raw.sm5.notna().all() and raw.precip.notna().all(), "gaps in the plotted hours"

ev = rd("events_real.csv", parse_dates=["t_start", "t_peak", "t_ws", "t_we", "t_ws_abs", "t_we_abs"])
ev = ev[(ev.wban == WBAN) & (ev.t_start >= T0) & (ev.t_start < T1)].sort_values("t_start").reset_index(drop=True)
assert len(ev) == 2
# independent re-derivation with the project's own detector and constants
s = season_series(u, WBAN, 2026)
d = detect_events(s, 2026)
d = d[(d.t_start >= T0) & (d.t_start < T1)].reset_index(drop=True)
for c in ("t_start", "t_peak", "t_ws", "t_we", "window_h", "censored"):
    assert (d[c].values == ev[c].values).all(), c
assert np.allclose(d[["pre", "peak", "amp", "rain_mm"]].values, ev[["pre", "peak", "amp", "rain_mm"]].values)

# storms (same grouping as detect_events): first/last wet hour of each >= 5 mm storm
p, t = s.precip.to_numpy(), s.index
wet = np.flatnonzero(p >= 0.2)
br = np.flatnonzero(np.diff(wet) > 24)
st_i, en_i = np.r_[wet[0], wet[br + 1]], np.r_[wet[br], wet[-1]]
storms = [(t[a], t[b], p[a:b + 1].sum()) for a, b in zip(st_i, en_i) if p[a:b + 1].sum() >= 5]
storm_end = {a: b for a, b, _ in storms}

# acquisitions, as used by code/02_real_schedules.py (one per pass) and code/08_sensor_tests.py (SMAP nominal times)
def one_per_pass(a):
    a = a.sort_values("time")
    return a[(a.time.diff() > H) | a.time.diff().isna()]
s1 = one_per_pass(pd.read_csv(os.path.join(PROC, "acq_s1.csv"), parse_dates=["time"]).query("wban == @WBAN"))
ni = one_per_pass(pd.read_csv(os.path.join(PROC, "acq_nisar.csv"), parse_dates=["time"]).query("wban == @WBAN"))
sm = pd.read_csv(os.path.join(PROC, "gee_smap.csv")).query("wban == @WBAN")
sm_rows = []
for ov, h in (("am", 6), ("pm", 18)):
    x = sm[["date", "longitude", f"soil_moisture_{ov}", f"retrieval_qual_flag_{ov}"]].dropna(subset=[f"soil_moisture_{ov}"])
    tt = (pd.to_datetime(x.date, utc=True) + pd.to_timedelta(h - x.longitude / 15, unit="h")).dt.round("min")
    sm_rows.append(pd.DataFrame({"time": tt.values, "flag": x[f"retrieval_qual_flag_{ov}"].values, "sm": x[f"soil_moisture_{ov}"].values}))
smap = pd.concat(sm_rows).sort_values("time")
smap["time"] = pd.to_datetime(smap.time, utc=True)
looks = {"Sentinel-1": s1.time, "NISAR": ni.time, "SMAP": smap.time}
inview = {k: v[(v >= T0) & (v < T1)] for k, v in looks.items()}

# ------------------------------------------------------------------ verification table
rows = []
for i, e in ev.iterrows():
    thr = e.pre + FRAC * e.amp
    a_lab, b_lab = e.t_start, storm_end[e.t_start]
    nxt = [x for x, _, _ in storms if x > e.t_start]
    reason = (f"censored: next storm's first wet hour ({nxt[0]:%d %b %H:%M} label); 5 cm SM there "
              f"{raw.sm5.get(e.t_we, np.nan):.3f} >= threshold" if e.censored else
              f"SM fell below threshold: {raw.sm5[e.t_we]:.3f} < {thr:.4f} at {e.t_we:%d %b %H:%M} label")
    ws_h, we_h = to_hours(pd.DatetimeIndex([e.t_ws]))[0], to_hours(pd.DatetimeIndex([e.t_we]))[0]
    wsa_h, wea_h = to_hours(pd.DatetimeIndex([e.t_ws_abs]))[0], to_hours(pd.DatetimeIndex([e.t_we_abs]))[0]
    inside, inside_abs = {}, {}
    for k, v in looks.items():
        oh = np.sort(to_hours(v))
        lab = np.ceil(oh)
        inside[k] = [str(x) for x, l in zip(np.sort(v.values), lab) if ws_h <= l < we_h]
        inside_abs[k] = [str(x) for x, l in zip(np.sort(v.values), lab) if wsa_h <= l < wea_h]
        assert bool(captured(oh, ws_h, we_h)) == (len(inside[k]) > 0)
    for k in ("Sentinel-1", "NISAR"):
        col = f"cap_{k} (NISAR era)"
        assert bool(e[col]) == (len(inside[k]) > 0), (k, e[col])
    rows.append({"event": f"{e.t_start:%d %b}",
                 "storm start (UTC, hour-end label)": f"{a_lab:%Y-%m-%d %H:%M}",
                 "storm end (UTC, hour-end label)": f"{b_lab:%Y-%m-%d %H:%M}",
                 "storm rain interval (UTC)": f"{a_lab - H:%d %b %H:%M} to {b_lab:%d %b %H:%M}",
                 "total rain (mm)": round(e.rain_mm, 1),
                 "baseline hours (labels)": f"{a_lab - 3 * H:%d %b %H:%M}-{a_lab - H:%H:%M}",
                 "baseline (m3/m3)": round(e.pre, 4), "peak (m3/m3)": e.peak, "peak time (label)": f"{e.t_peak:%d %b %H:%M}",
                 "peak rise A (m3/m3)": round(e.amp, 4), "50% threshold (m3/m3)": round(thr, 4),
                 "window start (label)": f"{e.t_ws:%Y-%m-%d %H:%M}", "window end (first label out)": f"{e.t_we:%Y-%m-%d %H:%M}",
                 "window interval (UTC)": f"{e.t_ws - H:%d %b %H:%M} to {e.t_we - H:%d %b %H:%M}",
                 "duration (h)": int(e.window_h), "censored": bool(e.censored), "termination": reason,
                 "S1 in window": "; ".join(inside["Sentinel-1"]) or "none", "NISAR in window": "; ".join(inside["NISAR"]) or "none",
                 "SMAP in window": "; ".join(inside["SMAP"]) or "none",
                 "abs-anomaly window (labels)": f"{e.t_ws_abs:%d %b %H:%M} to {e.t_we_abs:%d %b %H:%M} ({int(e.window_abs_h)} h)",
                 "S1 in abs window": "; ".join(inside_abs["Sentinel-1"]) or "none",
                 "NISAR in abs window": "; ".join(inside_abs["NISAR"]) or "none"})
tab = pd.DataFrame(rows)
tab.T.to_csv(os.path.join(HERE, "generated", "fig_wetting_window_audit.csv"), header=False)
print(tab.T.to_string())
print("acquisitions plotted:", {k: [f"{x:%d %b %H:%M}" for x in v] for k, v in inview.items()})
e26 = rd("events_real.csv", parse_dates=["t_start"]).query("wban == @WBAN and season == 2026")
era = e26[e26.t_start >= pd.Timestamp("2026-06-17", tz="UTC")]
print("NISAR-era events at station:", len(era), "sampled by S1 or NISAR:", int(era["cap_Sentinel-1 + NISAR (NISAR era)"].sum()))

# ------------------------------------------------------------------ figure (A = presentation, B = report/appendix)
e1, e2 = ev.iloc[0], ev.iloc[1]
thr1, thr2 = e1.pre + FRAC * e1.amp, e2.pre + FRAC * e2.amp
# display values: thresholds to 4 dp (event 1 is an exact tie at 0.2005, so 3 dp would be rounding-rule dependent)
assert f"{thr1:.4f}" == "0.2005" and f"{thr2:.4f}" == "0.2693" and f"{thr2:.3f}" == "0.269"
win = [(e.t_ws - H, e.t_we - H) for e in (e1, e2)]          # shaded intervals, UTC (hour-end labels -> interval)
n_in = {k: [int(((v >= a) & (v < b)).sum()) for a, b in win] for k, v in inview.items()}
assert n_in["Sentinel-1"] == [0, 0] and n_in["NISAR"] == [0, 2], n_in
s1_after = inview["Sentinel-1"][inview["Sentinel-1"] > win[1][1]].iloc[0]
SM_LS, THR_LS, BASE_LS = "-", (0, (5, 3)), (0, (1, 2))


def draw(ver):
    full = ver == "B"
    # slide: Sentinel-1 red solid, NISAR green solid (S1 drawn thicker as a second cue for red-green colour blindness)
    S1_STY = dict(color=S1C, lw=3.0) if full else dict(color="#C0392B", lw=3.0)
    NI_STY = dict(color=TEAL, lw=2.0, ls=(0, (4, 2))) if full else dict(color="#2E9E4F", lw=2.0, ls="-")
    fig = plt.figure(figsize=(12.6, 5.9 if full else 5.5))
    top, rain_h, gap = 0.93, (0.17 if full else 0.15), 0.035
    axr = fig.add_axes([0.075, top - rain_h, 0.905, rain_h])
    soil_bottom = 0.215 if full else 0.165
    axs = fig.add_axes([0.075, soil_bottom, 0.905, top - rain_h - gap - soil_bottom], sharex=axr)

    # measurements
    if full:   # report: hourly totals
        axr.bar(raw.index - H, raw.precip, width=1 / 24, align="edge", color=RAIN, lw=0)
        axr.set_ylabel("Rain\n(mm/h)", fontsize=14)
    else:      # slide: 6-hourly totals (hour-end records: the hour labelled hh covers hh-1 to hh), visible at slide scale
        r6 = raw.precip[raw.index > T0].groupby((raw.index[raw.index > T0] - H).floor("6h")).sum()
        assert abs(r6.sum() - raw.precip[raw.index > T0].sum()) < 1e-9
        axr.bar(r6.index, r6.values, width=0.25, align="edge", color="#2F5F8A", lw=0, zorder=3)
        axr.set_ylabel("Rain\n(mm/6 h)", fontsize=14)
    axr.set_ylim(0, 48); axr.set_yticks([0, 20, 40])
    axr.tick_params(labelbottom=False, labelsize=13)
    axs.plot(raw.index - HALF, raw.sm5, color=INK, lw=2.6, zorder=5)
    if not full:   # exponential axis: stretches the wet peaks, compresses the dry baseline
        axs.set_yscale("function", functions=(lambda y: np.exp(EXP_K * y), lambda z: np.log(np.clip(z, 1e-9, None)) / EXP_K))
    axs.set_ylabel("5 cm soil moisture (m³/m³)" if full else "5 cm soil moisture (m³/m³, exp)", fontsize=14)
    axs.set_ylim(0.08, 0.375)
    axs.yaxis.set_major_locator(FixedLocator([0.10, 0.15, 0.20, 0.25, 0.30, 0.35])); axs.yaxis.set_minor_locator(NullLocator())
    axs.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.2f}")); axs.tick_params(labelsize=13)
    for ax_ in (axr, axs):
        ax_.grid(axis="y", color=LIGHT, lw=0.8); ax_.set_axisbelow(True)

    # windows, baselines, thresholds, peaks
    for e, (a, b) in zip((e1, e2), win):
        for ax_ in (axr, axs):
            ax_.axvspan(a, b, color=PALE, lw=0, zorder=0)
        axs.hlines(e.pre + FRAC * e.amp, a, b, color=NAVY, lw=1.8, ls=THR_LS, zorder=4)
        if full:
            axs.hlines(e.pre, e.t_start - 4 * H, b, color=GREY, lw=1.3, ls=BASE_LS, zorder=3)
            axs.plot(e.t_peak - HALF, e.peak, "o", ms=7.5, mfc="white", mec=INK, mew=1.8, zorder=6)

    # acquisitions
    for tt in inview["Sentinel-1"]:
        for ax_ in (axr, axs):
            ax_.axvline(tt, zorder=2, **S1_STY)
    for tt in inview["NISAR"]:
        for ax_ in (axr, axs):
            ax_.axvline(tt, zorder=2, **NI_STY)
    if full:
        axs.plot(inview["SMAP"], np.full(len(inview["SMAP"]), 0.362), ls="none", marker="|", ms=11, mew=2.2, color=NAVY,
                 zorder=6, clip_on=False)

    kw = dict(fontsize=13 if not full else 12.5, color=INK, zorder=8)
    pbox = dict(boxstyle="square,pad=0.15", fc=PALE, ec="none")
    wbox = dict(boxstyle="square,pad=0.15", fc="white", ec="none")
    mid1, mid2 = win[0][0] + (win[0][1] - win[0][0]) / 2, win[1][0] + (win[1][1] - win[1][0]) / 2

    if full:
        # peaks (value and rise above the baseline), placed above the curve
        axs.text(e1.t_peak + 2 * H, e1.peak + 0.022, f"Peak {e1.peak:.3f} (rise +{e1.amp:.3f})", ha="left", va="center", bbox=pbox, **kw)
        axs.text(e2.t_peak + 4 * H, e2.peak + 0.013, f"Peak {e2.peak:.3f} (rise +{e2.amp:.3f})", ha="left", va="center", bbox=pbox, **kw)
        # thresholds: event 1 labelled left of its line (empty pre-storm area), event 2 below its line inside its window
        axs.text(e1.t_start - 4 * H, thr1, f"50 % line {thr1:.4f}", ha="right", va="center", bbox=wbox, **kw)
        axs.text(win[1][1] - 2 * H, thr2 - 0.006, f"50 % line {thr2:.4f}", ha="right", va="top", bbox=pbox, **kw)
        if full:   # threshold arithmetic, one boxed inset in the empty pre-storm area
            axs.text(T0 + 8 * H, 0.338, "50 % line = pre-storm baseline + 0.5 × peak rise\n"
                     f"17 Aug:  {e1.pre:.4f} + 0.5 × {e1.amp:.4f} = {thr1:.4f}\n"
                     f"22 Aug:  {e2.pre:.4f} + 0.5 × {e2.amp:.4f} = {thr2:.4f}",
                     ha="left", va="top", fontsize=12, color=INK, linespacing=1.25, zorder=8,
                     bbox=dict(boxstyle="square,pad=0.35", fc="white", ec=LIGHT, lw=1.0))

    # durations and acquisition outcomes
    yb = 0.163
    for (a, b), m, e in zip(win, (mid1, mid2), (e1, e2)):
        axs.annotate("", xy=(a, yb), xytext=(b, yb), arrowprops=dict(arrowstyle="<->", color=NAVY, lw=1.6, shrinkA=0, shrinkB=0))
        ni_in = inview["NISAR"][(inview["NISAR"] >= a) & (inview["NISAR"] < b)]
        if not full and len(ni_in):   # slide: centre the label between the last NISAR line and the window end, no box
            m = ni_in.iloc[-1] + (b - ni_in.iloc[-1]) / 2
        axs.text(m, yb + 0.008 if full else yb - 0.004, f"{e.window_h:.0f} h", ha="center", va="bottom" if full else "top",
                 fontsize=19 if full else 18, color=NAVY, fontweight="bold", bbox=pbox if full else None, zorder=8)
    if full:
        axs.text(mid1, yb - 0.005, "No radar acquisition\nduring window", ha="center", va="top", fontsize=13.5, color=RED,
                 fontweight="bold", linespacing=1.0, zorder=8)
        axs.text(mid2, yb - 0.005, f"{n_in['NISAR'][1]} NISAR acquisitions\nduring window", ha="center", va="top", fontsize=13.5,
                 color=TEAL, fontweight="bold", linespacing=1.0, bbox=pbox, zorder=8)
        axs.annotate("Sentinel-1 returns\nafter window", xy=(s1_after, 0.205), xytext=(s1_after + pd.Timedelta(hours=44), 0.135),
                     ha="center", va="center", fontsize=13, color=GREY, arrowprops=dict(arrowstyle="->", color=GREY, lw=1.2))

        # storm truncation of window 1: red mark at the next storm's first wet hour (both panels), note in the empty rain panel
        tcut = win[0][1]
        axr.axvline(tcut, color=RED, lw=1.6, zorder=6)
        axs.plot([tcut] * 2, [thr1 - 0.012, raw.sm5[e1.t_we] + 0.014], color=RED, lw=2.4, zorder=7, solid_capstyle="butt")
        if full:
            axr.text(tcut - 3 * H, 24, f"Storm-truncated: next\nstorm begins {tcut:%d %b %H:%M}\nUTC; soil still "
                     f"{raw.sm5[e1.t_we]:.3f}\n(≥ 50 % line {thr1:.4f})", ha="right", va="center", fontsize=11.5, color=RED,
                     linespacing=1.0, zorder=8)
        else:
            axr.text(tcut - 3 * H, 24, "Storm-truncated:\nnext storm begins", ha="right", va="center", fontsize=13.5, color=RED,
                     fontweight="bold", linespacing=1.0, zorder=8)

        if full:   # report: rainfall totals and baselines
            axr.text(e1.t_start - 3 * H, 41, f"Storm 1: {e1.rain_mm:.1f} mm in 2 h", ha="right", va="center", fontsize=12, color=INK,
                     bbox=wbox)
            s2a, s2b = e2.t_start - H, storm_end[e2.t_start]
            axr.annotate("", xy=(s2a, 22), xytext=(s2b, 22), arrowprops=dict(arrowstyle="|-|", color=GREY, lw=1.1, mutation_scale=4))
            axr.text(s2a + (s2b - s2a) / 2, 25, f"Storm 2: {e2.rain_mm:.1f} mm", ha="center", va="bottom", fontsize=12, color=INK,
                     zorder=7)
            axs.text(e1.t_start - 4 * H, e1.pre - 0.004, f"Pre-storm baseline {e1.pre:.4f}", ha="right", va="top", bbox=wbox, **kw)
            axs.text(mid2, e2.pre + 0.004, f"Baseline {e2.pre:.4f}", ha="center", va="bottom", bbox=pbox, **kw)

    axs.set_xlim(T0, T1)
    axs.xaxis.set_major_locator(mdates.DayLocator(interval=2)); axs.xaxis.set_minor_locator(mdates.DayLocator())
    axs.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    axs.set_xlabel("August 2026 (UTC)", fontsize=13, color=GREY, labelpad=2)

    handles = [Line2D([], [], color=INK, lw=2.6, label="USCRN 5 cm soil moisture (hourly mean)"),
               Patch(fc=PALE, ec="none", label="Wetting window"),
               Line2D([], [], color=NAVY, lw=1.8, ls=THR_LS, label="50 % of peak rise"),
               Line2D([], [], color=GREY, lw=1.3, ls=BASE_LS, label="Pre-storm baseline"),
               Line2D([], [], **S1_STY, label="Sentinel-1 acquisition (radar)"),
               Line2D([], [], **NI_STY, label="NISAR acquisition (radar)"),
               Line2D([], [], color=NAVY, marker="|", ls="none", ms=11, mew=2.2, label="SMAP retrieval (9 km radiometer)")]
    if not full:
        handles = [h for h in handles if h.get_label() not in ("Pre-storm baseline", "SMAP retrieval (9 km radiometer)")]
        axr.set_title("Two wetting windows at NOAA USCRN Stillwater, Oklahoma, August 2026 (exponential soil-moisture axis)",
                      loc="left", fontsize=17,
                      color=INK, fontweight="bold", pad=12)
    fig.legend(handles=handles, loc="lower center", ncol=4 if full else 5, fontsize=12.5, frameon=False, bbox_to_anchor=(0.53, -0.01),
               handlelength=2.2, columnspacing=1.3)
    name = "slide05_wetting_windows" if not full else "fig_wetting_window_B_report"
    fig.savefig(os.path.join(HERE, f"{name}.png"), bbox_inches="tight", pad_inches=0.06, dpi=600)
    plt.close(fig)
    return os.path.join(HERE, f"{name}.png")


outs = [draw("A")]          # draw("B") gives the annotated report/appendix version
print("wrote", outs)
