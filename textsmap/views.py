from django.shortcuts import render, redirect
from django.views.generic import CreateView, FormView, TemplateView
from .models import MappedText, ProcessedText
from .forms import TextProcessForm, CategoryAdjustmentForm
from django.contrib import messages
from openai import OpenAI
from .config import (
    GPT35_PROMPT_COST, GPT35_COMPLETION_COST, 
    INITIAL_KEYS,
    GPT4_PROMPT_COST, 
    GPT4_COMPLETION_COST
)
from .spreadsheet_utils import upload_to_spreadsheet, download_from_spreadsheet
import json
from django.conf import settings
import pandas as pd
from django import forms
from django.views import View
import logging
import traceback
from django.http import JsonResponse
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class TextProcessView(CreateView):
    model = MappedText
    form_class = TextProcessForm
    template_name = 'textmap/process_text.html'
    
    def dispatch(self, request, *args, **kwargs):
        """リクエスト処理前にSpreadsheetからデータを取得"""
        try:
            # temp_dirが存在しない場合は作成
            temp_dir = 'temp'
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            
            # Spreadsheetからデータを取得してCSVに保存
            download_from_spreadsheet('temp/mapping_result.csv')
            print("Spreadsheetからデータを取得しました")
            
        except Exception as e:
            print(f"Spreadsheetからのデータ取得エラー: {str(e)}")
            messages.error(request, 'データの取得に失敗しました')
            # エラー時も処理は継続（新規CSVが作成される）
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_current_categories(self):
        """現在のカテゴリーリストを取得"""
        try:
            # CSVファイルの存在確認
            if not os.path.exists('temp/mapping_result.csv'):
                print("CSVファイルが存在しません。初期カテゴリーを返します。")
                return [cat for cat in INITIAL_KEYS if cat not in ['id', 'timestamp']]
            
            # CSVからカテゴリーを取得
            df = pd.read_csv('temp/mapping_result.csv')
            categories = [col for col in df.columns if col not in ['id', 'timestamp']]
            
            print(f"現在のカテゴリー: {categories}")
            return categories or INITIAL_KEYS  # カテゴリーが空の場合は初期カテゴリーを返す
            
        except Exception as e:
            print(f"カテゴリー取得エラー: {str(e)}")
            # エラー時は初期カテゴリーを返す
            return [cat for cat in INITIAL_KEYS if cat not in ['id', 'timestamp']]
    
    def process_with_gpt4(self, text, categories):
        """GPT-4による解析を行う"""
        try:
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "あなたは候補者情報を構造化するアシスタントです。"
                            "提供された文章から、既存のカテゴリーに該当する情報を全て抽出し、"
                            "新しい重要な情報カテゴリーがあれば提案してください。"
                            "必ず指定されたJSON形式で返してください。"
                        )
                    },
                    {
                        "role": "user",
                        "content": f"""
                        次の文章から情報を抽出し、以下の形式のJSONで返してください：
                        {{
                            "existing_data": {{
                                "氏名": "値",
                                "会社名": "値",
                                ...他の必須カテゴリー
                            }},
                            "new_categories": {{
                                "新カテゴリー名": "値"
                            }}
                        }}

                        必須カテゴリー（情報がない場合は「情報なし」と記載）:
                        {categories}
                        
                        文章:
                        {text}
                        """
                    }
                ],
                temperature=0.2,
                max_tokens=2000
            )
            
            return {
                'content': response.choices[0].message.content.strip(),
                'usage': response.usage
            }
            
        except Exception as e:
            print(f"\nGPT Processing Error: {str(e)}")
            raise
    
    def calculate_cost(self, usage):
        """トークン使用量からコストを計算"""
        return {
            'prompt_tokens': usage.prompt_tokens,
            'completion_tokens': usage.completion_tokens,
            'total_tokens': usage.total_tokens,
            'cost_usd': (
                (usage.prompt_tokens * GPT4_PROMPT_COST) +
                (usage.completion_tokens * GPT4_COMPLETION_COST)
            ) / 1000
        }
    
    def form_valid(self, form):
        """フォームのバリデーション成功時の処理"""
        try:
            instance = form.save(commit=False)
            
            # 現在のカテゴリーを取得
            current_categories = self.get_current_categories()
            print(f"\n=== Processing New Text ===")
            print(f"Text length: {len(instance.input_text)}")
            
            # GPT-4による解析
            gpt_response = self.process_with_gpt4(instance.input_text, current_categories)
            
            # JSONパース
            result = json.loads(gpt_response['content'])
            print("\nParsed JSON:", json.dumps(result, indent=2, ensure_ascii=False))
            
            # セッションデータの保存
            session_data = {
                'input_text': instance.input_text,
                'existing_data': result['existing_data'],
                'new_categories': result.get('new_categories', {}),
                'tokens_info': self.calculate_cost(gpt_response['usage'])
            }
            
            self.request.session['temp_form_data'] = session_data
            self.request.session.modified = True
            
            print("Redirecting to confirm-name")
            return redirect('confirm-name')
            
        except json.JSONDecodeError as e:
            print(f"\nJSON Parse Error: {str(e)}")
            form.add_error(None, 'GPTからの応答を解析できませんでした。')
            return self.form_invalid(form)
            
        except Exception as e:
            print(f"\nGeneral Error: {str(e)}")
            form.add_error(None, f'エラーが発生しました：{str(e)}')
            return self.form_invalid(form)

