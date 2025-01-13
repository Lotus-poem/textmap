import os
import sys
# 標準出力の設定を先に行う
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)
# その後でGoogle関連のライブラリをインポート
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from pathlib import Path
from django.conf import settings

# プロジェクトのルートディレクトリを取得
BASE_DIR = Path(__file__).resolve().parent.parent

# tempディレクトリのパスを設定
TEMP_DIR = BASE_DIR / 'temp'
MAPPING_CSV = TEMP_DIR / 'mapping_result.csv'

# 必要なディレクトリを作成
TEMP_DIR.mkdir(exist_ok=True)

# GPT-4の料金（1000トークンあたり）
GPT4_PROMPT_COST = 0.03    # プロンプトの料金
GPT4_COMPLETION_COST = 0.06  # 応答の料金

# GPT-3.5-turboの料金（1000トークンあたり）
GPT35_PROMPT_COST = 0.0015   # プロンプトの料金
GPT35_COMPLETION_COST = 0.002  # 応答の料金

# 初期軸（最低限これだけは必ず使う）
INITIAL_KEYS = [
    "氏名",
    "会社名",
    "希望業界",
    "希望企業",
    "転職理由",
    "アピールポイント",
]

# Spreadsheet設定
SPREADSHEET_ID = '1jfB1wHqct45GyjOZPMlykjKDqdqvTVcN6IfmfZoQ7tQ'
SHEET_NAME = 'シート1'  # または必要なシート名
CREDENTIALS_PATH = os.path.join(
    settings.BASE_DIR,
    'credentials',
    'credentials.json'
)

def get_sheets_service():
    """Google Sheets APIのサービスを取得"""
    try:
        credentials = service_account.Credentials.from_service_account_file(
            CREDENTIALS_PATH,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        service = build('sheets', 'v4', credentials=credentials)
        return service
    except Exception as e:
        print(f"Sheets API service creation error: {str(e)}")
        raise 