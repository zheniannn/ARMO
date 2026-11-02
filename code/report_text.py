"""Proposal text. Every number is formatted from V (computed from results in data/processed)."""
import math
import pandas as pd


def f0(x): return f"{x:.0f}"
def f1(x): return f"{x:.1f}"
def f2(x): return f"{x:.2f}"
def f3(x): return f"{x:.3f}"


def has(V, k): return k in V and V[k] is not None and not (isinstance(V[k], float) and math.isnan(V[k]))


# Budget (USD), every line sourced in Section 5
BLS_MEDIAN = 101_920            # BLS OOH, geoscientists, May 2025 median
PERS = round(BLS_MEDIAN * 0.6)  # 0.5 FTE analyst + 0.1 FTE PI
EC2 = 0.384 * 2000              # m6i.2xlarge on-demand, 2,000 h/yr
S3 = 0.023 * 2048 * 12          # 2 TB S3 Standard, 12 months
COMP = round(EC2 + S3)
SENSORS = 12 * 545              # 12 HydraProbe sensors (2 sites x 2 profiles x 3 depths)
APC = 2160                      # IEEE JSTARS APC (IEEE 2026 APC list)
AGU = 755 + 70                  # AGU registration (AGU 2024 in-person early-bird member) + abstract fee
Y1 = dict(pers=PERS, data=0, comp=COMP, field=0, travel=0)
Y2 = dict(pers=PERS, data=0, comp=COMP, field=SENSORS, travel=APC + AGU)
IDC = 0.62


def budget():
    d1, d2 = sum(Y1.values()), sum(Y2.values())
    i1, i2 = d1 * IDC, d2 * IDC
    return d1, d2, i1, i2, d1 + i1, d2 + i2


def money(x): return f"{x:,.0f}"


