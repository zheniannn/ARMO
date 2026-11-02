"""Presentation deck (16:9) for the 5 Nov live talk; numbers read from results via load_values()."""
import os, importlib.util
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION
from PIL import Image
from common import ROOT, FIG

spec = importlib.util.spec_from_file_location("br", os.path.join(os.path.dirname(__file__), "20_build_report.py"))
br = importlib.util.module_from_spec(spec); spec.loader.exec_module(br)
import report_text as rt

OUT = os.path.join(ROOT, "slides", "ARMO_Slides_ES4304.pptx")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

NAVY = RGBColor(0x13, 0x29, 0x3D); TEAL = RGBColor(0x1B, 0x6F, 0x8A); AMBER = RGBColor(0xE8, 0xA3, 0x3D)
INK = RGBColor(0x1A, 0x1A, 0x1A); GREY = RGBColor(0x55, 0x55, 0x55); MIST = RGBColor(0xEE, 0xF3, 0xF6)
WHITE = RGBColor(0xFF, 0xFF, 0xFF); SOFT = RGBColor(0xCA, 0xDC, 0xE6)
HEAD, BODY = "Cambria", "Calibri"
W, H = Inches(13.333), Inches(7.5)


def f0(x): return f"{x:.0f}"


class Deck:
    def __init__(self):
        self.p = Presentation(); self.p.slide_width, self.p.slide_height = W, H
        self.blank = self.p.slide_layouts[6]; self.n = 0

    def slide(self, dark=False):
        s = self.p.slides.add_slide(self.blank); self.n += 1
        bg = s.background.fill; bg.solid(); bg.fore_color.rgb = NAVY if dark else WHITE
        if not dark:
            self.text(s, f"{self.n}", Inches(12.5), Inches(7.0), Inches(0.5), Inches(0.3), 10, GREY, align=PP_ALIGN.RIGHT,
                      name="SlideNum")
            self.text(s, "ES4304 | ARMO proposal", Inches(0.6), Inches(7.0), Inches(4), Inches(0.3), 10, GREY)
        return s

    def text(self, s, txt, x, y, w, h, size, color=INK, bold=False, font=BODY, align=PP_ALIGN.LEFT, italic=False,
             anchor=MSO_ANCHOR.TOP, name=None):
        tb = s.shapes.add_textbox(x, y, w, h)
        if name: tb.name = name
        tf = tb.text_frame; tf.word_wrap = True; tf.vertical_anchor = anchor
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        lines = txt if isinstance(txt, list) else [txt]
        for i, line in enumerate(lines):
            par = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            par.alignment = align
            r = par.add_run(); r.text = line
            r.font.size = Pt(size); r.font.color.rgb = color; r.font.bold = bold; r.font.name = font; r.font.italic = italic
            par.space_after = Pt(6)
        return tb

    def title(self, s, t, sub=None):
        self.text(s, t, Inches(0.6), Inches(0.35), Inches(12.1), Inches(0.8), 32, NAVY, bold=True, font=HEAD, name="Title")
        if sub:
            self.text(s, sub, Inches(0.6), Inches(1.12), Inches(12.1), Inches(0.45), 16, TEAL, italic=True)

    def bullets(self, s, items, x, y, w, h, size=16, color=INK):
        tb = s.shapes.add_textbox(x, y, w, h); tf = tb.text_frame; tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = 0
        for i, it in enumerate(items):
            par = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            bold_part, rest = (it.split("|", 1) + [""])[:2] if "|" in it else ("", it)
            r0 = par.add_run(); r0.text = "▪  "; r0.font.color.rgb = AMBER; r0.font.size = Pt(size); r0.font.name = BODY
            if bold_part:
                r = par.add_run(); r.text = bold_part; r.font.bold = True; r.font.size = Pt(size); r.font.color.rgb = color; r.font.name = BODY
            r = par.add_run(); r.text = rest; r.font.size = Pt(size); r.font.color.rgb = color; r.font.name = BODY
            par.space_after = Pt(10)
        return tb

    def image(self, s, fname, x, y, max_w, max_h):
        path = os.path.join(FIG, fname)
        iw, ih = Image.open(path).size
        sc = min(max_w / iw, max_h / ih)
        w, h = int(iw * sc), int(ih * sc)
        return s.shapes.add_picture(path, x + int((max_w - w) / 2), y, w, h)

    def card(self, s, x, y, w, h, head, body, big=None, fill=MIST, head_color=NAVY, body_size=17):
        r = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
        r.adjustments[0] = 0.06; r.fill.solid(); r.fill.fore_color.rgb = fill; r.line.fill.background(); r.shadow.inherit = False
        yy = y + Inches(0.2)
        if big:
            self.text(s, big, x + Inches(0.25), yy, w - Inches(0.5), Inches(0.9), 40, AMBER if fill != MIST else TEAL, bold=True, font=HEAD)
            yy += Inches(0.85)
        self.text(s, head, x + Inches(0.25), yy, w - Inches(0.5), Inches(0.7), 18, head_color, bold=True)
        self.text(s, body, x + Inches(0.25), yy + Inches(0.75), w - Inches(0.5), h - (yy - y) - Inches(0.5), body_size,
                  INK if fill == MIST else WHITE)

    def notes(self, s, t):
        s.notes_slide.notes_text_frame.text = t

    def move_to_backup(self, titles):
        """Append a 'Backup slides' divider, move the slides whose title is in `titles` after it, renumber."""
        s = self.slide(dark=True)
        self.text(s, "Backup slides", Inches(0.8), Inches(2.8), Inches(11), Inches(1.0), 40, AMBER, bold=True, font=HEAD)
        self.text(s, "For questions: marginal value, orbit designs, traceability, frequency options",
                  Inches(0.8), Inches(3.9), Inches(11), Inches(0.6), 20, SOFT)
        lst = self.p.slides._sldIdLst
        ids = list(lst)
        title = lambda sl: next((sh.text_frame.text for sh in sl.shapes if sh.name == "Title"), "")
        moving = [ids[i] for i, sl in enumerate(self.p.slides) if title(sl) in titles]
        assert len(moving) == len(titles), [title(sl) for sl in self.p.slides]
        for el in moving:
            lst.remove(el); lst.append(el)
        for k, sl in enumerate(self.p.slides, 1):
            for sh in sl.shapes:
                if sh.name == "SlideNum":
                    sh.text_frame.paragraphs[0].runs[0].text = str(k)
        self.n_main = len(ids) - len(moving)

    def save(self):
        self.p.save(OUT)


