import pypdf
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]

papers = [
    ("IEEE_TPWRS_2020_Reserve", ROOT / "literature/ieee_style_references/2020_Dynamic_Reserve_and_Transmission_Capacity_All.pdf"),
    ("IEEE_TSTE_2021_STGNN", ROOT / "literature/ieee_style_references/2021_Spatio-Temporal_Graph_Neural_Networks_for_Mul.pdf"),
    ("IEEE_TSG_2015_VAR_Pinson", ROOT / "literature/top_journal_papers/2015_IEEETSG_Dowell_ProbabilisticWindForecastingVAR.pdf"),
    ("IEEE_TPWRS_2019_Telemetry", ROOT / "literature/top_journal_papers/2019_IEEETPWRS_Pierre_WideAreaTelemetryDelayControl.pdf")
]

results = {}

for tag, p in papers:
    if not p.is_file():
        continue
    try:
        reader = pypdf.PdfReader(str(p))
        num_pages = len(reader.pages)
        # Extract title and abstract from first 2 pages
        text_p1 = reader.pages[0].extract_text()
        text_p2 = reader.pages[1].extract_text() if num_pages > 1 else ""
        full_text_start = (text_p1 + "\n" + text_p2)
        
        # Also grab concluding section from last 2 pages
        text_end = reader.pages[-2].extract_text() + "\n" + reader.pages[-1].extract_text()
        
        results[tag] = {
            "filename": p.name,
            "num_pages": num_pages,
            "start_excerpt": full_text_start[:3000],
            "end_excerpt": text_end[:3000]
        }
    except Exception as e:
        results[tag] = {"error": str(e)}

out_file = ROOT / "literature/extracted_ieee_insights.json"
out_file.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')
print(f"Extracted insights written to {out_file}. Extracted {len(results)} papers.")
