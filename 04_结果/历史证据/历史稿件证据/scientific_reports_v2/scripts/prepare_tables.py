"""Project existing fields into editable tables; no new estimates or intervals."""
from pathlib import Path
import csv
import hashlib
import json
import shutil
import tarfile

HERE = Path(__file__).resolve().parents[1]
DATA = HERE / "source_data"
OUT = HERE / "tables"
CELLS = ("F", "FZ", "O6", "OP6", "OZ6", "OPZ6")
NAMES = dict(zip(CELLS, ("Fresh", "Fresh + pitch", "Old", "Old + power", "Old + pitch", "Old + power + pitch")))


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def csv_rows(name):
    with (DATA / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def table(name, columns, rows):
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"]*len(columns)) + " |"]
    lines += ["| " + " | ".join(str(value) for value in row) + " |" for row in rows]
    (OUT / (name + ".md")).write_text("\n".join(lines) + "\n", encoding="utf-8")
    with (OUT / (name + ".csv")).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle); writer.writerow(columns); writer.writerows(rows)


def main():
    OUT.mkdir(exist_ok=True)
    original, controls, history = [load(name) for name in ["M_original_summary.json", "M_controls_summary.json", "M_historical_choices.json"]]
    main_rows=[]
    for cell in CELLS:
        row=[NAMES[cell]]
        for estimator in ["HGB","MLP"]:
            for recipe in ["Original","Common"]:
                if recipe == "Original":
                    key=f"{estimator}:{cell}"
                    value=original["mean_cost"][original["labels"].index(key)]
                    eligible=original["risk_qualified"][key]
                else:
                    key=f"{recipe}:{estimator}:{cell}"
                    value=controls["mean_metrics"]["C"][controls["labels"].index(key)]
                    eligible=controls["jointly_qualified"][key]
                row.append(f"{value:.3f}" + ("†" if not eligible else ""))
        main_rows.append(row)
    table("table2",["Input recipe","HGB original","HGB common","MLP original","MLP common"],main_rows)
    table("table3",["Original claim","HGB original","HGB common","MLP original","MLP common"],
          [[text]+["Not met" if not controls['corrected_routes'][f'{r}:{e}'][key] else 'Met'
                    for e in ['HGB','MLP'] for r in ['Original','Common']]
           for key,text in [('A','Important state benefit (A)'),('B','Power substitution (B)'),('C','Uniformly low state increment (C)')]])
    caption=(r"\textbf{Table 3. Outcomes of the original combined decision claims.} "
        r"Criteria retain the original 1\% cost, 10\% event and 0.001 weighted-uncovered-shortfall/$C^*$ limits with the corrected substitution predicate. "
        r"These are stored corrected-route outcomes of the later 596-coordinate diagnostic; original 154-family cost intervals remain separate. "
        r"Exact conjunctions are in the Supplementary Methods; stored risk bounds and failure witnesses are in Supplementary Tables S9--S10. ``Not met'' refers to the combined claim, not every component endpoint.")
    body=[r"\begin{table}[H]",r"\centering",r"\caption*{"+caption+"}",r"\small",r"\begin{tabular}{lcccc}",r"\toprule",
          r"Original claim & HGB original & HGB common & MLP original & MLP common \\",r"\midrule"]
    for key,text in [('A','Important state benefit (A)'),('B','Power substitution (B)'),('C','Uniformly low state increment (C)')]:
        outcomes=['Not met' if not controls['corrected_routes'][f'{r}:{e}'][key] else 'Met' for e in ['HGB','MLP'] for r in ['Original','Common']]
        body.append(text+' & '+' & '.join(outcomes)+r' \\')
    body.extend([r"\bottomrule",r"\end{tabular}",r"\end{table}"])
    (OUT/'table3.tex').write_text('\n'.join(body)+'\n')
    all_metrics=[]
    for recipe in ['Original','Common']:
        for estimator in ['HGB','MLP']:
            for cell in CELLS:
                key=f'{recipe}:{estimator}:{cell}';idx=controls['labels'].index(key)
                q=history['choices'][f'{estimator}:{cell}']['q'] if recipe=='Original' else controls['common_q']
                all_metrics.append([recipe,estimator,NAMES[cell],f'{q:.3f}',
                    *[f"{controls['mean_metrics'][metric][idx]:.4f}" for metric in ['C','R','U']],
                    f"{100*controls['mean_metrics']['V'][idx]:.4f}",
                    'Yes' if controls['jointly_qualified'][key] else 'No'])
    table('tableS2',['Calib.','Estimator','Recipe','q','C','R','U','V (%)','Qualified'],all_metrics)
    cost=[]
    for row in csv_rows('display_M_cost.csv'):
        short={'fresh_state':'Fresh pitch','old_state':'Old pitch','old_power':'Old power','P_premium_vs_Z':'Power vs pitch','residual_state':'Residual pitch'}
        cost.append([row['recipe'],row['estimator'],short[row['comparison']],row['family'],
                     row['kind'],f"{100*float(row['point']):.4f}",
                     f"[{100*float(row['lower']):.4f}, {100*float(row['upper']):.4f}]"])
    table('tableS3',['Calibration','Estimator','Contrast','Family','Type','Point (%)','Stored interval (%)'],cost)
    state=[]
    for row in csv_rows('display_R_cost.csv'):
        if row['condition']=='pitch_withheld':
            state.append([row['comparison'],row['block_span'],f"{float(row['point']):.6f}",
                          f"[{float(row['simultaneous_ci_lower']):.6f}, {float(row['simultaneous_ci_upper']):.6f}]"])
    table('tableS4',['Contrast','Block days','Cost difference','Stored interval'],state)
    mse=[]
    for seed in range(201,206):
        diagnostics=load(f'R_diagnostics_{seed}.json')
        values=diagnostics['continuous_pitch_mse_degrees_squared']
        mse.append([seed,*[f'{values[k]:.6f}' for k in ['pitch','wind','shuffle']],diagnostics['state_diagnostic_cells']])
    table('tableS5',['Fixed-fit seed','Pitch-target probe','Base-input probe','Shuffled-target probe','Finite-pitch cells'],mse)
    budget=[]
    for recipe in ['Original','Common']:
        for estimator in ['HGB','MLP']:
            for cell in ['OP6','OPZ6','Match_residual_state']:
                key=f'{recipe}:{estimator}:{cell}';idx=controls['labels'].index(key)
                budget.append([recipe,estimator,NAMES.get(cell,'Historical match'),
                    *[f"{controls['mean_metrics'][k][idx]:.4f}" for k in ['R','U','C']],
                    f"{100*controls['mean_metrics']['V'][idx]:.4f}",
                    'Yes' if controls['jointly_qualified'][key] else 'No'])
    table('tableS6',['Calibration','Estimator','Program','R','U','C','V (%)','Qualified'],budget)
    # Complete source records are copied or projected, never recalculated.
    shutil.copyfile(DATA/'R_paired_intervals.json',HERE/'supplement_data/Supplementary_Data1_R.json')
    shutil.copyfile(DATA/'M_original_summary.json',HERE/'supplement_data/Supplementary_Data2_M_original.json')
    shutil.copyfile(DATA/'M_controls_summary.json',HERE/'supplement_data/Supplementary_Data3_M_controls.json')
    for name in ['R_original_compact.tar.gz','M_original_compact.tar.gz','M_controls_compact.tar.gz']:
        with tarfile.open(HERE/'supplement_data'/name) as archive:
            selected=[member for member in archive.getmembers() if member.isfile() and member.name.endswith('/envelopes.json')]
            for member in selected:
                dest=HERE/'supplement_data'/(name.replace('_compact.tar.gz','')+'_envelopes.json')
                dest.write_bytes(archive.extractfile(member).read())
    (HERE/'qa/table_receipt.json').write_text(json.dumps({'status':'EXACT_STORED_FIELD_PROJECTIONS_AND_FORMATTING',
        'new_aggregates_or_intervals':False,'Cstar':controls['Cstar'],
        'sources':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(DATA.iterdir()) if p.is_file()},
        'outputs':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file()}},indent=2)+'\n')
    print('Stored-field tables and Supplementary Data prepared; no new statistics.')


if __name__=='__main__':
    main()
