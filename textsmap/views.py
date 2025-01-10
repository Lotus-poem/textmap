from django.shortcuts import render, redirect
from django.views.generic import CreateView, FormView, TemplateView
from .models import MappedText, ProcessedText
from .forms import TextProcessForm
from django.contrib import messages
from openai import OpenAI
from .config import (
    GPT35_PROMPT_COST, GPT35_COMPLETION_COST, 
    get_current_categories as config_get_categories,
    save_mapping_result,
    INITIAL_KEYS,
    GPT4_PROMPT_COST, 
    GPT4_COMPLETION_COST
)
import json
from django.conf import settings
import pandas as pd
from django import forms
from django.views import View
import logging
import traceback
from django.http import JsonResponse
from datetime import datetime

logger = logging.getLogger(__name__)

class TextProcessView(CreateView):
    model = MappedText
    form_class = TextProcessForm
    template_name = 'textmap/process_text.html'
    
    def get_current_categories(self):
        """現在のカテゴリーリストを取得"""
        from .config import get_current_categories
        categories = get_current_categories()
        return [cat for cat in categories if cat not in ['id', 'timestamp']]
    
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

class CategoryAdjustForm(forms.Form):
    def __init__(self, *args, new_categories=None, existing_categories=None, **kwargs):
        super().__init__(*args, **kwargs)
        if new_categories:
            for category, value in new_categories.items():
                self.fields[f'action_{category}'] = forms.ChoiceField(
                    label=f'新カテゴリー「{category}」（値: {value}）の処理',
                    choices=[
                        ('add', 'このカテゴリーを新規追加する'),
                        ('rename', 'カテゴリー名を変更して追加する'),
                        ('merge', '既存のカテゴリーに統合する'),
                        ('skip', 'このデータは使用しない')
                    ],
                    widget=forms.RadioSelect,
                    initial='add'
                )
                self.fields[f'rename_{category}'] = forms.CharField(
                    label='新しいカテゴリー名',
                    required=False
                )
                self.fields[f'merge_{category}'] = forms.ChoiceField(
                    label='統合先のカテゴリー',
                    choices=[(c, c) for c in existing_categories],
                    required=False
                )