def write(doc, V):
    d1, d2, i1, i2, t1, t2 = budget()
    TOTAL = t1 + t2
    nis = has(V, "nis_n_rec")
    H = V["h2h"].capture * 100                                   # each system alone / combined, same 979 events
    dlo, dhi = sorted([V['nis_P_detect_hh_valid_1sigma'] * 100, V['nis_P_detect_sat_valid_1sigma'] * 100])
    a1, n1 = H["ARMO alone (design D)"], H["NISAR alone"]
    r6, r3 = H["ROSE-L alone, 6-day"], H["ROSE-L alone, 3-day"]
    Dp = V["depth"]
    SZ, CO = V["siz"], V["cost"]
    D0 = V["designs"].set_index(V["designs"].design.str[0])

    doc.cover([
        "Earth System Science Pathfinder: Earth Venture Mission (EVM) class; science: ROSES A.17 Terrestrial Hydrology",
        f"Stage 1 (now): US$ {money(TOTAL)} retrieval study (Table 8). Stage 2: ARMO mission ≈ US$ {SZ.cost_total:.0f} M "
        "incl. launch, operations and 30 % reserve (Table 9)",
        "Stage 1: 2 years (2027–2028). Stage 2: 5-year development to launch (≈ 2033) and a 3-year science mission",
        "5 November 2026",
        "Do field-scale radars blink through the rain? Ground-truth evaluation of Sentinel-1 and NISAR revisit "
        "against 3,340 soil-moisture wetting events at 120 U.S. Climate Reference Network stations, and requirements "
        "for ARMO, a targeted L-band revisit mission",
        "Tang Zhen Ian [confirm]",
        "[Group members to be added]",
        "Water Resources; Agriculture and Food Security",
    ])
    doc.page_break()

    # ================================================================ 1
    doc.h1("1 Scientific/Technical Merit & Objectives")
    doc.para(
        "Every rain storm writes a brief signal into the top few centimetres of soil: moisture jumps within hours, "
        "then drains and evaporates over the following days. That transient state decides how much of the next storm "
        "runs off, how much water a crop actually received, and how the land surface feeds back on the weather. "
        "Field-scale (≤ 200 m) soil moisture can be mapped from orbit only by synthetic aperture radar (SAR); "
        "L-band radiometers such as SMAP revisit every 2–3 days but see ~40 km footprints. SAR missions revisit a "
        "given field only every 6–12 days. If wetting events fade within one or two days, the field-scale radar fleet "
        "is blind to most of them however accurate each image is. Before arguing for a new satellite, we test that "
        "concern against independent hourly ground truth.")
    doc.para("**Primary objective:** Our primary objective is to determine whether today's field-scale radar fleet "
             "(Sentinel-1 and NISAR) observes the rain-driven wetting events that dominate near-surface soil-moisture "
             "variability across the contiguous United States and, if not, what revisit a dedicated L-band mission "
             "(ARMO, the Agricultural Rapid Moisture Observatory) would need to capture at least 80 % of them.")
    doc.para(
        "**Hypotheses.** H1: rain-driven 5 cm wetting events are shorter than the revisit of today's field-scale radar "
        "fleet, so the fleet misses most of them. H2: when an event is sampled, its signal is smaller than the change "
        "noise of current radar retrievals. H3: a dedicated L-band revisit mission would raise event capture to ≥ 80 %. "
        "They address the 2017 Decadal Survey hydrology question H-4 (\"how do we improve preparedness and mitigation "
        "of water-related extreme events?\"; objectives H-4b flash floods and H-4c drought monitoring) and Targeted "
        "Observable TO-17 *Soil Moisture*, which the survey left unallocated because the programme of record \"does not "
        "include coverage after SMAP and SMOS\" (National Academies, 2018). **Proposal type:** two stages: a 2-year "
        "retrieval study, then an Earth Venture-class flight mission. It measures the problem against ground truth, "
        "derives what ARMO must achieve, and sizes and costs the spacecraft.")
    objs = [
        f"**Measure** the duration and amplitude of rain-driven 5 cm wetting events from hourly in-situ ground truth at "
        f"{V['n_stations']} NOAA USCRN stations (warm seasons 2025–2026).",
        "**Quantify** the fraction of these events captured by regular 1–12-day revisits and by the *actual* "
        "2025–2026 Sentinel-1 and NISAR acquisition records.",
        "**Test observability:** compare Sentinel-1 C-band backscatter, NISAR L-band soil moisture, the SMAP L-band "
        "radiometer and a no-satellite model (ERA5-Land) against ground truth when an event is sampled, by vegetation cover.",
        "**Derive** the revisit and noise requirements and the marginal value of ARMO over current and planned "
        "missions, and decide (YES / CONDITIONAL / NO) whether a new satellite is justified.",
    ]
    for i, o in enumerate(objs, 1):
        doc.bullet(o, num=i)
    doc.para(
        f"**Key finding.** Half of all wetting events stay above half their peak for less than {f1(V['win_med_d'])} days. "
        f"Even if every look were a perfect measurement, the combined 2026 Sentinel-1 + NISAR fleet captured only "
        f"{f0(V['cur'])} % (95 % CI {f0(V['cur_lo'])}–{f0(V['cur_hi'])} %) of {V['n_era']:,} events; "
        f"≥ 80 % needs a regular ≈ {f1(V['R80'])}-day revisit on its own, or a 2-day ARMO added to today's fleet. "
        + f"When sampled, Sentinel-1 registered {f0(V['s1_P_detect_given_sampled_1sigma'] * 100)} % of events and NISAR "
        f"{f0(dlo)}–{f0(dhi)} %; 70 % needs change noise ≤ {f3(V['snr_noise_req_70'])} m³/m³, a "
        f"{V['snr_now_db_L'] / V['snr_req_db_L']:.1f}-fold reduction at L-band. Two L-band smallsats would lift fleet "
        f"capture to {V['designs'].set_index(V['designs'].design.str[0]).loc['D', 'capture_fleet_plus_armo'] * 100:.0f} %. "
        f"**Scored alone on the same events, ARMO captures {f0(a1)} %, against {f0(n1)} % for NISAR and "
        f"{f0(r6)}–{f0(r3)} % for ROSE-L** (6- or 3-day revisit); at its detection requirement it would register "
        f"{f0(a1 * 0.7 / (n1 * dhi / 100))}–{f0(a1 * 0.7 / (n1 * dlo / 100))}× as many events as NISAR does today. With ROSE-L (≥ 2030) at ESA's "
        f"documented 6-day revisit the fleet reaches {f0(V['fut'])} % and ARMO still adds "
        f"{f0(V['fut3'] - V['fut'])}–{f0(V['fut2'] - V['fut'])} points. **We therefore propose ARMO in "
        f"two stages.** Stage 1 funds event-level retrieval research now (US$ {money(TOTAL)}, 2 years); its result sets "
        f"how capable ARMO's sensor must be. Stage 2 builds and launches ARMO either way: two ≈ {SZ.wet_kg:.0f} kg L-band "
        f"smallsats on one launcher, ≈ US$ {SZ.cost_total:.0f} M including launch, operations and a 30 % reserve, inside "
        f"the US$ 190 M Earth Venture Mission cap. If retrieval succeeds, ARMO registers 4–6× NISAR's events; if not, its "
        f"revisit alone still doubles them (Section 3.4).",
        after=4)

    # ================================================================ 2
    doc.h1("2 Background & Motivation")
    doc.para(
        "**Physical basis.** Microwave backscatter from soil is controlled by its dielectric constant, which rises from "
        "~3–5 for dry soil to > 20 for wet soil because liquid water has εᵣ ≈ 80 (Ulaby et al., 2014). "
        "For bare or sparsely vegetated surfaces σ⁰ in dB increases roughly linearly with volumetric soil "
        "moisture, which is the basis of change detection: with roughness and vegetation nearly constant between two "
        "looks from the same orbit, a backscatter increase maps to wetting (Wagner et al., 1999; Bauer-Marschallinger "
        "et al., 2019). Vegetation adds volume scattering and attenuates the soil signal; the effect is far stronger at "
        "C-band (5.4 GHz, λ ≈ 5.6 cm; senses ~1–2 cm) than at L-band (1.26 GHz, λ ≈ 24 cm; ~5 cm), "
        "which is why soil-moisture missions favour L-band (Entekhabi et al., 2010; Kim et al., 2017). "
        "SAR achieves 10–200 m resolution by aperture synthesis, but its swath (~250 km) is a small fraction of the "
        "orbit-to-orbit spacing (Luo et al., 2017), so a single SAR revisits a site only every 6–12 days (ESA, 2026; "
        "NISAR Science Team, 2023).")
    doc.para(
        "**What is known.** Satellite drydown studies find exponential decay time scales of a few days, shorter over "
        "sandier and more arid soils (McColl et al., 2017; Jiang et al., 2025), and SMAP dries faster than in-situ probes because it senses a thinner layer "
        "(Shellito et al., 2016). SMAP's 3-day revisit requirement was tied to inter-storm periods at 10–40 km "
        "(Entekhabi et al., 2010). At field scale, irrigation-detection studies show that ≤ 2–4-day sampling is "
        "needed (Le Page et al., 2020; Filippucci et al., 2020; Zappa et al., 2022), and 6-day Sentinel-1 sampling "
        "cannot separate an old heavy storm from recent light rain (Bazzi et al., 2019). Sentinel-1 backscatter has "
        "been regressed against USCRN data (Chatterjee et al., 2020). NISAR (launched 30 July 2025) now distributes a "
        "free 200 m L-band soil-moisture product (SME2) with an accuracy *goal* of 0.06 m³/m³ where vegetation "
        "water content < 5 kg/m², provided about twice per 12 days (NISAR Science Team, 2023; ASF, 2026). "
        "ESA's two-satellite ROSE-L targets a revisit of 6 days over global land and 3 days over Europe (Davidson, "
        "2023; Davidson et al., 2026; a secondary summary lists 3 days for soil moisture, eoPortal, 2026) and is "
        "listed for launch ≥ 2030 (WMO OSCAR, 2026).")
    doc.para(
        "**Knowledge gap.** Existing revisit studies concern irrigation at one or a few sites, often by synthetic "
        "subsampling of in-situ series (Filippucci et al., 2020; Zappa et al., 2022; Le Page et al., 2020). We found no multi-climate quantification of how many *rain-driven* "
        "wetting events the *actual* field-scale radar fleet captures, measured against hourly ground truth, nor any "
        "estimate of what a new mission would add once NISAR and ROSE-L are counted. Without those numbers, neither "
        "ROSE-L's revisit nor a new mission can be traced to an observed requirement. Table 1 summarises the "
        "capabilities that any new mission must beat.")
    doc.table(
        "Existing and planned soil-moisture-relevant missions (operational status as of November 2026). Sources: "
        "mission pages listed in References.",
        ["Mission (agency)", "Status", "Sensor", "SM / backscatter resolution", "Revisit (mid-latitude)", "Key limitation for field-scale events"],
        [["SMAP (NASA)", "Operating since 2015; radar failed 2015", "L-band radiometer", "~40 km (9 km grid)", "2–3 d", "Too coarse for fields"],
         ["Sentinel-1C/1D (ESA/EU)", "Operating; 1A ended operations Jun 2026", "C-band SAR", "5 × 20 m; no official SM product outside Europe", "6 d pair, 12 d per satellite", "C-band attenuated by crops"],
         ["NISAR (NASA–ISRO)", "Launched Jul 2025; provisional data since Jun 2026", "L- + S-band SAR", "SME2 200 m", "12 d repeat; SM ~2 per 12 d", "Revisit; provisional accuracy"],
         ["ROSE-L (ESA)", "Planned, launch ≥ 2030", "L-band SAR (2 sats)", "SM goal 25–50 m", "6 d global land; 3 d Europe", "Not yet in orbit"],
         ["SAOCOM-1A/1B (CONAE)", "Past 5-yr design life", "L-band SAR", "10–100 m", "8 d pair", "Restricted access"],
         ["ALOS-4 (JAXA)", "Operating since 2024", "L-band SAR", "3 m (200 km swath)", "14 d", "Limited free data, no SM product"],
         ["CIMR (ESA)", "Planned 2029", "Multi-band radiometer", "L-band ~58 km", "~daily", "Coarse"],
         ["BIOMASS (ESA)", "Launched Apr 2025", "P-band SAR (435 MHz)", "Forest products 200 m", "Global map every 228 d", "Barred over N. America (SOTR)"],
         ["Spire; Planet (commercial)", "Operating", "Models from GNSS-R, radiometers", "500 m; 1 km (100 m discontinued)", "Daily", "Modelled from coarse sensors; closed"]],
        [2.6, 2.6, 2.0, 2.7, 2.3, 3.6], size=7.5)
    doc.para(
        f"**ARMO's niche.** No open, all-weather system observes field-scale (≤ 200 m) soil moisture faster than "
        f"every ~6 days over the US. NISAR's 200 m product matches ARMO's resolution but not its revisit; commercial "
        f"daily products are modelled from 9 km or coarser sensors and are not open (Spire, 2024; Planet, 2026); "
        f"P-band SAR may not operate over North America (Quegan et al., 2019); and optical sensors get a clear look "
        f"inside only {f0(V['opt_daily'])} % of event windows even when imaging daily (Section 3.4). ARMO's novelty is "
        f"therefore revisit, not resolution: NISAR-class L-band retrieval at ≈ 1.4-day sampling, matched to events "
        f"that last {f1(V['win_med_d'])} days.")
    doc.para(
        f"**Study area.** We use the NOAA U.S. Climate Reference Network (USCRN; Bell et al., 2013), the most rigorous "
        f"open soil-moisture network available: triplicate probes at 5 cm, hourly reporting, co-located rain gauges and "
        f"soil temperature. USCRN is used to *validate*, not calibrate, satellite products, so it is independent of "
        f"every retrieval tested here. Its {sum(V['n_lc'].values())} qualifying stations ({V['n_stations']} with wetting events) span arid rangeland to humid forest "
        f"(Figure 1b), so a requirement derived from them is not tied to one climate. By ESA WorldCover, "
        f"{V['n_lc'].get('Grassland', 0)} stations sit in grassland, {V['n_lc'].get('Tree cover', 0)} in tree cover and "
        f"only {V['n_lc'].get('Cropland', 0)} in cropland (Section 3.4).")
    NE = V["need"]
    doc.para(
        f"**Where the need is (Figure 1).** Mapped in Earth Engine and calibrated with USCRN, Sentinel-1's actual 2026 "
        f"revisit is {NE.conus_R_s1_median:.1f} days at the median cell and 8–16 days over much of the Midwest and East "
        f"(a), where gridMET storms (Abatzoglou, 2013) bring the most wetting events (b). Sentinel-1 misses "
        f"≈ {NE.conus_missed_median:.0f} events per season at the median cell (c) and ≈ {NE.crop_missed_median:.0f} on "
        f"cropland, where ARMO would recover ≈ {NE.crop_gain_median:.0f}, mostly in the Corn Belt and Mississippi Delta "
        f"(d; MODIS MCD12Q1, Friedl and Sulla-Menashe, 2022): the longest gaps fall where events and farms are densest.",
        after=2)
    doc.figure("fig7_need_maps.png", 14.0,
               "The need, mapped in Google Earth Engine at 0.1° and calibrated with USCRN ground truth; each panel's "
               "caption gives its data and method. Panel b also shows the 120 USCRN stations of this study.")

    # ================================================================ 3
    doc.h1("3 Methodology & Work Plan")
    doc.para(
        "The analysis has three phases (Table 7 gives the two-stage schedule). This proposal reports the completed proof of concept "
        "(Phases 1–3 applied to the warm seasons of 2025 and 2026); the funded work extends it (Section 3.4).")
    doc.h2("3.1 Phase 1: Data Assembly and Pre-processing")
    doc.table(
        "Datasets. All are free; NISAR downloads need a NASA Earthdata login and the Earth Engine (GEE) products a "
        "free non-commercial Earth Engine account.",
        ["Dataset / product", "Variable and resolution", "Dates used", "Access", "Why chosen"],
        [["NOAA USCRN hourly02", "5 cm SM (m³/m³, mean of 3 probes), rain (mm), soil T; point, hourly",
          "Apr–Oct 2025, 2026", "NCEI HTTPS (open)", "Independent ground truth"],
         ["Sentinel-1 GRD catalogue", "Acquisition time, platform, orbit", "Mar 2025–Oct 2026",
          "Planetary Computer STAC (anonymous)", "Actual C-band revisit"],
         ["Sentinel-1 RTC", "γ⁰ VV, VH; 10 m (11 × 11 px window)", "Apr–Oct 2025, 2026",
          "Planetary Computer (anonymous token)", "C-band observability"],
         ["NISAR L3 SME2 / L2 GCOV", "Times, tracks; SM 200 m; L-band σ⁰ HH, HV",
          "Oct 2025–Oct 2026", "CMR (open) / ASF (Earthdata login)", "Actual L-band revisit and accuracy"],
         ["SMAP Enhanced L3 V006", "SM 9 km grid, 06:00 and 18:00 passes; quality flag; vegetation water content",
          "Apr–Oct 2025, 2026", "Google Earth Engine", "Frequent but coarse L-band benchmark"],
         ["MODIS MOD13Q1 V6.1; ESA WorldCover 2021; USDA CDL 2025", "NDVI 250 m, 16-day; land cover 10 m; crop type 30 m",
          "2021–2026", "Google Earth Engine", "Vegetation at each event and station"],
         ["gridMET; Sentinel-1 GRD; MODIS MCD12Q1 V6.1", "Daily rain 4 km; S1 acquisition days; land cover 500 m",
          "Apr–Oct 2025, 2026; 2024", "Google Earth Engine", "CONUS need maps (Figure 1)"],
         ["ERA5-Land (Open-Meteo)", "0–7 cm SM, 9 km, hourly; ERA5 rain", "Apr–Oct 2025, 2026",
          "Open-Meteo archive API", "No-satellite baseline"]],
        [3.0, 4.4, 2.3, 3.2, 2.9], size=7.5)
    doc.para(
        f"**Pre-processing.** (i) NOAA files contained runs of NUL bytes that silently corrupted parsing; we strip them "
        f"and keep only well-formed 38-field records. (ii) Missing-value sentinels are removed and SM outside "
        f"0–0.6 m³/m³ is rejected. (iii) Hours with 5 cm soil temperature ≤ 1 °C are masked, because "
        f"frozen water invalidates both the probe and the radar dielectric signal. (iv) A station-season is kept only "
        f"with ≥ 70 % valid hours, leaving {V['n_ss']} station-seasons. (v) Gaps ≤ 3 h are interpolated; longer "
        f"gaps are left empty. (vi) Each satellite look is matched to the hour-ending USCRN value that follows it, and "
        f"looks with rain in the preceding 3 h are excluded (wet canopy and ponding). (vii) Adjacent catalogue frames "
        f"of one pass are merged into one look. The warm season avoids snow and frozen soil; 2025 and 2026 bracket "
        f"the arrival of Sentinel-1C/1D and NISAR.")

    doc.h2("3.2 Phase 2: Analysis")
    doc.figure("fig2_workflow.png", 12.5, "Analysis workflow from data to mission decision.")
    doc.para(
        f"**Wetting events (O1).** A storm is a run of hours with ≥ 0.2 mm rain, with gaps < 24 h merged; it is an "
        f"event if total rain ≥ 5 mm and 5 cm SM rises by A ≥ 0.03 m³/m³ above its 3-h pre-storm mean "
        f"(a rise comparable to retrieval targets of 0.04–0.06 m³/m³). These thresholds were fixed before any "
        f"satellite data were examined and are varied in a sensitivity test. The *event window* W is the time "
        f"during which the anomaly stays ≥ 50 % of A; a second definition uses an absolute anomaly ≥ 0.03 m³/m³. "
        f"Windows are censored at the next storm, because a later look would see a different event.")
    doc.para(
        f"**Capture (O2).** An event is *captured* if at least one acquisition falls inside its window. This is an upper "
        f"bound on detection, since it assumes a perfect sensor. For regular revisits R = 1–12 days we average over "
        f"every start-day phase and both dawn and dusk overpasses (all missions here fly dawn–dusk orbits). For a "
        f"randomly phased periodic sampler the expected capture is E[min(1, W/R)], which we use as an analytical check. "
        f"For the real fleet we use the actual 2025–2026 acquisition times over each station. The decisive "
        f"*marginal-value* test (O4) adds a regular ARMO schedule, at random phase, to the real 2026 fleet and to a "
        f"future fleet that includes ROSE-L at ESA's documented 6-day revisit over global land (3 days, planned only "
        f"for Europe, as an optimistic check).")
    doc.para(
        f"**Observability (O3).** Within each station × relative orbit (fixed geometry), we compute the temporal "
        f"correlation of Sentinel-1 σ⁰VV with 5 cm SM, the backscatter noise floor from same-orbit pairs with "
        f"|ΔSM| < 0.01 m³/m³, and the probability that an event sampled inside its window raises σ⁰ above "
        f"that noise (1σ). The same tests are applied to NISAR SME2 soil moisture and L-band σ⁰HH (same track), and to "
        f"SMAP (same overpass, ≤ 3.5 days apart), together with absolute accuracy (bias, unbiased RMSE). Detection is "
        f"split by MODIS NDVI at the event and by land cover. To turn detection into a requirement, we model a sampled "
        f"event of size A as detected with probability Φ(kA/n − 1), where n is the sensor's change noise in "
        f"soil-moisture units and k a single factor fitted across all four sensors. ERA5-Land events are detected with "
        f"the same rules on its own SM and rainfall and matched to ground truth within ± 24 h (POD, FAR, CSI).")
    doc.para(
        "**Uncertainty and validation.** Confidence intervals come from a 2,000-member cluster bootstrap over stations, "
        "because events at one station are not independent. 2025 serves as development data and 2026 as an independent "
        "holdout. Nine alternative event definitions test threshold dependence. **Beyond the tutorials:** cloud-native "
        "range reads of Sentinel-1 COGs and NISAR HDF5 at 120 stations (no full scenes downloaded), Earth Engine "
        "time-series extraction, event-based sampling theory checked against simulation, real-schedule mission "
        "emulation, a cross-sensor detection model, and bootstrap inference.")

    doc.h2("3.3 Phase 3: Results and Synthesis")
    doc.para(
        f"**O1: Wetting events are short.** We detected {V['n_events']:,} events at {V['n_stations']} stations. The "
        f"median event peaked {f0(V['rise_med_h'])} h after rain began and rose by {f3(V['amp_med'])} m³/m³. Its "
        f"half-amplitude window lasted {f1(V['win_med_d'])} days (interquartile range {f1(V['win_q1_d'])}–"
        f"{f1(V['win_q3_d'])} d), and {f0(V['frac_lt2d'])} % of events lasted < 2 days (Figure 3, Figure 4a). The "
        f"absolute-threshold window was longer (median {f1(V['winabs_med_d'])} d). These are event-level half-lives at "
        f"5 cm, not the exponential drydown time scales fitted to satellite data, so the two are not directly "
        f"comparable.", after=2)
    doc.figure("fig3_stillwater_example.png", 13.5,
               "Example from Stillwater 2 W, Oklahoma. Most wetting windows (shaded) fall between Sentinel-1 (orange) and "
               "NISAR (violet) looks. NISAR's three tracks over this site give looks in pairs on consecutive days, "
               "followed by multi-day gaps.")
    doc.para(
        f"**O2: The fleet misses about half of all events.** Regular sampling captures {f0(V['c1'])} % of events at "
        f"1 day, {f0(V['c2'])} % at 2 days, {f0(V['c3'])} % at 3 days, {f0(V['c6'])} % at 6 days and {f0(V['c12'])} % "
        f"at 12 days (Figure 4b). The analytical model E[min(1, W/R)] reproduces the simulation within "
        f"{f1(V['max_an_err'])} percentage points, and the 2026 holdout agrees with 2025 (6 days: "
        f"{f0(V['c6_25'])} % vs {f0(V['c6_26'])} %). The pre-declared decision criterion (≥ 20-point gain from 6- "
        f"to 3-day sampling) is met: +{f0(V['c3'] - V['c6'])} points. Across the nine alternative event definitions, "
        f"6-day capture stays within {f0(V['sens6_lo'])}–{f0(V['sens6_hi'])} %. Measured against **actual "
        f"acquisitions**, Sentinel-1 captured {f0(V['s1_25'])} % of events in 2025 and {f0(V['s1_26'])} % in 2026. In "
        f"the NISAR era ({V['n_era']:,} events, {V['n_era_st']} stations), NISAR alone captured {f0(V['ni_era'])} % and "
        f"the combined fleet {f0(V['both_era'])} %, with station-to-station spread {f0(V['both_p10'])}–"
        f"{f0(V['both_p90'])} % (10th–90th percentile). The combined fleet's median gap is {f1(V['gap_both'])} days, "
        f"but its looks cluster: a *regular* {f1(V['gap_both'])}-day schedule would capture ≈ {f0(V['reg_equiv'])} %. "
        f"Uncoordinated timing therefore costs ≈ {f0(V['reg_equiv'] - V['both_era'])} points.", after=2)
    doc.figure("fig4_capture_vs_revisit.png", 13.5,
               "(a) Cumulative distribution of event-window durations. (b) Event capture versus revisit interval for "
               "regular sampling (bands = 95 % station-bootstrap CI; dashed = analytical model) and for the actual "
               "fleets, plotted at their median gap between looks (half-amplitude criterion).")

    o3 = (f"**O3: Sampling is not the only loss.** Over {int(V['s1_n_pairs_matched']):,} matched Sentinel-1 looks at "
          f"{int(V['s1_n_stations'])} stations, the median temporal correlation of σ⁰VV with 5 cm SM was "
          f"r = {f2(V['s1_median_r'])}. Across {int(V['s1_n_change_pairs']):,} same-orbit pairs, the backscatter change "
          f"tracked the ground-truth change at r = {f2(V['s1_r_change_vv'])}, with a sensitivity of "
          f"{f2(V['s1_pair_slope_db_per_0p1'])} dB per 0.1 m³/m³ (Figure 5a). Pairs without moisture change still "
          f"scatter by {f2(V['s1_noise_db_nochange'])} dB (speckle, vegetation growth and roughness), equivalent to "
          f"≈ {f2(V['s1_noise_sm_equiv'])} m³/m³ of soil moisture, "
          f"{'larger than' if V['s1_noise_sm_equiv'] > V['amp_med'] else 'comparable to'} the median event amplitude. "
          f"When a Sentinel-1 look did fall inside a window "
          f"({int(V['s1_n_sampled_events'])} events), σ⁰ rose above the 1σ noise in only "
          f"{f0(V['s1_P_detect_given_sampled_1sigma'] * 100)} % of cases (false-alarm rate "
          f"{f0(V['s1_false_alarm_nochange_1sigma'] * 100)} %; wet-up discrimination AUC = {f2(V['s1_auc_wetup'])}). "
          f"End to end, Sentinel-1 therefore registers ≈ {f0(V['s1_era'] * V['s1_P_detect_given_sampled_1sigma'])} % "
          f"of wetting events (Figure 5c). ")
    if nis:
        ratio = V['s1_noise_sm_equiv'] / V['nis_noise_hh_sm_equiv']
        lead = ("**L-band clearly outperforms C-band at event scale.**" if ratio >= 1.5 else
                "**L-band does not yet outperform C-band at event scale.**")
        o3 += (f"{lead} Across {int(V['nis_n_pairs']):,} same-track NISAR pairs, the change in L-band σ⁰HH "
               f"correlated with the ground-truth change at r = {f2(V['nis_r_change_hh'])} (C-band: "
               f"{f2(V['s1_r_change_vv'])}), with a sensitivity of {f2(V['nis_slope_hh_db_per_0p1'])} dB per 0.1 m³/m³. "
               f"However, its no-change noise ({f2(V['nis_noise_hh_db'])} dB) is equivalent to ≈ "
               f"{f3(V['nis_noise_hh_sm_equiv'])} m³/m³, no better than C-band, and only "
               f"{f0(V['nis_P_detect_hh_valid_1sigma'] * 100)} % of sampled events rose above it. NISAR's provisional SME2 "
               f"product ({int(V['nis_n_rec']):,} recommended retrievals at {int(V['nis_n_stations'])} stations) meets its "
               f"0.06 m³/m³ goal at {f0(V['nis_frac_station_ubrmse_le_006'] * 100)} % of stations (median per-station "
               f"unbiased RMSE {f3(V['nis_median_station_ubrmse'])}; pooled {f3(V['nis_ubrmse'])}, bias "
               f"{V['nis_bias']:+.3f}). Its same-track changes have a noise floor of only "
               f"{f3(V['nis_noise_sat_nochange'])} m³/m³ (r = {f2(V['nis_r_change_sat'])}), but the retrieved change is "
               f"damped to {V['snr_tab'].loc['NISAR SME2', 'slope_per_m3m3']:.2f} of the true change, so it registered "
               f"just {f0(V['nis_P_detect_sat_valid_1sigma'] * 100)} % of the {int(V['nis_n_sampled_sat_valid'])} sampled "
               f"events with a valid retrieval pair ({f0(V['nis_P_detect_sat_1sigma'] * 100)} % if looks without a "
               f"recommended retrieval count as misses). Absolute accuracy is therefore not the binding constraint. "
               f"Event sensitivity is. ")
    else:
        o3 += ("NISAR SME2 accuracy could not be evaluated in time; it is the first task of the funded work (Section 3.4). ")
    o3 += (f"The no-satellite baseline is continuous in time but unreliable at event scale. ERA5-Land tracks the "
           f"seasonal cycle (median r = {f2(V['era_r'])}; daily-change r = {f2(V['era_rdd'])}) and its rainfall "
           f"registers {f0(V['era_rain'])} % of gauge storms, yet it reproduced only {f0(V['era_pod'])} % of "
           f"ground-truth wetting events, and {f0(V['era_far'])} % of its own events had no ground counterpart "
           f"(CSI {f0(V['era_csi'])} %). Storm magnitude and soil response are wrong at the field, not storm timing.")
    doc.para(o3, after=2)
    S = V["strata"].set_index(["sensor", "dimension", "level"]).p_detect * 100
    sp, de = "NDVI < 0.35 (sparse)", "NDVI >= 0.6 (dense)"
    s1k, hhk, smk = "Sentinel-1 VV (C-band SAR)", "NISAR HH (L-band SAR)", "SMAP (L-band radiometer)"
    T = V["snr_tab"]
    doc.para(
        f"**Why sampled events are missed, and what would fix it.** Detection falls with vegetation for every sensor "
        f"(Figure 5b): from {f0(S[s1k, 'ndvi_bin', sp])} % to {f0(S[s1k, 'ndvi_bin', de])} % for Sentinel-1 and from "
        f"{f0(S[hhk, 'ndvi_bin', sp])} % to {f0(S[hhk, 'ndvi_bin', de])} % for NISAR HH between sparse (NDVI < 0.35) and "
        f"dense (NDVI ≥ 0.6) cover. Dense cover holds half or more of all sampled events, and the large group of "
        f"stations in tree cover fares poorly (Sentinel-1 {f0(S[s1k, 'cover', 'Tree cover'])} %, NISAR HH "
        f"{f0(S[hhk, 'cover', 'Tree cover'])} %). L-band backscatter beats C-band only where vegetation is sparse, and "
        f"those groups are small; NISAR's soil-moisture product is not worse than Sentinel-1 under dense cover "
        f"({f0(S['NISAR SME2 (L-band SAR)', 'ndvi_bin', de])} % vs {f0(S[s1k, 'ndvi_bin', de])} %, overlapping "
        f"intervals). The SMAP radiometer, with twice-daily looks and change noise of "
        f"{f3(V['sm_noise_nochange'])} m³/m³, has a look inside {f0(V['sm_capture_era'] * 100)} % of event windows, "
        f"registers {f0(V['sm_P_detect_1sigma'] * 100)} % of sampled events (false alarms "
        f"{f0(V['sm_false_alarm_1sigma'] * 100)} %) and {f0(V['sm_end_to_end_era'] * 100)} % end to end, but on a 9 km "
        f"grid that cannot resolve fields. One detection model with a single fitted factor (k = "
        f"{V['snr_k_calibration']:.2f}) reproduces all four sensors' rates within {V['snr_calibrated_mae_pts']:.0f} "
        f"points on average (Figure 5d). Solving it for 70 % detection of the observed events gives a change-noise "
        f"requirement of **≤ {f3(V['snr_noise_req_70'])} m³/m³**: {V['snr_req_db_L']:.2f} dB at L-band against "
        f"{V['snr_now_db_L']:.2f} dB today. If that noise is speckle, it needs ≈ {V['snr_looks_factor_L']:.0f}× more "
        f"independent looks, a trade between resolution and noise that ARMO's design must resolve.", after=2)
    doc.figure("fig6_observability.png", 13.0,
               "(a) Same-geometry backscatter change against ground-truth soil-moisture change, C-band Sentinel-1 VV and "
               "L-band NISAR HH. (b) Sampled events detected (1σ above no-change noise) by MODIS NDVI at the event; "
               "bars = 95 % CI. (c) Detection chain in the NISAR era: look in window, detection when sampled, their "
               "product, and ERA5-Land POD and false alarms. (d) Detection versus change noise: observed sensors and a "
               "detection model calibrated on them, giving ARMO's noise requirement.")
    doc.para(
        f"**O4: Requirement and marginal value of ARMO (Figure 6).** Capturing ≥ 80 % of events requires a regular "
        f"revisit of ≈ {f1(V['R80'])} days from a single system. Added to the *current* fleet, a 2-day ARMO raises "
        f"capture from {f0(V['cur'])} % to {f0(V['arm2'])} % ({f0(V['arm2_lo'])}–{f0(V['arm2_hi'])} %), and a 3-day "
        f"ARMO to {f0(V['arm3'])} %. A *future* fleet with ROSE-L at ESA's documented 6-day revisit over global land "
        f"would reach {f0(V['fut'])} % ({f0(V['fut_lo'])}–{f0(V['fut_hi'])} %), and ARMO would add "
        f"{f0(V['fut3'] - V['fut'])} (3-day) to {f0(V['fut2'] - V['fut'])} (2-day) points to it; at 3 days the fleet "
        f"would reach {f0(V['opt'])} % and a 2-day ARMO would add {f0(V['opt2'] - V['opt'])}.", after=2)
    doc.figure("fig5_marginal_value.png", 12.5,
               "Event capture by the real 2026 fleet, with ARMO added at 1–4-day revisit, and by a future fleet "
               "including ROSE-L at its documented 6-day global-land revisit. Error bars = 95 % station-bootstrap CI.")
    D = V["designs"].set_index(V["designs"].design.str[0])
    doc.para(
        f"**Mission feasibility: can a real orbit deliver this?** Idealised schedules ignore orbital geometry, so we "
        f"flew five candidate ARMO designs for the 136-day NISAR era (Table 3). The model is a circular dawn–dusk "
        f"sun-synchronous orbit at 620 km (inclination {D.loc['A', 'inclination_deg']:.2f}°, J2 nodal precession, "
        f"10 s steps) with a side-looking L-band ScanSAR imaging 25–45° off-nadir, a {int(D.loc['A', 'access_swath_km'])} km "
        f"access swath comparable to ALOS-4's wide modes (JAXA, 2024). A station is imaged at broadside when it lies "
        f"inside the access swath, and a SAR images only one side per pass. Each design's simulated passes were added to "
        f"the *real* Sentinel-1 + NISAR passes and scored against the same {V['n_era']} ground-truth events, averaged "
        f"over eight orbital phases. One satellite reaches {f0(D.loc['A', 'capture_fleet_plus_armo'] * 100)}–"
        f"{f0(D.loc['C', 'capture_fleet_plus_armo'] * 100)} %, and rolling to look both ways does not shorten its revisit "
        f"(design B). Only **two right-looking satellites 180° apart (design D)** clear the 80 % target "
        f"({f0(D.loc['D', 'capture_fleet_plus_armo'] * 100)} %, range {f0(D.loc['D', 'capture_min'] * 100)}–"
        f"{f0(D.loc['D', 'capture_max'] * 100)} % over phases; +{f0(D.loc['D', 'gain_pts'])} points). "
        f"We therefore define design D as the **baseline mission** and design C (one satellite, wider access) as the "
        f"**threshold mission**: the least capable configuration that still lifts capture to "
        f"{f0(D.loc['C', 'capture_fleet_plus_armo'] * 100)} %. Its mass, power and cost are sized below.", after=2)
    doc.table(
        "ARMO orbit and design trade (simulated, 17 Jun–31 Oct 2026; 620 km dawn–dusk SSO). Capture is for "
        f"the real fleet plus ARMO; the current fleet alone captures {f0(V['cur'])} %.",
        ["Design", "Satellites / look", "Access swath", "ARMO revisit", "Capture (phase range)", "Gain", "CONUS duty"],
        [[k, f"{int(r.n_sat)} / {'right only' if r.sides == 'R' else 'roll L/R alternate orbits'}",
          f"{int(r.access_swath_km)} km ({r.off_nadir}°)", f"{r.armo_mean_gap_d:.1f} d",
          f"{r.capture_fleet_plus_armo * 100:.0f} % ({r.capture_min * 100:.0f}–{r.capture_max * 100:.0f})",
          f"+{r.gain_pts:.0f} pts", f"{r.imaging_duty_conus * 100:.1f} %"] for k, r in D.iterrows()],
        [1.4, 3.6, 2.6, 1.9, 2.8, 1.3, 1.6], size=7.5, bold_last=False)
    Hc = V["h2h"]
    ci = lambda k: f"{Hc.loc[k, 'ci_lo'] * 100:.0f}–{Hc.loc[k, 'ci_hi'] * 100:.0f}"
    reg = lambda c: f"{c * dlo / 100:.0f}–{c * dhi / 100:.0f} %"
    doc.para(
        f"**Performance against NISAR and ROSE-L (Table 4).** Scored alone on the same {V['n_era']} events, design D "
        f"captures {f0(a1)} % ({ci('ARMO alone (design D)')} %), twice NISAR's {f0(n1)} % and above ROSE-L at "
        f"either 6 days ({f0(r6)} %) or 3 days ({f0(r3)} %). The gain is revisit, not resolution: both are L-band on "
        f"a 200 m grid, but ARMO samples a US station every {D.loc['D', 'armo_mean_gap_d']:.1f} days against "
        f"NISAR's median gap of {f1(V['gap_ni'])} days, and NISAR SME2 is delivered within 72 h (ASF, 2026) against "
        f"ARMO's ≤ 24 h requirement. Detection decides how much reaches users: "
        f"at NISAR's measured {f0(dlo)}–{f0(dhi)} %, NISAR registers {reg(n1)} of events; ARMO at its 70 % "
        f"requirement would register {f0(a1 * 0.7)} %.", after=2)
    doc.table(
        f"ARMO against NISAR and ROSE-L on the same {V['n_era']} ground-truth wetting events (17 Jun–31 Oct 2026). "
        "Capture = a look inside the event window; registered = capture × detection when sampled. ROSE-L detection "
        "is assumed equal to NISAR's measured rate; ARMO's is its requirement, not yet demonstrated.",
        ["System (L-band SAR)", "Revisit at US stations", "Capture alone (95 % CI)", "Capture with the fleet",
         "Detection when sampled", "Events registered"],
        [["NISAR (real 2026 passes)", f"median gap {f1(V['gap_ni'])} d", f"{f0(n1)} % ({ci('NISAR alone')})",
          f"{f0(H['Sentinel-1 + NISAR'])} % with Sentinel-1", f"{f0(dlo)}–{f0(dhi)} % (measured)", reg(n1)],
         ["ROSE-L, 6 d (ESA, global land)", "6 d", f"{f0(r6)} % ({ci('ROSE-L alone, 6-day')})",
          f"{f0(V['fut'])} %", "as NISAR (assumed)", reg(r6)],
         ["ROSE-L, 3 d (Europe; eoPortal)", "3 d", f"{f0(r3)} % ({ci('ROSE-L alone, 3-day')})",
          f"{f0(V['opt'])} %", "as NISAR (assumed)", reg(r3)],
         ["ARMO, design D (2 smallsats)", f"{D.loc['D', 'armo_mean_gap_d']:.1f} d (simulated)",
          f"{f0(a1)} % ({ci('ARMO alone (design D)')})",
          f"{f0(H['Sentinel-1 + NISAR + ARMO'])} %; {f0(H['Sentinel-1 + NISAR + ROSE-L 6-day + ARMO'])} % with ROSE-L",
          "≥ 70 % (requirement)", f"{f0(a1 * 0.7)} %"]],
        [3.4, 2.4, 2.6, 3.2, 2.6, 2.0], size=7.5)
    doc.table(
        "Science traceability matrix for ARMO: objectives flow to physical parameters, measurement and mission "
        "requirements. P = shown by this study; L = literature; U = unverified (future work).",
        ["Objective / hypothesis", "Physical parameter", "Measurement / instrument requirement", "Mission requirement",
         "Evidence", "Status"],
        [["O2, H1, H3: capture ≥ 80 % of wetting events", f"5 cm SM rise ≥ 0.03 m³/m³; window median {f1(V['win_med_d'])} d",
          "At least one look inside the event window",
          "Revisit ≤ 2 d, with or without ROSE-L. Baseline: 2 sats, 620 km dawn–dusk SSO, 180° apart (D). "
          "Threshold: 1 sat, 20–50° access (C)",
          f"Figure 6: {f0(V['arm2'])} % today, {f0(V['fut2'])} % with ROSE-L; Table 3: D {f0(D.loc['D', 'capture_fleet_plus_armo'] * 100)} %, "
          f"C {f0(D.loc['C', 'capture_fleet_plus_armo'] * 100)} %", "P"],
         ["O3, H2: detect ≥ 70 % of sampled events at ≤ 10 % false alarms (critical)",
          f"Event ΔSM (median {f3(V['amp_med'])} m³/m³) against change noise",
          f"Change noise ≤ {f3(V['snr_noise_req_70'])} m³/m³, i.e. L-band Δσ⁰ noise ≤ {V['snr_req_db_L']:.2f} dB "
          f"(today {V['snr_now_db_L']:.2f} dB)",
          f"≈ {V['snr_looks_factor_L']:.0f}× more independent looks per product if speckle-limited",
          f"Figure 5d model; today S1 {f0(V['s1_P_detect_given_sampled_1sigma'] * 100)} %, NISAR "
          f"{f0(V['nis_P_detect_hh_valid_1sigma'] * 100)}–{f0(V['nis_P_detect_sat_valid_1sigma'] * 100)} %, "
          f"SMAP {f0(V['sm_P_detect_1sigma'] * 100)} %", "U"],
         ["Vegetated fields", "SM beneath NDVI ≥ 0.6 canopy", "L-band (~1.26 GHz), HH + HV, 25–45° incidence", "–",
          "Ulaby et al. (2014); Figure 5b: L-band ahead only in sparse cover", "L/U"],
         ["Field scale", "SM of individual fields", "Product 100–200 m (ScanSAR, multi-looked); trades against row 2",
          f"{int(D.loc['A', 'access_swath_km'])} km access swath", "NISAR SME2 grid; SMAP's 9 km cannot resolve fields", "L"],
         ["Applications (Section 4)", "Antecedent wetness for flood forecasts", "–",
          f"Latency ≤ 24 h; CONUS imaging ≈ {D.loc['D', 'imaging_duty_conus'] * 100:.1f} % of each orbit",
          "Table 3; forecast cycles", "P/U"],
         ["Implementation", "–", f"L-band ScanSAR, {SZ.reflector_d_m:.1f} m mesh reflector, {SZ.P_peak_rf_w:.0f} W peak RF",
          f"2 × {SZ.wet_kg:.0f} kg, one launch; ≈ US$ {SZ.cost_total:.0f} M", "Table 6 (sizing)", "Estimate"]],
        [2.7, 2.6, 3.4, 3.4, 3.2, 1.1], size=7)
    doc.para(
        f"**Spacecraft sizing (Table 6).** At 45° off-nadir, the far edge of the access range, L-band ambiguity limits "
        f"require at least {SZ.Amin_45_m2:.0f} m² of aperture (Freeman et al., 2000), so each satellite carries a "
        f"{SZ.reflector_d_m:.1f} m deployable mesh reflector, half NISAR's 12 m (Rosen et al., 2015). With that gain, "
        f"a noise floor of −25 dB, 2 dB better than NISAR's ≈ −23 dB requirement (Fattahi et al., 2026), needs only "
        f"≈ {SZ.P_avg_rf_w:.0f} W of average radio power (radar equation, Ulaby et al., 2014; 3 dB ScanSAR margin). "
        f"Because the radar images only the US ({SZ.imaging_min_day:.0f} min per day), the orbit-average power is "
        f"≈ {SZ.orbit_avg_w:.0f} W and the data volume {SZ.data_gb_day:.0f} GB per day, downlinked in "
        f"{SZ.downlink_min_day:.0f} min to polar ground stations that see a dawn–dusk orbit every pass, so the 24 h "
        f"latency requirement has ample margin. A bottom-up mass budget gives ≈ {SZ.wet_kg:.0f} kg per satellite with a "
        f"30 % growth margin, so both fit one small launcher (Firefly Alpha: 630 kg to 500 km SSO; Firefly, 2026).",
        after=2)
    Mt = V["mass"].set_index("item").kg
    doc.table(
        "ARMO spacecraft and mission sizing (per satellite unless stated). Physics from the radar equation and the "
        "orbit model; masses below the reflector are our engineering estimates (code/22_armo_sizing.py).",
        ["Element", "Value", "Basis"],
        [["Orbit", f"620 km dawn–dusk SSO; 2 satellites 180° apart; {D0.loc['D', 'armo_mean_gap_d']:.1f}-day revisit", "Orbit simulation (Table 3)"],
         ["Antenna", f"{SZ.reflector_d_m:.1f} m mesh reflector ({SZ.antenna_area_m2:.0f} m²); L-band 1.26 GHz, HH + HV", f"A ≥ {SZ.Amin_45_m2:.0f} m² at 45° (Freeman et al., 2000)"],
         ["Radar power", f"{SZ.P_avg_rf_w:.0f} W average, {SZ.P_peak_rf_w:.0f} W peak RF; {SZ.radar_dc_w:.0f} W DC while imaging", "NESZ −25 dB, 20 MHz, 9 dB losses + margin"],
         ["Spacecraft power", f"{SZ.orbit_avg_w:.0f} W orbit average; {SZ.array_m2:.1f} m² array; {SZ.battery_wh:.0f} Wh battery", "Imaging 1.5 % of each orbit"],
         ["Data", f"{SZ.data_rate_mbps:.0f} Mbit/s while imaging; {SZ.data_gb_day:.0f} GB/day; {SZ.downlink_min_day:.0f} min/day X-band", "4-bit BAQ, 2 polarisations"],
         ["Mass", f"{Mt.iloc[9]:.0f} kg dry (best estimate), {SZ.dry_kg:.0f} kg with 30 % margin, {SZ.wet_kg:.0f} kg wet", "Reflector scaled from < 8 kg at 3.35 m (Sushko et al., 2021)"],
         ["Launch", f"Both satellites ({SZ.launch_kg:.0f} kg) on one small launcher; 120 m/s for phasing and de-orbit", "Firefly (2026)"],
         ["Cost", f"≈ US$ {SZ.cost_total:.0f} M incl. launch, 3-yr operations, 30 % reserve; threshold (1 sat) ≈ US$ {SZ.cost_threshold:.0f} M", "Section 5; EVM cap US$ 190 M"]],
        [2.3, 8.2, 5.8], size=7.5)

    doc.h2("3.4 Limitations and Way Forward")
    lims = [
        "**Point vs footprint.** A 5 cm probe samples about 1 m²; a SAR pixel samples 10–200 m. Station-to-pixel "
        "mismatch inflates apparent noise in O3 (Crow et al., 2012). *Fix:* the Stage 1 heterogeneity campaign "
        "(4 extra probe profiles at 2 sites) and triple collocation.",
        f"**Retrieval: the critical risk, and the payoff if it is met.** O3 shows that L-band change noise must fall "
        f"≈ {V['snr_now_db_L'] / V['snr_req_db_L']:.0f}-fold (Table 5) to detect 70 % of sampled events, a number from a "
        f"model fitted on four sensors and 4.5 months of provisional NISAR data. *If it is met,* ARMO alone registers "
        f"≈ {f0(a1 * 0.7)} % of all wetting events, {f0(a1 * 0.7 / (n1 * dhi / 100))}–{f0(a1 * 0.7 / (n1 * dlo / 100))}× NISAR "
        f"today ({f0(n1 * dlo / 100)}–{f0(n1 * dhi / 100)} %), and flood forecasters receive a field-scale wetness "
        f"update every {D0.loc['D', 'armo_mean_gap_d']:.1f} days within 24 h. *If it is not,* revisit still doubles the "
        f"result: at NISAR's measured detection ARMO registers {f0(a1 * dlo / 100)}–{f0(a1 * dhi / 100)} %, because the "
        f"revisit gain does not depend on retrieval. *Fix:* Stage 1 funds this research first, on the validated NISAR "
        f"release; its result sets ARMO's sensor (looks, bandwidth, power), not whether ARMO flies (Table 7).",
        f"**Engineering and cost risk.** A {SZ.reflector_d_m:.1f} m reflector has not flown on a "
        f"{SZ.wet_kg:.0f} kg spacecraft. NISAR flies 12 m and small-SAR reflectors of 3.35 m weigh < 8 kg, so the "
        f"technology exists, but deployment is the top engineering risk. The cost is a ± 40 % estimate by analogy "
        f"with ≈ {f0((190 / SZ.cost_total - 1) * 100)} % headroom under the cap. *Fix:* a reflector deployment test in "
        f"Stage 2 before the build; if cost grows, descope to the one-satellite threshold mission (≈ US$ {SZ.cost_threshold:.0f} M, "
        f"{f0(D0.loc['C', 'capture_fleet_plus_armo'] * 100)} % capture).",
        "**Representativeness.** CONUS, warm seasons, two years; only "
        f"{V['n_lc'].get('Cropland', 0)} of {sum(V['n_lc'].values())} stations sit in cropland, so detection over crops is "
        "barely sampled. *Fix:* add cropland networks (USDA SCAN, ISMN, SMAP core sites) and extend to 2015–2026.",
        "**Future-fleet assumption.** ROSE-L is simulated at ESA's 6-day global-land revisit (3 days is Europe); "
        "eoPortal (2026), a secondary source, lists 3 days for soil moisture, at which ARMO still adds "
        f"{f0(H['Sentinel-1 + NISAR + ROSE-L 3-day + ARMO'] - V['opt'])} points (Table 4). *Fix:* rerun when ESA "
        "publishes ROSE-L's US acquisition plan.",
        "**Alternatives without a new satellite fall short.** Coordinated phasing of existing passes recovers only "
        f"≈ {f0(V['reg_equiv'] - V['both_era'])} points; SMAP (9 km) and ERA5-type models cannot resolve fields; "
        "commercial daily products (Spire, Planet) are modelled from coarse sensors. Optical sensors need clear sky: "
        f"in MODIS cloud masks at our stations only {f0(V['opt_daily'])} % of events had a clear look even with daily "
        f"imaging, and {f0(V['opt5'])} % at a 5-day revisit against {f0(V['sar5'])} % for radar. *Fix:* optical data "
        "serve as vegetation and land-cover inputs; commercial products are tested against USCRN events in Stage 1.",
        f"**Frequency: why not P-band or UHF?** Longer wavelengths see deeper: ≈ 7 cm at P-band against ≈ 5 cm at "
        f"L-band, and > 10 cm below 0.5 GHz (Shen et al., 2021). Depth does not relax the revisit requirement: "
        f"on USCRN's 10 cm probes, events last {f1(Dp.loc[10, 'win_med_d'])} instead of {f1(Dp.loc[5, 'win_med_d'])} days "
        f"and a 2-day revisit captures {f0(Dp.loc[10, 'cap_R2'] * 100)} % (5 cm: {f0(Dp.loc[5, 'cap_R2'] * 100)} %). (i) "
        "*P-band SAR* shares 432–438 MHz with US space-object tracking radars, so BIOMASS may not operate over North "
        "America and Europe; it also needs a 12 m reflector and ionospheric correction (Quegan et al., 2019). (ii) *UHF/P-band signals of opportunity* "
        "reuse communications-satellite signals, so need no transmitter or licence. A tower test at "
        "260 MHz matched the top 10 cm within 0.02 m³/m³ (Yueh et al., 2020), but a seven-satellite SoOp SAR reaches "
        "≈ 200 m only at the swath edge and ≈ 1 km at its centre, relying on US Navy MUOS transmitters (Yueh et al., "
        "2021); only the SNOOPI CubeSat has flown (Garrison et al., 2024). *Fix:* L-band is the "
        "baseline; a UHF SoOp receiver is studied in Stage 1 as a hosted payload for root-zone moisture.",
    ]
    for l in lims:
        doc.bullet(l, size=10)
    doc.para(
        f"**Two-stage path to launch (Table 7).** *Stage 1* (2027–28, US$ {money(TOTAL)}): event-sensitive change-detection "
        "retrieval against USCRN on the validated NISAR release, a multi-year climatology with cropland networks, a field "
        "campaign, and the frequency, tasking and commercial-product tests. Its output is the change noise ARMO's sensor "
        "must reach, which sets looks, bandwidth and power. If 70 % proves out of reach, the retrieval still improves NISAR "
        "and ROSE-L products and ARMO still doubles the events registered, so Stage 2 proceeds either way. *Stage 2* "
        "(2029–36): build, test (including reflector deployment) and launch both satellites together (≈ 2033) within the "
        "5-year Earth Venture limit; then 3 years of operations with open products for NOAA and USDA within 24 h.", after=2)
    e = [""] * 10
    def row(label, marks):
        r = list(e)
        for k, m in marks.items():
            r[k - 1] = m
        return [label] + r
    tl = [row("Stage 1: event retrieval vs USCRN (validated NISAR), climatology, field campaign, trades", {1: "■", 2: "■"}),
          row("Stage 1 result sets the sensor: target change noise → looks, bandwidth, power", {2: "◆"}),
          row("Stage 2, Phases A–B: requirements, reflector deployment test, preliminary design", {3: "■", 4: "■"}),
          row("Stage 2, Phases C–D: build and test two spacecraft; launch together (◆ ≈ 2033)", {5: "■", 6: "■", 7: "◆"}),
          row("Stage 2, Phase E: operations; products to NOAA and USDA within 24 h", {8: "■", 9: "■", 10: "■"}),
          row("Publications, open data and code", {1: "■", 2: "■", 8: "■", 9: "■", 10: "■"})]
    doc.table("Two-stage schedule (Year 1 = 2027). ◆ = milestone. Stage 2 proceeds whatever Stage 1 finds.",
              ["Stage / phase / milestone"] + [f"Y{k}" for k in range(1, 11)], tl,
              [7.6] + [0.86] * 10, size=8)

    # ================================================================ 4
    doc.h1("4 Relevance to Society")
    doc.para(
        "**Challenge (Water Resources; Agriculture).** Irrigation is the largest US freshwater withdrawal: 118 billion "
        "gallons per day in 2015, 42 % of total freshwater withdrawals (Dieter et al., 2018). The 2012 flash drought "
        "(Otkin et al., 2018) caused nearly US$30 billion in damage (NOAA, 2013), and crop-insurance indemnities for that year reached a record US$17 billion (Hagstrom Report, 2013). "
        "Both droughts and floods turn on how fast the top layer wets and dries.")
    doc.para(
        "**Users and decisions.** (1) *NOAA National Water Model / flood forecasters*: the model routes hourly flows on "
        "> 2.7 million river reaches. Whether a basin's soils are still wet from a storm two days earlier decides the "
        "runoff from the next one, so a 6–12-day-old soil-moisture map initialises it with the wrong state. "
        "(2) *USDA NASS Crop-CASMA and FAS crop forecasting* already ingest SMAP at 1–9 km; field-scale event "
        "information would let them separate rain-fed from irrigated responses. (3) *Water managers and agricultural "
        "insurers* need evidence of when, and how much, water reached a field. (4) *Weather centres* (ECMWF "
        "operationally assimilates ASCAT and SMOS soil moisture; Weston et al., 2024) would gain observations at the moments the land "
        "state changes fastest.")
    doc.para(
        "**Why remote sensing, and its limits.** A farmer's probe measures one field perfectly; the 120 USCRN stations "
        "cover the contiguous US at one point per ~67,000 km². Only satellites map every field. Weekly products such "
        "as the US Drought Monitor do not need 2-day revisit, so the users who benefit are event-scale ones: flood "
        "forecasting, irrigation accounting and model calibration. Results would reach them as open ARMO "
        "soil-moisture maps within 24 h of each pass, a NISAR validation dataset, and the code that NASA's Applied "
        "Sciences and SMAP/NISAR Early Adopter communities can re-run.")

    # ================================================================ 5
    doc.h1("5 Budget Summary")
    doc.para(
        f"The request has two stages. **Stage 1, requested now (Table 8): US$ {money(TOTAL)}** for the 2-year retrieval "
        f"study. Personnel: 0.5 FTE analyst plus 0.1 FTE PI at the BLS May 2025 median geoscientist salary of "
        f"US$ {money(BLS_MEDIAN)} = US$ {money(PERS)}/yr; computing: 2,000 h/yr of an AWS m6i.2xlarge at US$ 0.384/h "
        f"plus 2 TB of S3 = US$ {money(COMP)}/yr; fieldwork: 12 HydraProbe sensors at US$ 545; publication: IEEE JSTARS "
        f"open-access fee (US$ {money(APC)}) and one AGU meeting (US$ {money(AGU)}); indirect costs at 62 %, the MIT "
        f"FY2026 federal rate (no public NTU rate exists). All data are free; the alternative, commercial X-band tasking for "
        f"the same 120 stations, would cost ≈ US$ 19–20 M (SkyWatch list prices) and senses only ~1 cm, so it was "
        f"rejected. **Stage 2 (Table 9): "
        f"≈ US$ {SZ.cost_total:.0f} M** for the ARMO mission, inside the US$ 190 M Earth Venture Mission cap, which "
        f"includes launch (NASA ESSP, 2020; FY2022 dollars). The flight system (US$ 70 M) is "
        f"estimated by analogy with NovaSAR-1 (≈ £45 M build and launch; SSTL, 2011; eoPortal, 2024) and CYGNSS "
        f"(US$ 102 M excluding launch; Ruf et al., 2013); launch ≈ US$ 15 M (Firefly, 2026; secondary price sources); "
        f"management and ground lines are our estimates. Cost drivers: personnel in Stage 1 ({f0(2 * PERS / (d1 + d2) * 100)} % of direct costs), the flight "
        f"system in Stage 2 ({f0(SZ.flight_share * 100)} %); the one-satellite threshold mission would cost "
        f"≈ US$ {SZ.cost_threshold:.0f} M, against US$ 1,174 M for NISAR (GAO, 2026).")
    rows = [["Personnel (0.5 FTE analyst, 0.1 FTE PI)", Y1["pers"], Y2["pers"], 0],
            ["Computing and storage", Y1["comp"], Y2["comp"], 0],
            ["Fieldwork and validation", Y1["field"], Y2["field"], 0],
            ["Travel and publication", Y1["travel"], Y2["travel"], 0],
            ["Total Direct Costs", d1, d2, 0],
            ["Indirect Costs (62 %, MIT FY2026 federal rate)", i1, i2, 0],
            ["Total Requested Funding", t1, t2, 0]]
    doc.table("Stage 1 budget summary (US$), requested now. Year 3 is zero because the study lasts 2 years.",
              ["Budget category", "Year 1", "Year 2", "Year 3", "Total"],
              [[r[0], money(r[1]), money(r[2]), money(r[3]), money(r[1] + r[2] + r[3])] for r in rows],
              [7.0, 2.2, 2.2, 1.6, 2.4], size=8, bold_last=True)
    cat = lambda k: CO[CO.item.str.contains(k, regex=False)]
    def line(label, keys):
        x = pd.concat([cat(k) for k in keys])
        return [label, x[x.phase == "A-D"].usd_m.sum(), x[x.phase == "E"].usd_m.sum()]
    rows = [line("Flight system: 2 spacecraft with L-band SAR; management, integration and test", ["Flight system", "Project management"]),
            line("Launch (one small launcher, both satellites)", ["Launch:"]),
            line("Science team, ground and data systems, operations", ["PI, science team", "Science team, processing", "Ground and science data",
                                                                     "Sustaining", "Mission operations", "Ground-station contacts"]),
            line("Reserves (30 % Phases A–D; 15 % Phase E)", ["Reserve"])]
    rows.append(["Total", sum(r[1] for r in rows), sum(r[2] for r in rows)])
    doc.table("Stage 2 mission cost estimate (FY2026 US$ M, ± 40 %). Phases A–D = 2029–33 (launch ≈ 2033); "
              "Phase E = 2034–36. Line items and bases: code/22_armo_sizing.py.",
              ["Budget category", "Phases A–D", "Phase E", "Total"],
              [[r[0], f"{r[1]:.1f}", f"{r[2]:.1f}", f"{r[1] + r[2]:.1f}"] for r in rows],
              [9.4, 2.4, 2.4, 2.2], size=8, bold_last=True)

    # ================================================================ refs etc.
    doc.page_break()
    doc.h1("References")
    for ref in sorted(REFERENCES[:-1], key=str.casefold) + REFERENCES[-1:]:   # alphabetical; unit-cost note last
        doc.para(ref, size=8.5, after=1.5, indent=0.6, align_just=False)
    doc.h1("Data and Code Availability")
    doc.para(
        "All analysis code (Python 3.14; scripts 01–23, run in order) is in the project folder `code/` and is "
        "reproducible from public data. Ground truth: NOAA USCRN hourly02 (https://www.ncei.noaa.gov/pub/data/uscrn/"
        "products/hourly02/). Sentinel-1: Microsoft Planetary Computer STAC collections `sentinel-1-grd` and "
        "`sentinel-1-rtc`. NISAR: NASA CMR collections NISAR_L2_GCOV_*_V1 and NISAR_L3_SME2_PROVISIONAL_V1 via ASF "
        "(Earthdata login). SMAP SPL3SMP_E V006, MODIS MOD13Q1 V6.1, ESA WorldCover v200 and USDA CDL 2025: Google "
        "Earth Engine (scripts 14–17, 23; gridMET IDAHO_EPSCOR/GRIDMET, COPERNICUS/S1_GRD, MODIS/061/MCD12Q1). ERA5-Land: Open-Meteo archive API. Repository: https://github.com/zheniannn/ARMO "
        "(MIT licence).", size=9.5)
    doc.h1("Individual Contribution Statements (half a page each)")
    doc.para("[Each team member writes their own half-page statement here: scripts, analyses, figures and report "
             "sections produced, a brief reflection on their role and what they would do differently.]", size=9.5)
    for k in (1, 2, 3):
        doc.para(f"**Team Member {k}: [Name]**", size=10, after=1)
        doc.para("[Half-page statement]", size=9.5, after=6)


