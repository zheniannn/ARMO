"""market.pdf: which niche does ARMO occupy? Soil-moisture market and pipeline, plus the optical/hyperspectral question.

Market facts come from agency, company and peer-reviewed sources checked on 2 Nov 2026 (source list in the PDF;
company claims are labelled). Project numbers are read from data/processed via 20_build_report.load_values() and
optical_capture.csv (script 18), so they match the report.
"""
import os, importlib.util
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from common import ROOT, PROC
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle, Image,
                                KeepTogether, CondPageBreak)

spec = importlib.util.spec_from_file_location("br", os.path.join(os.path.dirname(__file__), "20_build_report.py"))
br = importlib.util.module_from_spec(spec); spec.loader.exec_module(br)
V = br.load_values()
D = V["designs"].set_index(V["designs"].design.str[0])
OPT = pd.read_csv(os.path.join(PROC, "optical_capture.csv")); opt = OPT.set_index("revisit_d")
st = pd.read_csv(os.path.join(PROC, "optical_state.csv")).dropna(subset=["state"])
s = st.state.astype(int); CLEAR_ALL = (((s & 3) == 0) & ((s & 4) == 0)).mean()
OUT = os.path.join(ROOT, "market.pdf")
FIGF = os.path.join(ROOT, "figures", "fig_market_niche.png")
def f0(x): return f"{x:.0f}"

# ------------------------------------------------------------------ niche map
# (label, product resolution m, revisit over US d, revisit range, category, status/coverage note)
SYS = [
    ("SMAP 36 km", 36000, 2.5, (2, 3), "open", ""),
    ("SMAP 9 km (interpolated)", 9000, 2.5, (2, 3), "open", ""),
    ("SMOS", 44000, 2.5, None, "open", ""),
    ("HydroGNSS", 25000, 1.0, None, "open", ""),
    ("CIMR (2029)", 9000, 1.0, None, "planned", ""),
    ("SMAP/Sentinel-1 (paused Jul 2026)", 3000, 12, (3, 12), "open", ""),
    ("NISAR SME2", 200, 6, (6, 12), "open", ""),
    ("ROSE-L (2028-30; resolution TBD)", 100, 4.5, (3, 6), "planned", ""),
    ("SAOCOM (Pampas only)", 400, 8, None, "notus", ""),
    ("Sentinel-1 CLMS (Europe only)", 1180, 1.0, None, "notus", ""),
    ("Planet SWC (1 km)", 850, 1.0, None, "comm", ""),
    ("Spire (500 m)", 500, 1.0, None, "comm", ""),
    ("EOSDA (250 m)", 250, 2.5, (2, 3), "comm", ""),
]
BLUE, ORANGE, AQUA, GREY, INK, INK2 = "#2a78d6", "#eb6834", "#1baf7a", "#8d8b85", "#0b0b0b", "#52514e"
STYLE = {"open": dict(c=BLUE, fill=True, lab="Open, retrieved by the agency"),
         "comm": dict(c=ORANGE, fill=True, lab="Commercial, downscaled or fused"),
         "planned": dict(c=BLUE, fill=False, lab="Planned (open)"),
         "notus": dict(c=GREY, fill=True, lab="No CONUS product")}