class CategoryAdjustView(FormView):
    template_name = 'textmap/adjust_categories.html'
    form_class = CategoryAdjustForm
    success_url = '/result/'

    def get_current_categories(self):
        """現在のカテゴリーリストを取得"""
        from .config import get_current_categories
        categories = get_current_categories()
        return [cat for cat in categories if cat not in ['id', 'timestamp']]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        temp_data = self.request.session.get('temp_form_data', {})
        context['new_categories'] = temp_data.get('new_categories', {})
        context['existing_categories'] = self.get_current_categories()
        return context

    def form_valid(self, form):
        try:
            # セッションから一時データを取得
            temp_data = self.request.session.get('temp_form_data', {})
            new_categories = temp_data.get('new_categories', {})
            existing_data = temp_data.get('existing_data', {})  # 既存データを取得
            
            # 調整済みカテゴリーを保存するための辞書
            adjusted_data = existing_data.copy()  # 既存データをベースにする
            
            # カテゴリーの調整結果を処理
            for category, value in new_categories.items():
                action = self.request.POST.get(f'action_{category}')
                
                if action == 'add':
                    adjusted_data[category] = value
                elif action == 'rename':
                    new_name = self.request.POST.get(f'rename_{category}')
                    if new_name:
                        adjusted_data[new_name] = value
                elif action == 'merge':
                    merge_to = self.request.POST.get(f'merge_{category}')
                    if merge_to in adjusted_data:
                        adjusted_data[merge_to] = f"{adjusted_data[merge_to]}; {value}"
                    else:
                        adjusted_data[merge_to] = value

            # ProcessedTextモデルに保存
            processed_text_obj = ProcessedText.objects.create(
                original_text=temp_data.get('input_text', ''),
                processed_data=adjusted_data
            )

            # CSVファイルに保存
            from .config import save_mapping_result
            save_mapping_result(adjusted_data)

            # トークン情報も保存
            tokens_info = temp_data.get('tokens_info', {})
            if tokens_info:
                processed_text_obj.prompt_tokens = tokens_info.get('prompt_tokens', 0)
                processed_text_obj.completion_tokens = tokens_info.get('completion_tokens', 0)
                processed_text_obj.total_tokens = tokens_info.get('total_tokens', 0)
                processed_text_obj.cost_usd = tokens_info.get('cost_usd', 0)
                processed_text_obj.save()

            # セッションをクリア
            if 'temp_form_data' in self.request.session:
                del self.request.session['temp_form_data']

            messages.success(self.request, 'カテゴリーの調整が完了しました。')
            return super().form_valid(form)

        except Exception as e:
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

        if target_id:  # 更新の場合
            try:
                df = pd.read_csv('output/mapping_result.csv')
                record = df[df['id'] == target_id].iloc[0].to_dict()
                print(f"更新レコードを表示:")
                print(f"- ID: {target_id}")
                print(f"- 名前: {record.get('氏名', '')}")
                return {
                    'original_text': temp_data.get('input_text', ''),
                    'processed_data': record,
                    'tokens_info': temp_data.get('tokens_info', {}),
                    'is_update': True
                }
            except Exception as e:
                print(f"更新レコードの取得エラー: {str(e)}")
                messages.error(self.request, f'更新レコードの取得に失敗しました: {str(e)}')

        # 新規追加の場合
        print("新規レコードを表示")
        return {
            'original_text': temp_data.get('input_text', ''),
            'processed_data': temp_data.get('existing_data', {}),
            'tokens_info': temp_data.get('tokens_info', {}),
            'is_update': False
        }

    def update_csv(self, data):
        """CSVファイルを更新"""
        try:
            df = pd.read_csv('output/mapping_result.csv')
            target_id = self.request.session.get('target_record_id')
            
            print(f"\n=== CSV更新 ===")
            if target_id:  # 既存レコードの更新
                print(f"レコードを更新: ID {target_id}")
                # データの整形
                update_data = {}
                for column in df.columns:
                    update_data[column] = data.get(column, '')
                
                # インデックスを使用して更新
                idx = df.index[df['id'] == target_id].tolist()[0]
                for col in df.columns:
                    df.at[idx, col] = update_data[col]
            else:  # 新規レコードの追加
                data['id'] = len(df) + 1
                data['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print(f"新規レコードを追加: ID {data['id']}")
                df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
            
            df.to_csv('output/mapping_result.csv', index=False)
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
                messages.success(request, '変更を保存しました。')
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
            df = pd.read_csv('output/mapping_result.csv')
            print(f"CSVファイルの行数: {len(df)}")
            
            # 名前の列を正規化（空白を除去）
            df['氏名'] = df['氏名'].str.strip()
            
            # 重複チェック（IDの降順でソート）
            matching_records = df[df['氏名'] == confirmed_name].sort_values('id', ascending=False)
            print(f"一致するレコード数: {len(matching_records)}")
            
            if not matching_records.empty:
                # 最新（最大ID）のレコードを使用
                latest_record = matching_records.iloc[0]
                record_id = latest_record['id']
                
                print(f"最新レコードのID: {record_id}")
                print(f"一致するレコード:")
                print(matching_records[['id', '氏名', 'timestamp']].to_string())
                
                # 重複データをセッションに保存
                request.session['existing_record'] = latest_record.to_dict()
                request.session['target_record_id'] = int(record_id)
                request.session.modified = True
                
                print("check-duplicateにリダイレクト")
                return redirect('check-duplicate')
            
            print("重複なし - adjust-categoriesに進みます")
            return redirect('adjust-categories')
            
        except Exception as e:
            print(f"エラーが発生しました: {str(e)}")
            return redirect('adjust-categories')

class DuplicateCheckView(TemplateView):
    template_name = 'textmap/check_duplicate.html'

    def get(self, request, *args, **kwargs):
        print("DuplicateCheckView.get called")
        
        temp_data = request.session.get('temp_form_data', {})
        existing_data = temp_data.get('existing_data', {})
        name = existing_data.get('氏名', '')
        
        print(f"Looking for name: {name}")
        
        context = self.get_context_data(**kwargs)
        
        try:
            df = pd.read_csv('output/mapping_result.csv')
            
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
                    'matching_records': records
                })
                
                print(f"Found {len(records)} matching records")
                return self.render_to_response(context)
            
            print("No matching records found")
            return redirect('adjust-categories')
            
        except Exception as e:
            print(f"Error: {str(e)}")
            context['error'] = f"データの取得中にエラーが発生しました：{str(e)}"
            return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        record_id = request.POST.get('record_id')  # 選択されたレコードのID
        
        print(f"Selected action: {action}, Record ID: {record_id}")
        
        if action == 'update' and record_id:
            # 更新モードとターゲットIDを保存
            request.session['update_mode'] = True
            request.session['target_record_id'] = int(record_id)
            request.session.modified = True
            
            print(f"Redirecting to compare-update for record {record_id}")
            return redirect('compare-update')
        else:
            print("Redirecting to adjust-categories for new record")
            return redirect('adjust-categories')

