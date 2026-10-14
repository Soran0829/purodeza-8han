# 生成データ

`scripts/update_data.py` が取得結果を保存します。

- `incidents.json`: 地図表示に使う機械可読データ
- `patnet_aichi_archive.xlsx`: 同じデータの表計算ファイル

再実行すると、これらのファイルを最新の取得結果で置き換えます。Pythonコードは `scripts/` に置き、このフォルダーには生成データだけを保存します。