plt.rcParams.update({"font.family": "Arial", "font.size": 8.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": INK2, "xtick.color": INK2, "ytick.color": INK2, "savefig.dpi": 300, "savefig.bbox": "tight"})
fig, ax = plt.subplots(figsize=(6.6, 4.3))
ax.set_xscale("log"); ax.set_yscale("log")
ax.add_patch(Rectangle((10, 0.3), 190, 1.7, facecolor="#eef7f2", edgecolor=AQUA, linewidth=1, linestyle="--", zorder=0))
ax.text(13, 0.36, "ARMO niche: open, all-weather,\ndirect, <= 200 m, <= 2 days", fontsize=7.5, color=INK, va="bottom")
OFF = {"SMAP 36 km": (1.0, 0.84, "center"), "SMAP 9 km (interpolated)": (1.0, 1.2, "center"),
       "SMOS": (1.0, 1.2, "center"), "HydroGNSS": (1.15, 1.0, "left"), "CIMR (2029)": (1.0, 0.84, "center"),
       "SMAP/Sentinel-1 (paused Jul 2026)": (1.12, 1.0, "left"), "NISAR SME2": (1.12, 1.0, "left"),
       "ROSE-L (2028-30; resolution TBD)": (1.12, 1.0, "left"), "SAOCOM (Pampas only)": (1.12, 1.0, "left"),
       "Sentinel-1 CLMS (Europe only)": (1.15, 1.2, "left"), "Planet SWC (1 km)": (1.0, 0.84, "left"),
       "Spire (500 m)": (1.0, 0.84, "right"), "EOSDA (250 m)": (1.12, 1.0, "left")}
seen = set()
for lab, res, rev, rng, cat, _ in SYS:
    stl = STYLE[cat]
    if rng:
        ax.plot([res, res], rng, color=stl["c"], linewidth=1.2, alpha=0.6)
    ax.scatter(res, rev, s=46, facecolor=stl["c"] if stl["fill"] else "white", edgecolor=stl["c"], linewidth=1.4,
               zorder=3, label=stl["lab"] if cat not in seen else None)
    seen.add(cat)
    dx, dy, ha = OFF[lab]
    ax.text(res * dx, rev * dy, lab, fontsize=7, color=INK, ha=ha, va="center")
armo = D.loc["D"]
ax.scatter(200, armo.armo_mean_gap_d, marker="*", s=230, color=AQUA, edgecolor=INK, linewidth=0.6, zorder=4, label="ARMO (proposed)")
ax.text(200 * 0.78, armo.armo_mean_gap_d, f"ARMO: {armo.armo_mean_gap_d:.1f} d", fontsize=8, color=INK, ha="right", va="center", fontweight="bold")
ax.axhline(V["win_med_d"], color=INK2, linestyle=":", linewidth=0.9)
ax.text(2500, V["win_med_d"] * 0.93, f"median wetting event {V['win_med_d']:.1f} d", fontsize=7, color=INK2, ha="left", va="top")
ax.set_xlim(10, 1.5e5); ax.set_ylim(0.3, 20)
ax.set_xticks([10, 100, 1000, 10000, 100000]); ax.set_xticklabels(["10 m", "100 m", "1 km", "10 km", "100 km"])
ax.set_yticks([0.5, 1, 2, 3, 6, 12]); ax.set_yticklabels(["0.5", "1", "2", "3", "6", "12"])
ax.set_xlabel("Soil-moisture product resolution (log scale)"); ax.set_ylabel("Revisit over the US (days, log scale)")
ax.grid(color="#e4e3df", linewidth=0.5); ax.set_axisbelow(True)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=3, fontsize=7, frameon=False)
fig.savefig(FIGF); plt.close(fig)

# ------------------------------------------------------------------ PDF styles
FD = r"C:\Windows\Fonts"
for name, f in (("Body", "calibri.ttf"), ("Body-B", "calibrib.ttf"), ("Body-I", "calibrii.ttf"), ("Body-BI", "calibriz.ttf"),
                ("Head-B", "georgiab.ttf")):
    pdfmetrics.registerFont(TTFont(name, os.path.join(FD, f)))
addMapping("Body", 0, 0, "Body"); addMapping("Body", 1, 0, "Body-B"); addMapping("Body", 0, 1, "Body-I"); addMapping("Body", 1, 1, "Body-BI")
NAVY = colors.HexColor("#123b63"); RULE = colors.HexColor("#d9d7d1"); GREYT = colors.HexColor("#f3f2ef")
TINT = {"blue": (colors.HexColor("#eaf2fc"), colors.HexColor(BLUE)), "orange": (colors.HexColor("#fdf0e9"), colors.HexColor(ORANGE)),
        "green": (colors.HexColor("#e8f5ee"), colors.HexColor("#1b7a52"))}
ST = {"body": ParagraphStyle("body", fontName="Body", fontSize=10.5, leading=14, spaceAfter=5),
      "cell": ParagraphStyle("cell", fontName="Body", fontSize=8.3, leading=10.2),
      "cellh": ParagraphStyle("cellh", fontName="Body-B", fontSize=8.3, leading=10.2, textColor=colors.white),
      "cap": ParagraphStyle("cap", fontName="Body-I", fontSize=9, leading=11.5, textColor=colors.HexColor(INK2), spaceAfter=8),
      "h1": ParagraphStyle("h1", fontName="Head-B", fontSize=16, leading=20, textColor=NAVY, spaceBefore=6, spaceAfter=7),
      "h2": ParagraphStyle("h2", fontName="Head-B", fontSize=12, leading=15, textColor=NAVY, spaceBefore=7, spaceAfter=4),
      "bul": ParagraphStyle("bul", fontName="Body", fontSize=10.5, leading=13.8, leftIndent=13, bulletIndent=2, spaceAfter=2.5),
      "src": ParagraphStyle("src", fontName="Body", fontSize=7.8, leading=9.6, leftIndent=14, firstLineIndent=-14, spaceAfter=1.5),
      "title": ParagraphStyle("title", fontName="Head-B", fontSize=22, leading=27, textColor=NAVY, spaceAfter=4),
      "sub": ParagraphStyle("sub", fontName="Body", fontSize=12, leading=16, textColor=colors.HexColor(INK2), spaceAfter=10)}
story = []
def H1(t): story.extend([CondPageBreak(4 * cm), Paragraph(t, ST["h1"])])
def H2(t): story.extend([CondPageBreak(3 * cm), Paragraph(t, ST["h2"])])
def P(t): story.append(Paragraph(t, ST["body"]))
def B(items):
    for it in items:
        story.append(Paragraph(it, ST["bul"], bulletText="•"))
    story.append(Spacer(1, 3))
def box(title, body, tone="blue"):
    bg, edge = TINT[tone]
    rows = [[Paragraph(f"<b>{title}</b>", ParagraphStyle("bt", parent=ST["body"], textColor=edge, spaceAfter=2))]]
    rows += [[Paragraph(b, ParagraphStyle("bb", parent=ST["body"], fontSize=10, leading=13.2, spaceAfter=2))] for b in body]
    t = Table(rows, colWidths=[17 * cm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("LINEBEFORE", (0, 0), (0, -1), 3, edge),
                           ("LEFTPADDING", (0, 0), (-1, -1), 9), ("TOPPADDING", (0, 0), (-1, 0), 6), ("BOTTOMPADDING", (0, -1), (-1, -1), 6)]))
    story.extend([KeepTogether([t]), Spacer(1, 7)])
