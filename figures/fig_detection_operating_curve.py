"""P0-5  Empirical detection vs false alarms for the sensors we tested (OBSERVED), against ARMO's target (UNVALIDATED).

Scores (no model, no tuning on the evaluation set):
  positive  = a sampled wetting event: the same-geometry change (prior look -> first look inside the window), as in
              08_sensor_tests.py (s1_sampled_events.csv, nisar_sampled_events.csv, smap_sampled_events[_all].csv)
  negative  = an unchanged pair: same-geometry consecutive looks with |dSM| < 0.01 m3/m3 (*_pairs.csv)
  A detection = change > threshold. Thresholds are swept in units of each sensor's no-change noise sigma, so curves are
  comparable across dB and m3/m3 sensors.
  TPR = detected / sampled events (probability of detection). FPR = false alarms / unchanged pairs (probability of false
  detection) - NOT the false-alarm ratio FP/(TP+FP), which would need the base rate of events among all pairs.
Uncertainty: station-cluster bootstrap resampling stations once for positives and negatives together (2,000 draws).
Held-out evaluation (no leakage): the threshold for FPR <= 10 % is the 90th percentile of TRAINING negatives only, then
applied to held-out data: (i) year split 2025 -> 2026 (S1, SMAP); (ii) 5-fold split by station (all sensors).
The 1-sigma operating point uses sigma estimated from all negatives (in-sample), as in the published results.
Outputs: figures/fig_detection_operating_curve.png/.pdf, figures/generated/detection_operating_curve_stats.csv,
         figures/generated/detection_roc_points.csv
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import armo_evidence as ae
import figstyle as fs
from common import rd

fs.apply()
s1s = rd("s1_summary.csv", index_col=0).iloc[:, 0]
nis = rd("nisar_summary.csv", index_col=0).iloc[:, 0]
sms = rd("smap_summary.csv", index_col=0)
SENS = {  # name: (positives file, negatives file, column, published 1-sigma noise, colour)
    "Sentinel-1 VV (C, 10 m)": ("s1_sampled_events.csv", "s1_pairs.csv", "dvv", s1s["noise_db_nochange"], fs.ORANGE),
    "NISAR HH (L, 200 m)": ("nisar_sampled_events.csv", "nisar_pairs.csv", "dhh", nis["noise_hh_db"], fs.VIOLET),
    "NISAR SME2 (L, 200 m)": ("nisar_sampled_events.csv", "nisar_pairs.csv", "dsat", nis["noise_sat_nochange"], "#a99be8"),
    "SMAP all quality (9 km)": ("smap_sampled_events_all.csv", "smap_pairs_all.csv", "dsat", sms.loc["noise_nochange", "all"], fs.MAGENTA),
    "SMAP recommended (9 km)": ("smap_sampled_events.csv", "smap_pairs.csv", "dsat", sms.loc["noise_nochange", "recommended"], "#b0476f"),
}
K = np.linspace(-1.5, 4, 111)
stats, pts, curves = [], [], {}
for name, (fp, fn, col, sig, colr) in SENS.items():
    P = rd(fp).dropna(subset=[col]).reset_index(drop=True)
    N = rd(fn)
    N = N[N.dsm.abs() < 0.01].dropna(subset=[col]).reset_index(drop=True)
    P["year"] = pd.to_datetime(P.t_ws, utc=True, format="ISO8601").dt.year
    N["year"] = pd.to_datetime(N.time, utc=True, format="ISO8601").dt.year
    p, n = P[col].to_numpy() / sig, N[col].to_numpy() / sig
    tpr = np.array([(p > k).mean() for k in K]); fpr = np.array([(n > k).mean() for k in K])
    auc = (p[:, None] > n[None, :]).mean() + 0.5 * (p[:, None] == n[None, :]).mean() if len(n) * len(p) < 4e7 else np.nan
    if not np.isfinite(auc):
        from scipy.stats import mannwhitneyu
        auc = mannwhitneyu(p, n).statistic / (len(p) * len(n))
    curves[name] = (fpr, tpr, colr)
    # station-cluster bootstrap over the union of stations (positives and negatives resampled together)
    stn = np.union1d(P.wban.unique(), N.wban.unique())
    pi = {s: np.flatnonzero(P.wban.to_numpy() == s) for s in stn}; ni = {s: np.flatnonzero(N.wban.to_numpy() == s) for s in stn}
    rng = np.random.default_rng(ae.SEED)
    bt, bf, b10 = [], [], []
    for _ in range(ae.N_BOOT):
        ss = rng.choice(stn, stn.size)
        ip = np.concatenate([pi[s] for s in ss]); iN = np.concatenate([ni[s] for s in ss])
        if len(ip) == 0 or len(iN) == 0:
            continue
        bt.append((p[ip] > 1).mean()); bf.append((n[iN] > 1).mean())
        b10.append((p[ip] > np.quantile(n[iN], 0.9)).mean())
    thr10 = np.quantile(n, 0.9)
    row = dict(sensor=name, n_positive=len(p), n_negative=len(n), n_stations=len(stn), auc=auc,
               tpr_1sigma=(p > 1).mean(), tpr_1sigma_ci_lo=ae.ci95(bt)[0], tpr_1sigma_ci_hi=ae.ci95(bt)[1],
               fpr_1sigma=(n > 1).mean(), fpr_1sigma_ci_lo=ae.ci95(bf)[0], fpr_1sigma_ci_hi=ae.ci95(bf)[1],
               tpr_at_fpr10_insample=(p > thr10).mean(), tpr_at_fpr10_ci_lo=ae.ci95(b10)[0], tpr_at_fpr10_ci_hi=ae.ci95(b10)[1],
               threshold_fpr10_sigma=thr10)
    # held-out: year split
    if {2025, 2026} <= set(P.year) and {2025, 2026} <= set(N.year):
        thr = np.quantile(n[N.year == 2025], 0.9)
        row.update(year_split_tpr_2026=(p[P.year == 2026] > thr).mean(), year_split_fpr_2026=(n[N.year == 2026] > thr).mean(),
                   year_split_n_pos_2026=int((P.year == 2026).sum()), year_split_n_neg_2026=int((N.year == 2026).sum()))
    else:
        row.update(year_split_tpr_2026=np.nan, year_split_fpr_2026=np.nan, year_split_note="BLOCKED: one season only (NISAR 2026)")
    # held-out: 5-fold by station
    rng = np.random.default_rng(ae.SEED + 7)
    folds = np.array_split(rng.permutation(stn), 5)
    tp_, pn_, fp_, nn_ = 0, 0, 0, 0
    for f_ in folds:
        trn = ~N.wban.isin(f_).to_numpy()
        thr = np.quantile(n[trn], 0.9)
        tst_p = P.wban.isin(f_).to_numpy(); tst_n = ~trn
        tp_ += (p[tst_p] > thr).sum(); pn_ += tst_p.sum(); fp_ += (n[tst_n] > thr).sum(); nn_ += tst_n.sum()
    row.update(station_cv_tpr=tp_ / pn_, station_cv_fpr=fp_ / nn_)
    stats.append(row)
    pts += [dict(sensor=name, k_sigma=k, tpr=t, fpr=f) for k, t, f in zip(K, tpr, fpr)]
S = ae.write_stats("detection_operating_curve_stats", stats)
pd.DataFrame(pts).to_csv(os.path.join(ae.GEN, "detection_roc_points.csv"), index=False)

# ---------------------------------------------------------------- figure
fig, axs = plt.subplots(1, 3, figsize=(7.8, 3.2), gridspec_kw=dict(wspace=0.55, width_ratios=[1, 1, 1.05]))
groups = [("Field-scale radar", ["Sentinel-1 VV (C, 10 m)", "NISAR HH (L, 200 m)", "NISAR SME2 (L, 200 m)"]),
          ("SMAP (9 km, not field scale)", ["SMAP all quality (9 km)", "SMAP recommended (9 km)"])]
for ax, (ttl, names), lab in zip(axs[:2], groups, "ab"):
    ax.add_patch(Rectangle((0, 70), 10, 30, facecolor="none", edgecolor=fs.BLUE, ls="--", lw=1.1))
    ax.text(11, 97, "ARMO target\n(UNVALIDATED)", fontsize=6, color=fs.BLUE, va="top")
    ax.plot([0, 100], [0, 100], color=fs.MUTED, lw=0.7, ls=":")
    for nm in names:
        fpr, tpr, colr = curves[nm]
        r = S.set_index("sensor").loc[nm]
        ax.plot(fpr * 100, tpr * 100, color=colr, lw=1.6, label=f"{nm.split(' (')[0]}  AUC {r.auc:.2f}")
        ax.errorbar(r.fpr_1sigma * 100, r.tpr_1sigma * 100,
                    xerr=[[(r.fpr_1sigma - r.fpr_1sigma_ci_lo) * 100], [(r.fpr_1sigma_ci_hi - r.fpr_1sigma) * 100]],
                    yerr=[[(r.tpr_1sigma - r.tpr_1sigma_ci_lo) * 100], [(r.tpr_1sigma_ci_hi - r.tpr_1sigma) * 100]],
                    fmt="o", color=colr, mec="white", ms=5, capsize=1.5, lw=0.8)
    ax.set_xlim(0, 60); ax.set_ylim(0, 100)
    ax.set_xlabel("False alarms on unchanged pairs (%)", fontsize=7.6); ax.set_ylabel("Sampled events detected (%)", fontsize=7.6)
    ax.legend(fontsize=5.8, loc="lower right", handlelength=1.2)
    ax.set_title(ttl, loc="left", fontsize=7.8)
    fs.panel_label(ax, lab)
c = axs[2]
names = list(SENS)
y = np.arange(len(names))[::-1]
for yi, nm in zip(y, names):
    r = S.set_index("sensor").loc[nm]
    colr = SENS[nm][4]
    c.barh(yi + 0.18, r.tpr_at_fpr10_insample * 100, 0.32, color=colr, alpha=0.45)
    c.barh(yi - 0.18, r.station_cv_tpr * 100, 0.32, color=colr)
    c.text(max(r.tpr_at_fpr10_insample, r.station_cv_tpr) * 100 + 2, yi, f"{r.station_cv_tpr * 100:.0f} % (FPR {r.station_cv_fpr * 100:.0f} %)",
           va="center", fontsize=5.8)
c.axvline(70, color=fs.BLUE, ls="--", lw=1)
c.set_yticks(y); c.set_yticklabels([nm.replace(" (", "\n(") for nm in names], fontsize=5.8); c.set_xlim(0, 100)
c.set_xlabel("Detected at a 10 % false-alarm threshold (%)\npale = in-sample; solid = held-out stations", fontsize=7)
c.grid(axis="y", visible=False)
c.set_title("Held-out operating point", loc="left", fontsize=7.8)
fs.panel_label(c, "c")
fig.text(0.01, -0.22,
         "OBSERVED. Curves sweep the decision threshold in units of each sensor's no-change noise σ; dots = published 1σ rule with 95 % station-bootstrap CIs. "
         "Different sensors use different events and periods\n(S1 and SMAP 2025–2026; NISAR 2026, provisional SME2), so curves are not a same-cohort ranking. "
         "Held-out (c): threshold = 90th percentile of training-station negatives, scored on the other stations (5 folds).\n"
         "Dashed box = ARMO requirement (≥ 70 % detection at ≤ 10 % false alarms): a target, not a demonstrated result. "
         "The ≤ 0.038 m³/m³ noise requirement is MODEL-BASED (calibrated detection model), not measured here.",
         fontsize=5.8, color=fs.INK2)
ae.save(fig, "fig_detection_operating_curve")
print(S.round(3).T.to_string())