class CategoryAdjustView(FormView):
    template_name = 'textmap/adjust_categories.html'
    form_class = CategoryAdjustmentForm

    def get_form_kwargs(self):
        """フォームの初期化時に渡す引数を設定"""
        kwargs = super().get_form_kwargs()
        temp_data = self.request.session.get('temp_form_data', {})
        
        kwargs['new_categories'] = temp_data.get('new_categories', {})
        kwargs['existing_data'] = temp_data.get('existing_data', {})
        
        return kwargs

    def get_context_data(self, **kwargs):
        """テンプレートに渡すコンテキストを設定"""
        context = super().get_context_data(**kwargs)
        temp_data = self.request.session.get('temp_form_data', {})
        
        context['new_categories'] = temp_data.get('new_categories', {})
        context['existing_data'] = temp_data.get('existing_data', {})
        
        print("\n=== CategoryAdjustView: コンテキスト設定 ===")
        print(f"新規カテゴリー: {list(context['new_categories'].keys())}")
        print(f"既存データ: {list(context['existing_data'].keys())}")
        
        return context

    def form_valid(self, form):
        """フォームのバリデーション成功時の処理"""
        try:
            print("\n=== CategoryAdjustView: フォーム処理開始 ===")
            temp_data = self.request.session.get('temp_form_data', {})
            
            # 新規カテゴリーの処理
            for category, value in temp_data.get('new_categories', {}).items():
                action = form.cleaned_data.get(f'action_{category}')
                print(f"\nカテゴリー '{category}' の処理:")
                print(f"- 現在の値: {value}")
                print(f"- 選択されたアクション: {action}")
                
                if action == 'add':
                    temp_data['existing_data'][category] = value
                    print(f"- 新規追加: {category} = {value}")
                
                elif action == 'rename':
                    new_name = form.cleaned_data.get(f'rename_{category}')
                    if new_name:
                        temp_data['existing_data'][new_name] = value
                        print(f"- 名前変更: {category} → {new_name} = {value}")
                
                elif action == 'merge':
                    target = form.cleaned_data.get(f'merge_{category}')
                    if target:
                        current = temp_data['existing_data'].get(target, '')
                        merged_value = f"{current} | {value}" if current else value
                        temp_data['existing_data'][target] = merged_value
                        print(f"- 統合: {category} → {target} = {merged_value}")
            
            # 新規カテゴリーをクリア
            temp_data['new_categories'] = {}
            
            # セッションを更新
            self.request.session['temp_form_data'] = temp_data
            self.request.session.modified = True
            
            messages.success(self.request, 'カテゴリーの調整が完了しました')
            print("=== CategoryAdjustView: フォーム処理完了 ===\n")
            
            # 更新モードの場合はCompareUpdateViewへ
            if self.request.session.get('target_record_id'):
                print("更新モード: compare-updateへリダイレクト")
                return redirect('compare-update')
            else:
                print("新規モード: resultへリダイレクト")
                return redirect('result')
            
        except Exception as e:
            print(f"カテゴリー調整エラー: {str(e)}")
            messages.error(self.request, f'エラーが発生しました: {str(e)}')
            return self.form_invalid(form)

