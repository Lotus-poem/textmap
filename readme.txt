TextMap - GPT-4を活用したテキスト分類・カテゴリマッピングシステム

【システム概要】
フリーテキストを入力として受け取り、GPT-4による解析を通じて既存のカテゴリー体系への
マッピングを行うシステム。新しい概念は新カテゴリーとして追加可能で、
Google Spreadsheetと連携してデータを管理する仕組みを実装。

【主要機能】
1. テキスト入力・解析機能
   - フリーテキストの入力
   - GPT-4によるテキスト解析
   - 既存カテゴリーへのマッピング
   - 氏名の重複チェックと更新管理

2. カテゴリー管理機能
   - 新規カテゴリーの追加
   - カテゴリーの統合
   - カテゴリーの名称変更
   - 既存データとの比較・更新

3. データ管理機能
   - Google Spreadsheetとの同期
   - 一時データの管理（temp/mapping_result.csv）
   - 処理履歴の管理
   - GPT-4使用コストの追跡

【ファイル構成】
■ コアロジック
- views.py: ビューロジックの実装
- config.py: システム設定と定数定義
- spreadsheet_utils.py: Spreadsheet連携機能
- forms.py: フォーム定義
- models.py: モデル定義

■ テンプレート
- process_text.html: テキスト入力画面
- confirm_name.html: 氏名確認画面
- check_duplicate.html: 重複チェック画面
- adjust_categories.html: カテゴリー調整画面
- compare_update.html: データ比較画面
- result.html: 結果表示画面

【データフロー】
1. アプリケーション起動時
   - Spreadsheetからデータを取得
   - temp/mapping_result.csvに保存

2. テキスト処理時
   - GPT-4による解析
   - 氏名の重複チェック
   - カテゴリーの調整
   - 既存データとの比較（更新時）

3. 保存時
   - temp/mapping_result.csvに保存
   - Spreadsheetへの同期

【システム要件】
- Python 3.8以上
- Django 4.0以上
- OpenAI API Key
- Google Cloud Platformの認証情報
- Google Sheets API有効化

【環境設定】
1. 認証情報の配置
   - credentials/credentials.json: Google認証情報
   - .env: OpenAI APIキー等の環境変数

2. 初期設定
   - temp/ディレクトリの作成
   - 必要なPythonパッケージのインストール
   - データベースのマイグレーション

【注意事項】
- GPT-4 APIキーの適切な管理
- Google認証情報の適切な管理
- コスト管理のための定期的なモニタリング
- 一時ファイル（temp/）の定期的なクリーンアップ