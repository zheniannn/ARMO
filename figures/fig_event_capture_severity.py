"""P0-1  Which real wetting events does today's fleet miss?  (OBSERVED: real acquisition times vs USCRN windows)

Cohort: the matched NISAR-era cohort, 979 events at 107 USCRN stations, storms starting 17 Jun-31 Oct 2026.
A "real acquisition look" = at least one actual Sentinel-1C/1D or NISAR acquisition inside the event window
(events_real.csv columns cap_Sentinel-1 (NISAR era), cap_NISAR (NISAR era)). A look is NOT a retrieval or a detection.
(a) mutually exclusive look categories; (b) look probability by window duration with station-cluster bootstrap CIs;
(c) duration-adjusted check of event amplitude: is a large rise (>= 0.09 m3/m3) more or less likely to be looked at
    once window duration is held fixed? (direct standardisation to the cohort duration mix; paired bootstrap).
Outputs: figures/fig_event_capture_severity.png/.pdf, figures/generated/event_capture_severity_stats.csv
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import armo_evidence as ae
import figstyle as fs

fs.apply()
c = ae.era_cohort()
n = len(c)
BINS, LAB = [0, 24, 48, 72, 120, np.inf], ["< 1 d", "1–2 d", "2–3 d", "3–5 d", "≥ 5 d"]
c["dur"] = pd.cut(c.window_h, BINS, right=False, labels=LAB)
c["big"] = c.amp >= 0.09
cat = np.select([~c.s1 & ~c.ni, c.s1 & ~c.ni, ~c.s1 & c.ni], ["Neither", "Sentinel-1 only", "NISAR only"], "Both")
c["cat"] = cat
stats = []
order = ["Neither", "Sentinel-1 only", "NISAR only", "Both"]
for k in order:
    stats.append(dict(quantity=f"category: {k}", n=int((c.cat == k).sum()), denominator=n, value=(c.cat == k).mean()))

# (b) look probability by duration bin, station-cluster bootstrap
dur_rows = []
for lab in LAB:
    g = c[c.dur == lab].reset_index(drop=True)
    d = ae.boot_stat(g.wban, lambda i: g.fleet.to_numpy()[i].mean())
    lo, hi = ae.ci95(d)
    dur_rows.append(dict(bin=lab, n=len(g), k=int(g.fleet.sum()), p=g.fleet.mean(), lo=lo, hi=hi,
                         stations=g.wban.nunique()))
    stats.append(dict(quantity=f"fleet look | duration {lab}", n=int(g.fleet.sum()), denominator=len(g),
                      value=g.fleet.mean(), ci_lo=lo, ci_hi=hi))
dr = pd.DataFrame(dur_rows)

# (c) amplitude, crude and duration-standardised
w = c.dur.value_counts(normalize=True).reindex(LAB).to_numpy()
fl, big, dur = c.fleet.to_numpy(), c.big.to_numpy(), c.dur.astype(str).to_numpy()


def std_rates(idx):
    f, b, d_ = fl[idx], big[idx], dur[idx]
    out = []
    for grp in (True, False):
        r = []
        for lab in LAB:
            m = (b == grp) & (d_ == lab)
            r.append(f[m].mean() if m.any() else np.nan)
        out.append(np.nansum(np.array(r) * w) / np.sum(w[np.isfinite(r)]))
    crude = f[b].mean() - f[~b].mean()
    return out[0], out[1], out[0] - out[1], crude


est = std_rates(np.arange(n))
draws = np.array([std_rates(i) for i in ae.cluster_draws(c.wban)])
lo_s, hi_s = ae.ci95(draws[:, 2]); lo_c, hi_c = ae.ci95(draws[:, 3])
missed = ~c.fleet
stats += [dict(quantity="missed events with amp >= 0.09", n=int((missed & c.big).sum()), denominator=int(missed.sum()),
               value=(missed & c.big).sum() / missed.sum()),
          dict(quantity="look | amp >= 0.09 (crude)", n=int((c.fleet & c.big).sum()), denominator=int(c.big.sum()), value=c.fleet[c.big].mean()),
          dict(quantity="look | amp < 0.09 (crude)", n=int((c.fleet & ~c.big).sum()), denominator=int((~c.big).sum()), value=c.fleet[~c.big].mean()),
          dict(quantity="crude difference (big - small), pp", value=est[3] * 100, ci_lo=lo_c * 100, ci_hi=hi_c * 100),
          dict(quantity="duration-standardised look | amp >= 0.09", value=est[0]),
          dict(quantity="duration-standardised look | amp < 0.09", value=est[1]),
          dict(quantity="duration-standardised difference (big - small), pp", value=est[2] * 100, ci_lo=lo_s * 100, ci_hi=hi_s * 100),
          dict(quantity="Spearman rho(amp, window_h)", value=float(c.amp.rank().corr(c.window_h.rank())))]
ae.write_stats("event_capture_severity_stats", stats)

# ---------------------------------------------------------------- figure
fig = plt.figure(figsize=(7.4, 5.6))
gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.05], width_ratios=[1, 1.25], hspace=0.62, wspace=0.42)
a, b, cc = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[1, :])
cols = {"Neither": fs.MUTED, "Sentinel-1 only": fs.ORANGE, "NISAR only": fs.VIOLET, "Both": fs.INK2}
y = np.arange(4)[::-1]
for yi, k in zip(y, order):
    m = (c.cat == k).sum()
    a.barh(yi, m, color=cols[k], height=0.62)
    a.text(m + 8, yi, f"{m}  ({m / n * 100:.1f} %)", va="center", fontsize=7.5)
a.set_yticks(y); a.set_yticklabels(["No look", "Sentinel-1 only", "NISAR only", "Both"], fontsize=8)
a.set_xlim(0, 640); a.set_xlabel("Wetting events (n = 979)")
a.grid(axis="y", visible=False)
a.set_title("Real acquisition looks inside the window", loc="left", fontsize=8.8)
fs.panel_label(a, "a")

x = np.arange(len(LAB))
b.bar(x, dr.p * 100, color=fs.BLUE, width=0.62)
b.errorbar(x, dr.p * 100, yerr=[(dr.p - dr.lo) * 100, (dr.hi - dr.p) * 100], fmt="none", ecolor=fs.INK, capsize=3, lw=1)
for xi, r in zip(x, dr.itertuples()):
    b.text(xi, r.hi * 100 + 3, f"{r.p * 100:.0f} %", ha="center", fontsize=7.5)
    b.text(xi, 3, f"n={r.n}", ha="center", fontsize=6.6, color="white")
b.set_xticks(x); b.set_xticklabels(LAB, fontsize=7.6); b.set_ylim(0, 105)
b.set_xlabel("Wetting-window duration"); b.set_ylabel("Events with ≥ 1 real look (%)")
b.grid(axis="x", visible=False)
b.set_title("Short events are the ones missed", loc="left", fontsize=8.8)
fs.panel_label(b, "b")

# (c) amplitude within duration bins
for j, (grp, col, lab) in enumerate([(True, fs.RED, "rise ≥ 0.09 m³/m³"), (False, fs.AQUA, "rise < 0.09 m³/m³")]):
    ps, nn = [], []
    for l_ in LAB:
        g = c[(c.dur == l_) & (c.big == grp)].reset_index(drop=True)
        d = ae.boot_stat(g.wban, lambda i: g.fleet.to_numpy()[i].mean(), n=1000) if len(g) else np.array([np.nan])
        lo, hi = ae.ci95(d)
        ps.append((g.fleet.mean() if len(g) else np.nan, lo, hi)); nn.append(len(g))
        stats.append(dict(quantity=f"look | duration {l_}, {lab}", n=int(g.fleet.sum()), denominator=len(g),
                          value=g.fleet.mean() if len(g) else np.nan, ci_lo=lo, ci_hi=hi))
    ps = np.array(ps)
    xx = x + (j - 0.5) * 0.22
    cc.errorbar(xx, ps[:, 0] * 100, yerr=[(ps[:, 0] - ps[:, 1]) * 100, (ps[:, 2] - ps[:, 0]) * 100], fmt="o", color=col,
                ms=5, capsize=2.5, lw=1, label=lab)
    for xi, v, k in zip(xx, ps[:, 0], nn):
        cc.text(xi, 2, f"{k}", ha="center", fontsize=6.2, color=col)
cc.set_xticks(x); cc.set_xticklabels(LAB, fontsize=7.6); cc.set_ylim(0, 105)
cc.set_xlabel("Wetting-window duration (numbers = events in each group)")
cc.set_ylabel("Events with ≥ 1 real look (%)")
cc.grid(axis="x", visible=False)
cc.legend(loc="upper left", fontsize=7.2, ncol=2)
cc.set_title(f"Look rate by rise size within duration classes: duration-standardised difference (large − small) "
             f"{est[2] * 100:+.1f} pp (95 % CI {lo_s * 100:+.1f} to {hi_s * 100:+.1f})", loc="left", fontsize=8.2)
fs.panel_label(cc, "c")
fig.text(0.01, -0.035,
         f"OBSERVED. 979 USCRN wetting events, 107 stations, storms 17 Jun–31 Oct 2026. Look = ≥ 1 actual Sentinel-1C/1D or NISAR "
         f"acquisition inside the half-amplitude window (not a retrieval or detection).\n{int((missed & c.big).sum())} of "
         f"{int(missed.sum())} events without a look rose ≥ 0.09 m³/m³. 95 % CIs: station-cluster bootstrap (2,000 draws, seed "
         f"{ae.SEED}); standardisation uses the cohort's duration mix.", fontsize=6.4, color=fs.INK2)
ae.save(fig, "fig_event_capture_severity")
ae.write_stats("event_capture_severity_stats", stats)
print(pd.DataFrame(stats).round(4).to_string(index=False))
