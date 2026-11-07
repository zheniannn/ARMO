"""Deterministic checks for the evidence figures (offline; data/processed + figures/generated).

Run:  python tests/test_evidence.py          (plain runner; writes figures/generated/test_results.csv)
  or  python -m pytest tests/test_evidence.py
Tests that need a file which is absent are reported BLOCKED, never PASS.
"""
import glob
import os
import sys
import traceback
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "figures")); sys.path.insert(0, os.path.join(ROOT, "code"))
import armo_evidence as ae  # noqa: E402
from common import PROC  # noqa: E402

GEN = os.path.join(ROOT, "figures", "generated")


class Blocked(Exception):
    pass


def need(path):
    if not os.path.exists(path):
        raise Blocked(f"missing {os.path.relpath(path, ROOT)}")
    return path


def test_cohort_partition():
    c = ae.era_cohort()
    assert len(c) == 979 and c.wban.nunique() == 107
    parts = [(~c.s1 & ~c.ni).sum(), (c.s1 & ~c.ni).sum(), (~c.s1 & c.ni).sum(), (c.s1 & c.ni).sum()]
    assert parts == [474, 134, 209, 162] and sum(parts) == 979


def test_no_duplicate_events():
    ev = ae.events_real()
    assert not ev.key.duplicated().any()
    f = pd.read_csv(need(os.path.join(PROC, "armo_event_capture_by_phase.csv")))
    assert len(f) == 979 * 5 * 8
    assert not f.duplicated(["wban", "t_ws", "design", "phase"]).any()


def test_bootstrap_reproducible():
    c = ae.era_cohort()
    x = c.fleet.to_numpy(float)
    a = ae.ci95(ae.boot_stat(c.wban, lambda i: x[i].mean(), n=300))
    b = ae.ci95(ae.boot_stat(c.wban, lambda i: x[i].mean(), n=300))
    assert a == b and a[0] < x.mean() < a[1]


def test_paired_gain_bounds():
    g = pd.read_csv(need(os.path.join(GEN, "capture_gain_paired_stats.csv"))).set_index("design")
    for d, r in g.iterrows():
        assert 0 <= r.gain_pp <= 100
        assert r.gain_ci_station_lo <= r.gain_pp <= r.gain_ci_station_hi
        assert r.gain_ci_station_and_phase_lo <= r.gain_pp <= r.gain_ci_station_and_phase_hi
        assert abs(r.combined_capture - r.fleet_capture - r.gain_pp / 100) < 1e-9
    assert abs(g.loc["D", "gain_pp"] - 29.903) < 0.01


def test_adding_satellite_never_reduces_capture():
    f = pd.read_csv(need(os.path.join(PROC, "armo_event_capture_by_phase.csv")))
    assert (f.combined_look >= f.fleet_look).all()
    piv = f.pivot_table(index=["wban", "t_ws", "phase"], columns="design", values="combined_look", aggfunc="first")
    assert (piv["D"] >= piv["A"]).all(), "design D contains design A's satellite"
    assert (piv["E"] >= piv["B"]).all(), "design E contains design B's satellite"


def test_swath_monotone_and_baseline():
    s = pd.read_csv(need(os.path.join(PROC, "armo_swath_event_capture.csv")))
    f = pd.read_csv(need(os.path.join(PROC, "armo_event_capture_by_phase.csv")))
    base = s[s["mode"] == "baseline"].set_index(["wban", "t_ws", "phase"]).combined_look
    dD = f[f.design == "D"].set_index(["wban", "t_ws", "phase"]).combined_look
    assert (base.sort_index() == dD.sort_index()).all(), "362 km scenario must equal design D"
    fx = s[s["mode"] == "fixed"].pivot_table(index=["wban", "t_ws", "phase"], columns="swath_km", values="combined_look", aggfunc="first")
    ws = sorted(fx.columns)
    for a, b in zip(ws, ws[1:]):
        assert (fx[b] >= fx[a]).all(), f"centred fixed strip {b} km must contain {a} km"
    for W, g in s[s["mode"] != "baseline"].groupby("swath_km"):
        m = g.set_index(["wban", "t_ws", "phase", "mode"]).combined_look
        assert (m.groupby(level=[0, 1, 2]).max().sort_index() <= base.sort_index()).all()


def test_smap_policies_consistent():
    sm = pd.read_csv(need(os.path.join(PROC, "smap_summary.csv")), index_col=0)
    assert sm.loc["capture_era", "all"] > sm.loc["capture_era", "recommended"]
    assert sm.loc["n_retrievals", "all"] > sm.loc["n_retrievals", "recommended"]
    qa = pd.read_csv(need(os.path.join(GEN, "quality_attrition_stats.csv")))
    v = lambda sensor: float(qa[(qa.sensor == sensor) & qa.stage.str.startswith("Real look")].value.iloc[0])
    assert abs(v("SMAP all quality") - sm.loc["capture_era", "all"]) < 0.002
    assert abs(v("SMAP recommended") - sm.loc["capture_era", "recommended"]) < 0.002


def test_realistic_sizing_matches_slides():
    """The spacecraft values on the slides come from code/06_mission_design.py realistic_sizing()."""
    r = pd.read_csv(need(os.path.join(PROC, "armo_sizing_realistic.csv"))).set_index("parameter").value
    assert r["elevation_beams"] == 11 and r["sspa_200w_units"] == 14
    assert round(r["wet_mass_per_satellite"]) == 316 and round(r["launch_mass_two_plus_adapter"]) == 672
    assert abs(r["rf_power_peak"] - 2759) < 1 and round(r["orbit_average_power"]) == 165
    assert round(r["usable_swath_30_45deg_incidence"]) == 221


def test_slide_numbers_match():
    """code/15_slide_numbers.py recomputes every analysis number in the submitted slides."""
    s = pd.read_csv(need(os.path.join(GEN, "slide_numbers.csv")))
    assert len(s) >= 70 and (s.status == "MATCH").all(), s[s.status != "MATCH"].claim.tolist()


def test_manifest_complete():
    m = pd.read_csv(need(os.path.join(ROOT, "figures", "figure_manifest.csv")))
    pngs = {os.path.basename(p) for p in glob.glob(os.path.join(ROOT, "figures", "*.png"))}
    assert pngs <= set(m.figure_file), f"unlisted figures: {sorted(pngs - set(m.figure_file))}"
    for sc in m.source_script.dropna():
        for part in sc.split(";"):
            part = part.strip()
            if part.startswith(("figures/", "code/")):
                assert os.path.exists(os.path.join(ROOT, part.split(" ")[0])), part
    for col in ("title", "status", "inputs", "cohort", "uncertainty", "finding", "placement"):
        assert m[col].notna().all(), f"manifest column {col} has gaps"


def test_anchors_match():
    a = pd.read_csv(need(os.path.join(GEN, "anchor_check.csv")))
    assert (a.status == "MATCH").all(), a[a.status != "MATCH"].anchor.tolist()


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    rows = []
    for t in TESTS:
        try:
            t(); st, msg = "PASS", ""
        except Blocked as e:
            st, msg = "BLOCKED", str(e)
        except AssertionError as e:
            st, msg = "FAIL", str(e) or traceback.format_exc(limit=1)
        except Exception as e:  # noqa: BLE001
            st, msg = "ERROR", repr(e)
        rows.append(dict(test=t.__name__, status=st, detail=msg))
        print(f"{st:8s} {t.__name__} {msg}")
    pd.DataFrame(rows).to_csv(os.path.join(GEN, "test_results.csv"), index=False)
    sys.exit(0 if all(r["status"] in ("PASS",) for r in rows) else 1)
