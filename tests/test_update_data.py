"""Unit tests for the data-import helpers (no network access)."""

import unittest
from datetime import date
from unittest import mock

from scripts import update_data

ARTICLE_HTML = """
<html><head><title>t</title></head><body>
<div id="main"><div class="post">
<h2 class="entry-title">名古屋市昭和区</h2>
<div class="entry-utility">カテゴリー: 不審者情報 , 身近な犯罪情報</div>
<div class="entry-content">
■発生場所：愛知県名古屋市昭和区〇〇町1-2
■発生日時：10月19日(月)午後5時3分頃
■状況：男が声をかけてきた
■不審者等：年齢不明
</div></div></div></body></html>
"""


class MonthStartTest(unittest.TestCase):
    def test_returns_first_day_of_month(self):
        self.assertEqual(update_data.month_start(0).day, 1)

    def test_consecutive_months_are_adjacent(self):
        newer = update_data.month_start(0)
        older = update_data.month_start(1)
        self.assertEqual((newer.year * 12 + newer.month) - (older.year * 12 + older.month), 1)


class NormalizeMunicipalityTest(unittest.TestCase):
    def test_nagoya_ward_is_kept(self):
        self.assertEqual(update_data.normalize_municipality("愛知県名古屋市昭和区〇〇町1-2"), "名古屋市昭和区")

    def test_city_without_ward(self):
        self.assertEqual(update_data.normalize_municipality("愛知県春日井市"), "春日井市")

    def test_district_and_village_name(self):
        self.assertEqual(update_data.normalize_municipality("愛知県海部郡飛島村"), "海部郡飛島村")

    def test_unknown_text_returns_empty(self):
        self.assertEqual(update_data.normalize_municipality("特に記載なし"), "")


class SanitizePublicBodyTest(unittest.TestCase):
    def test_appearance_description_is_replaced(self):
        text = update_data.sanitize_public_body("男が黒い帽子をかぶっていた")
        self.assertNotIn("帽子", text)

    def test_plain_situation_is_kept(self):
        self.assertEqual(update_data.sanitize_public_body("男が声をかけてきた"), "男が声をかけてきた")


class ExtractArticleTest(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock()

    def _extract(self, html):
        with mock.patch.object(update_data, "fetch_soup") as fetch, \
             mock.patch.object(update_data, "geocode_area", return_value=(35.1, 136.9)):
            fetch.return_value = update_data.BeautifulSoup(html, "html.parser")
            return update_data.extract_article("http://patnet.jp/2020/10/19/x/", date(2020, 10, 19), self.session)

    def test_parses_suspicious_person_report(self):
        record = self._extract(ARTICLE_HTML)
        self.assertIsNotNone(record)
        self.assertEqual(record["reportedLocation"], "名古屋市昭和区")
        self.assertEqual(record["locationAccuracy"], "municipality")
        self.assertIn("不審者情報", record["category"])
        self.assertEqual(record["tag"], "声かけ")
        self.assertEqual(record["description"], "声かけに関する情報です。")
        self.assertEqual(record["body"], "男が声をかけてきた")
        self.assertEqual(len(record["id"]), 20)

    def test_skips_articles_without_suspicious_person_category(self):
        html = ARTICLE_HTML.replace("カテゴリー: 不審者情報 , 身近な犯罪情報", "カテゴリー: 防犯情報")
        self.assertIsNone(self._extract(html))


class ClassifyReportTest(unittest.TestCase):
    def test_exposure_is_detected(self):
        self.assertEqual(update_data.classify_report("男が児童の目の前で下半身を露出した"), "露出")

    def test_voyeurism_is_detected(self):
        self.assertEqual(update_data.classify_report("男が帰宅中の女子生徒にスマートフォンを向けた"), "のぞき・盗撮")

    def test_contact_is_detected(self):
        self.assertEqual(update_data.classify_report("男が歩行中の女性の体を触った"), "接触・危害")

    def test_following_is_detected(self):
        self.assertEqual(update_data.classify_report("男が下校中の児童の後をつけてきた"), "つきまとい・追尾")

    def test_intrusion_is_detected(self):
        self.assertEqual(update_data.classify_report("不審者が自宅敷地内に侵入した"), "侵入・住居への不審")

    def test_call_out_is_detected(self):
        self.assertEqual(update_data.classify_report("男が児童に「いくつなの」と声を掛けた"), "声かけ")

    def test_generic_report_falls_back_to_other(self):
        self.assertEqual(update_data.classify_report("近所で不審者が目撃された"), "その他")

    def test_retag_row_updates_tag_and_description(self):
        row = {"title": "春日井市", "body": "男が下半身を露出した", "tag": "声かけ・不審者情報"}
        update_data.retag_row(row)
        self.assertEqual(row["tag"], "露出")
        self.assertEqual(row["description"], "露出に関する情報です。")

    def test_retag_row_keeps_legacy_specific_tag_when_body_is_sanitized(self):
        row = {"title": "春日井市", "body": "不審な人物に関する情報です。詳しい状況は掲載元の記事をご確認ください。", "tag": "つきまとい"}
        update_data.retag_row(row)
        self.assertEqual(row["tag"], "つきまとい・追尾")


class BuildSessionTest(unittest.TestCase):
    def test_retry_adapter_is_mounted(self):
        session = update_data.build_session()
        self.assertIsNotNone(session.get_adapter("https://patnet.jp"))


if __name__ == "__main__":
    unittest.main()
