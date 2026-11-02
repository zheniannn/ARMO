"""ARMO spacecraft sizing: antenna, radar power, data volume, power and mass budgets, launch and a rough-order cost.

Physics (first-order, conservative; Ulaby et al. 2014; Freeman et al. 2000):
  antenna area   A >= 4 v lambda R tan(theta_i) / c            (range/azimuth ambiguity constraint, single beam)
  noise floor    NESZ = 16 pi R^3 v k T F L B lambda sin(theta_i) / (P_avg A^2 c)
                 (SAR radar equation for a distributed target, G = 4 pi A / lambda^2; solved for P_avg)
Orbit and imaging time come from the step-09 orbit model (design D: 620 km dawn-dusk SSO, 25-45 deg off-nadir, CONUS
imaging duty from armo_designs.csv). Every engineering assumption is listed in ASSUME and printed; values without a
public source are our estimates, not facts. Outputs: data/processed/armo_sizing.csv, armo_mass.csv, armo_cost.csv
"""
import os
import numpy as np
import pandas as pd
from common import PROC

MU, RE, C, KB = 398600.4418, 6371.0, 2.998e8, 1.380649e-23
H_KM, F_HZ = 620.0, 1.2575e9                  # orbit altitude; L-band centre (EESS 1215-1300 MHz)
LAM = C / F_HZ
ASSUME = dict(
    nesz_req_db=-25.0,       # 2 dB better than NISAR's ~-23 dB requirement (NISAR team, Fringe 2026)
    bandwidth_hz=20e6,       # range bandwidth: ~7.5 m slant resolution, multi-looked to 100-200 m products
    noise_fig_loss_db=6.0,   # receiver noise figure + system/processing losses (assumption)
    scansar_margin_db=3.0,   # extra margin for ScanSAR bursts and scalloping (assumption)
    tx_duty=0.10,            # transmit duty cycle (assumption, typical solid-state SAR)
    sspa_eff=0.35,           # GaN power-amplifier DC-to-RF efficiency (assumption)
    radar_elec_w=150.0,      # receivers, digital electronics, data storage while imaging (assumption)
    bus_w=150.0,             # bus orbit-average power: ADCS, C&DH, thermal, comms standby (assumption)
    xband_w=60.0, xband_rate_bps=400e6,   # downlink transmitter power and rate (assumption, commercial X-band radio)
    bits=4, rx_duty=0.7, n_pol=2,         # BAQ 4-bit samples, receive-window duty, HH + HV
    array_eff=0.28, packing=0.85, degr=0.85, margin_power=1.3,   # solar cells, packing, end-of-life, margin
    max_pass_min=10.0, dod=0.3,           # longest CONUS imaging pass; battery depth of discharge (assumption)
    reflector_kg_ref=8.0, reflector_d_ref=3.35,   # mesh reflector < 8 kg at 3.35 m (Sushko et al., EUSAR 2021)
    mass_margin=0.30,        # mass growth allowance at concept stage (assumption)
    dv_ms=120.0, isp_s=220.0,  # phasing to 180 deg, drag make-up, de-orbit within 5 years (estimate); hydrazine Isp
)


def geom(eta_deg, h=H_KM):
    """Slant range (m) and incidence angle (rad) for off-nadir angle eta on a spherical Earth."""
    r, e = RE + h, np.deg2rad(eta_deg)
    R = r * np.cos(e) - np.sqrt(RE ** 2 - (r * np.sin(e)) ** 2)
    th = np.arcsin(r * np.sin(e) / RE)
    return R * 1e3, th


