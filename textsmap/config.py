import os
import pandas as pd
from pathlib import Path
from datetime import datetime

# プロジェクトのルートディレクトリを取得
BASE_DIR = Path(__file__).resolve().parent.parent

# outputディレクトリのパスを設定
OUTPUT_DIR = BASE_DIR / 'output'
MAPPING_CSV = OUTPUT_DIR / 'mapping_result.csv'

# 必要なディレクトリを作成
OUTPUT_DIR.mkdir(exist_ok=True)

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

def get_current_categories():
    """CSVファイルから現在の全カテゴリーを取得"""
    if not MAPPING_CSV.exists():
        # CSVが存在しない場合は初期軸のみ返す
        return INITIAL_KEYS
    
    # CSVが存在する場合は、そのカラム名から必要な情報を抽出
    df = pd.read_csv(MAPPING_CSV, encoding='utf-8-sig')
    # id, timestampを除外した列名を取得
    categories = [col for col in df.columns if col not in ['id', 'timestamp']]
    return categories

def save_mapping_result(mapped_data):
    """マッピング結果をCSVに保存"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if not MAPPING_CSV.exists():
        # 初回の場合、新規作成
        df = pd.DataFrame(columns=['id', 'timestamp'] + INITIAL_KEYS)
    else:
        # 既存のCSVを読み込み
        df = pd.read_csv(MAPPING_CSV, encoding='utf-8-sig')
    
    # 新しいデータを準備
    new_data = {'timestamp': now}
    new_data.update(mapped_data)
    
    # 既存のカラムにない新しいキーがあれば、列を追加
    new_keys = set(mapped_data.keys()) - set(df.columns)
    for key in new_keys:
        df[key] = None  # 新しい列を追加
    
    # データを追加
    df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
    
    # IDを振り直して保存
    df['id'] = range(1, len(df) + 1)
    df.to_csv(MAPPING_CSV, index=False, encoding='utf-8-sig')
    
    return df.columns.tolist()  # 最新の列リストを返す 