class CompareUpdateView(TemplateView):
    template_name = 'textmap/compare_update.html'

    def get(self, request, *args, **kwargs):
        print("\n=== CompareUpdateView.get ===")
        
        if not request.session.get('update_mode'):
            return redirect('result')
            
        target_record_id = request.session.get('target_record_id')
        temp_data = request.session.get('temp_form_data', {})
        
        print("Session data:")
        print(f"- Target record ID: {target_record_id}")
        print(f"- Temp data: {temp_data}")
        
        # GPT-4の解析結果を取得
        existing_data = temp_data.get('existing_data', {})
        name = existing_data.get('氏名', '')
        
        context = self.get_context_data(**kwargs)
        
        try:
            df = pd.read_csv('output/mapping_result.csv')
            target_record = df[df['id'] == target_record_id].iloc[0]
            
            print(f"Target record data: {target_record.to_dict()}")
            print(f"GPT-4 extracted data: {existing_data}")
            
            # フィールドの比較データを作成
            fields = []
            
            # CSVの全カラムをチェック
            for field in df.columns:
                # id, timestamp, 氏名 は除外
                if field not in ['id', 'timestamp', '氏名']:
                    current_value = target_record.get(field, '')
                    new_value = existing_data.get(field, '')
                    
                    # 空値や'情報なし'を標準化
                    if pd.isna(current_value) or current_value == '情報なし':
                        current_value = ''
                    if pd.isna(new_value) or new_value == '情報なし':
                        new_value = ''
                    
                    # 値が異なる場合のみ表示
                    if str(current_value) != str(new_value) and new_value:
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
            df = pd.read_csv('output/mapping_result.csv')
            target_idx = df[df['id'] == target_record_id].index[0]
            
            if action == 'update':
                # 新しい値で更新
                new_value = request.POST.get(f'new_{field_name}')
                if new_value:
                    df.at[target_idx, field_name] = new_value
                    print(f"Updated {field_name} to: {new_value}")
                    
            elif action == 'keep':
                # 現在の値を維持
                current_value = df.at[target_idx, field_name]
                print(f"Keeping current value for {field_name}: {current_value}")
                
                # セッションの temp_form_data も更新
                temp_data = request.session.get('temp_form_data', {})
                if 'existing_data' in temp_data:
                    temp_data['existing_data'][field_name] = current_value
                    request.session['temp_form_data'] = temp_data
                    request.session.modified = True
            
            df.to_csv('output/mapping_result.csv', index=False)
            
            return JsonResponse({
                'success': True,
                'message': f'{field_name} was successfully processed'
            })
            
        except Exception as e:
            print(f"Error updating CSV: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
