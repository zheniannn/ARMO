"""Build the proposal (docx from the course template) with every number read from results."""
import os
import numpy as np
import pandas as pd
import docx
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from common import ROOT, PROC, FIG

TEMPLATE = next(p for p in (os.path.join(ROOT, "References", "Remote_Sensing_Final_Report_Template (3).docx"),
                            os.path.join(ROOT, "Remote_Sensing_Final_Report_Template (3).docx")) if os.path.exists(p))
OUT = os.path.join(ROOT, "report", "ARMO_Proposal_ES4304.docx")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
BODY_PT = 10.5


# ------------------------------------------------------------------ numbers
def load_values():
    V = {}
    ev = pd.read_csv(os.path.join(PROC, "events.csv"))
    st = pd.read_csv(os.path.join(PROC, "station_seasons.csv"))
    V["n_events"] = len(ev); V["n_stations"] = ev.wban.nunique(); V["n_ss"] = int(st.included.sum())
    V["win_med_d"] = ev.window_h.median() / 24; V["win_q1_d"] = ev.window_h.quantile(.25) / 24
    V["win_q3_d"] = ev.window_h.quantile(.75) / 24; V["hl_med_d"] = ev.half_life_h.median() / 24
    V["amp_med"] = ev.amp.median(); V["rain_med"] = ev.rain_mm.median(); V["cens"] = ev.censored.mean() * 100
    V["frac_lt2d"] = (ev.window_h < 48).mean() * 100; V["rise_med_h"] = ev.rise_h.median()
    V["winabs_med_d"] = ev.window_abs_h.median() / 24
    cap = pd.read_csv(os.path.join(PROC, "capture_synthetic.csv"))
    h = cap[cap.window == "half-amplitude"].set_index("R"); a = cap[cap.window == "abs0.03"].set_index("R")
    for R in (1, 2, 3, 4, 6, 12):
        V[f"c{R}"] = h.loc[R, "capture"] * 100; V[f"c{R}lo"] = h.loc[R, "ci_lo"] * 100; V[f"c{R}hi"] = h.loc[R, "ci_hi"] * 100
        V[f"ca{R}"] = a.loc[R, "capture"] * 100; V[f"an{R}"] = h.loc[R, "analytic"] * 100
        V[f"c{R}_25"] = h.loc[R, "cap_2025"] * 100; V[f"c{R}_26"] = h.loc[R, "cap_2026"] * 100
    V["max_an_err"] = (h.capture - h.analytic).abs().max() * 100
    # interpolate regular revisit giving 80 % capture
    V["R80"] = float(np.interp(0.80, h.capture.values[::-1], h.index.values[::-1]))
    sens = pd.read_csv(os.path.join(PROC, "sensitivity.csv"))
    V["sens6_lo"], V["sens6_hi"] = sens.cap_R6.min() * 100, sens.cap_R6.max() * 100
    V["sens2_lo"], V["sens2_hi"] = sens.cap_R2.min() * 100, sens.cap_R2.max() * 100
    V["sens_win_lo"], V["sens_win_hi"] = sens.median_window_h.min() / 24, sens.median_window_h.max() / 24
    real = pd.read_csv(os.path.join(PROC, "capture_real.csv")).set_index("fleet")
    V["s1_25"] = real.loc["Sentinel-1 (2025 season)", "capture"] * 100
    V["s1_26"] = real.loc["Sentinel-1 (2026 season)", "capture"] * 100
    V["s1_era"] = real.loc["Sentinel-1 (NISAR era)", "capture"] * 100
    V["ni_era"] = real.loc["NISAR (NISAR era)", "capture"] * 100
    V["both_era"] = real.loc["Sentinel-1 + NISAR (NISAR era)", "capture"] * 100
    V["both_era_abs"] = real.loc["Sentinel-1 + NISAR (NISAR era)", "capture_abs"] * 100
    V["n_era"] = int(real.loc["NISAR (NISAR era)", "n_events"]); V["n_era_st"] = int(real.loc["NISAR (NISAR era)", "n_stations"])
    V["both_p10"] = real.loc["Sentinel-1 + NISAR (NISAR era)", "station_p10"] * 100
    V["both_p90"] = real.loc["Sentinel-1 + NISAR (NISAR era)", "station_p90"] * 100
    rv = pd.read_csv(os.path.join(PROC, "revisit_real.csv")).groupby("fleet").median(numeric_only=True)
    for k, lab in (("S1", "s1"), ("NISAR", "ni"), ("S1+NISAR", "both")):
        V[f"gap_{lab}"] = rv.loc[k, "mean_gap_d"]; V[f"maxgap_{lab}"] = rv.loc[k, "max_gap_d"]; V[f"nacq_{lab}"] = rv.loc[k, "n_acq"]
    V["reg_equiv"] = float(np.interp(V["gap_both"], h.index.values, h.capture.values)) * 100
    mv = pd.read_csv(os.path.join(PROC, "marginal_value.csv")).set_index("scenario")
    def g(s): return mv.loc[s, "capture"] * 100, mv.loc[s, "ci_lo"] * 100, mv.loc[s, "ci_hi"] * 100
    V["cur"], V["cur_lo"], V["cur_hi"] = g("Current fleet (S1C/D + NISAR)")
    V["arm2"], V["arm2_lo"], V["arm2_hi"] = g("Current fleet + ARMO 2-day")
    V["arm3"], V["arm3_lo"], V["arm3_hi"] = g("Current fleet + ARMO 3-day")
    V["arm4"], _, _ = g("Current fleet + ARMO 4-day"); V["arm1"], _, _ = g("Current fleet + ARMO 1-day")
    V["fut"], V["fut_lo"], V["fut_hi"] = g("Future fleet (+ROSE-L 6-day)")   # ESA: 6 d global land, 2 sats
    V["opt"], _, _ = g("Optimistic future (+ROSE-L 3-day)"); V["opt2"], _, _ = g("Optimistic future + ARMO 2-day")
    V["fut2"], V["fut2_lo"], V["fut2_hi"] = g("Future fleet + ARMO 2-day")
    V["fut3"], V["fut3_lo"], V["fut3_hi"] = g("Future fleet + ARMO 3-day")
    s1 = pd.read_csv(os.path.join(PROC, "s1_summary.csv"), index_col=0).iloc[:, 0]
    V.update({f"s1_{k}": v for k, v in s1.items()})
    f = os.path.join(PROC, "nisar_summary.csv")
    if os.path.exists(f):
        ni = pd.read_csv(f, index_col=0).iloc[:, 0]
        V.update({f"nis_{k}": v for k, v in ni.items()})
    sm = pd.read_csv(os.path.join(PROC, "smap_summary.csv"), index_col=0)
    V.update({f"sm_{k}": float(v) for k, v in sm["all"].items()})
    V.update({f"smr_{k}": float(v) for k, v in sm["recommended"].items()})
    V.update({f"snr_{k}": v for k, v in pd.read_csv(os.path.join(PROC, "snr_summary.csv"), index_col=0).iloc[:, 0].items()})
    V["snr_tab"] = pd.read_csv(os.path.join(PROC, "snr_requirement.csv")).set_index("sensor")
    V["strata"] = pd.read_csv(os.path.join(PROC, "detection_strata.csv"))
    lc = pd.read_csv(os.path.join(PROC, "station_vegetation.csv"))
    V["n_lc"] = lc.cover.value_counts().to_dict(); V["crop9_med"] = lc.crop_frac_9km.median()
    V["ndvi_summer_med"] = lc.ndvi_summer.median()
    V["designs"] = pd.read_csv(os.path.join(PROC, "armo_designs.csv"))
    era = pd.read_csv(os.path.join(PROC, "era5_summary.csv")).set_index("a_min")
    V["era_pod"] = era.loc[0.02, "POD"] * 100; V["era_far"] = era.loc[0.02, "FAR"] * 100; V["era_csi"] = era.loc[0.02, "CSI"] * 100
    V["era_pod01"] = era.loc[0.01, "POD"] * 100; V["era_far01"] = era.loc[0.01, "FAR"] * 100
    ec = pd.read_csv(os.path.join(PROC, "era5_continuous.csv"))
    V["era_r"] = ec.r_raw.median(); V["era_ranom"] = ec.r_anom.median(); V["era_rdd"] = ec.r_daily_change.median()
    V["era_ubrmse"] = ec.ubrmse.median(); V["era_bias"] = ec.bias.median(); V["era_rain"] = ec.rain_detect.mean() * 100
    # head-to-head (step 21), sensing-depth test (step 21) and optical cloud test (step 18)
    V["h2h"] = pd.read_csv(os.path.join(PROC, "performance_headtohead.csv")).set_index("system")
    V["depth"] = pd.read_csv(os.path.join(PROC, "depth_summary.csv")).set_index("depth_cm")
    oc = pd.read_csv(os.path.join(PROC, "optical_capture.csv"))
    V["opt_daily"] = oc.capture.iloc[0] * 100
    r5 = oc[oc.revisit_d == 5].iloc[0]; V["opt5"], V["sar5"] = r5.capture * 100, r5.same_revisit_all_weather * 100
    # spacecraft sizing and mission cost (step 22)
    V["siz"] = pd.read_csv(os.path.join(PROC, "armo_sizing.csv")).iloc[0]
    V["mass"] = pd.read_csv(os.path.join(PROC, "armo_mass.csv"))
    V["cost"] = pd.read_csv(os.path.join(PROC, "armo_cost.csv"))
    V["need"] = pd.read_csv(os.path.join(PROC, "need_summary.csv")).iloc[0]     # step 23 (Earth Engine maps)
    return V