def table(header, rows, widths, cap=None):
    data = [[Paragraph(h, ST["cellh"]) for h in header]] + [[Paragraph(str(c), ST["cell"]) for c in r] for r in rows]
    t = Table(data, colWidths=[w * cm for w in widths], repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE), ("LEFTPADDING", (0, 0), (-1, -1), 4),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)] +
                          [("BACKGROUND", (0, i), (-1, i), GREYT) for i in range(2, len(data), 2)]))
    if cap:
        story.append(KeepTogether([Paragraph(cap, ST["cap"])]))
    story.extend([t, Spacer(1, 8)])

cur, arm2, fut, fut2, o3, o32 = V["cur"], V["arm2"], V["fut"], V["fut2"], V["opt"], V["opt2"]

# ------------------------------------------------------------------ content
story += [Paragraph("Where does ARMO fit?", ST["title"]),
          Paragraph("Market and pipeline review of satellite soil moisture, and whether multispectral or hyperspectral "
                    "sensing can improve ARMO. ES4304 · 2 November 2026", ST["sub"])]
box("Bottom line", [
    "<b>ARMO's niche is real but narrow.</b> No system flying or confirmed in the pipeline delivers soil moisture that is "
    "<b>open, all-weather, directly retrieved, ≤ 200 m and ≤ 2-day over the contiguous US</b>. ARMO would.",
    "<b>The novelty is the time dimension, not field-scale L-band.</b> NISAR's SME2 product is already open, L-band, "
    "directly retrieved and 200 m. It differs from ARMO only in revisit (about 6 days, 6–12 by NASA's own range). Do not "
    "claim that field-scale L-band soil moisture is new. Claim NISAR-class retrieval at about 4× the sampling, sized to "
    f"your measured {V['win_med_d']:.1f}-day wetting-event lifetime.",
    "<b>The main threats are ROSE-L and commercial downscaled products.</b> ROSE-L (Copernicus; 2028–2030 in ESA and CEOS sources, ≥ 2030 in WMO OSCAR as of Oct 2026) plans "
    "L-band soil moisture with a 3–6-day revisit. Spire (500 m, daily) and EOSDA (250 m, 2–3 days) already sell products that "
    "look similar on paper, but they are modelled from coarse sensors, not observed at field scale, and they are not open.",
    "<b>Multispectral and hyperspectral sensors cannot fill the niche, and should not fly on ARMO.</b> In your own data, "
    f"only {f0(OPT.capture.iloc[0] * 100)} % of wetting events get a clear optical look even with daily coverage, and "
    f"{f0(opt.loc[5, 'capture'] * 100)} % at Sentinel-2's 5-day revisit. In ARMO's dawn–dusk orbit the sun is too low or below the horizon for optical imaging. Use free "
    "optical data as ancillary inputs instead, as NISAR does."], "green")

H1("1. The niche map")
from PIL import Image as _PI
_w, _h = _PI.open(FIGF).size
story.append(KeepTogether([Image(FIGF, width=16.5 * cm, height=16.5 * cm * _h / _w),
    Paragraph("Figure 1. Every satellite soil-moisture source found, by product resolution and revisit over the US. "
              "Filled blue: open products retrieved by an agency. Orange: commercial products downscaled or fused from coarse "
              "sensors. Hollow: planned. Grey: no CONUS product. Bars show a revisit range. The dotted line is the median "
              f"wetting-event window at your {V['n_stations']} USCRN stations. The ARMO star is design D from your orbit "
              "simulation (2 satellites). Planet SWC and the Copernicus Sentinel-1 product share the same values (1 km, daily) and are "
              "drawn slightly apart.", ST["cap"])]))
