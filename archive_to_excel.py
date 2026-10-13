import json
import re
import argparse
import os
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

parser = argparse.ArgumentParser(description="パトネットあいちの月別記事を取得します")
parser.add_argument("--months", type=int, default=7, help="取得する直近の月数")
args = parser.parse_args()

if args.months < 1 or args.months > 120:
    parser.error("--months は1から120の範囲で指定してください")

today = date.today()
years_months = []
for offset in range(args.months):
    month_index = today.year * 12 + today.month - 1 - offset
    years_months.append((month_index // 12, f"{month_index % 12 + 1:02d}"))

all_incidents = []
print("=== パトネットあいち 構造不一致対策版ロボット起動 ===")

area_coords = {
    "名古屋": (35.1814, 136.9063),
    "豊田": (35.0874, 137.1564),
    "一宮": (35.3025, 136.8041),
    "岡崎": (34.9532, 137.1685),
    "豊橋": (34.7629, 137.3875),
    "春日井": (35.2443, 136.9715),
}

geocode_cache = {}


def find_reported_location(content):
    """Return the location named after 発生場所, when the article has one."""
    match = re.search(
        r"発生場所\s*[:：]?\s*(.+?)(?=■|状況|\s{2,}|$)",
        content,
    )
    if not match:
        return ""
    return re.sub(r"\s+", "", match.group(1)).strip("。、「」『』")


def geocode(location, city_name=None):
    """Resolve an address with GSI's address search; return lon/lat or None."""
    if not location:
        return None
    cache_key = (city_name, location)
    if cache_key in geocode_cache:
        return geocode_cache[cache_key]

    try:
        response = requests.get(
            "https://msearch.gsi.go.jp/address-search/AddressSearch",
            params={
                "q": f"愛知県{city_name}市{location}"
                if city_name
                else f"愛知県{location}"
            },
            timeout=10,
        )
        response.raise_for_status()
        results = response.json()
        if results:
            lon, lat = results[0]["geometry"]["coordinates"]
            result = (lat, lon)
        else:
            result = None
    except (requests.RequestException, ValueError, KeyError, TypeError) as error:
        print(f"住所検索に失敗: {location}: {error}")
        result = None

    geocode_cache[cache_key] = result
    time.sleep(0.2)
    return result

for year, month in years_months:
    # The source host currently presents a TLS certificate for a different
    # hostname. Use its working HTTP endpoint rather than disabling TLS checks.
    url = f"http://patnet.jp/{year}/{month}/"
    print(f"【スキャン中】 {year}年{month}月...")

    try:
        time.sleep(0.5)
        response = requests.get(url, timeout=10)
        response.encoding = response.apparent_encoding

        if response.status_code == 404:
            continue
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # 🔍 サイトのあらゆる構造に対応できるよう読み取り網を広げる
        articles = soup.find_all(
            ["article", "div", "li"],
            class_=[
                "post",
                "entry",
                "entry-content",
                "content",
                "post-item",
                "type-post",
            ],
        )

        # もし特定のクラス名で見つからない場合は、すべての段落や標準要素から探す
        if not articles:
            articles = soup.find_all("article")
        if not articles:
            articles = soup.find_all("div", id="main")

        for article in articles:
            title_el = article.find(["h1", "h2", "h3", "a"])
            title = title_el.text.strip() if title_el else "不審者情報"
            if len(title) > 30:
                title = "防犯・不審者情報"

            content = article.text.strip()
            if len(content) < 20:  # 文字数が少なすぎる空要素はスキップ
                continue

            reported_location = find_reported_location(content)
            area_name = next(
                (area for area in area_coords if area in content or area in title),
                None,
            )
            coordinates = geocode(reported_location, area_name)

            # If the article lacks a mappable incident address, use a city
            # center as an explicitly coarse fallback. Never invent offsets.
            if coordinates:
                lat, lng = coordinates
                location = f"愛知県{reported_location}"
                location_accuracy = "address"
            elif area_name:
                lat, lng = area_coords[area_name]
                location = f"愛知県{area_name}市付近（市の代表点）"
                location_accuracy = "city"
            else:
                lat, lng = 35.1814, 136.9063
                location = "愛知県内（場所を特定できず）"
                location_accuracy = "prefecture"

            tag = "声かけ事案"
            if "つきまとい" in content:
                tag = "つきまとい"
            elif "盗撮" in content or "ちかん" in content:
                tag = "のぞき・盗撮"

            all_incidents.append(
                {
                    "id": len(all_incidents) + 1,
                    "tag": tag,
                    "archivePath": f"{year}/{month}",
                    "date": f"{year}年{month}月 発生事案",
                    "location": location,
                    "reportedLocation": reported_location,
                    "locationAccuracy": location_accuracy,
                    "lat": lat,
                    "lng": lng,
                    "description": content[:140] + ("..." if len(content) > 140 else ""),
                }
            )

    except Exception as e:
        print(f"アクセスエラー: {e}")
        continue

if not all_incidents:
    raise RuntimeError("取得件数が0件です。既存の公開データは更新しません。")

# データの書き出し
df = pd.DataFrame(all_incidents)
output_dir = Path(os.environ.get("OUTPUT_DIR", "."))
output_dir.mkdir(parents=True, exist_ok=True)
df.to_excel(output_dir / "patnet_aichi_archive.xlsx", index=False, engine="openpyxl")

with (output_dir / "data.js").open("w", encoding="utf-8") as f:
    f.write("const crawledData = " + json.dumps(all_incidents, ensure_ascii=False) + ";")

with (output_dir / "data.json").open("w", encoding="utf-8") as f:
    json.dump(all_incidents, f, ensure_ascii=False)

print(
    f"\n🎉 処理完了：合計 {len(all_incidents)} 件のデータを 『data.js』 に書き出しました！"
)
