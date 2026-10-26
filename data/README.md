# 生成データ

`scripts/update_data.py` が取得結果を保存し、`scripts/archive_to_excel.py` がExcel版を作成します。

- `incidents.csv` / `incidents.json`: 地図表示にも使う機械可読データ
- `patnet_aichi_archive.xlsx`: 同じデータの表計算ファイル（閲覧用、`sourceUrl` はリンク）

再実行すると、これらのファイルを最新の取得結果で置き換えます。Pythonコードは `scripts/` に置き、このフォルダーには生成データだけを保存します。