def main():
    a = ASSUME
    v = np.sqrt(MU / (RE + H_KM)) * 1e3
    D = pd.read_csv(os.path.join(PROC, "armo_designs.csv"))
    duty_conus = float(D[D.design.str.startswith("D")].imaging_duty_conus.iloc[0])
    rows = {}
    for eta in (25, 35, 45):
        R, th = geom(eta)
        rows[eta] = dict(R_km=R / 1e3, inc_deg=np.rad2deg(th), A_min_m2=4 * v * LAM * R * np.tan(th) / C)
    A_min = rows[45]["A_min_m2"]                      # worst case: far edge of the access range
    D_refl = np.ceil(np.sqrt(4 * A_min / np.pi) * 10) / 10   # reflector diameter meeting it, rounded up 0.1 m
    A = np.pi * D_refl ** 2 / 4
    FL = 10 ** ((a["noise_fig_loss_db"] + a["scansar_margin_db"]) / 10); nesz = 10 ** (a["nesz_req_db"] / 10)
    R45, th45 = geom(45)
    P_avg = 16 * np.pi * R45 ** 3 * v * KB * 290 * FL * a["bandwidth_hz"] * LAM * np.sin(th45) / (nesz * A ** 2 * C)
    P_peak = P_avg / a["tx_duty"]
    radar_dc = P_avg / a["sspa_eff"] + a["radar_elec_w"]
    # data
    rate = a["n_pol"] * 1.2 * a["bandwidth_hz"] * 2 * a["bits"] * a["rx_duty"]       # bit/s while imaging
    img_s_day = duty_conus * 86400
    vol_bits = rate * img_s_day
    dl_s = vol_bits / a["xband_rate_bps"]
    # power
    orbit_avg = a["bus_w"] + radar_dc * duty_conus + a["xband_w"] * dl_s / 86400
    array_m2 = orbit_avg * a["margin_power"] / (1361 * a["array_eff"] * a["packing"] * a["degr"])
    batt_wh = (radar_dc + a["bus_w"]) * a["max_pass_min"] / 60 / a["dod"]
    siz = dict(v_ms=v, lambda_m=LAM, **{f"R_{k}_km": r["R_km"] for k, r in rows.items()},
               **{f"inc_{k}_deg": r["inc_deg"] for k, r in rows.items()}, **{f"Amin_{k}_m2": r["A_min_m2"] for k, r in rows.items()},
               reflector_d_m=D_refl, antenna_area_m2=A, P_avg_rf_w=P_avg, P_peak_rf_w=P_peak, radar_dc_w=radar_dc,
               data_rate_mbps=rate / 1e6, imaging_min_day=img_s_day / 60, data_gb_day=vol_bits / 8e9,
               downlink_min_day=dl_s / 60, orbit_avg_w=orbit_avg, array_m2=array_m2, battery_wh=batt_wh,
               duty_conus=duty_conus)
    # mass budget per satellite (current best estimate, kg)
    refl = a["reflector_kg_ref"] * (D_refl / a["reflector_d_ref"]) ** 2
    m = [("L-band mesh reflector (scaled by area from < 8 kg at 3.35 m)", refl, "Sushko et al. (2021), scaled"),
         ("Deployable boom and dual-pol L-band feed array", 18.0, "estimate"),
         ("SAR electronics: GaN amplifiers, receivers, digital, storage", 25.0, "estimate"),
         ("Structure and mechanisms", 45.0, "estimate"),
         (f"Power: {array_m2:.1f} m² array, {batt_wh:.0f} Wh battery, PCDU", 22.0, "estimate"),
         ("Attitude control: wheels, star trackers, magnetorquers", 18.0, "estimate"),
         ("Command and data handling; X-band downlink; S-band TT&C", 10.0, "estimate"),
         ("Thermal, harness", 12.0, "estimate"),
         ("Propulsion (dry)", 8.0, "estimate")]
    dry_cbe = sum(x[1] for x in m)
    dry = dry_cbe * (1 + a["mass_margin"])
    prop = dry * (np.exp(a["dv_ms"] / (9.80665 * a["isp_s"])) - 1)
    wet = dry + prop
    mass = pd.DataFrame(m, columns=["item", "kg", "basis"])
    mass = pd.concat([mass, pd.DataFrame([
        ("Dry mass, current best estimate", dry_cbe, "sum"),
        (f"Dry mass with {a['mass_margin']:.0%} growth margin", dry, "AIAA-style concept margin (assumption)"),
        (f"Propellant ({a['dv_ms']:.0f} m/s, Isp {a['isp_s']:.0f} s)", prop, "rocket equation"),
        ("Wet mass per satellite", wet, ""),
        ("Two satellites at launch", 2 * wet, "")], columns=["item", "kg", "basis"])], ignore_index=True)
    siz.update(dry_cbe_kg=dry_cbe, dry_kg=dry, prop_kg=prop, wet_kg=wet, launch_kg=2 * wet)
    # cost (FY2026 US$ M), rough order of magnitude (+-40 %)
    sal, idc = 101_920, 0.62                                   # BLS median geoscientist; MIT F&A rate (Section 5)
    fte = lambda n, yrs: n * sal * (1 + idc) * yrs / 1e6
    gs_min_day = 2 * siz["downlink_min_day"] * 1.5            # both satellites, 50 % pass-overhead margin
    cost = [("A-D", "PI, science team and algorithm development (3 FTE, 5 yr)", fte(3, 5), "BLS salary + 62 % F&A"),
            ("A-D", "Flight system: 2 spacecraft with L-band SAR (first unit incl. development 45, second 25)", 70.0,
             "Analogy: NovaSAR-1 ≈ £45 M build + launch (2011); CYGNSS US$ 102 M excl. launch (8 microsats)"),
            ("A-D", "Project management, systems engineering, mission assurance, integration and test (20 %)", 14.0, "estimate"),
            ("A-D", "Ground and science data systems", 6.0, "estimate"),
            ("A-D", "Launch: one dedicated small launcher for both satellites", 15.0, "Firefly Alpha class (≈ US$ 15 M, secondary sources)"),
            ("E", "Mission operations team (6 FTE, 3 yr)", fte(6, 3), "BLS salary + 62 % F&A"),
            ("E", "Sustaining engineering, software and ground-system maintenance (3 yr)", 3.0, "estimate"),
            ("E", f"Ground-station contacts ({gs_min_day:.0f} min/day at ≈ US$ 20/min, 3 yr)", gs_min_day * 365 * 3 * 20 / 1e6, "estimate (commercial ground-station pricing)"),
            ("E", "Science team, processing and open data distribution (3 FTE + cloud, 3 yr)", fte(3, 3) + 0.3, "BLS salary + 62 % F&A; AWS")]
    cost = pd.DataFrame(cost, columns=["phase", "item", "usd_m", "basis"])
    ad = cost[cost.phase == "A-D"].usd_m.sum(); e = cost[cost.phase == "E"].usd_m.sum()
    cost = pd.concat([cost, pd.DataFrame([("A-D", "Reserve, 30 % of Phases A-D", 0.30 * ad, "assumption (EVM-3 AO sets reserve rules)"),
                                          ("E", "Reserve, 15 % of Phase E", 0.15 * e, "assumption")],
                                         columns=cost.columns)], ignore_index=True)
    siz.update(cost_AD=cost[cost.phase == "A-D"].usd_m.sum(), cost_E=cost[cost.phase == "E"].usd_m.sum())
    siz["cost_total"] = siz["cost_AD"] + siz["cost_E"]
    # threshold mission (design C, one satellite): drop the second flight unit, its 20 % wrap and its 30 % reserve
    siz["cost_threshold"] = siz["cost_total"] - 25.0 * 1.2 * 1.3
    siz["flight_share"] = 70.0 / siz["cost_total"]
    siz["evm_cap"] = 190.0
    pd.DataFrame([siz]).to_csv(os.path.join(PROC, "armo_sizing.csv"), index=False)
    mass.to_csv(os.path.join(PROC, "armo_mass.csv"), index=False)
    cost.to_csv(os.path.join(PROC, "armo_cost.csv"), index=False)
    print(pd.Series(siz).round(3).to_string()); print(mass.round(1).to_string()); print(cost.round(2).to_string())


if __name__ == "__main__":
    main()
