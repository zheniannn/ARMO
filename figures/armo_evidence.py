"""Shared, tested helpers for the evidence figures (fig_event_capture_severity.py, fig_capture_gain_paired_ci.py, ...).

Everything reads data/processed/ only (no internet). Conventions:
  * event key  = (wban, t_ws): station WBAN + start of the half-amplitude wetting window (unique; tested)
  * NISAR era  = events whose storm starts in [2026-06-17, 2026-11-01)  -> the matched 979-event cohort
  * uncertainty = station-cluster bootstrap (resample whole stations with replacement), seeded, 2,000 draws;
    paired statistics are computed inside each draw from the same resampled events, never from two separate CIs.
Evidence classes used in captions and the manifest: OBSERVED, SIMULATED, MODEL-BASED, REQUIREMENT, UNVALIDATED.
"""
import os
import sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "code"))
from common import PROC, FIG  # noqa: E402

GEN = os.path.join(HERE, "generated")
os.makedirs(GEN, exist_ok=True)
ERA = (pd.Timestamp("2026-06-17", tz="UTC"), pd.Timestamp("2026-11-01", tz="UTC"))
N_BOOT, SEED = 2000, 20261103
S1C, NIC = "cap_Sentinel-1 (NISAR era)", "cap_NISAR (NISAR era)"


def events_real():
    ev = pd.read_csv(os.path.join(PROC, "events_real.csv"), parse_dates=["t_start", "t_peak", "t_ws", "t_we"])
    ev["key"] = ev.wban.astype(str) + "|" + ev.t_ws.dt.strftime("%Y-%m-%dT%H")
    ev["era"] = (ev.t_start >= ERA[0]) & (ev.t_start < ERA[1])
    return ev


def era_cohort():
    """The matched NISAR-era cohort with boolean real-look flags (S1, NISAR, either)."""
    ev = events_real()
    c = ev[ev.era].reset_index(drop=True).copy()
    c["s1"] = c[S1C].astype(float) > 0
    c["ni"] = c[NIC].astype(float) > 0
    c["fleet"] = c.s1 | c.ni
    return c


def cluster_draws(groups, n=N_BOOT, seed=SEED):
    """Index arrays for n station-cluster bootstrap draws (same draws can be reused for paired statistics)."""
    groups = np.asarray(groups)
    keys = np.unique(groups)
    pos = {k: np.flatnonzero(groups == k) for k in keys}
    rng = np.random.default_rng(seed)
    for _ in range(n):
        yield np.concatenate([pos[k] for k in rng.choice(keys, keys.size)])


def boot_stat(groups, fn, n=N_BOOT, seed=SEED):
    """Array of fn(idx) over station-cluster draws; fn receives the resampled row indices."""
    return np.array([fn(idx) for idx in cluster_draws(groups, n, seed)])


def ci95(draws):
    lo, hi = np.nanpercentile(draws, [2.5, 97.5])
    return float(lo), float(hi)


def wilson(k, n, z=1.96):
    if n == 0:
        return np.nan, np.nan
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return c - h, c + h


def save(fig, name, pdf=True):
    """Save PNG (300 dpi) and, where practical, a vector PDF next to it in figures/."""
    fig.savefig(os.path.join(FIG, name + ".png"), dpi=300)
    if pdf:
        fig.savefig(os.path.join(FIG, name + ".pdf"))


def write_stats(name, rows):
    """Write a tidy statistics table (list of dicts) to figures/generated/<name>.csv and return it."""
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(GEN, name + ".csv"), index=False)
    return df
