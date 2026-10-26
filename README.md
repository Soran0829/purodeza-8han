# Aichi Safety Radar

パトネットあいち（`http://patnet.jp/`）の「不審者情報」を収集し、市区町村単位に丸めた位置情報を地図に表示する非公式サイトです。

- 公開サイト: https://soran0829.github.io/purodeza-8han/
- リポジトリ: https://github.com/Soran0829/purodeza-8han

## 仕組み

```
パトネットあいち 月別アーカイブ（/YYYY/MM/）
        │  requests + BeautifulSoup で取得
        ▼
scripts/update_data.py
  ・「不審者情報」カテゴリの記事だけを抽出
  ・住所 → 市区町村に正規化 → 国土地理院ジオコーダで概略座標を取得
  ・記事URLのSHA-256先頭20桁をIDにして重複排除
  ・人物の外見・車両などの特徴表現を定型文に置換
        │
        ├── data/incidents.csv           台帳（原本）
        ├── data/incidents.json          地図表示用（CSVと同じ内容）
        └── data/patnet_aichi_archive.xlsx  Excel版（archive_to_excel.py が生成）
        ▼
GitHub Actions（毎日 06:17 JST / 手動 / main への該当変更）
  ・データをコミット
  ・site/ に index.html と data/ をコピー
  ・GitHub Pages へデプロイ
        ▼
index.html
  ・ブラウザで data/incidents.json を fetch
  ・Leaflet + 国土地理院タイルで表示（ピンはズームに応じてクラスタ化）
  ・右側（モバイルは下側）に記事一覧、クリックで地図が該当地点へ移動
```

HTML にデータを埋め込んでいるわけではないため、JSON を更新すれば HTML 自体の変更は不要です。

## ファイル構成

| パス | 役割 |
| --- | --- |
| `index.html` | 地図ページ本体（GitHub Pages のトップページ） |
| `scripts/update_data.py` | 記事取得・座標付与・CSV/JSON 更新 |
| `scripts/archive_to_excel.py` | CSV/JSON から Excel 版を生成 |
| `data/incidents.csv` | 追記型の台帳（UTF-8 BOM、14列） |
| `data/incidents.json` | 地図表示用の JSON（CSV と同じ内容） |
| `data/patnet_aichi_archive.xlsx` | 台帳の Excel 版（フィルタ・固定ヘッダー・元記事リンク付き） |
| `data/README.md` | 生成データの説明 |
| `.github/workflows/update-and-deploy.yml` | データ更新と GitHub Pages デプロイ |

## データ項目

`id`, `date`, `tag`, `category`, `title`, `location`, `reportedLocation`, `locationAccuracy`, `lat`, `lng`, `description`, `body`, `sourceUrl`, `lastChecked`

- `id`: 記事 URL の SHA-256 先頭20桁（重複判定に使用）
- `locationAccuracy`: `municipality`（市区町村の代表点）または `prefecture`（位置未特定時の愛知県代表点）
- `lat` / `lng`: 文字列で保存。Excel 出力時に数値へ変換
- `lastChecked`: 取得日時（UTC、ISO 8601）

## 利用許諾・位置情報の扱い

- 自動取得はパトネットあいちの公開月別ページから「不審者情報」カテゴリの記事を取得します。
- 初回・手動実行では直近12か月分を取得します。地図座標は発生場所の住所を地理院住所検索で町・市区単位に丸めてから求めます。細かな番地や人物の外見・車両など特定につながる特徴は保存しません。記事の「状況」本文とカテゴリ、掲載元へのリンクをCSV/地図に表示します。
- 公開情報は通報・注意情報で、犯罪が確認されたことや現在の危険を意味しません。位置は概略で、遅延や欠落もありえます。外部アプリで座標を再利用する場合は、データとジオコーディングサービスの利用条件を確認してください。
- 公開する場合は、非公式情報で位置が概略であること、遅延・欠落の可能性、掲載期間、削除窓口を明記してください。誤認、嫌がらせ、被害者特定につながるリスクを定期的に見直してください。
- 外部アプリで座標を使う場合、データ提供元の許諾と、座標を生成した地図・ジオコーディングサービスの保存・再利用条件をそれぞれ確認してください。

## データの更新

- `data/incidents.csv` が記事URL IDで重複を除いて追記する台帳です。
- `data/incidents.json` は地図表示用で、CSVと同時に更新します。
- Actions は次のタイミングで実行されます。
  - 手動実行（`workflow_dispatch`）
  - 毎日 06:17 JST（`cron: "17 21 * * *"`）
  - `main` への push（workflow / `scripts/**` / `index.html` / `README.md` の変更時）
- 実行内容: 直近12か月分を取得 → 重複排除・本文/カテゴリ補完 → CSV/JSON/XLSX をコミット → Pages へデプロイ
- 初回起動は **Actions → Update safety map and deploy → Run workflow**。以後は毎日自動実行されます。
- Pages の Source は **GitHub Actions** を選択してください。

## ローカルで更新する

Python 3.10 以降を用意します。

```powershell
python -m pip install requests beautifulsoup4 openpyxl
```

直近12か月を取得する場合（`--months` 省略時の既定値）:

```powershell
python scripts/update_data.py --months 12
```

- `--months` は 1〜12。2か月だけ更新する場合は `--months 2`。
- `--csv` / `--json` で出力先を変更できます（既定は `data/incidents.csv` / `data/incidents.json`）。
- 同じ記事はURL IDで重複を除外します。地図表示地点は町・市区町村のおおまかな代表位置です。
- ローカル実行だけでは公開サイトには反映されません。コミットして push すると Actions がデプロイします。

Excel版を作り直す場合:

```powershell
python scripts/archive_to_excel.py
```

```powershell
# 入力や出力を指定する場合
python scripts/archive_to_excel.py --source data/incidents.csv --xlsx data/patnet_aichi_archive.xlsx
```

## 地図ページ

- Leaflet 1.9.4 + `leaflet.markercluster` 1.5.3（CDN: unpkg）
- 背景地図は国土地理院の淡色地図タイル
- ピンはズーム13でクラスタが解除され、個別表示になります
- 記事一覧のカードをクリックすると、該当地点へズームしてポップアップを開きます
- モバイル（幅800px以下）では地図と一覧を上下に分割します
- 一覧から Excel 版をダウンロードできます

## 開発メモ

- `data/incidents.csv` / `data/incidents.json` / `data/patnet_aichi_archive.xlsx` はリポジトリで追跡しています（Actions が更新をコミットするため）。
- `scripts/archive_to_excel.py` は `openpyxl` のみに依存します。
- 取得先のHTML構造が変わると抽出に失敗します。その場合は `archive_posts` / `extract_article` のセレクタを確認してください。
