# Aichi Safety Radar

許諾を確認した安全情報をCSVに蓄積し、地図に表示するプロジェクトです。CSVを長期データの正本として保管し、地図用JSONを生成します。

## 利用許諾・位置情報の扱い

- 公開情報であっても、自動取得・保存・加工・再掲載・地図公開が許可されているとは限りません。情報提供元に取得方法、保存期間、公開範囲、更新頻度、座標データの外部アプリ利用まで確認してください。
- 許諾が未確認の間は自動取得・公開を実行しません。愛知県警察公式の[不審者等情報](https://www.pref.aichi.jp/police/anzen/shijo/map/)と[アイチポリス／安心・安全マップ](https://www.pref.aichi.jp/police/anzen/seian-s/anzenmap.html)をご利用ください。
- 表示地点は市または県の代表点です。住所ジオコーディングで発生場所を精密化しません。人物の特徴や個人を特定しうる本文も公開しません。
- 公開する場合は、非公式情報で位置が概略であること、遅延・欠落の可能性、掲載期間、削除窓口を明記してください。誤認、嫌がらせ、被害者特定につながるリスクを定期的に見直してください。
- 外部アプリで座標を使う場合、データ提供元の許諾と、座標を生成した地図・ジオコーディングサービスの保存・再利用条件をそれぞれ確認してください。

## データの更新

- `data/incidents.csv` が重複を除いて追記するデータ台帳です。
- `data/incidents.json` は地図表示用にCSVから生成します。
- `.github/workflows/update-and-deploy.yml` は手動起動・毎日06:17 JST・workflow/script/地図/READMEのmain更新で実行されます。Pages公開自体は許諾変数なしでも行います。
- Actionsは既存CSV/JSONをGitHub Pagesへデプロイします。`PATNET_REUSE_AUTHORIZED=true` を設定した場合のみ最新1か月分を取得し、CSV/JSONを更新コミットしてからデプロイします。生成データだけのpushは再起動対象外です。

## ローカルで登録する

Python 3.10以降と依存ライブラリを用意します。

```powershell
python -m pip install requests beautifulsoup4
```

許諾を得た記事テキストをUTF-8で保存し、記事ごとに空行で区切って実行します。

```powershell
python scripts/update_data.py --input .\authorized_reports.txt --authorized
```

同じ記事はIDで重複を除外します。許諾済みの場合のみ、月別アーカイブの自動取得を明示的に実行できます。

```powershell
python scripts/update_data.py --fetch --months 1 --authorized
```

## GitHub Actionsを有効にする

1. **Settings → Actions → General → Workflow permissions** で **Read and write permissions** を有効にします（CSV/JSONをActionsからコミットするため）。
2. **Settings → Pages** の **Build and deployment → Source** を **GitHub Actions** にします。
3. **Actions → Update safety map and deploy → Run workflow** から初回実行します。初期状態は空の地図を公開します。
4. 情報提供元に機械取得・保存・加工・地図公開の許諾を確認した場合のみ、リポジトリ変数 `PATNET_REUSE_AUTHORIZED=true` を設定してください。有効時は新着データを追記し、CSV/JSONを更新コミットしてから公開します。

後続は毎日06:17 JSTに自動実行されます。月別アーカイブに新着がない場合、ファイルのコミットは発生しませんがデプロイは続行します。
