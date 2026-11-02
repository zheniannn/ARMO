"""Re-run evaluation, figures and documents after the data-extraction scripts (01-05, 07, 14) have finished."""
import os, subprocess, sys
from common import ROOT

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
steps = ["06_s1_observability.py", "08_nisar_eval.py", "15_smap_eval.py", "16_detection_strata.py",
         "17_snr_requirement.py", "10_fig_map.py", "11_fig_results.py", "12_fig_workflow.py",
         "13_fig_observability.py", "21_armo_performance.py", "22_armo_sizing.py", "23_gee_need_maps.py", "19_market_report.py", "20_build_report.py", "30_build_slides.py", "40_review_and_qa.py"]
for s in steps:
    print(">>", s, flush=True)
    subprocess.run([PY, "-W", "ignore", os.path.join(HERE, s)], check=True, cwd=HERE, stdout=subprocess.DEVNULL)


def office(script, src, dst):
    subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", os.path.join(HERE, script),
                    "-in", src, "-out", dst], check=True)


office("to_pdf.ps1", os.path.join(ROOT, "report", "ARMO_Proposal_ES4304.docx"), os.path.join(ROOT, "report", "ARMO_Proposal_ES4304.pdf"))
office("pptx_to_pdf.ps1", os.path.join(ROOT, "slides", "ARMO_Slides_ES4304.pptx"), os.path.join(ROOT, "slides", "ARMO_Slides_ES4304.pdf"))
from pypdf import PdfReader
subprocess.run([PY, "-W", "ignore", os.path.join(HERE, "60_build_team_guide.py")], check=True, cwd=HERE, stdout=subprocess.DEVNULL)
for f in ("report/ARMO_Proposal_ES4304.pdf", "slides/ARMO_Slides_ES4304.pdf", "notes/ARMO_Team_Guide.pdf"):
    print(f, len(PdfReader(os.path.join(ROOT, f)).pages), "pages")
