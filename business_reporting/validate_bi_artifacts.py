"""Offline source, field-binding and portability checks; not a BI runtime test."""
import base64
import csv
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
REPORTING = ROOT / 'business_reporting'
with (ROOT / 'raw/KAG_conversion_data.csv').open() as f:
    original = list(csv.DictReader(f))
with (REPORTING / 'tableau/data/KAG_conversion_data.csv').open() as f:
    tableau = list(csv.DictReader(f))
renames = {'xyz_campaign_id': 'Campaign', 'Spent': 'Spend'}
assert tableau == [{renames.get(k,k):v for k,v in row.items()} for row in original]
twb = ET.parse(REPORTING / 'tableau/campaign_dashboard.twb')
for connection in twb.findall('.//connection'):
    if connection.get('class') == 'textscan':
        assert connection.get('directory') == 'data'
        assert (REPORTING/'tableau'/connection.get('directory')/connection.get('filename')).is_file()
assert len(twb.findall('./worksheets/worksheet')) == 3
project = REPORTING/'powerbi/project'
ads = (project/'pxpx.SemanticModel/definition/tables/Ads.tmdl').read_text()
encoded = re.search(r'Encoded = Text.Combine\(\{(.*?)\}\)',ads).group(1)
decoded = base64.b64decode(''.join(re.findall(r'"([^"]+)"',encoded)))
assert decoded == (ROOT/'raw/KAG_conversion_data.csv').read_bytes()
tables = {}
for path in (project/'pxpx.SemanticModel/definition/tables').glob('*.tmdl'):
    t = path.read_text()
    tables[path.stem] = {
        'Column': {a or b for a,b in re.findall(r"^\tcolumn (?:'([^']+)'|([^\n]+))",t,re.M)},
        'Measure': set(re.findall(r"^\tmeasure '([^']+)'",t,re.M)),
    }
visuals = list((project/'pxpx.Report/definition/pages').rglob('visual.json'))
assert len(visuals)==16
for path in visuals:
    v = json.loads(path.read_text())
    for role in v['visual']['query']['queryState'].values():
        for projection in role['projections']:
            kind = next(iter(projection['field']))
            f = projection['field'][kind]
            assert f['Property'] in tables[f['Expression']['SourceRef']['Entity']][kind]
expected = json.loads((REPORTING/'validation.json').read_text())
for e in expected['campaigns']:
    rows = [r for r in tableau if r['Campaign']==e['campaign']]
    assert abs(sum(float(r['Spend']) for r in rows)-e['spend'])<1e-8
    assert sum(int(r['Approved_Conversion']) for r in rows)==e['approved']
print('PASS: Tableau source matches all 1,143 rows; relative connection resolves; 3 worksheets; Power BI embedded source matches; 16 visual bindings; campaign totals reconcile.')
