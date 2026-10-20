import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from produce import convert


class ConvertTest(unittest.TestCase):
    def row(self):
        return {'transaction_time': '2020-01-02 03:04', 'amount': '28948.90',
                'population_city': '60', 'post_code': '00123', 'lat': '45.0838',
                'lon': '-120.6649', 'merchant_lat': '45.042827',
                'merchant_lon': '-120.709327', 'merch': 'Shop, Inc.'}

    def test_test_file_preserves_money_and_zip(self):
        row = self.row()
        result = convert(row, 'test.csv', 7)
        self.assertEqual(result['amount'], '28948.90')
        self.assertEqual(result['post_code'], '00123')
        self.assertIsNone(result['target'])
        self.assertEqual(result['source_row'], 7)
        self.assertEqual(result['transaction_time'], '2020-01-02 03:04:00')
        self.assertNotIn('source_row', row)

    def test_target(self):
        self.assertEqual(convert(dict(self.row(), target='0'), 'train.csv', 1)['target'], 0)

    def test_invalid_money(self):
        for amount in ('1.001', 'NaN', 'Infinity'):
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                convert(dict(self.row(), amount=amount), 'train.csv', 1)


if __name__ == '__main__':
    unittest.main()