# ------------------------------------------------------------------ docx helpers
def set_cell_bg(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd"); shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hex_fill)
    tcPr.append(shd)


def set_borders(table, color="A6A6A6", sz="4"):
    tblPr = table._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{edge}"); e.set(qn("w:val"), "single"); e.set(qn("w:sz"), sz); e.set(qn("w:color"), color)
        b.append(e)
    tblPr.append(b)


class Doc:
    def __init__(self):
        self.d = docx.Document(TEMPLATE)
        body = self.d.element.body
        kids = list(body.iterchildren())
        for el in kids[4:]:                       # keep title lines + cover table; drop guidance and placeholders
            if not el.tag.endswith("sectPr"):
                body.remove(el)
        self.fig = 0; self.tab = 0
        self.sty = {st.style_id: st for st in self.d.styles}

    def cover(self, rows):
        t = self.d.tables[0]
        for r, val in zip(t.rows, rows):
            c = r.cells[1]
            for p in c.paragraphs[1:]:
                p._p.getparent().remove(p._p)
            p = c.paragraphs[0]
            for run in p.runs[1:]:
                run._r.getparent().remove(run._r)
            run = p.runs[0] if p.runs else p.add_run()
            run.text = val; run.italic = False; run.font.color.rgb = RGBColor(0, 0, 0); run.font.size = Pt(10)

    def page_break(self):
        self.d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def h1(self, text):
        p = self.d.add_paragraph(text, style=self.sty["Heading1"])
        p.paragraph_format.space_before = Pt(8); p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.keep_with_next = True

    def h2(self, text):
        p = self.d.add_paragraph(text, style=self.sty["Heading2"])
        p.paragraph_format.space_before = Pt(5); p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.keep_with_next = True

    def para(self, text, size=BODY_PT, after=3, style=None, indent=None, align_just=True):
        p = self.d.add_paragraph(style=style)
        self._runs(p, text, size)
        pf = p.paragraph_format; pf.space_after = Pt(after); pf.space_before = Pt(0); pf.line_spacing = 1.0
        if align_just:
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if indent is not None:
            pf.left_indent = Cm(indent); pf.first_line_indent = Cm(-0.5)
        return p

    def _runs(self, p, text, size):
        # **bold** and *italic* inline markup
        import re
        for tok in re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*)", text):
            if not tok:
                continue
            if tok.startswith("**"):
                r = p.add_run(tok[2:-2]); r.bold = True
            elif tok.startswith("*"):
                r = p.add_run(tok[1:-1]); r.italic = True
            else:
                r = p.add_run(tok)
            r.font.size = Pt(size)

    def bullet(self, text, num=None, size=BODY_PT):
        lead = f"{num}. " if num is not None else "• "
        return self.para(lead + text, size=size, after=1.5, indent=0.6)

    def figure(self, fname, width_cm, caption):
        self.fig += 1
        p = self.d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(1); p.paragraph_format.keep_with_next = True
        p.add_run().add_picture(os.path.join(FIG, fname), width=Cm(width_cm))
        c = self.d.add_paragraph(); c.paragraph_format.space_after = Pt(6)
        r = c.add_run(f"Figure {self.fig}. "); r.bold = True; r.font.size = Pt(9)
        self._runs(c, caption, 9)
        c.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        return self.fig

    def table(self, caption, header, rows, widths_cm, size=8.5, bold_last=False, first_col_bold=False):
        self.tab += 1
        c = self.d.add_paragraph(); c.paragraph_format.space_after = Pt(2); c.paragraph_format.space_before = Pt(3)
        c.paragraph_format.keep_with_next = True
        r = c.add_run(f"Table {self.tab}. "); r.bold = True; r.font.size = Pt(9)
        self._runs(c, caption, 9)
        t = self.d.add_table(rows=1 + len(rows), cols=len(header))
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        set_borders(t)
        grid = t._tbl.tblGrid
        for j, gc in enumerate(grid.findall(qn("w:gridCol"))):
            gc.set(qn("w:w"), str(int(widths_cm[j] * 567)))
        for i, row in enumerate([header] + rows):
            trPr = t.rows[i]._tr.get_or_add_trPr()
            cs = OxmlElement("w:cantSplit"); trPr.append(cs)
            for j, val in enumerate(row):
                cell = t.cell(i, j)
                cell.width = Cm(widths_cm[j])
                p = cell.paragraphs[0]; p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.keep_with_next = i < len(rows)   # keep the whole table on one page
                self._runs(p, str(val), size)
                if i == 0:
                    set_cell_bg(cell, "DCE6F1")
                    for run in p.runs: run.bold = True
                elif (bold_last and i == len(rows)) or (first_col_bold and j == 0):
                    for run in p.runs: run.bold = True
        sp = self.d.add_paragraph(); sp.paragraph_format.space_after = Pt(2)
        for run in sp.runs: run.font.size = Pt(4)
        return t

    def footer_page_numbers(self):
        sec = self.d.sections[0]
        p = sec.footer.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run()
        for tag, text in (("begin", None), (None, "PAGE"), ("end", None)):
            if tag:
                f = OxmlElement("w:fldChar"); f.set(qn("w:fldCharType"), tag); r._r.append(f)
            else:
                it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = text; r._r.append(it)

    def save(self):
        self.d.save(OUT)


if __name__ == "__main__":
    import report_text
    V = load_values()
    doc = Doc()
    report_text.write(doc, V)
    doc.footer_page_numbers()
    doc.save()
    print("saved", OUT)
