"""Unit tests for the Excel export helpers."""

import tempfile
import unittest
from pathlib import Path

from openpyxl import load_workbook

from scripts import archive_to_excel

ROWS = [
    {"id": "a" * 20, "date": "10月19日(月)", "tag": "声かけ・不審者情報", "category": "不審者情報",
     "title": "名古屋市昭和区", "location": "名古屋市昭和区付近", "reportedLocation": "名古屋市昭和区",
     "locationAccuracy": "municipality", "lat": "35.15", "lng": "136.93",
     "description": "説明", "body": "本文", "sourceUrl": "http://patnet.jp/x/",
     "lastChecked": "2020-01-01T00:00:00+00:00"},
    {"id": "b" * 20, "body": "=1+1"},
]


class WriteSheetTest(unittest.TestCase):
    def _write(self, path):
        archive_to_excel.write_sheet(ROWS, path)
        return path.read_bytes()

    def test_output_is_byte_deterministic(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as tmp:
            first = self._write(Path(tmp) / "a.xlsx")
            second = self._write(Path(tmp) / "b.xlsx")
        self.assertEqual(first, second)

    def test_coordinates_are_written_as_numbers(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as tmp:
            path = Path(tmp) / "a.xlsx"
            archive_to_excel.write_sheet(ROWS, path)
            sheet = load_workbook(path).active
            lat = sheet.cell(row=2, column=archive_to_excel.FIELDS.index("lat") + 1)
        self.assertEqual(lat.value, 35.15)

    def test_formula_like_text_stays_text(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as tmp:
            path = Path(tmp) / "a.xlsx"
            archive_to_excel.write_sheet(ROWS, path)
            sheet = load_workbook(path).active
            body = sheet.cell(row=3, column=archive_to_excel.FIELDS.index("body") + 1)
        self.assertEqual(body.data_type, "s")
        self.assertEqual(body.value, "=1+1")


class LoadRowsTest(unittest.TestCase):
    def test_rejects_non_array_json(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as tmp:
            path = Path(tmp) / "x.json"
            path.write_text('{"a": 1}', encoding="utf-8")
            with self.assertRaises(ValueError):
                archive_to_excel.load_rows(path)


if __name__ == "__main__":
    unittest.main()