P("Reading the map: the passive radiometers (SMAP, SMOS, CIMR) and GNSS reflectometry (HydroGNSS) are fast but 9–44 km. "
  "Everything finer than about 1 km is either slow (NISAR, about 6 days), planned (ROSE-L), outside the US (SAOCOM, the "
  "Copernicus Sentinel-1 product), or commercial and modelled (Spire, EOSDA, Planet). The lower-left box, field-scale and "
  "faster than a wetting event, contains only ARMO.")

H1("2. Every soil-moisture source, checked")
rows = [
    ["SMAP L3 [S1–S3]", "Passive L-band", "36 km; 9 km interpolated", "2–3 d", "Operating since 2015", "Open", "Direct, coarse"],
    ["SMOS [S4–S5]", "Passive L-band", "~44 km", "< 3 d", "Extension confirmed to end-2025; later status not found", "Open", "Direct, coarse"],
    ["CIMR [S6]", "Passive, L to Ka", "L-band footprint 58 km; SM planned 9 and 36 km", "~daily", "Planned: CIMR-A 2029", "Open", "Coarse"],
    ["HydroGNSS [S7]", "GNSS reflectometry", "25 km", "1 d", "Launched 28 Nov 2025", "Open", "Coarse"],
    ["CYGNSS [S8, S9]", "GNSS reflectometry", "9 and 36 km", "Sub-daily, sparse", "±38° latitude only; planned de-orbit 1 Jan 2027", "Open", "Trained on SMAP"],
    ["SMAP/Sentinel-1 [S10, S11]", "Passive L + C-band SAR", "3 km (1 km unvalidated)", "3–12 d", "<b>Forward processing paused 1 Jul 2026</b>", "Open", "Disaggregated"],
    ["Sentinel-1 CLMS [S12]", "C-band SAR", "1 km", "Daily", "<b>Europe only</b>", "Open", "Direct, relative"],
    ["<b>NISAR SME2</b> [S13–S15]", "L-band SAR", "<b>200 m</b>", "<b>~6 d</b> (6–12)", "Provisional since 28 Oct 2025; 72 h latency", "Open", "<b>Direct</b>"],
    ["<b>ROSE-L</b> [S16–S18]", "L-band SAR, 2 sats, dawn–dusk", "Unclear (\"resolution unclear yet\")", "3 d (eoPortal) or 6 d global land (ESA slides)", "Planned 2028–2030; CONUS priority not found", "Copernicus (expected open)", "Direct"],
    ["SAOCOM-1A/1B [S19, S20]", "L-band SAR", "150–800 m", "8 d (pair)", "Product over Argentine Pampas only", "Non-commercial test", "Direct + model"],
    ["ALOS-2 / ALOS-4 [S21]", "L-band SAR", "No soil-moisture product", "14 d", "Operating", "JAXA policy", "–"],
    ["ICEYE, Capella, Umbra, Synspective, iQPS [S22, S23]", "<b>X-band</b> SAR", "No soil-moisture product", "Tasked", "Operating", "Commercial", "X-band \"strongly affected by vegetation\""],
    ["<b>Planet SWC</b> [S24, S25]", "Passive microwave, LPRM model", "<b>1 km</b> (20 m and 100 m <b>discontinued</b>)", "Near-daily", "Operating", "Commercial", "Downscaled"],
    ["<b>Spire</b> (company claim) [S26]", "GNSS-R fused with CYGNSS, SMAP, S1", "500 m (100 m planned)", "Daily", "Product since Apr 2024", "Commercial", "Fused / modelled"],
    ["<b>EOSDA</b> (company claim) [S27]", "SMAP-based", "250 m", "2–3 d", "Operating", "Commercial", "Downscaled from 9 km"],
    ["BIOMASS [P1, P2]", "P-band SAR (435 MHz)", "No SM product (forest maps 200 m)", "Global map every 228 d", "Launched 29 Apr 2025; <b>may not operate over North America</b>", "ESA", "–"],
    ["UHF/P-band SoOp: SNOOPI [P3–P5]", "Receive-only, reflected Navy MUOS signals", "Concept: ≈ 200 m at swath edge, ~1 km centre", "–", "One 6U CubeSat demo (2024); no product", "–", "Root zone, ~10 cm"],
]
table(["System", "Sensing", "SM resolution", "Revisit (US)", "Status", "Access", "Retrieval"], rows,
      [3.0, 2.4, 2.6, 1.8, 3.2, 1.7, 2.3],
      "Table 1. Soil-moisture sources checked 2 Nov 2026. Bold marks the closest competitors. Sources in the list at the end; company figures are the companies' own claims.")