def build(V):
    d = Deck()
    d1, d2, i1, i2, t1, t2 = rt.budget(); total = t1 + t2
    nis = rt.has(V, "nis_n_rec")
    H = V["h2h"].capture * 100
    dlo, dhi = sorted([V['nis_P_detect_hh_valid_1sigma'] * 100, V['nis_P_detect_sat_valid_1sigma'] * 100])
    a1, n1 = H["ARMO alone (design D)"], H["NISAR alone"]
    r6, r3 = H["ROSE-L alone, 6-day"], H["ROSE-L alone, 3-day"]
    Dp = V["depth"]
    SZ = V["siz"]

    # 1 title
    s = d.slide(dark=True)
    d.text(s, "Do field-scale radars blink through the rain?", Inches(0.8), Inches(1.6), Inches(11.5), Inches(1.4), 44, WHITE, bold=True, font=HEAD)
    d.text(s, f"Ground truth from {V['n_stations']} US Climate Reference Network stations tests whether Sentinel-1 and NISAR see "
              f"soil-moisture wetting events, and makes the case for launching ARMO, a targeted L-band revisit mission",
           Inches(0.8), Inches(3.2), Inches(11.0), Inches(1.0), 20, SOFT)
    d.text(s, "ES4304 Eyes on Earth | NASA ROSES-style proposal | 5 November 2026", Inches(0.8), Inches(5.6), Inches(11), Inches(0.4), 16, AMBER)
    d.text(s, "Tang Zhen Ian  [+ group members]", Inches(0.8), Inches(6.1), Inches(11), Inches(0.4), 16, WHITE)
    d.notes(s, "We are selling a problem: field-scale radar may be blind to the short wetting events that matter for floods "
               "and irrigation. We test it with independent ground truth before asking for a satellite.")

    # 2 problem
    s = d.slide(); d.title(s, "Every storm writes a two-day signal into the soil", "And most satellites look at the wrong moment")
    d.image(s, "fig3_stillwater_example.png", Inches(0.5), Inches(1.75), Inches(8.3), Inches(5.0))
    d.bullets(s, ["Moisture jumps within |hours of rain, then decays over 1–3 days",
                  "That state sets |runoff from the next storm, crop water and land–air fluxes",
                  f"At Stillwater, OK: |11 events, only 5 seen by any radar look"],
              Inches(9.0), Inches(2.0), Inches(3.9), Inches(4.5), 16)
    d.notes(s, "Hourly 5 cm soil moisture from the USCRN probe (blue). Shaded windows are when at least half the wetting is "
               "still present. Orange and violet ticks are actual Sentinel-1 and NISAR acquisitions.")

    # 3 why satellites miss
    s = d.slide(); d.title(s, "Resolution or revisit: today you must choose one", "Field scale needs SAR, and SAR revisits slowly")
    cards = [("SMAP radiometer", "~40 km footprint\n2–3 day revisit", "40 km"),
             ("Sentinel-1C/1D", "10 m C-band SAR\n6–12 day revisit; crops attenuate C-band", "6–12 d"),
             ("NISAR (2025)", "200 m L-band soil moisture\n12-day repeat; SM ~2× per 12 d", "12 d"),
             ("ROSE-L (planned)", "L-band, 6 d over global land (3 d Europe)\nLaunch ≥ 2030 (WMO OSCAR)", "≥ 2030")]
    for i, (h, b, big) in enumerate(cards):
        d.card(s, Inches(0.6 + i * 3.1), Inches(1.9), Inches(2.85), Inches(3.6), h, b, big=big, body_size=16)
    d.text(s, "Physics: L-band (24 cm) penetrates crops and senses ~5 cm; C-band (5.6 cm) senses ~1–2 cm and is attenuated by vegetation.",
           Inches(0.6), Inches(5.9), Inches(12), Inches(0.6), 15, GREY, italic=True)
    d.notes(s, "Radiometers have revisit but not resolution; SAR has resolution but not revisit. The swath is a small "
               "fraction of the orbit-to-orbit spacing.")

    # 3a need maps (Earth Engine)
    NE = V["need"]
    s = d.slide(); d.title(s, "Where the gap bites: the Midwest and East", "Sentinel-1 revisits slowest where rain, and farms, are most frequent")
    d.image(s, "fig7_need_maps.png", Inches(0.3), Inches(1.6), Inches(8.6), Inches(5.3))
    d.bullets(s, [f"Sentinel-1 revisit: |{NE.conus_R_s1_median:.1f} d median, 8–16 d over the Midwest and East",
                  f"Wetting events: |≈ {NE.conus_events_median:.0f} per season (gridMET, calibrated to USCRN, r = {NE.r_onsets_events:.2f})",
                  f"Missed by Sentinel-1: |≈ {NE.conus_missed_median:.0f} per season; ≈ {NE.crop_missed_median:.0f} on cropland",
                  f"ARMO adds: |≈ {NE.crop_gain_median:.0f} events per season on cropland, mostly the Corn Belt and Delta"],
              Inches(9.1), Inches(1.8), Inches(3.9), Inches(5), 15)
    d.notes(s, f"All from Google Earth Engine at 0.1 deg. (a) Sentinel-1 GRD distinct acquisition days, Apr-Oct 2026; they agree "
               f"with our Planetary Computer record at the stations (r = {NE.r_days_gee_vs_pc:.2f}). (b) gridMET storm onsets "
               f"(>= 5 mm after a drier day), scaled by {NE.k_events_per_onset:.2f} wetting events per onset, fitted at "
               f"{int(NE.n_station_seasons)} USCRN station-seasons. (c) events x (1 - E[min(1, W/R)]) with the USCRN windows. "
               f"(d) gain with a 1.4-day ARMO, where MODIS cropland >= 25 %.")

    # 3b niche
    s = d.slide(); d.title(s, "ARMO's niche: field scale plus fast revisit", "Open, all-weather, ≤ 200 m and ≤ 2 days over the US: nobody fills this box today")
    d.image(s, "fig_market_niche.png", Inches(0.4), Inches(1.65), Inches(7.6), Inches(5.2))
    d.bullets(s, ["NISAR SME2: |same 200 m L-band, but ~6-day revisit and 72 h latency",
                  "ROSE-L: |6 d global land (ESA); 3 d per eoPortal; launch ≥ 2030",
                  "Spire, Planet: |daily but modelled from coarse sensors, closed; Planet dropped 100 m",
                  f"Optical: |a clear look in only {f0(V['opt_daily'])} % of events, even daily",
                  "Novelty = |revisit, not resolution"],
              Inches(8.2), Inches(1.75), Inches(4.7), Inches(5.2), 15)
    d.notes(s, "Market review checked 2 Nov 2026 (market.pdf). Say it carefully: field-scale L-band already exists in NISAR. "
               "What does not exist is field-scale, all-weather, open soil moisture faster than every ~6 days over the US.")

    # 4 question
    s = d.slide(); d.title(s, "Research question")
    d.text(s, "Does today's field-scale radar fleet observe rain-driven soil-moisture wetting events and, if not, what revisit "
              "would a dedicated L-band mission need to capture ≥ 80 % of them?",
           Inches(0.6), Inches(1.3), Inches(12.1), Inches(1.2), 20, TEAL, italic=True)
    objs = [("O1  Measure", "Event duration and amplitude from hourly ground truth"),
            ("O2  Quantify", "Capture by regular revisits and by actual S1 / NISAR passes"),
            ("O3  Test", "Is a sampled event detectable? S1, NISAR, SMAP, ERA5-Land"),
            ("O4  Decide", "Revisit and noise requirements; marginal value of ARMO")]
    for i, (h, b) in enumerate(objs):
        d.card(s, Inches(0.6 + i * 3.1), Inches(2.65), Inches(2.85), Inches(2.45), h, b, body_size=17)
    d.bullets(s, ["H1: |events are shorter than the fleet's revisit, so most are missed",
                  "H2: |a sampled event's signal is smaller than today's change noise",
                  "H3: |a dedicated L-band revisit mission lifts capture to ≥ 80 %"],
              Inches(0.6), Inches(5.3), Inches(7.6), Inches(1.6), 15)
    d.text(s, ["Decadal Survey 2017: question H-4 (floods, droughts)", "Soil moisture TO-17: unallocated, no coverage after SMAP",
               "Two stages: retrieval study, then an Earth Venture-class mission"],
           Inches(8.5), Inches(5.3), Inches(4.3), Inches(1.6), 13, TEAL, italic=True)
    d.notes(s, "Three testable hypotheses. The 2017 Decadal Survey lists soil moisture as Targeted Observable TO-17 but left it "
               "unallocated because nothing is planned after SMAP and SMOS; it points such observables to Venture-class proposals. "
               "We are asking for the research that decides whether that mission should be built.")

    # 5 ground truth
    s = d.slide(); d.title(s, "Ground truth first: 120 reference stations, hourly", "NOAA US Climate Reference Network, warm seasons 2025–2026")
    d.image(s, "fig1_study_area.png", Inches(0.4), Inches(1.7), Inches(8.0), Inches(5.2))
    d.bullets(s, [f"{V['n_events']:,} |wetting events at {V['n_stations']} stations",
                  "Triplicate |5 cm probes, rain gauge, soil temperature",
                  "Independent: |used to validate, never to calibrate, satellite products",
                  "QC: |NUL-byte repair, frozen mask, ≥ 70 % valid hours",
                  f"Land cover (Earth Engine): |{V['n_lc'].get('Grassland', 0)} grassland, {V['n_lc'].get('Tree cover', 0)} tree, only {V['n_lc'].get('Cropland', 0)} cropland"],
              Inches(8.7), Inches(1.9), Inches(4.2), Inches(5), 15)
    d.notes(s, "Ground truth is the backbone. USCRN is NOAA's climate-grade network; it spans desert to humid forest. It deliberately avoids farms, which is a limitation for an agricultural mission.")

    # 6 method
    s = d.slide(); d.title(s, "Method: from probe to mission decision")
    d.image(s, "fig2_workflow.png", Inches(0.6), Inches(1.3), Inches(8.2), Inches(5.4))
    d.bullets(s, ["Event: |≥ 5 mm rain and a rise ≥ 0.03 m³/m³",
                  "Window: |time the anomaly stays ≥ 50 % of peak",
                  "Captured: |a satellite look falls inside the window",
                  "Real schedules: |14k S1 and 6k NISAR passes from STAC/CMR",
                  "Stats: |station bootstrap; 2026 holdout; 9 alternative thresholds"],
              Inches(9.0), Inches(1.5), Inches(3.9), Inches(5.2), 15)
    d.notes(s, "Beyond tutorials: cloud-native range reads of COG and HDF5 at 120 sites; sampling theory E[min(1,W/R)].")

    # 7 O1/O2
    s = d.slide(); d.title(s, f"Half of all events fade within {V['win_med_d']:.1f} days", "Capture falls quickly with revisit interval")
    d.image(s, "fig4_capture_vs_revisit.png", Inches(0.4), Inches(1.7), Inches(8.6), Inches(5.0))
    d.card(s, Inches(9.3), Inches(1.8), Inches(3.5), Inches(2.3), "captured at 6-day revisit", f"{f0(V['c3'])} % at 3 days; {f0(V['c1'])} % at 1 day",
           big=f"{f0(V['c6'])} %", body_size=16)
    d.card(s, Inches(9.3), Inches(4.35), Inches(3.5), Inches(2.3), "for 80 % capture", "Regular revisit from one system",
           big=f"≈ {V['R80']:.1f} d", body_size=16)
    d.notes(s, f"The analytical model matches simulation within {V['max_an_err']:.1f} points; 2025 and 2026 agree.")

    # 8 actual fleet
    s = d.slide(); d.title(s, "The real 2026 fleet sees about half of the events", "Even assuming every look were a perfect measurement")
    stats = [(f"{f0(V['s1_era'])} %", "Sentinel-1C/1D", f"median gap {V['gap_s1']:.1f} d"),
             (f"{f0(V['ni_era'])} %", "NISAR L-band", f"median gap {V['gap_ni']:.1f} d; max {V['maxgap_ni']:.0f} d"),
             (f"{f0(V['both_era'])} %", "S1 + NISAR", f"regular sampling at the same rate: {f0(V['reg_equiv'])} %")]
    for i, (big, h, b) in enumerate(stats):
        d.card(s, Inches(0.6 + i * 4.1), Inches(1.9), Inches(3.8), Inches(2.6), h, b, big=big, body_size=17)
    d.text(s, f"{V['n_era']:,} wetting events at {V['n_era_st']} stations, 17 Jun–31 Oct 2026. Looks cluster on consecutive days, "
              f"so uncoordinated timing costs ≈ {f0(V['reg_equiv'] - V['both_era'])} percentage points.",
           Inches(0.6), Inches(4.9), Inches(12), Inches(1.0), 17, INK)
    d.notes(s, "Capture is an upper bound on detection. Next slide: what happens when a look does land in an event.")

    # 9 O3
    s = d.slide(); d.title(s, "When sampled, can the sensor see it?", "Field-scale radars mostly not; the 9 km SMAP radiometer does better")
    d.image(s, "fig6_observability.png", Inches(0.4), Inches(1.6), Inches(7.9), Inches(5.3))
    items = [f"Sentinel-1 (C): |detects {f0(V['s1_P_detect_given_sampled_1sigma'] * 100)} % of sampled events; "
             f"noise ≈ {V['s1_noise_sm_equiv']:.2f} m³/m³",
             f"NISAR (L): |{f0(V['nis_P_detect_hh_valid_1sigma'] * 100)} % (σ⁰HH), {f0(V['nis_P_detect_sat_valid_1sigma'] * 100)} % (SME2); "
             f"noise no lower than C-band",
             f"SMAP 9 km: |{f0(V['sm_P_detect_1sigma'] * 100)} % when sampled, {f0(V['sm_end_to_end_era'] * 100)} % end to end, "
             f"but cannot resolve fields",
             f"ERA5-Land: |POD {f0(V['era_pod'])} %, false alarms {f0(V['era_far'])} %"]
    d.bullets(s, items, Inches(8.5), Inches(1.75), Inches(4.4), Inches(5.2), 14)
    d.notes(s, "Panel c is the detection chain: look in window x detect when sampled. NISAR SME2 is counted only where a valid "
               "retrieval pair exists (22 % if missing retrievals count as misses). SMAP looks twice a day with low noise, "
               "so frequency plus low noise make event detection possible, at 9 km.")

    # 9b requirement
    s = d.slide(); d.title(s, "What would it take to see the events?", "A detection model calibrated on all four sensors sets ARMO's noise requirement")
    req = [(f"≤ {V['snr_noise_req_70']:.3f}", "m³/m³ change noise", "detects 70 % of sampled events (model fits sensors within "
            f"{V['snr_calibrated_mae_pts']:.0f} pts)"),
           (f"{V['snr_req_db_L']:.2f} dB", "L-band σ⁰ noise needed", f"today {V['snr_now_db_L']:.2f} dB: a "
            f"{V['snr_now_db_L'] / V['snr_req_db_L']:.1f}× reduction"),
           (f"≈ {V['snr_looks_factor_L']:.0f}×", "more independent looks", "if the noise is speckle: a resolution vs noise trade")]
    for i, (big, h, b) in enumerate(req):
        d.card(s, Inches(0.6 + i * 4.1), Inches(1.9), Inches(3.8), Inches(3.0), h, b, big=big, body_size=16)
    d.text(s, "This turns the critical risk into a number ARMO's design must meet, and Phase A research must show is reachable "
              "(multi-looking, burst averaging, SMAP–SAR fusion).",
           Inches(0.6), Inches(5.3), Inches(12.1), Inches(1.0), 17, INK)
    d.notes(s, "Model: P(detect | event size A) = Phi(k A / n - 1), n = change noise in soil-moisture units, one factor k fitted "
               "across S1, NISAR HH, NISAR SME2 and SMAP. Solved for 70 % over the observed event sizes.")

    # 10 O4
    s = d.slide(); d.title(s, "What would ARMO add?", f"Large gain today; still +{f0(V['fut2'] - V['fut'])} points once ROSE-L flies")
    d.image(s, "fig5_marginal_value.png", Inches(0.4), Inches(1.6), Inches(8.9), Inches(4.2))
    d.card(s, Inches(9.5), Inches(1.8), Inches(3.3), Inches(2.2), "with ARMO 2-day, today", f"from {f0(V['cur'])} %", big=f"{f0(V['arm2'])} %")
    d.card(s, Inches(9.5), Inches(4.2), Inches(3.3), Inches(2.2), "added on top of ROSE-L", "2-day ARMO, points gained",
           big=f"+{f0(V['fut2'] - V['fut'])} pts")
    d.notes(s, "The value of a new satellite depends on what else flies. ROSE-L is simulated at ESA's documented "
               "two-satellite revisit over global land (6 days; 3 days applies to Europe only).")

    # 10a head-to-head
    s = d.slide(); d.title(s, f"Head to head: ARMO captures {a1 / n1:.0f}× as many events as NISAR",
                           f"Each system alone, scored on the same {V['n_era']} ground-truth events (Jun–Oct 2026)")
    mid = (dlo + dhi) / 200
    cd = CategoryChartData()
    cd.categories = ["NISAR (real passes)", "ROSE-L 6-day", "ROSE-L 3-day", "ARMO (2 smallsats)"]
    cd.add_series("Look inside the event window", [round(n1), round(r6), round(r3), round(a1)])
    cd.add_series("Event registered (look × detection)", [round(n1 * mid), round(r6 * mid), round(r3 * mid), round(a1 * 0.7)])
    gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.5), Inches(1.7), Inches(8.3), Inches(5.1), cd)
    ch = gf.chart; ch.has_legend = True; ch.legend.position = XL_LEGEND_POSITION.BOTTOM; ch.legend.include_in_layout = False
    ch.legend.font.size = Pt(13); ch.legend.font.name = BODY
    ch.value_axis.maximum_scale = 100; ch.value_axis.minimum_scale = 0; ch.value_axis.has_major_gridlines = True
    ch.value_axis.major_gridlines.format.line.color.rgb = RGBColor(0xDD, 0xDD, 0xDD)
    ch.value_axis.tick_labels.font.size = Pt(12); ch.category_axis.tick_labels.font.size = Pt(13)
    ch.value_axis.has_title = True; ch.value_axis.axis_title.text_frame.text = "Wetting events (%)"
    ch.value_axis.axis_title.text_frame.paragraphs[0].runs[0].font.size = Pt(12)
    for ser, col in zip(ch.plots[0].series, (TEAL, AMBER)):
        ser.format.fill.solid(); ser.format.fill.fore_color.rgb = col
    pl = ch.plots[0]; pl.gap_width = 60; pl.overlap = -5; pl.has_data_labels = True
    pl.data_labels.font.size = Pt(13); pl.data_labels.number_format = '0"%"'; pl.data_labels.number_format_is_linked = False
    pl.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
    d.card(s, Inches(9.1), Inches(1.8), Inches(3.8), Inches(2.4), "registered by ARMO, if it meets its requirement",
           f"NISAR today: {n1 * dlo / 100:.0f}–{n1 * dhi / 100:.0f} %", big=f"{a1 * 0.7:.0f} %", body_size=15)
    d.card(s, Inches(9.1), Inches(4.4), Inches(3.8), Inches(2.4), "with S1 + NISAR + ROSE-L",
           f"ARMO lifts capture from {f0(V['fut'])} % (6-day ROSE-L)", big=f"{f0(H['Sentinel-1 + NISAR + ROSE-L 6-day + ARMO'])} %", body_size=15)
    d.notes(s, f"Same events, same rules. NISAR uses its real 2026 passes; ROSE-L is a regular 6- or 3-day sampler; ARMO "
               f"is design D flown in our orbit model. Amber bars multiply capture by detection when sampled: NISAR's "
               f"measured {f0(dlo)}–{f0(dhi)} % (midpoint shown), assumed the same for ROSE-L, and ARMO's 70 % requirement, "
               f"which is not yet demonstrated. The gain is revisit: both are L-band at 200 m.")

    # 10b orbit feasibility
    s = d.slide(); d.title(s, "Can a real orbit deliver it?", "Simulated 620 km dawn-dusk orbits, scored against ground truth")
    D = V["designs"]
    rows = [["Design", "ARMO revisit", "Fleet + ARMO capture", "CONUS imaging duty"]]
    for _, r in D.iterrows():
        rows.append([r.design[3:], f"{r.armo_mean_gap_d:.1f} d", f"{r.capture_fleet_plus_armo * 100:.0f} %", f"{r.imaging_duty_conus * 100:.1f} %"])
    tbl = s.shapes.add_table(len(rows), 4, Inches(0.6), Inches(1.8), Inches(12.1), Inches(3.6)).table
    for c, wdt in enumerate((6.4, 1.8, 2.2, 1.7)):
        tbl.columns[c].width = Inches(wdt)
    for i, r in enumerate(rows):
        for j, v in enumerate(r):
            cell = tbl.cell(i, j); cell.text = v
            par = cell.text_frame.paragraphs[0]; par.runs[0].font.size = Pt(15); par.runs[0].font.name = BODY
            hl = i > 0 and r[0].startswith("2 sats (180")
            par.runs[0].font.bold = i == 0 or hl; par.runs[0].font.color.rgb = WHITE if i == 0 else INK
            cell.fill.solid(); cell.fill.fore_color.rgb = TEAL if i == 0 else (SOFT if hl else (MIST if i % 2 else WHITE))
    d.text(s, f"Only two satellites clear 80 %. Rolling left/right does not shorten a single satellite's revisit. "
              f"Regional imaging needs < 2 % of each orbit, far less than global mapping.",
           Inches(0.6), Inches(5.7), Inches(12.1), Inches(0.9), 17, INK)
    d.notes(s, "J2 sun-synchronous propagation, 10 s steps, 25-45 deg off-nadir ScanSAR, one side per pass; "
               "passes added to the real S1+NISAR schedule; 8 orbital phases.")

    # 10c mission concept
    s = d.slide(); d.title(s, "The ARMO mission concept", "Two L-band smallsats, one launch, field-scale wetness to forecasters within 24 hours")
    steps = [("Fly", "2 smallsats, 620 km dawn–dusk orbit, 180° apart"),
             ("Image", f"Only the US: {SZ.imaging_min_day:.0f} min/day, 362 km access, HH + HV"),
             ("Downlink", f"{SZ.data_gb_day:.0f} GB/day to polar ground stations, every orbit"),
             ("Process", "Cloud change-detection retrieval, 100–200 m"),
             ("Deliver", "NOAA National Water Model, USDA, open data, < 24 h")]
    for i, (h, b) in enumerate(steps):
        x = Inches(0.6 + i * 2.5)
        d.card(s, x, Inches(1.85), Inches(2.2), Inches(2.2), h, b, body_size=14)
        if i < len(steps) - 1:
            ar = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, x + Inches(2.22), Inches(2.8), Inches(0.26), Inches(0.35))
            ar.fill.solid(); ar.fill.fore_color.rgb = AMBER; ar.line.fill.background()
    specs = [(f"{SZ.wet_kg:.0f} kg", "per satellite, wet (30 % margin)"),
             (f"{SZ.reflector_d_m:.1f} m", f"mesh reflector, {SZ.antenna_area_m2:.0f} m²"),
             (f"{SZ.orbit_avg_w:.0f} W", f"orbit average; {SZ.P_peak_rf_w:.0f} W peak RF"),
             (f"${SZ.cost_total:.0f} M", "incl. launch, 3-yr ops, 30 % reserve")]
    for i, (big, h) in enumerate(specs):
        d.card(s, Inches(0.6 + i * 3.1), Inches(4.35), Inches(2.85), Inches(2.3), h, "", big=big, fill=MIST, body_size=12)
    d.notes(s, f"Antenna: at 45 deg off-nadir L-band needs >= {SZ.Amin_45_m2:.0f} m2 to avoid ambiguities (Freeman et al. 2000), "
               f"hence a {SZ.reflector_d_m:.1f} m mesh reflector, half NISAR's 12 m. Radar equation: NESZ -25 dB (2 dB better "
               f"than NISAR's ~-23 dB) needs ~{SZ.P_avg_rf_w:.0f} W average RF. Mass: bottom-up budget, reflector scaled from "
               f"< 8 kg at 3.35 m (Sushko et al. 2021); both satellites ({SZ.launch_kg:.0f} kg) fit one Firefly Alpha-class "
               f"launch (630 kg to 500 km SSO). Cost by analogy with NovaSAR-1 and CYGNSS, +-40 %; Earth Venture cap US$ 190 M.")

    # 11 ARMO concept
    s = d.slide(); d.title(s, "ARMO traceability: objective to requirement", "Baseline = design D (2 satellites); threshold = design C (1 satellite)")
    rows = [["Objective", "Requirement", "Evidence"],
            ["Capture ≥ 80 % of events", "Revisit ≤ 2 d, with or without ROSE-L", f"{f0(V['arm2'])} % today / {f0(V['fut2'])} % with ROSE-L"],
            ["Detect ≥ 70 % when sampled", f"Noise ≤ {V['snr_noise_req_70']:.3f} m³/m³ ({V['snr_req_db_L']:.2f} dB)", "Calibrated model; unverified"],
            ["See under vegetation", "L-band ~1.26 GHz, HH + HV", "Literature; L-band σ⁰ ahead only in sparse cover"],
            ["Field scale", "100–200 m, ScanSAR multi-look", "Trades against noise"],
            ["Orbit", "620 km dawn–dusk SSO, 180° apart", "Orbit simulation (D 81 %, C 77 %)"],
            ["Spacecraft", f"2 × {SZ.wet_kg:.0f} kg, {SZ.reflector_d_m:.1f} m reflector, one launch", f"Sizing: ≈ US$ {SZ.cost_total:.0f} M incl. launch"]]
    tbl = s.shapes.add_table(len(rows), 3, Inches(0.6), Inches(1.8), Inches(12.1), Inches(4.4)).table
    for c, wdt in enumerate((3.0, 4.6, 4.5)):
        tbl.columns[c].width = Inches(wdt)
    for i, r in enumerate(rows):
        for j, v in enumerate(r):
            cell = tbl.cell(i, j); cell.text = v
            par = cell.text_frame.paragraphs[0]; par.runs[0].font.size = Pt(15); par.runs[0].font.name = BODY
            par.runs[0].font.bold = i == 0; par.runs[0].font.color.rgb = WHITE if i == 0 else INK
            cell.fill.solid(); cell.fill.fore_color.rgb = TEAL if i == 0 else (MIST if i % 2 else WHITE)
    d.notes(s, "Mission cost is not requested here; analogs: NovaSAR-1 S-band smallsat (GBP 21 M UKSA investment), "
               "NISAR NASA life-cycle cost US$1,174 M (GAO 2026; US$867 M 2016 baseline).")

    # 11b frequency options
    s = d.slide(); d.title(s, "Why L-band, not P-band or UHF?", "Deeper sensing does not buy longer events, and P-band radar may not operate over the US")
    opts = [("P-band SAR (BIOMASS, 435 MHz)", "Secondary allocation behind US space-object tracking radars: may not operate over North America\n"
             "12 m reflector, not a smallsat; 6 MHz bandwidth; ionospheric correction"),
            ("UHF / P-band signals of opportunity", "Receive-only: reuses Navy MUOS signals, no licence needed\n"
             "≈ 200 m only at swath edge, ~1 km at centre; 7 satellites; one CubeSat demo (SNOOPI)"),
            ("L-band SAR (ARMO baseline)", "Senses ~5 cm, works under crops\nSame band as NISAR and ROSE-L: retrievals and calibration transfer")]
    for i, (h, b) in enumerate(opts):
        d.card(s, Inches(0.6 + i * 4.1), Inches(1.85), Inches(3.8), Inches(3.3), h, b, body_size=14)
    d.text(s, f"Ground truth at 10 cm (P/UHF depth): {Dp.loc[10, 'n_events']:,} events instead of {Dp.loc[5, 'n_events']:,}; "
              f"windows {Dp.loc[10, 'win_med_d']:.1f} d vs {Dp.loc[5, 'win_med_d']:.1f} d; a 2-day revisit captures "
              f"{Dp.loc[10, 'cap_R2'] * 100:.0f} % (5 cm: {Dp.loc[5, 'cap_R2'] * 100:.0f} %). Way forward: study a UHF receiver as a hosted secondary payload for root-zone moisture.",
           Inches(0.6), Inches(5.45), Inches(12.1), Inches(1.2), 16, INK)
    d.notes(s, "Sources: Quegan et al. 2019 RSE (BIOMASS, SOTR restriction, 12 m reflector, 6 MHz); Shen et al. 2021 IEEE TGRS "
               "(P-band ~7 cm vs L-band ~5 cm; >10 cm below 0.5 GHz); Yueh et al. 2020 IEEE GRSL (260 MHz tower, 0.02 m3/m3 "
               "against top 10 cm; single frequency dominated by surface moisture); Yueh et al. 2021 IEEE JSTARS (SoOp SAR concept); "
               "Garrison et al. 2024 Adv. Space Res. (SNOOPI). The 10 cm result is our own: same event rules on USCRN 10 cm probes.")

    # 12 verdict
    s = d.slide(dark=True)
    d.text(s, "Verdict: retrieval first, then launch ARMO", Inches(0.8), Inches(0.6), Inches(11.8), Inches(0.9), 38, AMBER, bold=True, font=HEAD)
    d.text(s, "The revisit gap is real and measured. Find out how good the sensor can be, then launch either way.",
           Inches(0.8), Inches(1.5), Inches(11.5), Inches(0.6), 20, WHITE)
    conds = [("Stage 1 (2027–28): retrieval", f"US$ {total / 1000:.0f} k, 2 years. Event retrieval on validated NISAR vs USCRN; result sets ARMO's sensor (looks, bandwidth, power)"),
             ("Stage 2 (2029–36): launch ARMO", f"Two {SZ.wet_kg:.0f} kg L-band smallsats, one launch ≈ 2033; ≈ US$ {SZ.cost_total:.0f} M, under the US$ 190 M Earth Venture cap"),
             ("It pays off either way", f"Retrieval works: {f0(a1 * 0.7)} % of events registered, 4–6× NISAR. "
              f"It doesn't: revisit alone still doubles NISAR ({f0(a1 * dlo / 100)}–{f0(a1 * dhi / 100)} % vs {f0(n1 * dlo / 100)}–{f0(n1 * dhi / 100)} %)")]
    for i, (h, b) in enumerate(conds):
        d.card(s, Inches(0.8 + i * 4.0), Inches(2.6), Inches(3.75), Inches(3.4), h, b, fill=TEAL, head_color=AMBER, body_size=18)
    d.notes(s, "We tried to kill our own mission with ground truth. It survives: the revisit gain is measured, the spacecraft "
               "fits a Venture-class budget. We fund retrieval first because its result decides how good ARMO's sensor must be, "
               "not whether ARMO flies: the revisit gain pays off either way. ROSE-L is assumed at ESA's 6-day "
               f"global-land revisit; at 3 days ARMO still adds {f0(H['Sentinel-1 + NISAR + ROSE-L 3-day + ARMO'] - V['opt'])} points.")

    # 13 limitations + timeline
    s = d.slide(); d.title(s, "Limitations and the two-stage plan")
    d.bullets(s, [f"Retrieval: |if 70 % is reached, {f0(a1 * 0.7)} % of events registered, 4–6× NISAR; if not, still 2×",
                  f"Reflector: |{SZ.reflector_d_m:.1f} m on a {SZ.wet_kg:.0f} kg satellite not yet flown; deployment test before build",
                  f"Cost: |± 40 %; descope to one satellite (≈ US$ {SZ.cost_threshold:.0f} M)",
                  f"Few farms: |only {V['n_lc'].get('Cropland', 0)} of {sum(V['n_lc'].values())} stations are cropland",
                  "Scope: |CONUS warm seasons; NISAR still provisional"],
              Inches(0.6), Inches(1.6), Inches(6.3), Inches(5), 17)
    plan = [("Stage 1 (2027–28), US$ 0.22 M", "Retrieval on validated NISAR vs USCRN; field campaign\nResult sets the sensor: looks, bandwidth, power"),
            ("Stage 2 build (2029–33)", "Design, reflector test, build two spacecraft; launch ≈ 2033"),
            ("Stage 2 operations (2034–36)", "Open products to NOAA and USDA in < 24 h")]
    for i, (h, b) in enumerate(plan):
        d.card(s, Inches(7.2), Inches(1.4 + i * 1.85), Inches(5.6), Inches(1.7), h, b, body_size=15)
    d.notes(s, "Each limitation has a fix. Point-vs-pixel mismatch is handled by the Phase B field campaign; P-band SAR is "
               "barred over the US and UHF signals of opportunity reach only ~1 km at swath centre, so L-band stays the baseline.")

    # 14 society + budget
    s = d.slide(); d.title(s, "Who would use it, and what it costs")
    cards = [("of US freshwater is for irrigation", "USGS Circular 1441 (2015 data)", "42 %"),
             ("2012 flash-drought damage", "NOAA 2013", "≈ $30 B"),
             ("Stage 1: retrieval study now", "2 years; personnel-driven; data free", f"${total / 1000:.0f} k"),
             ("Stage 2: ARMO mission", "Incl. launch; Earth Venture cap $190 M", f"${SZ.cost_total:.0f} M")]
    for i, (h, b, big) in enumerate(cards):
        d.card(s, Inches(0.6 + i * 3.1), Inches(1.4), Inches(2.9), Inches(2.4), h, b, big=big, body_size=15)
    d.bullets(s, ["NOAA National Water Model: |antecedent wetness for flood forecasts",
                  "USDA Crop-CASMA / FAS: |separate rain-fed from irrigated response",
                  "Water managers and insurers: |when and how much water reached a field",
                  "Commercial X-band alternative: |≈ US$ 19–20 M for the same looks, and physically unsuited"],
              Inches(0.6), Inches(4.2), Inches(12.1), Inches(2.6), 17)
    d.notes(s, "Weekly drought products do not need 2-day revisit; event-scale users do.")

    # 15 close
    s = d.slide(dark=True)
    d.text(s, "Take-home", Inches(0.8), Inches(0.8), Inches(11), Inches(0.8), 36, AMBER, bold=True, font=HEAD)
    take = [f"Wetting events last ~{V['win_med_d']:.1f} days; today's fleet captures {f0(V['cur'])} % at best",
            f"When sampled, field-scale radar detects {f0(V['nis_P_detect_hh_valid_1sigma'] * 100)}–{f0(V['nis_P_detect_sat_valid_1sigma'] * 100)} % of events; 9 km SMAP {f0(V['sm_P_detect_1sigma'] * 100)} %",
            f"Alone, ARMO captures {f0(a1)} % vs NISAR {f0(n1)} % and ROSE-L {f0(r6)}–{f0(r3)} %; with the fleet {V['designs'].capture_fleet_plus_armo.iloc[3] * 100:.0f} %",
            f"Stage 1: fund retrieval first (US$ {total / 1000:.0f} k) to learn how good ARMO's sensor can be",
            f"Stage 2: launch two {SZ.wet_kg:.0f} kg smallsats (≈ US$ {SZ.cost_total:.0f} M); revisit alone doubles NISAR, retrieval adds the rest",
            "Questions?"]
    d.bullets(s, take, Inches(0.8), Inches(1.9), Inches(11.5), Inches(4.5), 22, WHITE)
    d.move_to_backup(["What would ARMO add?", "Can a real orbit deliver it?", "ARMO traceability: objective to requirement",
                      "Why L-band, not P-band or UHF?"])
    d.save()
    print("saved", OUT, d.n, "slides")


if __name__ == "__main__":
    build(br.load_values())
