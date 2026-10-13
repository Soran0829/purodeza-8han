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

for year, month in years_months:
    url = f"https://patnet.jp/{year}/{month}/"
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

        for idx, article in enumerate(articles):
            title_el = article.find(["h1", "h2", "h3", "a"])
            title = title_el.text.strip() if title_el else "不審者情報"
            if len(title) > 30:
                title = "防犯・不審者情報"

            content = article.text.strip()
            if len(content) < 20:  # 文字数が少なすぎる空要素はスキップ
                continue

            # 座標の割り振り
            lat, lng = 35.1814, 136.9063
            location = "愛知県内"
            for area, coord in area_coords.items():
                if area in content or area in title:
                    lat, lng = coord[0] + (idx * 0.012), coord[1] + (
                        idx * 0.008
                    )  # ピンが重ならないよう分散
                    location = f"愛知県{area}市付近"
                    break

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
                    "lat": lat,
                    "lng": lng,
                    "description": content[:140] + "...",
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

print(
    f"\n🎉 処理完了：合計 {len(all_incidents)} 件のデータを 『data.js』 に書き出しました！"
)