H = V["h2h"].capture * 100; DP = V["depth"]
P(f"<b>Head to head on your ground truth</b> (script 21_armo_performance.py, same {V['n_era']} events, each system alone): "
  f"ARMO design D captures {f0(H['ARMO alone (design D)'])} % of wetting events, NISAR {f0(H['NISAR alone'])} %, ROSE-L "
  f"{f0(H['ROSE-L alone, 6-day'])} % at 6 days or {f0(H['ROSE-L alone, 3-day'])} % at 3 days. <b>Deeper sensing does not "
  f"help:</b> the same event rules on USCRN's 10 cm probes (a stand-in for P-band or UHF depth) give "
  f"{DP.loc[10, 'n_events']:,} events instead of {DP.loc[5, 'n_events']:,}, lasting {DP.loc[10, 'win_med_d']:.1f} instead of "
  f"{DP.loc[5, 'win_med_d']:.1f} days, so a lower frequency would not relax ARMO's revisit requirement.")

H1("3. Competitor by competitor: where ARMO differs, and where it does not")
table(["Competitor", "Same as ARMO", "Different from ARMO", "How to say it"], [
    ["NISAR SME2", "Open, L-band, direct retrieval, 200 m", f"Revisit ~6 d vs {D.loc['D', 'armo_mean_gap_d']:.1f} d; 72 h latency; still Provisional",
     f"\"NISAR-class retrieval at ~4× the sampling.\" Your data: Sentinel-1 + NISAR capture {f0(cur)} % of events; adding ARMO, {f0(D.loc['D', 'capture_fleet_plus_armo'] * 100)} %."],
    ["ROSE-L", "L-band, 2 satellites, dawn–dusk orbit (the same concept)", "Launch 2028–2030; soil-moisture resolution unclear; US acquisition priority not published; 3–6 d revisit",
     f"\"Even with ROSE-L at 6 days the fleet reaches {f0(fut)} %; at 3 days {f0(o3)} %, and a 2-day ARMO still adds {f0(o32 - o3)} points.\""],
    ["Spire, EOSDA", "Fine pixels, frequent updates", "Modelled from coarse sensors (SMAP 9 km, GNSS-R); commercial; not validated against wetting events",
     "\"Downscaling spreads a coarse signal over fine pixels; it cannot observe a field-scale event the coarse sensor smoothed out.\" Make testing this against USCRN events a Stage 1 task."],
    ["Planet SWC", "Near-daily", "Now 1 km (fine-scale products discontinued); passive-microwave model; commercial", "Not a field-scale competitor today."],
    ["Commercial X-band SAR", "All-weather, fast tasking", "X-band is \"strongly affected by vegetation\"; small scenes; no soil-moisture product; tasking cost",
     "\"No commercial operator sells field-scale soil moisture; X-band senses the canopy, not the soil.\""],
    ["Optical / thermal (Hydrosat, constellr, HLS, OPTRAM)", "Fine resolution (10–70 m)", "Needs clear sky; senses millimetres, not 0–5 cm", "See Section 4: clouds hide most events."],
], [2.6, 3.4, 5.0, 6.0])

H1("4. Can multispectral or hyperspectral sensing improve ARMO?")
P("<b>Short answer: use it as an input, do not fly it.</b> Three pieces of evidence, the first from your own ground truth.")
H2("4.1 Clouds hide most wetting events (your USCRN data)")
P(f"Rain causes wetting events, and rain comes with cloud. We checked the MODIS cloud mask at all {V['n_stations']} stations "
  f"at the real overpass times inside each of the {V['n_events']:,} event windows (Terra about 10:30 local, the same slot as "
  f"Sentinel-2 and Landsat; Aqua about 13:30). Only {CLEAR_ALL * 100:.0f} % of all overpasses were clear.")
table(["Sensor (regular revisit, random phase)", "Events with a clear look in the window", "All-weather radar, same revisit"],
      [["Daily optical, Terra + Aqua (best case for any optical sensor)", f"{opt.loc[0.5, 'capture'] * 100:.0f} %", "–"]] +
      [[f"Morning optical, {int(R)}-day" + (" (≈ two Sentinel-2s)" if R == 5 else " (≈ Landsat 8 + 9)" if R == 8 else ""),
        f"{opt.loc[R, 'capture'] * 100:.0f} %", f"{opt.loc[R, 'same_revisit_all_weather'] * 100:.0f} %"] for R in (1, 2, 3, 5, 8)],
      [8.0, 4.5, 4.5], "Table 2. Clear-sky optical capture of USCRN wetting events (script 18_optical_clouds.py). A clear look is "
      "an upper bound: optical methods still need bare soil or modest vegetation.")
