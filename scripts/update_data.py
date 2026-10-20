"""Fetch, normalize, and append Aichi safety reports.

Automated collection and republication require source-owner authorization. Keep
network fetching disabled unless the operator has obtained that authorization.
"""

import argparse
import csv
import hashlib
import json
import os
import re
import time
from datetime import date, datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

FIELDS = [
    "id", "date", "tag", "location", "reportedLocation", "locationAccuracy",
    "lat", "lng", "description", "sourceUrl", "lastChecked",
]
AREA_COORDS = {
    "名古屋": (35.1814, 136.9063), "豊田": (35.0874, 137.1564),
    "一宮": (35.3025, 136.8041), "岡崎": (34.9532, 137.1685),
    "豊橋": (34.7629, 137.3875), "春日井": (35.2443, 136.9715),
}


def parse_report(content, title=""):
    """Extract only coarse, non-identifying fields from a source report."""
    text = re.sub(r"\s+", " ", content).strip()
    place = re.search(r"発生場所\s*[:：]?\s*(.+?)(?=■|状況|内容|$)", text)
    location = re.sub(r"\s+", "", place.group(1)).strip("。、「」『』") if place else ""
    area = next((name for name in AREA_COORDS if name in text or name in title), None)
    # Avoid producing address-level public coordinates. The point denotes a broad area only.
    if area:
        lat, lng = AREA_COORDS[area]
        place_label = f"愛知県{area}市付近（市の代表点）"
        accuracy = "city"
    else:
        lat, lng = 35.1814, 136.9063
        place_label = "愛知県内（場所を特定できず）"
        accuracy = "prefecture"
    tag = "つきまとい" if "つきまとい" in text else (
        "のぞき・盗撮" if "盗撮" in text or "ちかん" in text else "声かけ事案"
    )
    # Omit descriptions that could identify a victim or suspect.
    summary = f"{tag}に関する情報。詳細は出典を確認してください。"
    return {"tag": tag, "location": place_label, "reportedLocation": location,
            "locationAccuracy": accuracy, "lat": lat, "lng": lng, "description": summary}


def geocode(location, city_name=None, session=None):
    """Optional GSI address lookup for authorized internal workflows only."""
    if not location:
        return None
    response = (session or requests).get(
        "https://msearch.gsi.go.jp/address-search/AddressSearch",
        params={"q": f"愛知県{city_name}市{location}" if city_name else f"愛知県{location}"},
        timeout=10,
    )
    response.raise_for_status()
    results = response.json()
    if not results:
        return None
    lng, lat = results[0]["geometry"]["coordinates"]
    return lat, lng


def load_csv(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def save_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def stable_id(source_url, content):
    return hashlib.sha256(f"{source_url}\n{content}".encode("utf-8")).hexdigest()[:20]


def fetch_reports(months):
    """Collect monthly archive entries. Call only with permission enabled."""
    today = date.today()
    reports = []
    for offset in range(months):
        month_index = today.year * 12 + today.month - 1 - offset
        year, month = month_index // 12, month_index % 12 + 1
        url = f"http://patnet.jp/{year}/{month:02d}/"
        response = requests.get(url, timeout=(10, 30))
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "html.parser")
        articles = soup.find_all("article") or soup.find_all("div", id="main")
        for article in articles:
            content = article.get_text(" ", strip=True)
            if len(content) < 20:
                continue
            heading = article.find(["h1", "h2", "h3", "a"])
            title = heading.get_text(" ", strip=True) if heading else ""
            reports.append((url, content, title, f"{year}年{month:02d}月"))
        time.sleep(0.5)
    return reports


def parse_text_input(input_path):
    """Read authorized reports from a UTF-8 text file, separated by blank lines."""
    reports = []
    if not input_path:
        return reports
    for block in re.split(r"\n\s*\n", input_path.read_text(encoding="utf-8-sig")):
        block = block.strip()
        if block:
            reports.append(("", block, "", "発生時期未確認"))
    return reports


def main():
    parser = argparse.ArgumentParser(description="パトネットあいち情報をCSVに蓄積し、地図データを出力")
    parser.add_argument("--input", type=Path, help="権限を得た情報を手動保存したUTF-8テキスト（1記事ずつ空行区切り）")
    parser.add_argument("--fetch", action="store_true", help="許諾済みの月別アーカイブを取得")
    parser.add_argument("--months", type=int, default=1)
    parser.add_argument("--authorized", action="store_true", help="取得・保存・再掲載の許諾を得ていることを確認")
    parser.add_argument("--csv", type=Path, default=Path(os.environ.get("OUTPUT_DIR", "data")) / "incidents.csv")
    parser.add_argument("--json", type=Path, default=Path(os.environ.get("OUTPUT_DIR", "data")) / "incidents.json")
    args = parser.parse_args()
    if args.input and not args.authorized:
        parser.error("手動入力データの保存・再掲載にも許諾が必要です。確認後に --authorized を指定してください")
    if args.fetch and not args.authorized:
        parser.error("自動取得には情報提供元から取得・保存・再掲載の許諾を得たうえで --authorized を指定してください")
    if not args.fetch and not args.input:
        parser.error("--input または（許諾済みの場合のみ）--fetch を指定してください")
    if not 1 <= args.months <= 120:
        parser.error("--months は1から120の範囲で指定してください")

    reports = fetch_reports(args.months) if args.fetch else []
    reports.extend(parse_text_input(args.input))

    existing = load_csv(args.csv)
    known = {row.get("id", "") for row in existing}
    checked = datetime.now(timezone.utc).isoformat(timespec="seconds")
    added = 0
    for source_url, content, title, report_date in reports:
        identifier = stable_id(source_url, content)
        if identifier in known:
            continue
        parsed = parse_report(content, title)
        existing.append({"id": identifier, "date": report_date, **parsed,
                         "sourceUrl": source_url, "lastChecked": checked})
        known.add(identifier)
        added += 1
    save_csv(args.csv, existing)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    # JSON remains the map's runtime format; CSV is the durable append-only ledger.
    with args.json.open("w", encoding="utf-8") as file:
        json.dump(existing, file, ensure_ascii=False, indent=2)
    print(f"CSV: {args.csv}（新規 {added} 件 / 累計 {len(existing)} 件）")
    print(f"地図データ: {args.json}")


if __name__ == "__main__":
    main()