REFERENCES = [
    "ASF (2026). NISAR Soil Moisture (SME2) product guide and provisional known issues. Alaska Satellite Facility. https://nisar-docs.asf.alaska.edu/sme2/",
    "Abatzoglou, J. T. (2013). Development of gridded surface meteorological data for ecological applications and modelling. Int. J. Climatol., 33(1), 121–131. https://doi.org/10.1002/joc.3413",
    "Bauer-Marschallinger, B., et al. (2019). Toward global soil moisture monitoring with Sentinel-1: harnessing assets and overcoming obstacles. IEEE Trans. Geosci. Remote Sens., 57(1), 520–539. https://doi.org/10.1109/TGRS.2018.2858004",
    "Bazzi, H., Baghdadi, N., El Hajj, M., & Zribi, M. (2019). Potential of Sentinel-1 surface soil moisture product for detecting heavy rainfall in the south of France. Sensors, 19(4), 802. https://doi.org/10.3390/s19040802",
    "Bell, J. E., et al. (2013). U.S. Climate Reference Network soil moisture and temperature observations. J. Hydrometeorol., 14, 977–988. https://doi.org/10.1175/JHM-D-12-0146.1",
    "BLS (2026). Occupational Outlook Handbook: Geoscientists (median pay, May 2025). https://www.bls.gov/ooh/life-physical-and-social-science/geoscientists.htm",
    "Chatterjee, S., Huang, J., & Hartemink, A. E. (2020). Establishing an empirical model for surface soil moisture retrieval at the U.S. Climate Reference Network using Sentinel-1 backscatter and ancillary data. Remote Sens., 12(8), 1242. https://doi.org/10.3390/rs12081242",
    "Crow, W. T., et al. (2012). Upscaling sparse ground-based soil moisture observations for the validation of coarse-resolution satellite soil moisture products. Rev. Geophys., 50, RG2002. https://doi.org/10.1029/2011RG000372",
    "Didan, K. (2021). MODIS/Terra Vegetation Indices 16-Day L3 Global 250m SIN Grid V061. NASA LP DAAC. https://doi.org/10.5067/MODIS/MOD13Q1.061",
    "Davidson, M. (2023). ROSE-L mission in brief (ESA Land Training Course, slide 6: revisit with 2 satellites 6 days global land, 3 days Europe). https://eo4society.esa.int/wp-content/uploads/2023/11/ROSEL_TrainingCourseLandRS_Malcolm-Davidson.pdf",
    "Davidson, M., Iannini, L., Kubanek, J., et al. (2026). ROSE-L mission objectives and science status. ESA Fringe 2026, Kraków, 16 June 2026. https://fringe2026.esa.int/iframe-agenda/files/ID_534.pdf",
    "Dieter, C. A., Maupin, M. A., Caldwell, R. R., et al. (2018). Estimated use of water in the United States in 2015. USGS Circular 1441. https://doi.org/10.3133/cir1441",
    "eoPortal (2024). NovaSAR-1 (430 kg S-band SAR smallsat; 3 m × 1 m antenna). https://eoportal.org/satellite-missions/novasar-1",
    "eoPortal (2026). ROSE-L (Radar Observing System for Europe in L-band). https://www.eoportal.org/satellite-missions/rose-l (secondary source)",
    "ESA (2025). ESA's Biomass mission launches on Vega-C (29 April 2025). https://www.esa.int/ESA_Multimedia/Videos/2025/04/ESA_s_Biomass_mission_launches_on_Vega-C",
    "Fattahi, H., Ghaemi, H., Hawkins, B. P., et al. (2026). NISAR L-band product status: from raw echoes to analysis-ready science data products (NESZ requirement ~ −23 dB). ESA Fringe 2026. https://fringe2026.esa.int/iframe-agenda/files/ID_282.pdf",
    "Firefly Aerospace (2026). Alpha launch vehicle: 630 kg to 500 km SSO. https://fireflyspace.com/alpha/",
    "Freeman, A., Johnson, W. T. K., Huneycutt, B., et al. (2000). The \"myth\" of the minimum SAR antenna area constraint. IEEE Trans. Geosci. Remote Sens., 38(1), 320–324. https://doi.org/10.1109/36.823926",
    "Friedl, M., & Sulla-Menashe, D. (2022). MODIS/Terra+Aqua Land Cover Type Yearly L3 Global 500 m SIN Grid V061 (MCD12Q1). NASA LP DAAC. https://doi.org/10.5067/MODIS/MCD12Q1.061",
    "Garrison, J. L., Vega, M. A., Shah, R., et al. (2024). SNOOPI: Demonstrating Earth remote sensing using P-band signals of opportunity (SoOp) on a CubeSat. Adv. Space Res., 73(6), 2855–2879. https://doi.org/10.1016/j.asr.2023.10.050",
    "Entekhabi, D., et al. (2010). The Soil Moisture Active Passive (SMAP) mission. Proc. IEEE, 98(5), 704–716. https://doi.org/10.1109/JPROC.2010.2043918",
    "ESA (2026). Sentinel-1 facts and figures; ROSE-L contract and mission pages. https://www.esa.int/Applications/Observing_the_Earth/Copernicus/Sentinel-1/Facts_and_figures",
    "Filippucci, P., et al. (2020). Soil moisture as a potential variable for tracking and quantifying irrigation. Adv. Water Resour., 136, 103502. https://doi.org/10.1016/j.advwatres.2019.103502",
    "Gorelick, N., Hancher, M., Dixon, M., Ilyushchenko, S., Thau, D., & Moore, R. (2017). Google Earth Engine: Planetary-scale geospatial analysis for everyone. Remote Sens. Environ., 202, 18–27. https://doi.org/10.1016/j.rse.2017.06.031",
    "Hagstrom Report (2013). Crop indemnities reach almost $17 billion (23 April 2013). https://hagstromreport.com/2013news_files/2013_0423_crop-indemnities-reach-almost-17-billion.html",
    "GAO (2026). NASA: Assessments of Major Projects, GAO-26-108556 (NISAR current life-cycle cost estimate). https://files.gao.gov/reports/GAO-26-108556/index.html",
    "JAXA (2024). ALOS-4 (DAICHI-4) overview and observation modes. https://www.eorc.jaxa.jp/ALOS/en/alos-4/a4_about_e.htm ; CEOS WGISS-60 JAXA agency report (ScanSAR ~700 km). https://ceos.org/document_management/Working_Groups/WGISS/Meetings/WGISS-60/Presentations/2.3_Agency%20Report%20JAXA_Makoto%20NATSUISAKA_v1.pdf",
    "Jiang, H., Lv, S., Hu, Y., & Wen, J. (2025). Contrasting drydown time scales: SMAP L-band vs. AMSR2 C-band brightness temperatures against ground observations and SMAP products. Remote Sens., 17, 3307. https://doi.org/10.3390/rs17193307",
    "Kim, S., et al. (2017). Surface soil moisture retrieval using the L-band synthetic aperture radar onboard the Soil Moisture Active–Passive satellite and evaluation at core validation sites. IEEE Trans. Geosci. Remote Sens., 55(4), 1897–1914. https://doi.org/10.1109/TGRS.2016.2631126",
    "Le Page, M., et al. (2020). Potential for the detection of irrigation events on maize plots using Sentinel-1 soil moisture products. Remote Sens., 12(10), 1621. https://hal.inrae.fr/hal-02613686v1",
    "Luo, X., Wang, M., Dai, G., & Chen, X. (2017). A novel technique to compute the revisit time of satellites and its application in remote sensing satellite optimization design. Int. J. Aerospace Eng., 2017, 6469439. https://doi.org/10.1155/2017/6469439",
    "McColl, K. A., et al. (2017). Global characterization of surface soil moisture drydowns. Geophys. Res. Lett., 44, 3682–3690. https://doi.org/10.1002/2017GL072819",
    "Microsoft (2026). Planetary Computer STAC: sentinel-1-grd and sentinel-1-rtc collections. https://planetarycomputer.microsoft.com/",
    "MIT (2026). Facilities and administrative (F&A) rates, FY2026. https://ras.mit.edu/facilities-and-administrative-fa-rates",
    "Muñoz-Sabater, J., et al. (2021). ERA5-Land: a state-of-the-art global reanalysis dataset for land applications. Earth Syst. Sci. Data, 13, 4349–4383. https://doi.org/10.5194/essd-13-4349-2021",
    "NASA ESSP (2020). Earth Venture Mission-3 (EVM-3) Announcement of Opportunity: cost cap US$ 190 M (FY2022), including launch. https://essp.larc.nasa.gov/EVM-3/",
    "National Academies of Sciences, Engineering, and Medicine (2018). Thriving on Our Changing Planet: A Decadal Strategy for Earth Observation from Space. The National Academies Press. https://doi.org/10.17226/24938 (Table 6.1, H-4; Appendix C, TO-17)",
    "NISAR Science Team (2023). NISAR L3 Soil Moisture Algorithm Theoretical Basis Document, JPL D-107679 Rev. 3.3; NISAR Provisional Soil Moisture V1, https://doi.org/10.5067/NIL3SME2-P1",
    "NOAA (2013). 2012 ranks as 2nd costliest year with 11 billion-dollar disasters (NOAA Research, 13 June 2013). https://research.noaa.gov/2013/06/13/",
    "NOAA NCEI (2026). U.S. Climate Reference Network hourly02 product. https://www.ncei.noaa.gov/pub/data/uscrn/products/hourly02/",
    "NSIDC DAAC (accessed 2026). SMAP Enhanced L3 Radiometer Global and Polar Grid Daily 9 km EASE-Grid Soil Moisture, Version 6 (SPL3SMP_E). https://doi.org/10.5067/M20OXIZHY3RJ ; via Google Earth Engine NASA/SMAP/SPL3SMP_E/006",
    "NOAA OWP (2026). National Water Model. https://water.noaa.gov/about/nwm",
    "Otkin, J. A., et al. (2018). Flash droughts: a review and assessment of the challenges imposed by rapid-onset droughts in the United States. Bull. Amer. Meteor. Soc., 99, 911–919. https://doi.org/10.1175/BAMS-D-17-0149.1",
    "Planet (2026). Soil Water Content technical specification (20 m and 100 m sales discontinued; 1 km). https://docs.planet.com/data/planetary-variables/soil-water-content/techspec/",
    "Quegan, S., Le Toan, T., Chave, J., et al. (2019). The European Space Agency BIOMASS mission: Measuring forest above-ground biomass from space. Remote Sens. Environ., 227, 44–60. https://doi.org/10.1016/j.rse.2019.03.032",
    "Rosen, P. A., Hensley, S., Shaffer, S., et al. (2015). The NASA-ISRO SAR mission: an international space partnership for science and societal benefit. 2015 IEEE Radar Conference, 1610–1613. https://doi.org/10.1109/RADAR.2015.7131255",
    "Ruf, C., Gleason, S., Jelenak, Z., et al. (2013). The NASA EV-2 Cyclone Global Navigation Satellite System (CYGNSS) mission. 2013 IEEE Aerospace Conference, 1–7. https://doi.org/10.1109/AERO.2013.6497202",
    "Shen, X., Walker, J. P., Ye, N., et al. (2021). Soil moisture retrieval depth of P- and L-band radiometry: predictions and observations. IEEE Trans. Geosci. Remote Sens., 59(8), 6814–6822. https://doi.org/10.1109/TGRS.2020.3026384",
    "Shellito, P. J., et al. (2016). SMAP soil moisture drying more rapid than observed in situ following rainfall events. Geophys. Res. Lett., 43, 8068–8075. https://doi.org/10.1002/2016GL069946",
    "SkyWatch (2026). ICEYE and Capella Space pricing. https://skywatch.com/geospatial-data-providers/iceye/ ; https://skywatch.com/geospatial-data-providers/capella-space/",
    "SSTL (2011). Government investment brings low cost radar satellites to market (NovaSAR build and launch ≈ £45 M). https://sstl.co.uk/media-hub/latest-news/2011/government-investment-brings-low-cost-radar-satellites-to-market",
    "Sushko, O., Medzmariashvili, E., Tserodze, S., et al. (2021). Design and analysis of light-weight deployable mesh reflector antenna for small multibeam SAR satellite. EUSAR 2021, VDE Verlag. https://www.tib.eu/en/search/id/vde:455457092",
    "Spire Global (2024). Soil Moisture Insights (500 m, daily; company product page, 30 April 2024). https://spire.com/?p=14420",
    "Ulaby, F. T., Long, D. G., et al. (2014). Microwave Radar and Radiometric Remote Sensing. University of Michigan Press.",
    "USDA NASS (2026). Crop-CASMA metadata. https://www.nass.usda.gov/Research_and_Science/Cropland/metadata/metadata_cropcasma.htm",
    "USDA NASS (2026). Cropland Data Layer, 2025. https://www.nass.usda.gov/Research_and_Science/Cropland/SARS1a.php",
    "Wagner, W., Lemoine, G., & Rott, H. (1999). A method for estimating soil moisture from ERS scatterometer and soil data. Remote Sens. Environ., 70, 191–207.",
    "Weston, P., de Rosnay, P., & Fairbairn, D. (2024). Soil moisture data assimilation at ECMWF. EGU General Assembly 2024, EGU24-1769. https://meetingorganizer.copernicus.org/EGU24/EGU24-1769.html",
    "WMO OSCAR (2026). Satellite: ROSE-L A (updated 19 October 2026). https://space.oscar.wmo.int/satellites/view/rose_l_a",
    "Vermote, E., & Wolfe, R. (2021). MODIS/Terra (MOD09GA) and Aqua (MYD09GA) Surface Reflectance Daily L2G Global 1 km and 500 m SIN Grid V061 (state_1km cloud mask). NASA LP DAAC. https://doi.org/10.5067/MODIS/MOD09GA.061",
    "Yueh, S. H., Shah, R., Xu, X., Elder, K., & Starr, B. (2020). Experimental demonstration of soil moisture remote sensing using P-band satellite signals of opportunity. IEEE Geosci. Remote Sens. Lett., 17(2), 207–211. https://doi.org/10.1109/LGRS.2019.2918764",
    "Yueh, S. H., Shah, R., Xu, X., Stiles, B., & Bosch-Lluis, X. (2021). A satellite synthetic aperture radar concept using P-band signals of opportunity. IEEE J. Sel. Topics Appl. Earth Observ. Remote Sens., 14, 2796–2816. https://doi.org/10.1109/JSTARS.2021.3059242",
    "Zanaga, D., Van De Kerchove, R., Daems, D., et al. (2022). ESA WorldCover 10 m 2021 v200. Zenodo. https://doi.org/10.5281/zenodo.7254221",
    "Zappa, L., et al. (2022). How accurately can we retrieve irrigation timing and water amounts from (satellite) soil moisture? Int. J. Appl. Earth Obs. Geoinf., 113, 102979. https://doi.org/10.1016/j.jag.2022.102979",
    "Unit costs: AWS EC2 m6i.2xlarge (https://www.doit.com/compute/spot/us-east-1/m6i.2xlarge); AWS S3 (https://aws.amazon.com/s3/pricing/); Stevens HydraProbe (https://www.fondriest.com/stevens-hydraprobe-soil-moisture-sensors.htm); IEEE 2026 APC list (https://journals.ieeeauthorcenter.ieee.org/wp-content/uploads/sites/7/2026-07-30-IEEE-Article-Processing-Charges-List.pdf); AGU 2024 registration and abstract fees (https://agu.org/annual-meeting-2024/attend; https://www.agu.org/annual-meeting-2024/About).",
]