P("At every revisit, cloud cuts optical capture to roughly half of what an all-weather radar gets. That is before asking "
  "whether optical light measures the right layer: it reaches \"only millimeters into the soil\" [O2], while L-band senses "
  "the top few centimetres.")
H2("4.2 ARMO's orbit cannot host an optical camera")
P("ARMO flies a dawn–dusk orbit (18:00 ascending node, like Sentinel-1 [O9]), where a SAR satellite \"does not "
  "experience the eclipse\" except briefly near the winter solstice, so its solar panels stay lit [O10]. Our geometry check for 25–49° N gives overpasses at about 06:15–06:35 and 17:25–17:45 local time. The sun "
  "is then 13–23° above the horizon in June, 3–6° at the equinoxes and <b>below the horizon in December</b>. Sentinel-2 "
  "flies at 10:30 precisely for \"a suitable level of solar illumination\" [O8]. Adding optics would also strain a smallsat "
  "whose SAR already \"requires higher power\" than an optical payload [O10]. The one smallsat that tried SAR plus optical on "
  "a single bus (GalaxEye Drishti, launched May 2026) lost contact during commissioning, before imaging [O11].")
H2("4.3 What optical data should do for ARMO (free, at no mass or power cost)")
B(["<b>Vegetation correction.</b> NISAR corrects L-band backscatter for vegetation with \"daily climatology derived using "
   "the MODIS 250-m\" NDVI, and retrieves only where vegetation water content is below 5 kg/m² [O5]. ARMO can use the "
   "same, upgraded to 30 m HLS NDVI (Landsat + Sentinel-2, every 2–3 days [O7]). NISAR also found \"HV itself was more "
   "representative of VWC\" [O5], so ARMO should carry HV.",
   "<b>Masks.</b> ESA WorldCover (10 m) and USDA CDL (30 m) land cover, as NISAR uses [O5], and 30 m irrigation maps [O6] so "
   "irrigation is not mistaken for rain wetting.",
   "<b>Clear-day cross-check.</b> Optical soil-moisture methods such as OPTRAM (errors below 0.04 cm³/cm³ with local "
   "calibration [O1]) can check ARMO's dry-down patterns on clear days. They cannot replace it during storms.",
   "<b>Leave hyperspectral out.</b> Satellite hyperspectral soil moisture is weak (PRISMA R² = 0.385 [O3]). Commercial "
   "Pixxel and Wyvern lack the SWIR bands that optical soil-moisture methods need [O4]. Occasional EnMAP or EMIT scenes "
   "could help calibrate the vegetation model at test sites."])

H1("5. Threats a panel will raise, and your answers")
table(["Challenge", "Answer"], [
    ["\"NISAR already does 200 m L-band soil moisture.\"", f"Yes, every ~6 days. Your ground truth shows events last {V['win_med_d']:.1f} days, and NISAR + Sentinel-1 capture {f0(cur)} %. ARMO is about revisit, not resolution."],
    ["\"ROSE-L will do this from 2028.\"", f"eoPortal lists a 3-day soil-moisture revisit; ESA's own slides give 6 days over global land. At 6 days the fleet reaches {f0(fut)} %, at 3 days {f0(o3)} %, and ARMO still adds {f0(o32 - o3)}–{f0(fut2 - fut)} points. ROSE-L's US acquisition plan is not published."],
    ["\"Spire and EOSDA already sell daily 250–500 m soil moisture.\"", "Those are modelled from 9 km SMAP or GNSS-R, commercial and not open. No published test shows they capture field-scale wetting events. Propose that test against USCRN in Stage 1. If they pass, ARMO's case weakens, and you will have said so first."],
    ["\"Why not just use optical or thermal at 30 m?\"", f"Clouds: only {f0(OPT.capture.iloc[0] * 100)} % of events have a clear look even with daily coverage, {f0(opt.loc[5, 'capture'] * 100)} % at a 5-day revisit (Table 2); and optical senses millimetres, not the top 5 cm."],
    ["\"Can two satellites really give 1.4 days?\"", "Your orbit simulation assumes a 362 km access range (25–45° off-nadir) per satellite. That is within what L-band SAR already flies: ALOS-4's ScanSAR covers a 700 km swath at 25 m [S21]. State the imaging mode in the requirements study."],
], [5.0, 12.0])
box("Suggested wording for the report and slides", [
    "\"No open, all-weather system observes field-scale (≤ 200 m) soil moisture faster than every ~6 days over the US. "
    "NISAR's 200 m product matches ARMO's resolution but not its revisit; commercial daily products are downscaled from "
    "9 km or coarser sensors. ARMO targets that gap: NISAR-class retrieval at ~1.4-day sampling, matched to wetting events "
    f"that last {V['win_med_d']:.1f} days.\""], "blue")

