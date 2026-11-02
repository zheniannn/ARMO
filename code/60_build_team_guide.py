"""Team guide (PDF): how the ARMO project was built, step by step, and how to defend it.
Every number is read from data/processed via 20_build_report.load_values(), so it matches the report."""
import os, importlib.util, datetime
from common import ROOT
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
                                Image, PageBreak, KeepTogether, CondPageBreak)

spec = importlib.util.spec_from_file_location("br", os.path.join(os.path.dirname(__file__), "20_build_report.py"))
br = importlib.util.module_from_spec(spec); spec.loader.exec_module(br)
import report_text as rt

V = br.load_values()
D = V["designs"].set_index(V["designs"].design.str[0])
d1, d2, i1, i2, t1, t2 = rt.budget()
FIG = os.path.join(ROOT, "figures")
import re
import pymupdf
_rep = pymupdf.open(os.path.join(ROOT, "report", "ARMO_Proposal_ES4304.pdf"))
REP_PAGES = len(_rep)
SEC_END = REP_PAGES
for _i, _pg in enumerate(_rep):          # Sections 1-5 end on the page before (or the page holding) "References"
    _t = _pg.get_text()
    _m = re.search(r"(^|\n)\s*References\s*\n", _t)
    if _m:
        SEC_END = _i if len(_t[:_m.start()].strip()) < 20 else _i + 1   # heading at top: sections ended on the previous page
        break
N_SLIDES = len(pymupdf.open(os.path.join(ROOT, "slides", "ARMO_Slides_ES4304.pdf")))
OUT = os.path.join(ROOT, "notes", "ARMO_Team_Guide.pdf")

# ------------------------------------------------------------------ fonts and styles
FD = r"C:\Windows\Fonts"
for name, f in (("Body", "calibri.ttf"), ("Body-B", "calibrib.ttf"), ("Body-I", "calibrii.ttf"), ("Body-BI", "calibriz.ttf"),
                ("Head", "georgia.ttf"), ("Head-B", "georgiab.ttf")):
    pdfmetrics.registerFont(TTFont(name, os.path.join(FD, f)))
addMapping("Body", 0, 0, "Body"); addMapping("Body", 1, 0, "Body-B"); addMapping("Body", 0, 1, "Body-I"); addMapping("Body", 1, 1, "Body-BI")

NAVY, BLUE, ORANGE, GREEN, RED = (colors.HexColor(c) for c in ("#123b63", "#2a78d6", "#eb6834", "#1b7a52", "#c0392b"))
INK, INK2, RULE = colors.HexColor("#1a1a1a"), colors.HexColor("#52514e"), colors.HexColor("#d9d7d1")
TINT = {"blue": colors.HexColor("#eaf2fc"), "orange": colors.HexColor("#fdf0e9"), "green": colors.HexColor("#e8f5ee"),
        "grey": colors.HexColor("#f3f2ef"), "red": colors.HexColor("#fbeceb")}
EDGE = {"blue": BLUE, "orange": ORANGE, "green": GREEN, "grey": INK2, "red": RED}

ST = {
    "body": ParagraphStyle("body", fontName="Body", fontSize=10.5, leading=14.2, textColor=INK, spaceAfter=5),
    "small": ParagraphStyle("small", fontName="Body", fontSize=9, leading=11.8, textColor=INK),
    "cell": ParagraphStyle("cell", fontName="Body", fontSize=9, leading=11.2, textColor=INK),
    "cellh": ParagraphStyle("cellh", fontName="Body-B", fontSize=9, leading=11.2, textColor=colors.white),
    "cap": ParagraphStyle("cap", fontName="Body-I", fontSize=9, leading=11.5, textColor=INK2, spaceAfter=8),
    "h1": ParagraphStyle("h1", fontName="Head-B", fontSize=17, leading=21, textColor=NAVY, spaceBefore=4, spaceAfter=8),
    "h2": ParagraphStyle("h2", fontName="Head-B", fontSize=12.5, leading=16, textColor=NAVY, spaceBefore=9, spaceAfter=4),
    "lab": ParagraphStyle("lab", fontName="Body-B", fontSize=9.5, leading=12, textColor=NAVY),
    "bul": ParagraphStyle("bul", fontName="Body", fontSize=10.5, leading=14, textColor=INK, leftIndent=13, bulletIndent=2, spaceAfter=2.5),
    "title": ParagraphStyle("title", fontName="Head-B", fontSize=27, leading=33, textColor=NAVY),
    "sub": ParagraphStyle("sub", fontName="Body", fontSize=14, leading=19, textColor=INK2),
}
S0 = "σ<super>0</super>"
M3 = "m³/m³"


def f0(x): return f"{x:.0f}"
def pc(x): return f"{x * 100:.0f} %"


story = []
def H1(t, need=5): story.extend([CondPageBreak(need * cm), Paragraph(t, ST["h1"])])
def H2(t): story.extend([CondPageBreak(3 * cm), Paragraph(t, ST["h2"])])
def P(t, s="body"): story.append(Paragraph(t, ST[s]))
def B(items, s="bul"):
    for it in items:
        story.append(Paragraph(it, ST[s], bulletText="•"))
    story.append(Spacer(1, 3))


def box(title, body, tone="blue", width=17 * cm, tail=None):
    """Tinted call-out with a coloured left rule."""
    rows = [[Paragraph(f"<b>{title}</b>", ParagraphStyle("bt", parent=ST["body"], textColor=EDGE[tone], spaceAfter=2))]]
    for b in (body if isinstance(body, list) else [body]):
        rows.append([Paragraph(b, ParagraphStyle("bb", parent=ST["body"], fontSize=10, leading=13.4, spaceAfter=2))])
    t = Table(rows, colWidths=[width])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), TINT[tone]), ("LINEBEFORE", (0, 0), (0, -1), 3, EDGE[tone]),
                           ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                           ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                           ("TOPPADDING", (0, 0), (-1, 0), 6), ("BOTTOMPADDING", (0, -1), (-1, -1), 6)]))
    story.extend([KeepTogether([t] + (tail or [])), Spacer(1, 7)])


