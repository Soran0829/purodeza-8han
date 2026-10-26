# Aichi Safety Radar

パトネットあいちの不審者情報を取得してCSVへ蓄積し、住所から市区町村単位の座標を求め、HTML地図にピン表示します。

## 利用許諾・位置情報の扱い

- 自動取得はパトネットあいちの公開月別ページから「不審者情報」カテゴリの記事を取得します。
- 初回・手動実行では直近12か月分を取得します。地図座標は発生場所の住所を地理院住所検索で町・市区単位に丸めてから求めます。細かな番地や人物の外見・車両など特定につながる特徴は保存しません。記事の「状況」本文とカテゴリ、掲載元へのリンクをCSV/地図に表示します。
- 公開情報は通報・注意情報で、犯罪が確認されたことや現在の危険を意味しません。位置は概略で、遅延や欠落もありえます。外部アプリで座標を再利用する場合は、データとジオコーディングサービスの利用条件を確認してください。
- 公開する場合は、非公式情報で位置が概略であること、遅延・欠落の可能性、掲載期間、削除窓口を明記してください。誤認、嫌がらせ、被害者特定につながるリスクを定期的に見直してください。
- 外部アプリで座標を使う場合、データ提供元の許諾と、座標を生成した地図・ジオコーディングサービスの保存・再利用条件をそれぞれ確認してください。

## ファイル構成

- `index.html`: 地図ページ本体（GitHub Pages のトップページ）
- `scripts/update_data.py`: 記事取得・座標付与・CSV/JSON 更新
- `scripts/archive_to_excel.py`: JSON/CSV から Excel 版を作成
- `data/incidents.csv` / `data/incidents.json`: 記事URL IDで重複を除いて追記する台帳
- `data/patnet_aichi_archive.xlsx`: 台帳の Excel 版（閲覧用）
- `.github/workflows/update-and-deploy.yml`: 毎日の更新と Pages デプロイ

## データの更新

- `data/incidents.csv` が記事URL IDで重複を除いて追記する台帳です。
- `data/incidents.json` は地図表示用で、CSVと同時に更新します。
- Actionsは手動起動・毎日06:17 JST・workflow/script/地図/READMEのmain更新で実行し、直近12か月分を重複排除・本文/カテゴリ補完してCSV/JSON/XLSXをコミットしてからPagesへデプロイします。
- Actionsの初回起動は **Actions → Update safety map and deploy → Run workflow**。以後は毎日自動実行されます。

## ローカルで更新する

Python 3.10以降と依存ライブラリを用意します。

```powershell
python -m pip install requests beautifulsoup4 openpyxl
```

プロジェクトフォルダーで直近12か月を取得する場合（`--months` 省略時の既定値）:

```powershell
python scripts/update_data.py --months 12
```

同じ記事はURL IDで重複を除外します。地図表示地点は町・市区町村のおおまかな代表位置です。

Excel版を作り直す場合:

```powershell
python scripts/archive_to_excel.py
```
