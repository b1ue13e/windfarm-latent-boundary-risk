import pypdf
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

papers = [
    ROOT / "literature/ieee_style_references/2020_Dynamic_Reserve_and_Transmission_Capacity_All.pdf",
    ROOT / "literature/ieee_style_references/2021_Spatio-Temporal_Graph_Neural_Networks_for_Mul.pdf",
    ROOT / "literature/top_journal_papers/2019_IEEETPWRS_Pierre_WideAreaTelemetryDelayControl.pdf",
    ROOT / "literature/top_journal_papers/2015_IEEETSG_Dowell_ProbabilisticWindForecastingVAR.pdf",
    ROOT / "literature/top_journal_papers/2021_IEEETII_Pellegrino_OffshoreWindFarmSCADAMonitoring.pdf"
]

for p in papers:
    if not p.is_file():
        continue
    try:
        reader = pypdf.PdfReader(str(p))
        first_page = reader.pages[0].extract_text()
        print("="*60)
        print(f"FILE: {p.name} (Pages: {len(reader.pages)})")
        lines = [line.strip() for line in first_page.splitlines() if line.strip()]
        for l in lines[:15]:
            print("  ", l[:90])
    except Exception as e:
        print(f"Error reading {p.name}: {e}")
