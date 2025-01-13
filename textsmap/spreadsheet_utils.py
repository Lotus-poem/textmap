import pandas as pd
from .config import get_sheets_service, SPREADSHEET_ID, SHEET_NAME
import os

def download_from_spreadsheet(csv_path):
    """SpreadsheetからCSVにデータをダウンロード"""
    try:
        print(f"\n=== Downloading from Spreadsheet ===")
        service = get_sheets_service()
        
        # シートの内容を取得
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{SHEET_NAME}!A1:ZZ'
        ).execute()
        
        # データがない場合は空のCSVを作成
        if 'values' not in result:
            print("No data found in Spreadsheet. Creating empty CSV.")
            df = pd.DataFrame(columns=['id', 'timestamp'])
            os.makedirs(os.path.dirname(csv_path), exist_ok=True)
            df.to_csv(csv_path, index=False)
            return
        
        # データをDataFrameに変換
        values = result['values']
        headers = values[0]
        data = values[1:] if len(values) > 1 else []
        
        #print(f"Headers found: {headers}")
        print(f"Number of rows: {len(data)}")
        
        df = pd.DataFrame(data, columns=headers)
        
        # CSVとして保存
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        df.to_csv(csv_path, index=False)
        
        print(f"Successfully downloaded data to {csv_path}")
        #print(f"CSV contents:\n{df.head()}\n")
        
    except Exception as e:
        print(f"Error downloading from Spreadsheet: {str(e)}")
        raise

def upload_to_spreadsheet(csv_path):
    """CSVからSpreadsheetにデータをアップロード"""
    try:
        print(f"\n=== Uploading to Spreadsheet ===")
        service = get_sheets_service()
        
        # CSVを読み込み
        print(f"Reading CSV from: {csv_path}")
        df = pd.read_csv(csv_path)
        
        # NaN値を空文字列に変換
        df = df.fillna('')
        
        print(f"CSV contents:\n{df.head()}")
        print(f"Total rows: {len(df)}")
        
        # データを準備（値を文字列に変換）
        values = [df.columns.tolist()]
        for _, row in df.iterrows():
            # 各値を文字列に変換
            values.append([str(val) if val != '' else '' for val in row.tolist()])
        
        print(f"Headers to upload: {df.columns.tolist()}")
        
        # シートをクリア
        print("Clearing existing sheet data...")
        clear_result = service.spreadsheets().values().clear(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{SHEET_NAME}!A1:ZZ'
        ).execute()
        print("Sheet cleared")
        
        # データを更新
        print("Uploading new data...")
        body = {
            'values': values
        }
        update_result = service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{SHEET_NAME}!A1',
            valueInputOption='RAW',
            body=body
        ).execute()
        
        print(f"Successfully uploaded {len(df)} rows to Spreadsheet")
        print(f"Update result: {update_result}\n")
        
    except Exception as e:
        print(f"Error uploading to Spreadsheet: {str(e)}")
        print(f"Error details: {type(e).__name__}")
        if hasattr(e, 'content'):
            print(f"Error content: {e.content}")
        raise 