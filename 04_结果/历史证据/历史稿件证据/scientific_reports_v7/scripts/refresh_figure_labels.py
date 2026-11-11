"""Re-export two label revisions from saved estimates, without research execution."""
from pathlib import Path
import hashlib
import importlib.util
import json

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('stored_figures',ROOT/'scripts/build_figures.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
previous=json.loads((ROOT/'author_working/qa/figure_receipt.json').read_text())
module.timing()
module.reconstruction()
module.sensitivity()
old=[r for r in previous['plotted_fields'] if r['figure']=='fig3']
assert old==module.FIELDS, 'Label revision changed plotted source values'
previous['source_code_sha256']=hashlib.sha256((ROOT/'scripts/build_figures.py').read_bytes()).hexdigest()
previous['label_revision']={'fig1':'Action updated; common forecast unchanged',
                            'fig3':'Additions distinguished from replacement; input and target labels aligned',
                            'figS1':'Same addition and replacement terms as the main reconstruction figure',
                            'numerical_fields_unchanged':True}
(ROOT/'author_working/qa/figure_receipt.json').write_text(json.dumps(previous,indent=2)+'\n')
print('Updated labels; plotted values retained.')