class ResultView(View):
    template_name = 'textmap/result.html'

    def get_processed_data(self):
        """セッションからデータを取得"""
        temp_data = self.request.session.get('temp_form_data', {})
        target_id = self.request.session.get('target_record_id')

        print(f"\n=== ResultView: データ取得 ===")
        print(f"Target ID: {target_id}")

        # 新規追加の場合
        if not target_id or not os.path.exists('temp/mapping_result.csv'):
            print("新規レコードを表示")
            return {
                'original_text': temp_data.get('input_text', ''),
                'processed_data': temp_data.get('existing_data', {}),
                'tokens_info': temp_data.get('tokens_info', {}),
                'is_update': False
            }

        # 更新の場合
        try:
            df = pd.read_csv('temp/mapping_result.csv')
            record = df[df['id'] == target_id].iloc[0].to_dict()
            
            # 既存レコードとexisting_dataをマージ
            processed_data = record.copy()
            
            # CompareUpdateViewと同じ条件で更新
            for field, new_value in temp_data.get('existing_data', {}).items():
                current_value = processed_data.get(field, '')
                
                # 新しい値が存在し、「情報なし」でない場合のみ更新
                if new_value and new_value != '情報なし':
                    processed_data[field] = new_value
                elif field in processed_data and processed_data[field] == '情報なし':
                    # 既存の値が「情報なし」で、新しい値もない場合は
                    # 「情報なし」を維持
                    continue
            
            print("\n=== 更新後のデータ ===")
            print(json.dumps(processed_data, indent=2, ensure_ascii=False))
            
            return {
                'original_text': temp_data.get('input_text', ''),
                'processed_data': processed_data,
                'tokens_info': temp_data.get('tokens_info', {}),
                'is_update': True
            }
        except Exception as e:
            print(f"更新レコードの取得エラー: {str(e)}")
            return {
                'original_text': temp_data.get('input_text', ''),
                'processed_data': temp_data.get('existing_data', {}),
                'tokens_info': temp_data.get('tokens_info', {}),
                'is_update': False
            }

    def update_csv(self, data):
        """CSVファイルを更新"""
        try:
            print("\n=== ResultView: CSV更新開始 ===")
            temp_data = self.request.session.get('temp_form_data', {})
            
            # カラムの準備（idとtimestampを先頭に）
            all_columns = ['id', 'timestamp'] + list(temp_data.get('existing_data', {}).keys())
            
            # CSVファイルの存在確認
            if not os.path.exists('temp/mapping_result.csv'):
                print("CSVファイルが存在しません。新規作成します。")
                df = pd.DataFrame(columns=all_columns)
                os.makedirs('temp', exist_ok=True)
            else:
                df = pd.read_csv('temp/mapping_result.csv')
                # 新しいカラムがあれば追加
                for col in all_columns:
                    if col not in df.columns:
                        print(f"新しいカラムを追加: {col}")
                        df[col] = ''

            target_id = self.request.session.get('target_record_id')
            
            if target_id:  # 既存レコードの更新
                print(f"レコードを更新: ID {target_id}")
                idx = df.index[df['id'] == target_id].tolist()[0]
                for col, value in data.items():
                    if col not in ['id', 'timestamp']:  # idとtimestampは更新しない
                        df.at[idx, col] = value
            else:  # 新規レコードの追加
                data['id'] = len(df) + 1
                data['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print(f"新規レコードを追加: ID {data['id']}")
                df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
            
            df.to_csv('temp/mapping_result.csv', index=False)
            print("=== CSV更新完了 ===\n")
            return True, None
            
        except Exception as e:
            print(f"CSV更新エラー: {str(e)}")
            return False, str(e)

    def get(self, request, *args, **kwargs):
        """結果表示"""
        context = self.get_processed_data()
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """編集内容を保存"""
        try:
            # POSTデータから編集内容を取得
            edited_data = {}
            for key, value in request.POST.items():
                if key not in ['csrfmiddlewaretoken']:
                    edited_data[key] = value.strip()

            # CSVファイルを更新
            success, error = self.update_csv(edited_data)
            
            if success:
                try:
                    # SpreadsheetにCSVの内容を反映
                    upload_to_spreadsheet('temp/mapping_result.csv')
                    print("Spreadsheetの更新が完了しました")
                    messages.success(request, '変更を保存しました。')
                except Exception as e:
                    print(f"Spreadsheet更新エラー: {str(e)}")
                    messages.warning(request, 'CSVは更新されましたが、Spreadsheetの更新に失敗しました')

                # セッションデータをクリア
                if 'temp_form_data' in request.session:
                    del request.session['temp_form_data']
                if 'target_record_id' in request.session:
                    del request.session['target_record_id']
                return redirect('text-process')
            else:
                messages.error(request, f'保存中にエラーが発生しました: {error}')
                context = self.get_processed_data()
                return render(request, self.template_name, context)

        except Exception as e:
            messages.error(request, f'予期せぬエラーが発生しました: {str(e)}')
            context = self.get_processed_data()
            return render(request, self.template_name, context)

class NameConfirmView(TemplateView):
    template_name = 'textmap/confirm_name.html'

    def get(self, request, *args, **kwargs):
        temp_data = request.session.get('temp_form_data', {})
        existing_data = temp_data.get('existing_data', {})
        
        context = self.get_context_data(**kwargs)
        context.update({
            'original_text': temp_data.get('input_text', ''),
            'extracted_name': existing_data.get('氏名', '')
        })
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        confirmed_name = request.POST.get('confirmed_name', '').strip()
        temp_data = request.session.get('temp_form_data', {})
        temp_data['existing_data']['氏名'] = confirmed_name
        request.session['temp_form_data'] = temp_data
        request.session.modified = True
        
        print(f"\n=== 名前の重複チェック ===")
        print(f"検索する名前: '{confirmed_name}'")

        try:
            # CSVファイルの存在確認
            if not os.path.exists('temp/mapping_result.csv'):
                print("CSVファイルが存在しません。重複チェックをスキップします。")
                return redirect('adjust-categories')

            df = pd.read_csv('temp/mapping_result.csv')
            print(f"CSVファイルの行数: {len(df)}")
            
            # 名前の列を正規化（空白を除去）
            df['氏名'] = df['氏名'].str.strip()
            
            # 重複チェック（IDの降順でソート）
            matching_records = df[df['氏名'] == confirmed_name].sort_values('id', ascending=False)
            print(f"一致するレコード数: {len(matching_records)}")
            
            if not matching_records.empty:
                print(f"一致するレコード:")
                print(matching_records[['id', '氏名', 'timestamp']].to_string())
                return redirect('check-duplicate')
            
            print("重複なし - adjust-categoriesに進みます")
            return redirect('adjust-categories')
            
        except Exception as e:
            print(f"エラーが発生しました: {str(e)}")
            # エラーが発生しても処理を継続
            return redirect('adjust-categories')

class DuplicateCheckView(TemplateView):
    template_name = 'textmap/check_duplicate.html'

    def get(self, request, *args, **kwargs):
        
        temp_data = request.session.get('temp_form_data', {})
        existing_data = temp_data.get('existing_data', {})
        name = existing_data.get('氏名', '')
        
        context = self.get_context_data(**kwargs)
        
        try:
            df = pd.read_csv('temp/mapping_result.csv')
            
            # 名前が一致する全レコードを取得（タイムスタンプ降順）
            matching_records = df[df['氏名'] == name].sort_values('timestamp', ascending=False)
            
            if not matching_records.empty:
                # 各レコードの情報を整形
                records = []
                for _, record in matching_records.iterrows():
                    records.append({
                        'id': int(record['id']),
                        'timestamp': record['timestamp'],
                        'data': {
                            col: record[col]
                            for col in df.columns[3:]  # id, timestamp, 氏名 以外
                            if pd.notna(record[col]) and record[col] != '情報なし'
                        }
                    })
                
                context.update({
                    'name': name,
                    'matching_records': records,
                    'has_new_categories': bool(temp_data.get('new_categories', {}))  # 新カテゴリーの有無を追加
                })
                
                return self.render_to_response(context)
            
            print("No matching records found")
            return redirect('adjust-categories')
            
        except Exception as e:
            print(f"Error: {str(e)}")
            context['error'] = f"データの取得中にエラーが発生しました：{str(e)}"
            return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        record_id = request.POST.get('record_id')
        
        print(f"\n=== Duplicate Check ===")
        print(f"選択したアクション: {action}, 保存先ID: {record_id}")
        
        temp_data = request.session.get('temp_form_data', {})
        has_new_categories = bool(temp_data.get('new_categories', {}))
        
        if action == 'update' and record_id:
            # 更新モードとターゲットIDを保存
            request.session['update_mode'] = True
            request.session['target_record_id'] = int(record_id)
            request.session.modified = True
            
            if has_new_categories:
                print("Redirecting to adjust-categories for new categories")
                return redirect('adjust-categories')
            else:
                print(f"Redirecting to compare-update for record {record_id}")
                return redirect('compare-update')
        else:
            print("Redirecting to adjust-categories for new record")
            return redirect('adjust-categories')

class CompareUpdateView(TemplateView):
    template_name = 'textmap/compare_update.html'

    def get(self, request, *args, **kwargs):
        print("\n=== CompareUpdateView.get ===")
        
        if not request.session.get('target_record_id'):
            return redirect('result')
            
        target_record_id = request.session.get('target_record_id')
        temp_data = request.session.get('temp_form_data', {})
        existing_data = temp_data.get('existing_data', {})
        name = existing_data.get('氏名', '')
        
        context = self.get_context_data(**kwargs)
        
        try:
            df = pd.read_csv('temp/mapping_result.csv')
            target_record = df[df['id'] == target_record_id].iloc[0]
            
            #print(f"Target record data: {target_record.to_dict()}")
            #print(f"GPT-4 extracted data: {existing_data}")
            
            # フィールドの比較データを作成
            fields = []
            
            # existing_dataの各フィールドをチェック
            for field, new_value in existing_data.items():
                if field in ['id', 'timestamp', '氏名']:
                    continue
                    
                current_value = target_record.get(field, '')
                if pd.isna(current_value):
                    current_value = ''
                
                # 両方の値が存在し、「情報なし」でない場合のみ処理
                if (new_value and current_value and 
                    new_value != '情報なし' and current_value != '情報なし' and
                    str(current_value) != str(new_value)):
                    
                    fields.append({
                        'name': field,
                        'current_value': current_value,
                        'new_value': new_value,
                        'has_changes': True
                    })
            
            print(f"Fields to update: {fields}")
            
            context.update({
                'fields': fields,
                'name': name,
                'record_id': target_record_id
            })
            
            return self.render_to_response(context)
            
        except Exception as e:
            print(f"Error: {str(e)}")
            print("Stack trace:", traceback.format_exc())
            context['error'] = f"データの取得中にエラーが発生しました：{str(e)}"
            return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        target_record_id = request.session.get('target_record_id')
        action = request.POST.get('action')
        field_name = request.POST.get('field_name')
        
        print(f"\n=== CompareUpdateView.post ===")
        print(f"Action: {action}")
        print(f"Field: {field_name}")
        
        try:
            # CSVから現在のデータを取得
            df = pd.read_csv('temp/mapping_result.csv')
            current_record = df[df['id'] == target_record_id].iloc[0].to_dict()
            
            temp_data = request.session.get('temp_form_data', {})
            
            if action == 'update':
                # 新しい値をセッションに保存
                new_value = request.POST.get(f'new_{field_name}')
                if new_value:
                    temp_data['existing_data'][field_name] = new_value
                    print(f"Updated {field_name} to: {new_value}")
                    
            elif action == 'keep':
                # 現在の値をセッションに保存
                current_value = current_record.get(field_name, '')
                temp_data['existing_data'][field_name] = current_value
                print(f"Keeping current value for {field_name}: {current_value}")
            
            elif action == 'merge':
                # 現在の値と新しい値を結合
                current_value = current_record.get(field_name, '')
                new_value = request.POST.get(f'new_{field_name}')
                merged_value = f"{current_value} | {new_value}"
                temp_data['existing_data'][field_name] = merged_value
                print(f"Merged values for {field_name}: {merged_value}")
            
            # 他のフィールドの値を保持
            for field, value in current_record.items():
                if field not in ['id', 'timestamp']:
                    if field not in temp_data['existing_data'] or temp_data['existing_data'][field] == '情報なし':
                        temp_data['existing_data'][field] = value
            
            # セッションを更新
            request.session['temp_form_data'] = temp_data
            request.session.modified = True
            
            return JsonResponse({
                'success': True,
                'message': f'{field_name} was successfully processed'
            })
            
        except Exception as e:
            print(f"Error processing field: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
