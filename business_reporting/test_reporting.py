import copy
import csv
import unittest
from validate import SOURCE, summarize, validate


class ReportingTests(unittest.TestCase):
    def setUp(self):
        with SOURCE.open() as source:
            self.rows = list(csv.DictReader(source))

    def test_original_source_and_totals(self):
        result = summarize(validate(self.rows))
        self.assertEqual(len(self.rows), 1143)
        self.assertEqual(sum(c['approved'] for c in result), 1079)
        self.assertAlmostEqual(sum(c['spend'] for c in result), 58705.23, places=2)

    def test_duplicate_fails(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            validate(self.rows + [self.rows[0]])

    def test_invalid_count_fails(self):
        for column, value in [('Clicks', '-1'), ('Impressions', '1.5'), ('Spent', '-0.01')]:
            rows = copy.deepcopy(self.rows)
            rows[0][column] = value
            with self.assertRaises(ValueError):
                validate(rows)

    def test_zero_denominators(self):
        row = dict(self.rows[0], Impressions='0', Clicks='0', Approved_Conversion='0', Spent='0')
        result = summarize(validate([row]))[0]
        self.assertIsNone(result['cpa'])
        self.assertIsNone(result['ctr'])


if __name__ == '__main__':
    unittest.main()
