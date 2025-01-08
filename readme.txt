TextMap - GPT-4を活用したテキスト分類・カテゴリマッピングシステム

【システム概要】
フリーテキストを入力として受け取り、GPT-4による解析を通じて既存のカテゴリー体系への
マッピングを行うシステム。新しい概念は新カテゴリーとして追加可能で、
データベースが継続的に進化する仕組みを実装。

【主要機能】
1. テキスト入力・解析機能
   - フリーテキストの入力
   - GPT-4によるテキスト解析
   - 既存カテゴリーへのマッピング

2. カテゴリー管理機能
   - 新規カテゴリーの追加
   - カテゴリーの統合
   - カテゴリーの名称変更
   - 不要カテゴリーの除外

3. データ管理機能
   - 解析結果のデータベース保存
   - CSVエクスポート
   - 処理履歴の管理
   - GPT-4使用コストの追跡

【ファイル構成】
■ コアロジック
- views.py: https://github.com/Lotus-poem/textmap/blob/main/textsmap/views.py
- forms.py: https://github.com/Lotus-poem/textmap/blob/main/textsmap/forms.py
- models.py: https://github.com/Lotus-poem/textmap/blob/main/textsmap/models.py

■ アプリケーション設定（myapp）
- urls.py: https://github.com/Lotus-poem/textmap/blob/main/myapp/urls.py
- apps.py: https://github.com/Lotus-poem/textmap/blob/main/myapp/apps.py
- admin.py: https://github.com/Lotus-poem/textmap/blob/main/myapp/admin.py

■ テンプレート
- テキスト処理画面: https://github.com/Lotus-poem/textmap/blob/main/templates/textsmap/process_text.html
- カテゴリー調整画面: https://github.com/Lotus-poem/textmap/blob/main/templates/textsmap/adjust_categories.html
- 結果表示画面: https://github.com/Lotus-poem/textmap/blob/main/templates/textsmap/result.html

【UIフロー】
process_text.html
  ↓ （テキスト入力・解析実行）
adjust_categories.html
  ↓ （カテゴリーの調整・確定）
result.html
  ↓ （結果の確認・エクスポート）
process_text.html
  （新規テキスト入力へ）

【システム処理フロー】
1. テキスト解析処理
   - ユーザーからのテキスト入力受付
   - GPT-4 APIによるテキスト解析
   - カテゴリーマッピングの生成

2. カテゴリー処理
   - 既存カテゴリーとのマッチング
   - 新規カテゴリーの提案
   - ユーザーによる調整の反映

3. データ管理処理
   - 確定データのDB保存
   - 処理履歴の記録
   - コスト計算・保存
   - CSVエクスポート

【データベース設計】
- TextInput: 入力テキストの保存
- Category: カテゴリー定義の管理
- TextCategory: テキストとカテゴリーの関連付け
- ProcessingHistory: 処理履歴とコスト管理

【技術スタック】
- フレームワーク: Django
- AI: GPT-4 API
- データベース: SQLite（開発環境）
- フロントエンド: HTML/CSS/JavaScript

【注意事項】
- GPT-4 APIキーの適切な管理が必要
- コスト管理のための定期的なモニタリングを推奨
- 新カテゴリー追加時は既存カテゴリーとの重複確認が必要 