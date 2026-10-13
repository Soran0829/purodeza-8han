# Aichi Safety Radar

パトネットあいちの月別記事を定期取得し、地図に表示するプロジェクトです。取得したデータはサイト用のJSONと、ダウンロードできるExcelに出力します。

## 初回設定（GitHub Pagesで公開）

1. GitHubでこのリポジトリを開きます。
2. **Settings → Pages** を開きます。
3. **Build and deployment** の **Source** で **GitHub Actions** を選びます。
4. このプロジェクトの変更を `main` ブランチへpushします。`main` へのpushで自動的に取得・公開処理が始まります。
5. GitHubの **Actions** タブで **Update safety map and deploy** を開き、実行が緑のチェックになったことを確認します。
6. **Settings → Pages** に表示されるサイトURLを開きます。地図と記事一覧が表示されれば公開完了です。

初回設定後は、毎日日本時間の午前6:17に自動で更新されます。GitHub Actionsの定期実行には多少の遅れが出る場合があります。

## 手動で更新する方法

1. リポジトリの **Actions** タブを開きます。
2. 左側の **Update safety map and deploy** を選択します。
3. **Run workflow** → ブランチ `main` を選択 → **Run workflow** を押します。
4. 実行が緑のチェックになったら、Pagesのサイトを再読み込みします。

## 更新データ

- 地図は公開時に作られた `data.json` を読み込みます。
- Excelはサイトの `patnet_aichi_archive.xlsx` からダウンロードできます。
- 取得対象は実行日を含む直近7か月です。
- 記事に「発生場所」があれば住所検索してピンを置きます。住所が特定できない場合は、市の代表点または県内の代表点に表示し、その旨を地図上の場所欄に記載します。
- 取得件数が0件の場合、ワークフローは失敗して既存の公開サイトを維持します。テスト用データで置き換わることはありません。

## エラーの確認

1. GitHubの **Actions** タブで赤い×の実行を選びます。
2. 赤くなった **Fetch source data** などのステップを開き、エラー内容を確認します。
3. パトネットあいち側の一時的なアクセスエラーなら、時間をおいて **Run workflow** から再実行します。
4. **Pages** のSourceが **GitHub Actions** になっているかも確認します。

## ローカルで取得する場合（任意）

Python 3.10以降を用意し、プロジェクトフォルダーで次を実行します。

```powershell
python -m pip install requests beautifulsoup4 pandas openpyxl
python archive_to_excel.py --months 7
```

成功すると、同じフォルダーに `data.js`、`data.json`、`patnet_aichi_archive.xlsx` が作られます。公開サイトの更新はGitHub Actions経由で行ってください。
