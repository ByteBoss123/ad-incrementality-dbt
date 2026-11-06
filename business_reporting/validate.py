"""Independent controls for the reporting extension; Python standard library only."""
import csv
import hashlib
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'raw/KAG_conversion_data.csv'


def validate(rows):
    seen = set()
    for row in rows:
        key = row['ad_id']
        if key in seen:
            raise ValueError('Duplicate ad_id: ' + key)
        seen.add(key)
        for name in ('Impressions', 'Clicks', 'Total_Conversion', 'Approved_Conversion'):
            value = float(row[name])
            if value < 0 or not value.is_integer():
                raise ValueError('Invalid count: ' + name)
        if float(row['Spent']) < 0:
            raise ValueError('Negative spend')
        if int(row['Clicks']) > int(row['Impressions']):
            raise ValueError('Clicks exceed impressions')
        if int(row['Approved_Conversion']) > int(row['Total_Conversion']):
            raise ValueError('Approved conversions exceed total conversions')
        if row['age'] not in ('30-34', '35-39', '40-44', '45-49'):
            raise ValueError('Unknown age band')
    return rows


def summarize(rows):
    db = sqlite3.connect(':memory:')
    db.execute('CREATE TABLE ads (campaign TEXT, impressions INTEGER, clicks INTEGER, spend REAL, approved INTEGER)')
    db.executemany('INSERT INTO ads VALUES (?,?,?,?,?)', [
        (r['xyz_campaign_id'], int(r['Impressions']), int(r['Clicks']), float(r['Spent']), int(r['Approved_Conversion'])) for r in rows
    ])
    sql = db.execute('SELECT campaign, COUNT(*), SUM(impressions), SUM(clicks), SUM(spend), SUM(approved) FROM ads GROUP BY campaign ORDER BY campaign').fetchall()
    output = []
    for campaign, ads, impressions, clicks, spend, approved in sql:
        subset = [r for r in rows if r['xyz_campaign_id'] == campaign]
        assert abs(sum(float(r['Spent']) for r in subset) - spend) < 1e-8
        assert sum(int(r['Approved_Conversion']) for r in subset) == approved
        output.append(dict(campaign=campaign, ads=ads, impressions=impressions, clicks=clicks,
                           spend=spend, approved=approved, cpa=spend/approved if approved else None,
                           ctr=clicks/impressions if impressions else None))
    db.close()
    return output


if __name__ == '__main__':
    with SOURCE.open() as source:
        rows = validate(list(csv.DictReader(source)))
    result = {'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
              'row_count': len(rows), 'campaigns': summarize(rows),
              'limitations': ['No dates, revenue, budget, or customer identifiers in the ad export.',
                              'CPA means cost per approved conversion, not customer acquisition cost.',
                              'Descriptive campaign comparisons do not establish causal lift.']}
    (Path(__file__).parent / 'validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