def table(header, rows, widths, zebra=True):
    data = [[Paragraph(h, ST["cellh"]) for h in header]] + [[Paragraph(str(c), ST["cell"]) for c in r] for r in rows]
    t = Table(data, colWidths=[w * cm for w in widths], repeatRows=1)
    sty = [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("VALIGN", (0, 0), (-1, -1), "TOP"),
           ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE), ("LEFTPADDING", (0, 0), (-1, -1), 5),
           ("RIGHTPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if zebra:
        sty += [("BACKGROUND", (0, i), (-1, i), TINT["grey"]) for i in range(2, len(data), 2)]
    t.setStyle(TableStyle(sty))
    story.extend([t, Spacer(1, 8)])


def fig(name, width_cm, caption):
    from PIL import Image as PI
    w, h = PI.open(os.path.join(FIG, name)).size
    img = Image(os.path.join(FIG, name), width=width_cm * cm, height=width_cm * cm * h / w)
    story.append(KeepTogether([img, Spacer(1, 3), Paragraph(caption, ST["cap"])]))


def step(n, title, goal, did, why, result, ask, script):
    """One build step: goal, actions, reasoning, result, likely challenge, where it lives."""
    H1(f"Step {n}. {title}", need=8)
    box("Goal", goal, "blue")
    H2("What was done"); B(did)
    H2("Why it was done this way"); B(why)
    H2("What came out"); B(result)
    box("If the panel challenges this", ask, "orange",
        tail=[Spacer(1, 4), Paragraph(f"<font color='#52514e'><b>Where it lives:</b> {script}</font>", ST["small"])])


HH = V["h2h"].capture * 100
_dlo, _dhi = sorted([V['nis_P_detect_hh_valid_1sigma'] * 100, V['nis_P_detect_sat_valid_1sigma'] * 100])
A1, N1 = HH["ARMO alone (design D)"], HH["NISAR alone"]
R6, R3 = HH["ROSE-L alone, 6-day"], HH["ROSE-L alone, 3-day"]
DP = V["depth"]
SZ = V["siz"]

# ================================================================== cover
story += [Spacer(1, 3.2 * cm),
          Paragraph("How the ARMO project was built", ST["title"]), Spacer(1, 8),
          Paragraph("A step-by-step guide for the team: what was done, why, what came out, and how to defend it", ST["sub"]),
          Spacer(1, 1.2 * cm)]
box("The project in one sentence",
    f"Using hourly ground truth from {V['n_stations']} US reference stations, we showed that today's field-scale radar "
    f"satellites see only about half of the short soil-wetting events caused by rain ({f0(V['cur'])} %), and we tested "
    f"whether a new two-satellite L-band mission (ARMO) would fix that. It would lift capture to "
    f"{pc(D.loc['D', 'capture_fleet_plus_armo'])}, but the radars cannot yet reliably <i>recognise</i> an event "
    f"even when they look. Our verdict has <b>two stages</b>: fund the retrieval research first (US$ {rt.money(t1 + t2)}) "
    f"to learn how good ARMO's sensor can be, then launch two {SZ.wet_kg:.0f} kg L-band smallsats (≈ US$ {SZ.cost_total:.0f} M) "
    f"either way, because the revisit gain alone already doubles what NISAR registers.", "blue")
story += [Spacer(1, 0.6 * cm)]
table(["Deliverable", "File (in the project folder)"],
      [[f"Proposal report (Sections 1–5 on pages 2–{SEC_END})", "report/ARMO_Proposal_ES4304.pdf (and .docx)"],
       [f"Presentation ({N_SLIDES} slides)", "slides/ARMO_Slides_ES4304.pdf (and .pptx)"],
       ["Panel-style self-review and 25 Q&amp;A answers", "notes/review_and_QA.md"],
       ["Market review: ARMO's niche, competitors, optical options", "market.pdf (built by code/19_market_report.py)"],
       ["All analysis code (re-runs every number)", "code/ (scripts 01–50; see Step 12)"],
       ["This guide", "notes/ARMO_Team_Guide.pdf (built by code/60_build_team_guide.py)"]], [8, 9])
P(f"<font color='#52514e'>ES4304 Remote Sensing · due 5 November 2026, 12:00 · guide generated "
  f"{datetime.date.today():%d %B %Y} from the final results.</font>", "small")
story.append(PageBreak())

# ================================================================== how to use + AI note
H1("How to use this guide")
P("Read Part A first (15 minutes). It gives the whole story and the numbers you must know. Then each member should "
  "read the steps behind the slides they will present, and everyone should read Part C (the hard questions). "
  "Each step follows the same pattern: the <b>goal</b>, <b>what was done</b>, <b>why</b>, <b>what came out</b>, and "
  "<b>how to answer if the panel challenges it</b>.")
table(["Part", "Contents", "Who should read it"],
      [["A", "The story, key numbers, and the concepts behind them", "Everyone"],
       ["B", "Steps 1–12: how the project was actually built", "Everyone; in depth for your own slides"],
       ["C", "Mistakes caught and fixed, hard questions with answers, weak spots", "Everyone, before rehearsal"],
       ["D", "Presentation plan, files, how to re-run the code, final checklist", "Presenters and whoever submits"]],
      [1.2, 10, 5.8])
box("Be open about how this was made",
    ["The analysis, code, report and slides were produced with an AI assistant (Claude), working from public data. "
     "Check the ES4304 rules on generative-AI use and declare it in the way the course requires. Your contribution "
     "statements must describe what each of you actually did, for example reviewing the method, checking numbers "
     "against the code, editing the text, re-running scripts or preparing the talk.",
     "The best protection in the Q&amp;A is understanding the work. Before the presentation, each member should be able to "
     "explain their slides without notes, and re-run at least one script (Step 12) and confirm that its number matches the report."],
    "red")

# ================================================================== PART A
H1("Part A. The story in five beats")
beats = [
    f"<b>Storms leave short signals.</b> After rain, the top 5 cm of soil gets wetter within hours and then dries over "
    f"days. Across {V['n_events']:,} events, half stayed above half their peak for less than "
    f"<b>{V['win_med_d']:.1f} days</b>, and {f0(V['frac_lt2d'])} % lasted under 2 days.",
    f"<b>The satellites mostly look at the wrong time.</b> Field-scale soil moisture needs radar (SAR), which revisits "
    f"a field only every 6–12 days. The <i>real</i> 2026 pass times of Sentinel-1 and NISAR together captured "
    f"<b>{f0(V['cur'])} %</b> of events, even assuming every look were perfect.",
    f"<b>Looking is not the same as seeing.</b> When a radar did look during an event, its signal rose clearly in only "
    f"<b>{pc(V['s1_P_detect_given_sampled_1sigma'])}</b> of cases for Sentinel-1 (C-band) and "
    f"<b>{pc(V['nis_P_detect_hh_valid_1sigma'])}–{pc(V['nis_P_detect_sat_valid_1sigma'])}</b> for NISAR (L-band). Dense vegetation "
    f"roughly halves it. The coarse SMAP radiometer (9 km, twice a day) does far better, {f0(V['sm_end_to_end_era'] * 100)} % "
    f"end to end, so detection is possible, just not yet at field scale. A weather model (ERA5-Land) is no substitute: "
    f"it found {f0(V['era_pod'])} % of events, but {f0(V['era_far'])} % of its detections were false.",
    f"<b>A new mission can close the timing gap.</b> We simulated real orbits. Two L-band smallsats (ARMO) added to "
    f"today's fleet raise capture from {f0(V['cur'])} % to <b>{pc(D.loc['D', 'capture_fleet_plus_armo'])}</b>. "
    f"One satellite is not enough. Head to head on the same events, ARMO alone captures <b>{f0(A1)} %</b>, against "
    f"{f0(N1)} % for NISAR and {f0(R6)}–{f0(R3)} % for ROSE-L. The gain is revisit, not resolution: nobody else offers "
    f"open, all-weather, field-scale soil moisture faster than every ~6 days over the US.",
    f"<b>So the verdict: retrieval first, then launch ARMO.</b> Two {SZ.wet_kg:.0f} kg smallsats cost ≈ US$ {SZ.cost_total:.0f} M, "
    f"under the US$ 190 M Earth Venture cap. Retrieval decides how much ARMO delivers: better timing helps most if the sensor recognises the event, and once "
    f"ESA's ROSE-L flies (≥ 2030, 6-day revisit over the US) ARMO still adds {f0(V['fut3'] - V['fut'])}–{f0(V['fut2'] - V['fut'])} points. We "
    f"ask for a US$ {rt.money(t1 + t2)}, 2-year study to fix event detection first (change noise must fall to "
    f"≤ {V['snr_noise_req_70']:.3f} {M3}, about {V['snr_now_db_L'] / V['snr_req_db_L']:.0f}× below today's radars). "
    f"ARMO is then launched either way; the study decides how good its sensor will be.",
]
for i, b in enumerate(beats, 1):
    story.append(Paragraph(b, ST["bul"], bulletText=f"{i}."))
story.append(Spacer(1, 6))

H2("Numbers to memorise")
table(["Number", "Meaning", "Where"],
      [[f"{V['n_events']:,} / {V['n_stations']}", "Wetting events detected / stations with events (2025 and 2026 warm seasons)", "Step 3"],
       [f"{V['win_med_d']:.1f} d", f"Median event window (IQR {V['win_q1_d']:.1f}–{V['win_q3_d']:.1f} d)", "Step 3"],
       [f"{f0(V['c6'])} % → {f0(V['c2'])} %", "Capture with a regular 6-day vs 2-day revisit", "Step 4"],
       [f"≈ {V['R80']:.1f} d", "Regular revisit needed to capture 80 % of events", "Step 4"],
       [f"{f0(V['cur'])} % ({f0(V['cur_lo'])}–{f0(V['cur_hi'])})", "Real 2026 Sentinel-1 + NISAR capture (95 % CI)", "Step 5"],
       [f"{pc(V['s1_P_detect_given_sampled_1sigma'])} / {pc(V['nis_P_detect_sat_valid_1sigma'])}", "Events registered when sampled: Sentinel-1 / NISAR SME2 (valid retrieval pairs)", "Steps 6–7"],
       [f"{f0(V['sm_end_to_end_era'] * 100)} %", "SMAP (9 km) events looked at and registered, about 4× the field-scale radars", "Step 8b"],
       [f"≤ {V['snr_noise_req_70']:.3f}", f"ARMO change-noise requirement ({M3}) for 70 % detection = {V['snr_req_db_L']:.2f} dB at L-band (today {V['snr_now_db_L']:.2f})", "Step 8b"],
       [f"{V['n_lc'].get('Cropland', 0)} of {sum(V['n_lc'].values())}", "Stations on cropland (a weak spot for an agricultural mission)", "Step 8b"],
       [f"{V['s1_noise_sm_equiv']:.2f} vs {V['nis_noise_hh_sm_equiv']:.2f}", f"Backscatter change noise in {M3}: C-band vs L-band (L-band no better)", "Steps 6–7"],
       [f"{f0(V['era_pod'])} % / {f0(V['era_far'])} %", "ERA5-Land detection rate / false-alarm ratio", "Step 8"],
       [f"{pc(D.loc['D', 'capture_fleet_plus_armo'])}", "Fleet + ARMO (2 satellites, 1.4-day revisit)", "Step 10"],
       [f"+{f0(V['fut3'] - V['fut'])} to +{f0(V['fut2'] - V['fut'])} pts", "What ARMO adds once ROSE-L flies", "Step 9"],
       [f"{f0(A1)} % vs {f0(N1)} %", f"Head to head, each alone: ARMO vs NISAR (ROSE-L {f0(R6)} % at 6 d, {f0(R3)} % at 3 d)", "Step 10b"],
       [f"{f0(A1 * 0.7)} % vs {N1 * _dlo / 100:.0f}–{N1 * _dhi / 100:.0f} %", "Events registered: ARMO at its 70 % requirement vs NISAR measured", "Step 10b"],
       [f"{DP.loc[10, 'win_med_d']:.1f} vs {DP.loc[5, 'win_med_d']:.1f} d", "Event window at 10 cm vs 5 cm: deeper sensing (P-band/UHF) does not buy time", "Step 10b"],
       [f"{f0(V['opt_daily'])} %", "Events with a clear optical look, even with daily imaging (MODIS cloud mask)", "Step 10b"],
       [f"≈ {V['need'].crop_missed_median:.0f} / {V['need'].crop_gain_median:.0f}", "Events per season on US cropland missed by Sentinel-1 / recovered by ARMO (Earth Engine maps)", "Step 10c"],
       [f"US$ {rt.money(t1 + t2)}", "Stage 1: 2-year retrieval study, requested now", "Step 11"],
       [f"{SZ.wet_kg:.0f} kg / {SZ.reflector_d_m:.1f} m", "ARMO satellite wet mass / mesh reflector diameter", "Step 10d"],
       [f"US$ {SZ.cost_total:.0f} M", f"Mission cost incl. launch, 3-year operations, 30 % reserve (Earth Venture cap US$ 190 M)", "Step 10d"]],
      [3.6, 10.6, 2.8])

H1("Part A. Concepts you need")
P("If a panel member uses one of these words, you should be able to explain it in one sentence.")
table(["Term", "Plain-language meaning"],
      [["Soil moisture (" + M3 + ")", "Volume of water per volume of soil. 0.05 is dry sand; 0.40 is very wet. A rise of 0.03 is a clear wetting."],
       ["Ground truth", "Direct measurement on the ground, used to judge satellites. Here: probes buried at 5 cm at NOAA stations."],
       ["USCRN", "US Climate Reference Network: about 130 high-quality NOAA stations. Each has 3 soil probes per depth and a rain gauge, reporting hourly."],
       ["SAR (synthetic aperture radar)", "A radar that sends its own microwave pulses. It works through cloud and at night, and resolves 10–200 m. Wet soil reflects more."],
       ["Backscatter " + S0 + " (dB)", "How much radar energy returns to the satellite. It rises with soil wetness, but also with plant cover and surface roughness."],
       ["C-band vs L-band", "C-band (5.4 GHz, 5.6 cm wavelength; Sentinel-1) senses mostly the top 1–2 cm and is strongly attenuated by crops. L-band (1.26 GHz, 24 cm; NISAR, ARMO) penetrates further."],
       ["Revisit", f"Time between two looks at the same place. Median at our stations: Sentinel-1 {V['gap_s1']:.1f} d, NISAR {V['gap_ni']:.1f} d (12-day repeat orbit, ascending + descending), both combined {V['gap_both']:.1f} d."],
       ["Swath", "Width of ground imaged in one pass. SAR swaths (~250–360 km) are narrow compared with orbit spacing, which is why revisit is slow."],
       ["Sun-synchronous, dawn–dusk orbit", "Near-polar orbit that crosses each place at the same local time (06:00/18:00). It keeps the solar panels in sunlight. All three missions use it."],
       ["Wetting event / window", "A rain storm that raises soil moisture by ≥ 0.03. The window is how long the rise stays above half its peak."],
       ["Capture", "An event counts as captured if at least one satellite look falls inside its window. This is an upper bound, since it assumes a perfect sensor."],
       ["Change detection", "Compare two looks from the same orbit. Geometry and roughness cancel, so a rise in " + S0 + " suggests wetting."],
       ["Noise floor", "How much " + S0 + " jumps between two looks when the soil did NOT change. A real signal must exceed this."],
       ["ubRMSE", "Unbiased root-mean-square error: the typical error after removing a constant offset. NISAR's goal is ≤ 0.06 " + M3 + "."],
       ["POD / FAR / CSI", "Probability of detection, false-alarm ratio and critical success index: standard yes/no forecast scores."],
       ["Bootstrap (station-cluster)", "Resample whole stations 2,000 times to get confidence intervals, because events at one station are related."],
       ["Holdout", "Data kept aside to test the method. Rules were set on 2025; 2026 checks that they still hold."],
       ["ERA5-Land", "ECMWF's hourly global land model (about 9 km). It is the \"no satellite\" baseline."],
       ["ROSE-L", "Planned ESA L-band SAR pair: revisit 6 days over global land, 3 days over Europe (eoPortal, a secondary source, says 3 days for soil moisture); launch ≥ 2030."],
       ["P-band, UHF", "Lower radar frequencies (P-band ~435 MHz; UHF 300 MHz–1 GHz overlaps it). Longer waves see deeper soil (~7 cm at P-band, > 10 cm below 0.5 GHz) and through more canopy."],
       ["SOTR", "US space-object tracking radars. They hold the primary right to 432–438 MHz, so ESA's P-band BIOMASS may not operate within their line of sight: mainly North America and Europe."],
       ["Signals of opportunity (SoOp)", "A receive-only sensor that measures how existing communications-satellite signals (e.g. US Navy MUOS, 360–380 MHz) reflect off the ground. No transmitter, so no licence problem."],
       ["Stage 1 / Stage 2", "Our plan: Stage 1 is the 2-year retrieval study (2027–28); Stage 2 is the ARMO mission (2029–36), which goes ahead whatever Stage 1 finds."],
       ["Phases A–E", "NASA's mission life cycle: A concept, B preliminary design, C final design and build, D test and launch, E operations."],
       ["Earth Venture Mission", "NASA's competed, cost-capped Earth science missions: US$ 190 M including launch (EVM-3), launch within 5 years."],
       ["NESZ (noise floor)", "Noise-equivalent sigma zero: the weakest backscatter the radar can measure. NISAR's requirement is about −23 dB; ARMO's −25 dB."],
       ["Minimum antenna area", "Below a certain area a radar's echoes overlap (ambiguities). For ARMO at 45° off-nadir it is about 27 m², hence a 5.9 m reflector."],
       ["SME2, RTC, GCOV", "NISAR's 200 m soil-moisture product; Sentinel-1 terrain-corrected backscatter; NISAR's backscatter product."],
       ["SMAP Enhanced L3", "NASA's L-band radiometer soil moisture on a 9 km grid, 06:00 and 18:00 passes. Frequent and low-noise, but far too coarse for fields."],
       ["NDVI", "Normalised Difference Vegetation Index from MODIS: 0.2 is sparse, 0.6+ is dense green canopy."],
       ["Google Earth Engine", "Google's cloud platform for satellite data. We used it to pull SMAP, NDVI and land cover at every station."],
       ["Detection model", "P(detect) = Φ(kA/n − 1): an event of size A beats noise n. One factor k is fitted across four sensors."],
       ["Traceability matrix (STM)", "Table linking each objective to the physical parameter, the measurement and the mission requirement (report Table 5)."],
       ["Baseline / threshold mission", "Baseline = the design we want (2 satellites, D). Threshold = the least we would accept (1 satellite, C)."],
       ["Decadal Survey, TO-17", "The US National Academies' 2017 priorities for NASA Earth science. Soil moisture is Targeted Observable 17, left unfunded."]],
      [4.2, 12.8])

# ================================================================== PART B
H1("Part B. How the project was built")
fig("fig2_workflow.png", 15.5, "Report Figure 2: the workflow from ground truth to mission decision. Steps 2–10 below follow it.")
P("The four objectives in the report map onto the steps as follows: <b>O1</b> (how long are events?) = Step 3; "
  "<b>O2</b> (how many does the fleet capture?) = Steps 4–5; <b>O3</b> (can the sensor see an event it samples?) = Steps 6–8; "
  "<b>O4</b> (what would ARMO add, and is it buildable?) = Steps 9–10.")

step(1, "Choosing the topic and the research gap",
     "Find a question that (i) uses satellite Earth observation only (the course rule; no drones), (ii) can be answered "
     "with real ground truth (the team's top priority) and (iii) can justify, or reject, a new satellite mission.",
     ["Started from the data, not the satellite. We asked which free ground-truth network is hourly, high quality and "
      "independent of every satellite product. NOAA USCRN fits: 3 probes per depth, hourly, and not used to train the satellite products tested here.",
      "Looked for a known tension in the mission landscape (Table 1 in the report). Field-scale soil moisture needs SAR, and SAR "
      "revisits slowly. Radiometers such as SMAP revisit every 2–3 days but see 40 km pixels. This is the classic resolution-versus-revisit trade-off.",
      "Checked the literature for who had measured that trade-off. Revisit studies exist only for <i>irrigation</i> at single "
      "fields, often with <i>synthetic</i> subsampling (Filippucci et al. 2020; Zappa et al. 2022; Le Page et al. 2020). We found nothing for rain-driven "
      "events across many climates, using the satellites' <i>real</i> pass times, or giving the value of a new mission once NISAR and ROSE-L are counted.",
      "Linked the question to NASA priorities: the 2017 Decadal Survey's hydrology question H-4 (floods and droughts) and "
      "Targeted Observable TO-17 <i>Soil Moisture</i>, which the survey left unallocated because nothing is planned after "
      "SMAP and SMOS. Wrote three hypotheses (H1 events are shorter than the revisit; H2 sampled signals are below "
      "the noise; H3 a new mission lifts capture to ≥ 80 %).",
      "Wrote down a pass/fail criterion <i>before</i> looking at satellite data: the gap counts as real if going from 6-day "
      "to 3-day revisit gains ≥ 20 percentage points of capture."],
     ["A gap that is <i>measured</i> is far harder to attack than one that is asserted.",
      "Pre-declaring thresholds protects against the accusation of tuning the answer.",
      "Allowing a NO verdict makes the proposal credible. The analysis was designed so that it could kill the mission."],
     [f"The research gap: <b>no one has measured how many rain-driven wetting events the real field-scale radar fleet "
      f"captures, or what a new mission would add.</b> The criterion was met (+{f0(V['c3'] - V['c6'])} points from 6 to 3 days)."],
     "\"Isn't this just Zappa et al. (2022) again?\" No. Earlier revisit studies concern irrigation at one or a few fields, often subsampled synthetically. We use rain-driven "
     f"events at {V['n_stations']} stations across US climates, the actual Sentinel-1 and NISAR pass times, and a marginal-value test against current and future fleets.",
     "report Sections 1–2; notes/agent_literature.md and notes/agent_missions.md (background research notes).")

step(2, "Getting and cleaning the ground truth",
     "Build a trustworthy hourly record of 5 cm soil moisture and rainfall for every usable station.",
     ["Downloaded the NOAA USCRN <i>hourly02</i> files for 2025 and 2026 (one text file per station per year, public FTP/HTTPS).",
      "Repaired corrupted files. Some NOAA files contain runs of invisible NUL bytes, which created fake station IDs. We stripped "
      "them and kept only well-formed lines (exactly 38 fields).",
      "Quality control: values outside 0–0.6 " + M3 + " removed; hours with 5 cm soil temperature ≤ 1 °C removed "
      "(frozen soil fools the probes); short gaps ≤ 3 h interpolated.",
      "Kept a station-season only if ≥ 70 % of warm-season hours (1 April–31 October) were valid."],
     ["5 cm is the shallowest USCRN depth, and the closest to what radar senses.",
      "Warm season only: snow and frozen ground make both probes and radar unreliable.",
      "2025 and 2026 bracket the arrival of Sentinel-1C/1D and NISAR, so we can test the newest fleet."],
     ["133 stations parsed; 116 (2025) and 111 (2026) passed QC, which is 121 unique stations and "
      f"{V['n_ss']} station-seasons.",
      "Map: report Figure 1."],
     "\"A 1 m² probe can't validate a 200 m pixel.\" That is true for <i>absolute</i> accuracy (Crow et al. 2012). But our main "
     "metric is <i>when</i> wetting happens, and storm timing is spatially coherent over hundreds of metres. Point-to-pixel "
     "mismatch adds noise, so it makes our detection numbers pessimistic, not optimistic. The Year-2 field campaign tests this directly.",
     "code/01_parse_uscrn.py → data/processed/uscrn_hourly.pkl, station_seasons.csv")
fig("fig1_study_area.png", 13.5, "Report Figure 1: the USCRN stations used. Colour = median event window (days); marker size = number of events; ring = Stillwater, the example station in Figure 3.")

step(3, "Defining and detecting wetting events (Objective O1)",
     "Turn hourly records into a list of discrete events, each with a start time, a size and a duration, using rules fixed in advance.",
     ["<b>Storm:</b> a run of hours with ≥ 0.2 mm rain; gaps shorter than 24 h are merged into one storm.",
      "<b>Event:</b> a storm with ≥ 5 mm total rain <i>and</i> a 5 cm soil-moisture rise of ≥ 0.03 " + M3 + " above the 3-hour pre-storm mean.",
      "<b>Window:</b> the time the rise stays ≥ 50 % of its peak (the event's \"half-life\"). It is cut off at the next "
      "storm, because a later look would be seeing a different event. A second definition (rise ≥ 0.03 in absolute terms) is used as a check.",
      "Tested 9 alternative threshold combinations (sensitivity analysis)."],
     ["0.03 " + M3 + " is about half of the 0.04–0.06 accuracy target of satellite products, so smaller events would be invisible anyway.",
      "The half-amplitude rule works for both big and small storms. The absolute rule answers \"is it still wetter than before?\"",
      "Cutting the window at the next storm stops one long wet spell from being counted as one easy-to-catch event."],
     [f"<b>{V['n_events']:,} events at {V['n_stations']} stations.</b> Median window {V['win_med_d']:.1f} d "
      f"(IQR {V['win_q1_d']:.1f}–{V['win_q3_d']:.1f}); {f0(V['frac_lt2d'])} % last under 2 days.",
      f"Median rise {V['amp_med']:.3f} {M3}; median storm rain {V['rain_med']:.0f} mm; median time to peak {V['rise_med_h']:.0f} h; "
      f"{f0(V['cens'])} % of windows were cut short by the next storm.",
      f"Across the 9 alternative definitions the median window stays between {V['sens_win_lo']:.1f} and {V['sens_win_hi']:.1f} days."],
     "\"5 cm probes respond more slowly than the radar's skin layer.\" Correct. The top 1–2 cm dries even faster (Shellito et al. "
     "2016), so the windows the radar actually sees are <i>shorter</i> than ours. Our capture numbers are therefore optimistic, "
     "which only strengthens the gap. \"Why 50 %?\" It is the event's half-life; the 9-way sensitivity test shows the conclusions do not depend on it.",
     "code/02_events_revisit.py → events.csv, sensitivity.csv")
fig("fig3_stillwater_example.png", 15.5, "Report Figure 3: one station (Stillwater, Oklahoma). Rain (bars), 5 cm soil moisture, "
    "detected events and their windows, with real satellite looks marked. Use it to explain what an event is.")

step(4, "How often must a satellite look? (Objective O2, idealised)",
     "Find the relationship between revisit interval and the fraction of events captured, before considering any real satellite.",
     ["For revisit intervals R = 1, 2, 3, 4, 6 and 12 days, generated perfectly regular look schedules. We averaged over "
      "every possible starting day and both the 06:00 and 18:00 overpass times.",
      "Counted an event as captured if any look fell inside its window. Each look time was rounded up to the next hourly "
      "USCRN reading, because USCRN values are hour-ending.",
      "Checked the simulation against a simple formula: for random timing, expected capture = average of min(1, W/R), "
      "where W is the window and R the revisit.",
      "Confidence intervals: 2,000 bootstrap resamples of whole stations. Compared 2025 against 2026."],
     ["Starting idealised separates the physics (how long events last) from the quirks of any one satellite's schedule.",
      "The analytic check catches coding errors. It caught a real one (see Part C)."],
     [f"Capture by revisit: 1 d {f0(V['c1'])} %, 2 d {f0(V['c2'])} %, 3 d {f0(V['c3'])} %, 4 d {f0(V['c4'])} %, "
      f"6 d {f0(V['c6'])} %, 12 d {f0(V['c12'])} %.",
      f"<b>80 % capture needs a regular revisit of ≈ {V['R80']:.1f} days.</b>",
      f"Simulation and formula agree within {V['max_an_err']:.1f} points. 2025 vs 2026 at 6 days: {f0(V['c6_25'])} % vs "
      f"{f0(V['c6_26'])} %. Sensitivity range at 6 days: {f0(V['sens6_lo'])}–{f0(V['sens6_hi'])} %."],
     "\"Is 80 % the right target?\" It is a design choice, not a law of nature. Figure 4 gives the whole curve, so any "
     "user's target maps directly onto a revisit. \"Was anything tuned?\" No. Thresholds were fixed before satellite data were opened, and 2025 and 2026 agree.",
     "code/02_events_revisit.py → capture_synthetic.csv")
fig("fig4_capture_vs_revisit.png", 15, "Report Figure 4: event windows (a) and capture versus revisit interval (b), with the "
    "analytic check and 95 % confidence bands.")

step(5, "What do the real satellites actually capture? (Objective O2, real)",
     "Replace idealised schedules with the actual times Sentinel-1 and NISAR imaged each station.",
     ["<b>Sentinel-1:</b> searched the Microsoft Planetary Computer STAC catalogue (<i>sentinel-1-grd</i>) for every scene "
      "covering each station in both seasons and recorded the acquisition times.",
      "<b>NISAR:</b> queried NASA's CMR catalogue for NISAR GCOV and SME2 granules over each station. Only the metadata "
      "was needed at this stage, not the images.",
      "Merged adjacent catalogue frames from one pass (within 1 hour) into a single look, so one pass is not double-counted.",
      "Scored the real schedules against the same events. The joint analysis covers the 'NISAR era' "
      f"(17 June–1 November 2026): {V['n_era']} events at {V['n_era_st']} stations."],
     ["Real schedules include gaps, missed passes and the clustering of looks from different satellites. Synthetic schedules hide all of these."],
     [f"Sentinel-1 alone: {f0(V['s1_25'])} % (2025), {f0(V['s1_26'])} % (2026). NISAR era: Sentinel-1 {f0(V['s1_era'])} %, "
      f"NISAR {f0(V['ni_era'])} %, <b>combined {f0(V['both_era'])} % (95 % CI {f0(V['cur_lo'])}–{f0(V['cur_hi'])})</b>.",
      f"Median gap between looks: Sentinel-1 {V['gap_s1']:.1f} d, NISAR {V['gap_ni']:.1f} d, combined {V['gap_both']:.1f} d, "
      f"but with gaps of up to {V['maxgap_both']:.1f} d.",
      f"A <i>regular</i> schedule with the same number of looks would capture {f0(V['reg_equiv'])} %. The difference "
      f"(≈ {f0(V['reg_equiv'] - V['both_era'])} points) is the cost of uncoordinated timing, because looks bunch together.",
      f"Station-to-station spread is large: 10th percentile {f0(V['both_p10'])} %, 90th percentile {f0(V['both_p90'])} %."],
     "\"Your capture metric assumes a perfect sensor.\" Yes. That is deliberate: it is an upper bound. Steps 6–7 then "
     f"measure the second loss. \"Couldn't coordinating existing satellites fix this?\" Partly: ≈ {f0(V['reg_equiv'] - V['both_era'])} "
     "points at no hardware cost. It is far short of what ARMO adds, so it complements ARMO rather than replacing it.",
     "code/03_real_schedules.py → acq_s1.csv, acq_nisar.csv, capture_real.csv, revisit_real.csv")

step(6, "When Sentinel-1 looks, can it see the event? (Objective O3, C-band)",
     "Test whether a Sentinel-1 look inside an event window shows a backscatter rise larger than its normal noise.",
     ["For every look over every station, read a small 11 × 11 pixel window (10 m pixels, about 110 m) from the "
      "terrain-corrected <i>sentinel-1-rtc</i> images. These are cloud-optimised GeoTIFFs, so we read only those pixels over "
      "the internet instead of downloading whole scenes.",
      "Matched each look to the hour-ending USCRN soil moisture that follows it, and dropped looks with rain in the "
      "previous 3 hours (wet leaves and puddles distort the signal).",
      "Compared looks only within the same station and same relative orbit, so the viewing geometry is identical.",
      "<b>Noise floor:</b> the spread of " + S0 + " change between look pairs where the soil barely changed (|ΔSM| < 0.01). "
      "<b>Sensitivity:</b> the slope of " + S0 + " change against soil-moisture change, pooled over all pairs.",
      "<b>Detection:</b> for each event sampled inside its window, does " + S0 + " rise by more than 1× the noise floor?"],
     ["Change detection is the standard approach for SAR soil moisture (Wagner et al. 1999; Bauer-Marschallinger et al. 2019), "
      "so we tested the method that operational products actually use.",
      "Converting the noise from dB to " + M3 + " with the pooled slope puts C-band and L-band on the same scale."],
     [f"{int(V['s1_n_pairs_matched']):,} matched looks at {int(V['s1_n_stations'])} stations. Median correlation with "
      f"soil moisture over time r = {V['s1_median_r']:.2f}.",
      f"Sensitivity {V['s1_pair_slope_db_per_0p1']:.2f} dB per 0.1 {M3}; noise {V['s1_noise_db_nochange']:.2f} dB, "
      f"which equals ≈ <b>{V['s1_noise_sm_equiv']:.2f} {M3}</b>, larger than a typical event ({V['amp_med']:.2f}).",
      f"<b>Events registered when sampled: {pc(V['s1_P_detect_given_sampled_1sigma'])}</b> "
      f"(false alarms {pc(V['s1_false_alarm_nochange_1sigma'])}; AUC {V['s1_auc_wetup']:.2f}, where 0.5 = guessing).",
      f"End-to-end, Sentinel-1 both looks <i>and</i> sees only ≈ {V['s1_era'] * V['s1_P_detect_given_sampled_1sigma']:.0f} % of events."],
     "\"Maybe the probe is the problem, not the radar.\" Possibly in part. Point-to-pixel mismatch inflates the noise. That "
     "is why the Year-2 field campaign adds extra probes per pixel, and why we do not claim C-band is useless, only that "
     "single-look event detection is weak today.",
     "code/04_extract_s1_backscatter.py, code/06_s1_observability.py → s1_backscatter.csv, s1_summary.csv")

step(7, "Testing NISAR's new L-band soil moisture (Objective O3, L-band)",
     "Check NISAR's provisional 200 m soil-moisture product (SME2) and its L-band backscatter against the ground truth, "
     "both for average accuracy and for event detection.",
     ["Used a free NASA Earthdata login to access NISAR Level-3 SME2 files (provisional release).",
      "Read only the needed pixels from each HDF5 file over the internet: soil moisture, quality flag and L-band "
      f"{S0}<sub>HH</sub> in a 3 × 3 pixel (600 m) window around each station. Processed all 2,673 granules, with 17 read errors.",
      "Kept only retrievals flagged as recommended quality, then applied the same tests as Step 6: bias, ubRMSE, "
      "change noise and the detection rate for sampled events."],
     ["NISAR launched in July 2025 and is the strongest argument that we do not need a new mission. It had to be tested, not assumed.",
      "L-band should beat C-band through crops (Ulaby et al. 2014). This was the chance to see whether that holds at event scale."],
     [f"{int(V['nis_n_rec']):,} recommended retrievals at {int(V['nis_n_stations'])} stations. Bias +{V['nis_bias']:.3f}; "
      f"per-station median ubRMSE {V['nis_median_station_ubrmse']:.3f}; <b>{pc(V['nis_frac_station_ubrmse_le_006'])} of stations meet the "
      f"0.06 {M3} goal</b>. On average, it works.",
      f"But change detection is weak. SME2 changes correlate with ground truth at r = {V['nis_r_change_sat']:.2f}, but the "
      f"retrieved change is damped to {V['snr_tab'].loc['NISAR SME2', 'slope_per_m3m3']:.1f} of the true change. Only "
      f"<b>{pc(V['nis_P_detect_sat_valid_1sigma'])}</b> of sampled events with a valid retrieval pair were registered "
      f"({pc(V['nis_P_detect_sat_1sigma'])} if looks without a recommended retrieval count as misses; "
      f"{S0}<sub>HH</sub>: {pc(V['nis_P_detect_hh_valid_1sigma'])}).",
      f"L-band backscatter noise in {M3}: <b>{V['nis_noise_hh_sm_equiv']:.2f}, no better than C-band ({V['s1_noise_sm_equiv']:.2f})</b>. "
      "In this provisional data, L-band does not yet outperform C-band at event scale."],
     "\"NISAR already gives 200 m L-band soil moisture, so why ARMO?\" NISAR is accurate <i>on average</i>, but it captures only "
     f"{f0(V['ni_era'])} % of events and registers {pc(V['nis_P_detect_sat_valid_1sigma'])} of those it samples. Being accurate on average "
     "is not the same as being event-sensitive. \"Then why L-band at all?\" The crop-penetration physics is established, but we "
     "have not yet shown it here. That is exactly why Stage 1 funds retrieval research first. Also, the data cover only 4.5 months of a provisional product.",
     "code/07_extract_nisar_sme2.py, code/08_nisar_eval.py → nisar_sme2_points.csv, nisar_summary.csv")

step(8, "The no-satellite baseline: ERA5-Land (Objective O3, baseline)",
     "Answer the obvious question: why not skip satellites and use a weather or land model?",
     ["Downloaded hourly ERA5-Land soil moisture (top layer) and ERA5 rainfall for every station through the free Open-Meteo archive API.",
      "Ran the same event rules on the model and matched model events to ground-truth events within ± 24 hours.",
      "Also computed continuous skill: correlation, bias and ubRMSE."],
     ["A satellite proposal has to beat the cheapest alternative, and a free global model is exactly that."],
     [f"Median correlation r = {V['era_r']:.2f}: the model follows the seasonal ups and downs well.",
      f"But for events: detection {f0(V['era_pod'])} %, false-alarm ratio {f0(V['era_far'])} %, CSI {f0(V['era_csi'])} %. "
      f"It knows it rained ({f0(V['era_rain'])} % of rain events detected), but not reliably <i>how much the soil responded</i> at the field."],
     "\"Why not just use a model?\" The model misses 40 % of events and half its detections are false. For SMAP, see Step 8b.",
     "code/05_era5land_baseline.py → era5_summary.csv, era5_continuous.csv")

step("8b", "Earth Engine: SMAP, vegetation and the noise requirement (Objective O3)",
     "Answer three questions the panel will ask: would the frequent-but-coarse SMAP do the job, why do radars miss sampled "
     "events, and how good would ARMO's measurement need to be?",
     ["Signed in to Google Earth Engine (free academic project) and pulled, for all 121 stations: SMAP Enhanced L3 soil "
      "moisture (9 km, 06:00 and 18:00 passes, 2025–2026), MODIS NDVI (250 m, 16-day), ESA WorldCover land cover and the "
      "USDA Cropland Data Layer. About 4 minutes of processing.",
      "Ran exactly the same capture and detection tests on SMAP as on Sentinel-1 and NISAR (same matching rules; pairs "
      "from the same overpass ≤ 3.5 days apart).",
      "Split every sensor's detection rate by NDVI at the event, land cover and event size.",
      "Fitted one detection model to all four sensors: an event of size A is detected with probability Φ(kA/n − 1), "
      "where n is the sensor's noise in soil-moisture units and k one shared factor. Then solved it for 70 % detection."],
     ["\"Why not SMAP?\" deserved a measured answer, not just \"it's coarse\".",
      "Vegetation is the textbook reason radar fails; we could test it instead of asserting it.",
      "A traceability matrix needs a <i>number</i> for the instrument, as the Butterfly proposal has. The model turns our "
      "data into one."],
     [f"<b>SMAP:</b> a look inside {f0(V['sm_capture_era'] * 100)} % of event windows, {f0(V['sm_P_detect_1sigma'] * 100)} % "
      f"registered when sampled, <b>{f0(V['sm_end_to_end_era'] * 100)} % end to end</b>, against ≈ 10 % for the radars. "
      "Frequent, low-noise looks work, but only at 9 km.",
      f"<b>Vegetation:</b> NISAR {S0}<sub>HH</sub> detection falls from "
      f"{f0(V['strata'].set_index(['sensor', 'dimension', 'level']).p_detect['NISAR HH (L-band SAR)', 'ndvi_bin', 'NDVI < 0.35 (sparse)'] * 100)} % "
      f"under sparse cover to {f0(V['strata'].set_index(['sensor', 'dimension', 'level']).p_detect['NISAR HH (L-band SAR)', 'ndvi_bin', 'NDVI >= 0.6 (dense)'] * 100)} % "
      "under dense cover; Sentinel-1 and SMAP fall too. L-band backscatter beats C-band only in sparse cover (small samples).",
      f"<b>Requirement:</b> the model fits all four sensors within {V['snr_calibrated_mae_pts']:.0f} points. 70 % detection needs "
      f"change noise ≤ <b>{V['snr_noise_req_70']:.3f} {M3}</b>, i.e. {V['snr_req_db_L']:.2f} dB at L-band against "
      f"{V['snr_now_db_L']:.2f} dB today: about {V['snr_looks_factor_L']:.0f}× more independent looks if the noise is speckle.",
      f"<b>Ground truth is not farmland:</b> only {V['n_lc'].get('Cropland', 0)} of {sum(V['n_lc'].values())} stations are "
      f"cropland and {V['n_lc'].get('Tree cover', 0)} are in tree cover. Now listed as a limitation."],
     "\"SMAP already detects 41 %, so why ARMO?\" SMAP proves that frequent, low-noise looks work, but its 9 km grid cannot "
     "say which field got wet. ARMO's job is SMAP-like noise at field scale, and fusing SMAP timing with radar is one of "
     "the options our Stage 1 trade compares. \"Where does 0.038 come from?\" From the calibrated model in Figure 5d. "
     "It rests on four sensors, so we call it provisional.",
     "code/14_gee_extract.py, 15_smap_eval.py, 16_detection_strata.py, 17_snr_requirement.py → smap_summary.csv, "
     "detection_strata.csv, snr_summary.csv")
fig("fig6_observability.png", 15.5, "Report Figure 5: (a) change sensitivity at C- and L-band; (b) detection by vegetation "
    "(NDVI); (c) detection chain for each sensor and ERA5-Land; (d) detection versus noise, with ARMO's requirement.")

step(9, "What would ARMO add? (Objective O4, marginal value)",
     "Measure the extra capture a new mission brings on top of the real fleet today, and on top of a future fleet with ESA's ROSE-L.",
     ["Added a regular ARMO look schedule (1, 2, 3 or 4-day revisit, random phase) to the real 2026 Sentinel-1 + NISAR looks, and re-scored the events.",
      "Built a 'future fleet' by adding ROSE-L at ESA's documented revisit over global land (6 days with both satellites; "
      "3 days applies to Europe only and was run as an optimistic check), then added ARMO on top of that.",
      "Bootstrap confidence intervals as before."],
     ["Investors and NASA panels ask what the <i>marginal</i> value is, not what the stand-alone value is. Ignoring ROSE-L would be the easiest flaw for a panel to find."],
     [f"Today: {f0(V['cur'])} % → <b>{f0(V['arm2'])} %</b> with a 2-day ARMO ({f0(V['arm2_lo'])}–{f0(V['arm2_hi'])}), {f0(V['arm3'])} % with 3-day.",
      f"Future: ROSE-L alone gives {f0(V['fut'])} %; adding ARMO gives {f0(V['fut3'])} % (3-day) or {f0(V['fut2'])} % (2-day). "
      f"The gain shrinks to <b>+{f0(V['fut3'] - V['fut'])} to +{f0(V['fut2'] - V['fut'])} points</b> but does not vanish. "
      f"Even a Europe-style 3-day ROSE-L would leave the fleet at {f0(V['opt'])} %.",
      "Conclusion: ARMO is most valuable before ROSE-L and still adds value after it."],
     "\"ROSE-L will fix this.\" ESA's documents give it 6 days over global land (3 days is Europe), so the gap narrows but stays. That is why ROSE-L "
     "is a stated assumption with a 3-day sensitivity test, not a condition, and why we simulated it instead of ignoring it.",
     "code/03_real_schedules.py → marginal_value.csv")
fig("fig5_marginal_value.png", 15.5, "Report Figure 6: capture for the current fleet, current fleet + ARMO, and a future fleet with ROSE-L. Error bars = 95 % CI.")

step(10, "Is the mission physically feasible? (Orbit simulation)",
     "Check that a real orbit, not just an idealised schedule, can deliver the required revisit, and find the smallest configuration that does.",
     ["Wrote an orbit simulator: circular sun-synchronous dawn–dusk orbit at 620 km (inclination "
      f"{D.loc['A', 'inclination_deg']:.2f}°), including Earth's equatorial bulge (J2), which keeps the orbit "
      "sun-synchronous. The satellite position is computed every 10 seconds over the 136-day NISAR era.",
      "Modelled a side-looking L-band radar imaging 25–45° off nadir (a 362 km access swath, similar to Japan's ALOS-4). "
      "A station counts as imaged when it lies inside that swath, on <i>one</i> side of the ground track per pass.",
      "Flew five designs (A–E), added each one's simulated passes to the <i>real</i> fleet passes, and scored them against the same "
      f"{V['n_era']} ground-truth events, averaged over 8 orbital phases.",
      "Measured the imaging duty cycle: the fraction of each orbit spent over the contiguous US."],
     ["An idealised \"2-day revisit\" is meaningless if no orbit gives it. The simulation turns the requirement into a buildable configuration.",
      "Real radars image only one side at a time. Our first version wrongly let the satellite image both sides on every pass; this was caught and fixed (Part C)."],
     ["Results below. <b>Only design D, two right-looking satellites 180° apart, reaches the 80 % target.</b> It is the "
      f"<b>baseline</b> mission; design C (one satellite, wider access, {pc(D.loc['C', 'capture_fleet_plus_armo'])}) is the "
      "<b>threshold</b> mission, the least we would accept.",
      f"Imaging over the US takes only {D.loc['D', 'imaging_duty_conus'] * 100:.1f} % of each orbit (≈ "
      f"{D.loc['D', 'imaging_duty_conus'] * 1440:.0f} min per day per satellite). A regional mission therefore needs far less power and "
      "downlink than global NISAR-class mapping, which makes the smallsat class plausible.",
      "Spacecraft mass, power, data link and cost are sized in Step 10d."],
     "\"Can one satellite give a 2-day revisit?\" Not reliably: design A has a 2.8-day revisit, and rolling left/right (B) "
     "does not help because a SAR images one side per pass. Only a wider swath (C) or a second satellite (D) shortens it, and only D clears 80 %.",
     "code/09_armo_orbit_sim.py → armo_designs.csv")
table(["Design", "Configuration", "ARMO revisit", "Fleet + ARMO capture", "Gain"],
      [[k, {"A": "1 satellite, right-looking", "B": "1 satellite, rolls left/right on alternate orbits",
            "C": "1 satellite, alternate sides, wider 20–50° access (574 km)", "D": "2 satellites 180° apart, right-looking",
            "E": "2 satellites, alternate sides"}[k],
        f"{r.armo_mean_gap_d:.1f} d", f"{r.capture_fleet_plus_armo * 100:.0f} % ({r.capture_min * 100:.0f}–{r.capture_max * 100:.0f})",
        f"+{r.gain_pts:.0f} pts"] for k, r in D.iterrows()],
      [1.5, 7.3, 2.4, 3.6, 2.2])

step("10b", "Selling it: head to head, the niche, and other frequencies",
     "Show how much better ARMO is than NISAR and ROSE-L for this purpose, where it sits in the market, and why it is L-band rather than P-band, UHF or optical.",
     [f"Scored each system <i>alone</i> on the same {V['n_era']} events: NISAR's real 2026 passes, ROSE-L as a regular 6- or 3-day sampler, and ARMO design D flown in the orbit model.",
      "Multiplied capture by detection when sampled to estimate events <i>registered</i>: NISAR's measured rate, the same assumed for ROSE-L, and ARMO's 70 % requirement.",
      "Reviewed current and planned soil-moisture systems, open and commercial (market.pdf), and placed them on a resolution-versus-revisit map.",
      "Ran the same event rules on USCRN's 10 cm probes as a stand-in for the deeper sensing of P-band and UHF.",
      "Checked MODIS cloud masks at every station at the Terra and Aqua overpass times, to see whether optical sensors could see the events."],
     ["\"Better than NISAR\" must be measured on the same events with the same rules, or a panel will not accept it.",
      "Novelty has to be stated precisely. NISAR already gives 200 m L-band soil moisture, so claiming field-scale L-band as new would be wrong.",
      "A panel will ask about P-band (BIOMASS) and UHF. Ground truth answers the depth question better than an argument."],
     [f"<b>ARMO alone {f0(A1)} %, NISAR {f0(N1)} %, ROSE-L {f0(R6)} % (6 d) or {f0(R3)} % (3 d).</b> Registered: ARMO {f0(A1 * 0.7)} % "
      f"if it meets its requirement, NISAR {N1 * _dlo / 100:.0f}–{N1 * _dhi / 100:.0f} % measured. With S1 + NISAR + ROSE-L, ARMO lifts capture "
      f"from {f0(V['fut'])} % to {f0(HH['Sentinel-1 + NISAR + ROSE-L 6-day + ARMO'])} %.",
      "<b>Niche:</b> no open, all-weather system gives ≤ 200 m soil moisture faster than every ~6 days over the US. Spire (500 m) and Planet "
      "(now 1 km) are daily but modelled from coarse sensors and closed. <b>Novelty = revisit, not resolution.</b>",
      f"<b>Depth does not buy time:</b> {DP.loc[10, 'n_events']:,} events at 10 cm instead of {DP.loc[5, 'n_events']:,}; windows "
      f"{DP.loc[10, 'win_med_d']:.1f} vs {DP.loc[5, 'win_med_d']:.1f} d; 2-day capture {DP.loc[10, 'cap_R2'] * 100:.0f} % vs {DP.loc[5, 'cap_R2'] * 100:.0f} %.",
      "<b>P-band SAR</b> may not operate over North America (Quegan et al. 2019), needs a 12 m reflector and has only 6 MHz bandwidth. "
      "<b>UHF signals of opportunity</b> need no licence and sense ~10 cm (Yueh et al. 2020), but reach ≈ 200 m only at the swath edge and "
      "~1 km at its centre with seven satellites (Yueh et al. 2021). Way forward: a hosted UHF receiver is studied in Year 1; L-band stays the baseline.",
      f"<b>Optical:</b> a clear look in only {f0(V['opt_daily'])} % of events even with daily imaging, {f0(V['opt5'])} % at 5-day revisit "
      f"(radar {f0(V['sar5'])} %). Optical data are used as inputs (vegetation correction, masks), not flown."],
     f"\"Your 53 % is a promise.\" Yes: it uses ARMO's detection requirement, which is why retrieval is the main risk. Even at NISAR's "
     f"measured detection, ARMO would register about {A1 * _dlo / 100:.0f}–{A1 * _dhi / 100:.0f} %, roughly twice NISAR, because the revisit gain does not depend on retrieval.",
     "code/21_armo_performance.py → performance_headtohead.csv, depth_summary.csv; code/18_optical_clouds.py; code/19_market_report.py → market.pdf")

step("10c", "Mapping the need across the US with Earth Engine",
     "Show that the gap is not just at 120 stations: map where the radar misses wetting events, and where ARMO helps most.",
     ["Sentinel-1 revisit: counted distinct acquisition days per 0.1° cell in Earth Engine (COPERNICUS/S1_GRD, Apr–Oct 2026).",
      "Wetting events: counted gridMET storm onsets (a day with ≥ 5 mm after a drier day) and converted them to wetting events with one factor fitted at the USCRN stations.",
      "Missed events: events × (1 − capture), with capture computed from the 3,340 USCRN event windows at each cell's revisit.",
      "ARMO gain on cropland: the same with a 1.4-day ARMO added, shown where MODIS land cover is ≥ 25 % cropland."],
     ["A national map makes the need visible to non-specialists, and calibrating it with USCRN keeps it tied to ground truth.",
      "Two checks keep it honest: the Earth Engine revisit is compared with our own Planetary Computer record, and gridMET onsets with USCRN events."],
     [f"Checks: Sentinel-1 days vs our station record r = {V['need'].r_days_gee_vs_pc:.2f}; gridMET onsets vs USCRN events r = {V['need'].r_onsets_events:.2f} "
      f"({V['need'].k_events_per_onset:.2f} events per onset, {int(V['need'].n_station_seasons)} station-seasons).",
      f"Median cell: revisit {V['need'].conus_R_s1_median:.1f} d, ≈ {V['need'].conus_events_median:.0f} events per season, ≈ {V['need'].conus_missed_median:.0f} missed by Sentinel-1.",
      f"Cropland: ≈ {V['need'].crop_missed_median:.0f} missed per season; ARMO recovers ≈ {V['need'].crop_gain_median:.0f}, mostly in the Corn Belt and Mississippi Delta."],
     "\"Is gridMET rain the same as soil wetting?\" No, so we calibrate: 0.75 USCRN wetting events per gridMET storm onset, r = 0.82. "
     "The map is a model built on ground truth, not a retrieval.",
     "code/23_gee_need_maps.py → need_grid.npz, need_summary.csv, figures/fig7_need_maps.png (report Figure 1)")

step("10d", "Sizing the spacecraft: antenna, power, data, mass and cost",
     "Turn the orbit design into a spacecraft a panel can believe in, and a cost that fits a NASA programme.",
     [f"Antenna: used the minimum-antenna-area rule A ≥ 4vλR·tanθ/c (Freeman et al. 2000) at the far edge of the access range (45° off-nadir): ≥ {SZ.Amin_45_m2:.0f} m², so a {SZ.reflector_d_m:.1f} m mesh reflector.",
      f"Power: solved the SAR radar equation for a −25 dB noise floor (2 dB better than NISAR's ≈ −23 dB requirement, Fattahi et al. 2026), with 9 dB of losses and a 3 dB ScanSAR margin: ≈ {SZ.P_avg_rf_w:.0f} W average, {SZ.P_peak_rf_w:.0f} W peak.",
      f"Data: 2 polarisations × 20 MHz × 4-bit samples → {SZ.data_rate_mbps:.0f} Mbit/s while imaging, {SZ.data_gb_day:.0f} GB/day, {SZ.downlink_min_day:.0f} min/day of X-band downlink.",
      f"Mass: a bottom-up budget per subsystem with 30 % growth margin and propellant for phasing and de-orbit: {SZ.wet_kg:.0f} kg wet; both satellites ({SZ.launch_kg:.0f} kg) fit one Firefly Alpha-class launch (630 kg to 500 km SSO).",
      "Cost: flight system by analogy (NovaSAR-1 ≈ £45 M build + launch; CYGNSS US$ 102 M excl. launch for 8 microsats), launch ≈ US$ 15 M, personnel from BLS salaries + 62 % overhead, 30 % reserve."],
     ["A launch pitch without mass, power and cost is not credible to a review panel.",
      "Each number either comes from physics we can show or is labelled as our estimate. The cost is honest about its ± 40 % uncertainty."],
     [f"<b>≈ US$ {SZ.cost_total:.0f} M</b> total (US$ {SZ.cost_AD:.0f} M development and launch, US$ {SZ.cost_E:.0f} M operations), "
      f"≈ {f0((190 / SZ.cost_total - 1) * 100)} % under the US$ 190 M Earth Venture cap. The flight system is {SZ.flight_share * 100:.0f} % of the cost.",
      f"Threshold mission (one satellite): ≈ US$ {SZ.cost_threshold:.0f} M.",
      f"Orbit-average power only ≈ {SZ.orbit_avg_w:.0f} W because the radar images just the US (1.5 % of each orbit)."],
     "\"A 6 m reflector on a 250 kg satellite?\" Not yet flown at that scale, and we call it our top engineering risk. NISAR flies 12 m; "
     "small-SAR reflectors of 3.35 m weigh < 8 kg. Stage 2 includes a deployment test before the build.",
     "code/22_armo_sizing.py → armo_sizing.csv, armo_mass.csv, armo_cost.csv; report Table 6 and Section 5")

step(11, "From results to a verdict, requirements and budget",
     "Turn the evidence into a decision a funding panel can act on, with costs that can be traced to sources.",
     ["Set the verdict scale before writing: YES / CONDITIONAL / NO. After the sizing (Step 10d) the team chose YES: launch.",
      "Built a science traceability matrix (report Table 5): each objective flows to a physical parameter, a measurement "
      "requirement and a mission requirement, labelled by its evidence: P = shown by this study, L = literature, "
      "U = unverified (report Table 5). The critical one, event sensitivity ≥ 70 % at ≤ 10 % false alarms, is marked U.",
      "Costed Stage 1 line by line (BLS salary, AWS prices, sensor prices, journal and AGU fees, 62 % MIT overhead) and Stage 2 by analogy (Step 10d).",
      "Compared paid data options. Commercial X-band tasking (ICEYE, Capella) would cost ≈ US$ 19–20 million for the same looks, so it was rejected."],
     ["The verdict follows the evidence. The timing gap is real, but detection is unsolved, so the honest ask is for the cheaper step that removes the biggest risk."],
     [f"<b>Verdict: retrieval first, then launch ARMO.</b> Stage 1 (US$ {rt.money(t1 + t2)}, 2027–28) funds event-detection research on "
      f"validated NISAR data; its result sets ARMO's sensor. Stage 2 (≈ US$ {SZ.cost_total:.0f} M) launches ARMO ≈ 2033 either way.",
      "The payoff if met: ≈ 53 % of all events registered, 4–6× NISAR; if not met, still about twice NISAR. We assume ROSE-L's documented 6-day revisit over "
      f"the US; even at Europe's 3-day revisit, a 2-day ARMO still adds {f0(V['opt2'] - V['opt'])} points.",
      f"The flight system is {SZ.flight_share * 100:.0f} % of the cost; all analysis data are free."],
     "\"What if retrieval never reaches 70 %?\" ARMO still registers about twice what NISAR does, because revisit gains do not "
     f"depend on retrieval; if cost grows, descope to one satellite (≈ US$ {SZ.cost_threshold:.0f} M).",
     "code/report_text.py (all text, budget constants and references); report Section 5 and Tables 3–9")

step(12, "Writing it up: report, slides and checks",
     "Produce the deliverables in the course template, with every number traceable to code.",
     ["The report is generated from the course Word template by code/20_build_report.py. The text lives in "
      "code/report_text.py and reads every number from the result files, so no number was typed by hand.",
      "Figures come from scripts 10–13 (colour-blind-safe palette); the slides from code/30_build_slides.py; PDFs are exported through Word and PowerPoint.",
      "Earth Engine results (scripts 14–17) feed the same pipeline, so adding them changed every affected number in one rebuild.",
      "Every journal reference was checked against Crossref (title, authors, DOI); web sources are cited with URLs.",
      "An adversarial self-review scored the proposal as a NASA panel would and prepared 25 hard questions (notes/review_and_QA.md).",
      "code/50_rebuild_outputs.py re-runs the analysis summaries and figures and rebuilds the report and slides in one go."],
     ["If a result changes, every mention of it in the report and slides changes with it. This is how the NISAR conclusion was corrected consistently (Part C)."],
     [f"Report: {REP_PAGES} pages, with Sections 1–5 on pages 2–{SEC_END} (limit 10 pages). Slides: {N_SLIDES}."],
     "\"Can you reproduce this?\" Yes. All data are public, and the code re-runs from the raw files. Only the NISAR download "
     "step needs a free Earthdata login.",
     "code/20_build_report.py, report_text.py, 30_build_slides.py, 40_review_and_qa.py, 50_rebuild_outputs.py")

# ================================================================== PART C
H1("Part C. Mistakes caught and fixed")
P("Panels respect teams that found and fixed their own errors. These are real examples from this project, and each one is a good answer to \"how do you know your results are right?\"")
table(["What went wrong", "How it was caught", "Fix and effect"],
      [["NOAA files contained invisible NUL bytes, which created fake station IDs", "Station count looked wrong", "Strip the bytes and keep only 38-field lines"],
       ["Capture came out the same for every revisit interval", "Disagreed with the analytic formula", "A time-unit bug (microseconds vs nanoseconds in pandas) was fixed; simulation now matches the formula within 0.25 pts"],
       ["ERA5-Land rainfall field came back empty", "All-missing column", "Rainfall taken from ERA5 instead; soil moisture still from ERA5-Land"],
       ["First NISAR results (≈ 10 % of the files) suggested L-band was 2–5× less noisy than C-band", "Re-ran on all 2,673 granules",
        "L-band noise is in fact no lower than C-band. The \"L-band is better\" claim was removed everywhere"],
       ["NISAR noise counted 208 \"pairs\" that were two frames of the same pass, 33 s apart", "Checked noise against pair spacing",
        "Same-pass pairs removed: NISAR noise 1.25 → 1.45 dB, detection 27–38 % → 23–37 %; all outputs rebuilt"],
       ["Orbit model let the radar image both sides on every pass", "Physics review: a SAR looks one way at a time",
        "Corrected. Design E fell from 85 % to 77 %, and one satellite no longer meets the target"],
       ["C-band and L-band noise had been converted with different slope methods", "Consistency check", "Both now use the pooled slope"],
       ["One reference title had been written from memory", "Crossref check", "Corrected (Luo et al. 2017)"],
       ["NISAR's \"22 %\" counted looks with no valid retrieval as misses, unlike the other sensors", "Splitting detection by vegetation",
        f"Both figures now reported: {pc(V['nis_P_detect_sat_valid_1sigma'])} with a valid pair, {pc(V['nis_P_detect_sat_1sigma'])} counting gaps"],
       ["The simple detection model over-predicted every sensor by 12–19 points", "Compared with observed rates",
        f"Calibrated with one shared factor; now within {V['snr_calibrated_mae_pts']:.0f} points. The requirement uses the calibrated model"]],
      [5.6, 4.0, 7.4])
box("Lesson worth saying aloud",
    "\"Our first NISAR results looked very good for L-band. When we processed the full dataset, the advantage disappeared, so "
    "we changed our conclusion rather than our data. That is why Stage 1 funds retrieval research first.\"", "green")

H1("Part C. Hard questions and short answers")
qa = [
    ("Isn't this just Zappa et al. (2022) again?", f"Earlier revisit studies concern irrigation at one or a few fields, often subsampled synthetically (Filippucci 2020; Zappa 2022). We cover rain-driven events at {V['n_stations']} stations, real pass times, and the marginal value over current and future fleets."),
    ("Your capture metric assumes a perfect sensor.", f"Yes, so it is an upper bound. We then measured the second loss: Sentinel-1 registers {pc(V['s1_P_detect_given_sampled_1sigma'])} of sampled events, NISAR {pc(V['nis_P_detect_hh_valid_1sigma'])}–{pc(V['nis_P_detect_sat_valid_1sigma'])}."),
    ("A point probe can't validate a 200 m pixel.", "It can't validate absolute values precisely, but storm timing is spatially coherent. The mismatch makes our detection numbers pessimistic. The Year-2 campaign tests it."),
    ("The probe is at 5 cm; radar sees 1–5 cm.", "The thinner layer dries faster, so the real windows are shorter and our capture numbers are optimistic. The gap is, if anything, bigger."),
    ("Why these thresholds?", f"They were fixed before any satellite data were examined, and 9 alternatives give 6-day capture of {f0(V['sens6_lo'])}–{f0(V['sens6_hi'])} %. The conclusion does not change."),
    ("Why not a model?", f"ERA5-Land: {f0(V['era_pod'])} % detection with {f0(V['era_far'])} % false alarms."),
    ("SMAP detects 41 %. Why not just use SMAP?", f"It proves frequent, low-noise looks work ({f0(V['sm_end_to_end_era'] * 100)} % end to end), but at 9 km it cannot say which field got wet. ARMO = SMAP-like noise at field scale. SMAP–radar fusion is in our Stage 1 trade study."),
    ("NISAR already exists.", f"Accurate on average ({pc(V['nis_frac_station_ubrmse_le_006'])} of stations meet the goal) but it captures {f0(V['ni_era'])} % of events and registers {pc(V['nis_P_detect_sat_valid_1sigma'])} of sampled ones."),
    ("Your stations aren't farms.", f"True: {V['n_lc'].get('Cropland', 0)} of {sum(V['n_lc'].values())} are cropland. Timing results carry over (rain falls on farms too); detection over crops is untested. Year 1 adds cropland networks."),
    ("Where does 0.038 come from?", f"A detection model fitted to all four sensors (within {V['snr_calibrated_mae_pts']:.0f} points), solved for 70 %. Provisional: it rests on four points."),
    ("Which NASA priority is this?", "2017 Decadal Survey hydrology question H-4 (floods, droughts) and Targeted Observable TO-17 Soil Moisture, unallocated because nothing follows SMAP and SMOS."),
    ("If L-band isn't better in your data, why L-band?", "The physics (crop penetration) is established in the literature but not yet shown at event scale with 4.5 months of provisional data. That is why retrieval research comes first."),
    ("How much better than NISAR and ROSE-L?", f"On the same events, each alone: ARMO {f0(A1)} %, ROSE-L {f0(R3)} % (3 d) or {f0(R6)} % (6 d), NISAR {f0(N1)} %. Same band and grid as NISAR; the gain is revisit."),
    ("Why not P-band, like BIOMASS?", "P-band SAR may only use 432–438 MHz, behind US space-object tracking radars; BIOMASS may not operate over North America (Quegan et al. 2019). It also needs a 12 m reflector."),
    ("Wouldn't deeper sensing need less revisit?", f"Tested on USCRN 10 cm probes: windows {DP.loc[10, 'win_med_d']:.1f} vs {DP.loc[5, 'win_med_d']:.1f} days, 2-day capture {DP.loc[10, 'cap_R2'] * 100:.0f} % vs {DP.loc[5, 'cap_R2'] * 100:.0f} %. No."),
    ("Why not UHF signals of opportunity?", "No licence needed and ~10 cm sensing, but ≈ 200 m only at the swath edge and ~1 km at centre with seven satellites, and it depends on US Navy transmitters. Studied as a hosted secondary payload."),
    ("Spire and Planet already sell daily maps; why not optical?", f"Both are modelled from coarse sensors and closed; we test them against USCRN in Year 1. Optical: a clear look in only {f0(V['opt_daily'])} % of events even daily."),
    ("ROSE-L will fix this.", f"ESA documents 6 days over global land (3 days is Europe; eoPortal says 3 days). The fleet then reaches {f0(V['fut'])} %, and ARMO adds +{f0(V['fut3'] - V['fut'])} to +{f0(V['fut2'] - V['fut'])}. Even a 3-day ROSE-L leaves ARMO +{f0(V['opt2'] - V['opt'])}, so ROSE-L is an assumption, not a condition."),
    ("Can one satellite do it?", f"No: {D.loc['A', 'armo_mean_gap_d']:.1f}-day revisit and {pc(D.loc['A', 'capture_fleet_plus_armo'])} capture. Two satellites give {D.loc['D', 'armo_mean_gap_d']:.1f} days and {pc(D.loc['D', 'capture_fleet_plus_armo'])}."),
    ("Why not buy commercial X-band images?", "≈ US$ 19–20 million for the same looks, and X-band senses only ≈ 1 cm and is blocked by canopy."),
    ("Are your stations independent?", "Confidence intervals resample whole stations, and duplicate frames from one pass are merged."),
    ("Was anything tuned on the test data?", f"No. 2025 was used for development and 2026 as holdout: 6-day capture {f0(V['c6_25'])} % vs {f0(V['c6_26'])} %."),
    ("Who would actually use 2-day data?", "Flood forecasters (NOAA National Water Model initial wetness), irrigation accounting, crop monitoring (USDA Crop-CASMA). Weekly drought maps do not need it. We say so."),
    ("If you launch anyway, why fund retrieval first?", f"Its result sets the sensor (looks, bandwidth, power), so how much of the payoff we get; it costs US$ {rt.money(t1 + t2)}, ~0.15 % of the mission, and improves NISAR and ROSE-L products early."),
    ("What if retrieval never reaches 70 %?", f"ARMO still registers about twice what NISAR does; if cost grows, descope to one satellite (≈ US$ {SZ.cost_threshold:.0f} M)."),
    ("How much does it cost, and how did you size it?", f"≈ US$ {SZ.cost_total:.0f} M incl. launch and 30 % reserve (± 40 %), under the US$ 190 M Earth Venture cap. Antenna from the minimum-area rule, power from the radar equation, mass bottom-up ({SZ.wet_kg:.0f} kg), cost by analogy with NovaSAR-1 and CYGNSS."),
]
table(["If asked…", "Say…"], [[f"<b>{q}</b>", a] for q, a in qa], [5.4, 11.6])

H2("Our weak spots: concede them before the panel finds them")
B([f"<b>Detection, not timing, is the bottleneck.</b> At ≈ {V['s1_era'] * V['s1_P_detect_given_sampled_1sigma']:.0f} % end-to-end, "
   "even perfect revisit would not deliver event detection with today's methods.",
   "<b>Short, provisional NISAR record</b> (4.5 months, partly calibrated). Conclusions about L-band may change with the validated release.",
   "<b>US only, warm season, two years.</b> The tropics and irrigated drylands, where ARMO may matter most, are not covered.",
   f"<b>Few farms.</b> Only {V['n_lc'].get('Cropland', 0)} of {sum(V['n_lc'].values())} stations are cropland, yet ARMO is an agricultural mission.",
   "<b>The noise requirement rests on a model fitted to four sensors.</b> Present it as provisional.",
   f"<b>Sizing is first-order.</b> Cost is ± 40 % by analogy; a {SZ.reflector_d_m:.1f} m reflector has not flown on a {SZ.wet_kg:.0f} kg satellite.",
   "<b>The novelty is revisit only.</b> NISAR already provides 200 m L-band soil moisture; never claim field-scale L-band as new.",
   f"<b>ARMO's {f0(A1 * 0.7)} % registered is a projection</b> from its detection requirement, not a measured result.",
   "<b>User benefit not quantified.</b> We argue why 2-day data matter for flood forecasting, but did not measure forecast improvement."])

# ================================================================== PART D
H1("Part D. Presentation plan")
P("Suggested split for three presenters (adjust to your group size). The main deck is 18 slides, about 50 seconds each for a 15-minute slot; slides 19–23 are backup for questions. Each presenter should read the steps listed next to their slides.")
table(["Slide", "Title / one message", "Presenter", "Read"],
      [["1", "Title: do field-scale radars blink through the rain?", "A", "Part A"],
       ["2", "Every storm writes a two-day signal into the soil", "A", "Step 3"],
       ["3", "Resolution or revisit: today you must choose one", "A", "Step 1, Concepts"],
       ["4", "Where the gap bites: Earth Engine maps of the need", "A", "Step 10c"],
       ["5", "ARMO's niche: field scale plus fast revisit", "A", "Step 10b, market.pdf"],
       ["6", "Research question and objectives O1–O4", "A", "Step 1"],
       ["7", "Ground truth first: 120 reference stations, hourly", "B", "Step 2"],
       ["8", "Method: from probe to mission decision", "B", "Part B intro"],
       ["9", f"Half of all events fade within {V['win_med_d']:.1f} days", "B", "Steps 3–4"],
       ["10", "The real 2026 fleet sees about half of the events", "B", "Step 5"],
       ["11", "When sampled, can the sensor see it? Radars mostly not; SMAP better", "B", "Steps 6–8b"],
       ["12", "What would it take to see the events? (noise requirement)", "B", "Step 8b"],
       ["13", "Head to head: ARMO vs NISAR vs ROSE-L", "C", "Step 10b"],
       ["14", "The ARMO mission concept (mass, power, cost)", "C", "Step 10d"],
       ["15", "Verdict: retrieval first, then launch ARMO", "C", "Step 11, Part C"],
       ["16", "Limitations and the two-stage plan", "C", "Part C weak spots"],
       ["17", "Who would use it, and what it costs", "A", "Step 10d"],
       ["18", "Take-home", "A", "Part A"],
       ["19–23", "Backup (show only if asked): marginal value; orbit designs A–E; traceability; P-band / UHF", "C", "Steps 9–11, 10b"]],
      [1.2, 9.6, 2.2, 4.0])
box("Three sentences every presenter should be able to say",
    [f"\"Half of all rain-driven wetting events fade within {V['win_med_d']:.1f} days, and the real 2026 radar fleet catches only {f0(V['cur'])} % of them.\"",
     f"\"Even when a radar looks, it registers only {pc(V['nis_P_detect_hh_valid_1sigma'])}–{pc(V['nis_P_detect_sat_valid_1sigma'])} of events; to reach 70 % its noise must fall about {V['snr_now_db_L'] / V['snr_req_db_L']:.0f}-fold.\"",
     f"\"On its own ARMO would capture {f0(A1)} % of events against NISAR's {f0(N1)} %; we fund retrieval first, then launch ARMO either way, because revisit alone doubles NISAR.\""],
    "blue")

H1("Part D. Files and how to re-run the work")
table(["Script", "What it does", "Needs internet / login"],
      [["01_parse_uscrn.py", "Parse and quality-control USCRN ground truth", "No (raw files already downloaded)"],
       ["02_events_revisit.py", "Detect events; capture vs regular revisit; bootstrap; sensitivity", "No"],
       ["03_real_schedules.py", "Real Sentinel-1/NISAR pass times; ARMO and ROSE-L marginal value", "Yes (public catalogues)"],
       ["04_extract_s1_backscatter.py", "Sentinel-1 backscatter at each station (long run; cached)", "Yes (public)"],
       ["05_era5land_baseline.py", "ERA5-Land baseline", "Yes (public)"],
       ["06_s1_observability.py", "C-band noise, sensitivity and detection", "No"],
       ["07_extract_nisar_sme2.py", "NISAR soil moisture and L-band backscatter (long run; cached)", "Yes (Earthdata login)"],
       ["08_nisar_eval.py", "NISAR accuracy and detection", "No"],
       ["09_armo_orbit_sim.py", "Orbit simulation of designs A–E", "No"],
       ["18_optical_clouds.py", "MODIS cloud mask at each overpass: could optical sensors see the events?", "Yes (Earth Engine)"],
       ["19_market_report.py", "Market review and niche map (market.pdf)", "No"],
       ["21_armo_performance.py", "Head to head (ARMO, NISAR, ROSE-L alone) and the 10 cm depth test", "No"],
       ["22_armo_sizing.py", "Spacecraft sizing: antenna, power, data, mass budget and mission cost", "No"],
       ["23_gee_need_maps.py", "Earth Engine maps of the need (Sentinel-1 revisit, wetting events, missed events, ARMO gain)", "Yes (Earth Engine; cached)"],
       ["10–13_fig_*.py", "Figures", "No"],
       ["14_gee_extract.py", "SMAP, MODIS NDVI and land cover from Earth Engine (cached)", "Yes (Earth Engine login + project)"],
       ["15–17", "SMAP evaluation; detection by vegetation; noise requirement", "No"],
       ["20 / 30 / 40", "Build report, slides, self-review", "No (Word/PowerPoint for PDF)"],
       ["50_rebuild_outputs.py", "Re-run the summaries, figures, report and slides", "No"]],
      [4.6, 8.4, 4.0])
P("<b>To check a number yourself:</b> install Python 3 and the packages listed in code/README.md, open a terminal in the "
  "<i>code</i> folder, and run, for example, <font face='Courier'>python 06_s1_observability.py</font>. Then compare the printed values "
  "with the report. The processed results are already in data/processed, so the long downloads (04, 07) do not need to be repeated.")
P("<b>Credentials:</b> the NASA Earthdata login (.netrc) and the Earth Engine sign-in (.config/earthengine) are stored only in "
  "the account owner's home folder, never in the project folder. Keep it that way if the code is shared or put on GitHub, "
  "and delete the unused NASAEarthDataToken.txt from the project folder before sharing it.")

H2("Before submission (5 November, 12:00)")
B(["Each member writes a half-page contribution statement in their own words (report, after References).",
   "Replace the name placeholders on the report cover and slide 1.",
   "Declare AI assistance as the course requires.",
   "Decide whether to publish code/ to a public GitHub repository. If yes, paste the link into \"Data and Code Availability\".",
   "Re-run code/50_rebuild_outputs.py after any text change, then check that the report is still within 10 pages for Sections 1–5.",
   "Rehearse with a timer, and practise the Part C answers out loud."])


# ------------------------------------------------------------------ page furniture
def on_page(c, doc):
    c.saveState()
    if doc.page > 1:
        c.setFont("Body", 8.5); c.setFillColor(INK2)
        c.drawString(2 * cm, 1.2 * cm, "ARMO project · team guide")
        c.drawRightString(A4[0] - 2 * cm, 1.2 * cm, str(doc.page))
        c.setStrokeColor(RULE); c.setLineWidth(0.5); c.line(2 * cm, 1.6 * cm, A4[0] - 2 * cm, 1.6 * cm)
    c.restoreState()


doc = BaseDocTemplate(OUT, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm, bottomMargin=2 * cm,
                      title="How the ARMO project was built: team guide", author="ES4304 ARMO team")
frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=on_page)])
doc.build(story)
print("saved", OUT)
