"""Derive ARMO's event-sensitivity (noise) requirement from the four sensors tested.

Model: a sampled event of size A changes the sensor by s*A plus Gaussian noise sigma (the no-change
spread of same-geometry pairs). With a 1-sigma threshold, P(detect | A) = Phi(A / n - 1), where
n = sigma / s is the noise in soil-moisture units. The model is checked against the observed detection
rates of Sentinel-1, NISAR (HH and SME2) and SMAP, then solved for the n that detects 70 % of the
observed event-size distribution. n is converted to backscatter (dB) with the measured L- and C-band
sensitivities; if the noise is speckle-dominated, noise falls as 1/sqrt(looks).
Outputs: data/processed/snr_requirement.csv (sensor table), snr_summary.csv
"""
import os
import numpy as np
import pandas as pd
from scipy import stats, optimize
from common import PROC


def rd(f, **k): return pd.read_csv(os.path.join(PROC, f), **k)


ev = rd("events.csv")
s1 = rd("s1_summary.csv", index_col=0).iloc[:, 0]
ni = rd("nisar_summary.csv", index_col=0).iloc[:, 0]
sm = rd("smap_summary.csv", index_col=0)["all"]
s1p, nip, smp = rd("s1_pairs.csv"), rd("nisar_pairs.csv"), rd("smap_pairs_all.csv")


def slope(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    return stats.linregress(x[ok], y[ok]).slope


cases = [  # name, change column, pairs, sampled events, noise
    ("Sentinel-1 VV", "dvv", s1p, rd("s1_sampled_events.csv"), s1["noise_db_nochange"]),
    ("NISAR HH", "dhh", nip, rd("nisar_sampled_events.csv"), ni["noise_hh_db"]),
    ("NISAR SME2", "dsat", nip, rd("nisar_sampled_events.csv"), ni["noise_sat_nochange"]),
    ("SMAP", "dsat", smp, rd("smap_sampled_events_all.csv"), sm["noise_nochange"]),
]
rows = []
for name, col, pr, det, sig in cases:
    s = slope(pr.dsm.to_numpy(float), pr[col].to_numpy(float))
    n = sig / s
    d = det.dropna(subset=[col])
    rows.append(dict(sensor=name, slope_per_m3m3=s, noise=sig, noise_sm_equiv=n, n_events=len(d),
                     p_observed=(d[col] > sig).mean(), p_model=stats.norm.cdf(d.amp / n - 1).mean(),
                     snr_median_event=ev.amp.median() / n))
tab = pd.DataFrame(rows)
amps = ev.amp.to_numpy()


# The ideal model is optimistic for every sensor (events vary more than one slope and noise capture).
# Calibrate with ONE factor k shared by all sensors (effective sensitivity = k x slope), fitted to the
# observed rates weighted by events, and use the calibrated model for the requirement.
det_amps = {r[0]: r[3].dropna(subset=[r[1]]).amp.to_numpy() for r in cases}


def p_k(n, a, k): return stats.norm.cdf(k * a / n - 1).mean()


def loss(k):
    return sum(r.n_events * (p_k(r.noise_sm_equiv, det_amps[r.sensor], k) - r.p_observed) ** 2 for r in tab.itertuples())


K = optimize.minimize_scalar(loss, bounds=(0.1, 2), method="bounded").x
tab["p_calibrated"] = [p_k(r.noise_sm_equiv, det_amps[r.sensor], K) for r in tab.itertuples()]


def p_of(n, k=K): return stats.norm.cdf(k * amps / n - 1).mean()


n70 = optimize.brentq(lambda n: p_of(n) - 0.70, 0.002, 0.5)
n50 = optimize.brentq(lambda n: p_of(n) - 0.50, 0.002, 0.5)
n70_ideal = optimize.brentq(lambda n: p_of(n, 1.0) - 0.70, 0.002, 0.5)
L = tab.set_index("sensor").loc["NISAR HH"]; C = tab.set_index("sensor").loc["Sentinel-1 VV"]
summ = dict(k_calibration=K, noise_req_70=n70, noise_req_50=n50, noise_req_70_ideal=n70_ideal, snr_req_median=np.median(amps) / n70,
            req_db_L=n70 * L.slope_per_m3m3, req_db_C=n70 * C.slope_per_m3m3,
            now_db_L=L.noise, now_db_C=C.noise,
            looks_factor_L=(L.noise / (n70 * L.slope_per_m3m3)) ** 2,
            model_mae_pts=(tab.p_model - tab.p_observed).abs().mean() * 100,
            calibrated_mae_pts=(tab.p_calibrated - tab.p_observed).abs().mean() * 100)
tab.to_csv(os.path.join(PROC, "snr_requirement.csv"), index=False)
pd.Series(summ).to_csv(os.path.join(PROC, "snr_summary.csv"))
print(tab.round(3).to_string(index=False)); print(pd.Series(summ).round(3).to_string())