H1("Sources (checked 2 Nov 2026)")
P("Labels: company figures are the companies' own claims. Every source below was opened and the quoted figure read on the page, "
  "except where marked.")
SRC = [
    "S1 NSIDC SPL3SMP v9 (36 km; 2015–present) https://nsidc.org/data/spl3smp/versions/9",
    "S2 NSIDC SPL3SMP_E v6 (9 km, Backus-Gilbert interpolation) https://nsidc.org/data/spl3smp_e/versions/6",
    "S3 NASA JPL SMAP mission description (\"every 2-3 days\") https://smap.jpl.nasa.gov/mission/description/",
    "S4 Hydrol. Earth Syst. Sci. 23, 255 (2019) (SMOS ~44 km, < 3 days) https://hess.copernicus.org/articles/23/255/2019/",
    "S5 ESA eoGateway, SMOS (extension \"until the end of 2025\") https://earth.esa.int/eogateway/missions/smos",
    "S6 ESA, CIMR facts and figures (CIMR-A 2029; L-band 58 km) https://esa.int/Applications/Observing_the_Earth/Copernicus/CIMR/CIMR_facts_and_figures ; SM at 9 and 36 km: CEOS LPV soil-moisture plenary 2025, https://lpvs.gsfc.nasa.gov/PDF/LPV_Plenary_2025/LPV_plenary_soil_moisture.pdf",
    "S7 ESA, HydroGNSS (launched 28 Nov 2025; data opened) https://www.esa.int/Applications/Observing_the_Earth/FutureEO/HydroGNSS ; 25 km, 1-day: CEOS LPV 2025 (S6)",
    "S8 PO.DAAC CYGNSS L3 soil moisture v3.2 (9/36 km; trained on SMAP; ±38°) https://podaac.jpl.nasa.gov/dataset/CYGNSS_L3_SOIL_MOISTURE_V3.2",
    "S9 CYGNSS de-orbit 1 Jan 2027: R&D World article read via a mirror only (original blocked); single source, treat with caution",
    "S10 NSIDC SPL2SMAP_S v3 (\"forward processing was paused on 01 July 2026\"; 1 km \"should be used with caution\") https://nsidc.org/data/spl2smap_s/versions/3",
    "S11 Das et al., Remote Sens. Environ. 233, 111380 (2019) (revisit \"degrades from 3 days to 12 days\")",
    "S12 Copernicus Land Monitoring Service, daily surface soil moisture 1 km (\"continental Europe\") https://land.copernicus.eu/api/en/products/soil-moisture/daily-surface-soil-moisture-v1.0",
    "S13 ASF NISAR SME2 guide (200 m; \"twice every 12 days\"; 0.06 m³/m³ goal where VWC < 5 kg/m²; Provisional) https://nisar-docs.asf.alaska.edu/sme2/",
    "S14 NASA Earthdata SNWG, Global NISAR soil moisture (\"6 to 12 days\") https://www.earthdata.nasa.gov/about/nasa-support-snwg/solutions/global-nisar-soil-moisture",
    "S15 NASA Earthdata, NISAR L3 SME2 Provisional collection (from 2025-10-28) https://www.earthdata.nasa.gov/data/catalog/asf-nisar-l3-sme2-provisional-v1-1",
    "S16 ESA, ROSE-L contract signed (\"launch planned in 2028\"; maps soil moisture) https://www.esa.int/Applications/Observing_the_Earth/Copernicus/Contract_signed_for_new_Copernicus_ROSE-L_mission",
    "S17 eoPortal, ROSE-L (soil moisture \"revisit time of three days\"; dawn–dusk 693–700 km; no launch year) https://www.eoportal.org/satellite-missions/rose-l (secondary source)",
    "S18 CEOS LPV 2025 (ROSE-L \"Planned 2028/2030\"; \"resolution unclear yet\") (S6); Davidson (2023), ESA ROSE-L training slides (6 days global land, 3 days Europe), cited in the report",
    "S19 eoPortal, SAOCOM (8 days as a pair; soil-moisture maps) https://www.eoportal.org/satellite-missions/saocom",
    "S20 CONAE SAOCOM catalogue (Pampas only; non-commercial) https://catalogos.conae.gov.ar/Catalogo/catalogoSatSaocomAdel_en.html",
    "S21 eoPortal, ALOS-2 and ALOS-4 (14-day repeat; ALOS-4 ScanSAR 700 km at 25 m) https://www.eoportal.org/satellite-missions/alos-4",
    "S22 WMO OSCAR, ICEYE SAR (X-band; \"Strongly affected by vegetation\") https://space.oscar.wmo.int/instruments/view/iceye_sar",
    "S23 eoPortal, Umbra (X-band); New Space Economy guide to commercial SAR (ICEYE, Capella, Synspective, iQPS are X-band; secondary source)",
    "S24 Planet docs, Soil Water Content tech spec (\"Sales for Planet's 20m and 100m ... discontinued\"; 1000 m) https://docs.planet.com/data/planetary-variables/soil-water-content/techspec/ (company)",
    "S25 Planet SWC validation whitepaper (2023) (old 100 m product used SMAP/AMSR2 plus Sentinel-2 infrared) (company)",
    "S26 Spire, Soil Moisture Insights (30 Apr 2024: \"down to 500-meter resolution\", \"Updated daily\"; 100 m as a future goal) https://spire.com/?p=14420 (company)",
    "S27 EOS Data Analytics docs (SMAP L1B_TB/L2_SM_P_E; 250 m; 2–3 days) https://doc.eos.com/docs/statistics/soil-moisture/ (company)",
    "O1 Sadeghi et al., Remote Sens. Environ. 198, 52–68 (2017), OPTRAM",
    "O2 Nie et al., Remote Sens. 12, 2587 (2020) (optical reaches \"only millimeters into the soil\")",
    "O3 Jambhali et al., IEEE JSTARS (2025) (PRISMA soil moisture R² = 0.385)",
    "O4 Pixxel Firefly (450–900 nm) https://www.pixxel.space/firefly ; Wyvern (503–799 nm) https://gee-community-catalog.org/projects/wyvern/ (company / catalogue)",
    "O5 NISAR L3 Soil Moisture ATBD, JPL D-107679 R3.3 (2023) (MODIS 250 m NDVI climatology; VWC < 5 kg/m²; HV and VWC)",
    "O6 Xie, Gibbs & Lark, Earth Syst. Sci. Data 13, 5689 (2021), LANID 30 m irrigation maps (to 2017)",
    "O7 NASA HLS project (\"two to three day latency\"; 30 m) https://www.earthdata.nasa.gov/data/projects/hls",
    "O8 Copernicus SentiWiki, Sentinel-2 mission (10:30 overpass for \"a suitable level of solar illumination\") https://sentiwiki.copernicus.eu/web/s2-mission",
    "O9 Copernicus SentiWiki, Sentinel-1 mission (18:00 ascending node) https://sentiwiki.copernicus.eu/web/s1-mission",
    "O10 Won et al., IAC-09.C3.2.7 (2009), KARI (SAR \"requires higher power\") (abstract only)",
    "O11 Deccan Herald, 7 Jul 2026, Mission Drishti loses communication (news) https://www.deccanherald.com/science/mission-drishti-worlds-first-optosar-satellite-loses-communication-with-ground-4065533",
    "P1 Quegan et al., Remote Sens. Environ. 227, 44–60 (2019), BIOMASS (435 MHz, 6 MHz; SOTR restrictions \"mainly exclude the North American continent and Europe\"; 12 m reflector; 228-day global cycle) https://doi.org/10.1016/j.rse.2019.03.032",
    "P2 ESA, Biomass launches on Vega-C, 29 Apr 2025 https://www.esa.int/ESA_Multimedia/Videos/2025/04/ESA_s_Biomass_mission_launches_on_Vega-C",
    "P3 Yueh et al., IEEE Geosci. Remote Sens. Lett. 17(2), 207–211 (2020) (260 MHz tower; 0.02 m³/m³ vs top 10 cm; single frequency limited)",
    "P4 Yueh et al., IEEE JSTARS 14, 2796–2816 (2021) (SoOp SAR concept: ~200 m outer swath, ~1 km centre, 7 satellites, 100 km swath)",
    "P5 Garrison et al., Adv. Space Res. 73(6), 2855–2879 (2024), SNOOPI; NASA ESTO SNOOPI page (\"launched in 2024\"; 240–380 MHz) https://esto.nasa.gov/invest/snoopi",
    "Own analysis: optical capture (script 18_optical_clouds.py, MODIS MOD09GA/MYD09GA state_1km via Google Earth Engine); sun elevation in a dawn–dusk orbit (spherical geometry, no refraction); capture and orbit results from the report (scripts 02, 03, 09).",
]
for t in SRC:
    story.append(Paragraph(t, ST["src"]))


def on_page(c, doc):
    c.saveState(); c.setFont("Body", 8.5); c.setFillColor(colors.HexColor(INK2))
    c.drawString(2 * cm, 1.2 * cm, "ARMO · market and niche review"); c.drawRightString(A4[0] - 2 * cm, 1.2 * cm, str(doc.page))
    c.restoreState()


doc = BaseDocTemplate(OUT, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm, bottomMargin=2 * cm,
                      title="Where does ARMO fit? Market and niche review", author="ES4304 ARMO team")
doc.addPageTemplates([PageTemplate(id="p", frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)], onPage=on_page)])
doc.build(story)
print("saved", OUT)
