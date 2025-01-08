from django.shortcuts import render, redirect
from django.views.generic import ListView, DetailView, CreateView, FormView, TemplateView
from .models import MappedText, Category, ProcessedText
from .forms import TextProcessForm, CategoryAdjustmentForm
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

logger = logging.getLogger(__name__)

class MappedTextListView(ListView):
    model = MappedText
    template_name = 'textsmap/mappedtext_list.html'
    context_object_name = 'texts'

class MappedTextDetailView(DetailView):
    model = MappedText
    template_name = 'textsmap/mappedtext_detail.html'
    context_object_name = 'text'

class TextProcessView(CreateView):
    model = MappedText
    form_class = TextProcessForm
    template_name = 'textsmap/process_text.html'
    
    def get_current_categories(self):
        """現在のカテゴリーリストを取得"""
        from .config import get_current_categories
        categories = get_current_categories()
        return [cat for cat in categories if cat not in ['id', 'timestamp']]
    
    def form_valid(self, form):
        try:
            instance = form.save(commit=False)
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            
            # 現在の有効なカテゴリーを取得
            current_categories = self.get_current_categories()
            print("\n=== Processing New Text ===")
            print("Text length:", len(instance.input_text))
            print("Current categories:", current_categories)
            
            try:
                print("\nSending request to GPT-4...")
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
                            {current_categories}
                            
                            文章:
                            {instance.input_text}
                            """
                        }
                    ],
                    temperature=0.2,
                    max_tokens=2000
                )

                content = response.choices[0].message.content.strip()
                print("\nGPT Response:", content)
                
                try:
                    result = json.loads(content)
                    print("\nParsed JSON:", json.dumps(result, indent=2, ensure_ascii=False))
                    
                    if result.get('new_categories'):
                        print("\nNew categories found:", result['new_categories'])
                        session_data = {
                            'input_text': instance.input_text,
                            'existing_data': result['existing_data'],
                            'new_categories': result['new_categories'],
                            'tokens_info': {
                                'prompt_tokens': response.usage.prompt_tokens,
                                'completion_tokens': response.usage.completion_tokens,
                                'total_tokens': response.usage.total_tokens,
                                'cost_usd': (
                                    (response.usage.prompt_tokens * GPT4_PROMPT_COST) +
                                    (response.usage.completion_tokens * GPT4_COMPLETION_COST)
                                ) / 1000
                            }
                        }
                        print("\nSaving to session:", json.dumps(session_data, indent=2, ensure_ascii=False))
                        self.request.session['temp_form_data'] = session_data
                        self.request.session.modified = True
                        return redirect('adjust-categories')
                    
                    print("\nNo new categories found, saving directly")
                    # ProcessedTextモデルに保存
                    processed_text = ProcessedText.objects.create(
                        original_text=instance.input_text,
                        processed_data=result['existing_data'],
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=response.usage.completion_tokens,
                        total_tokens=response.usage.total_tokens,
                        cost_usd=(
                            (response.usage.prompt_tokens * GPT4_PROMPT_COST) +
                            (response.usage.completion_tokens * GPT4_COMPLETION_COST)
                        ) / 1000
                    )

                    # CSVファイルに保存
                    save_mapping_result(result['existing_data'])

                    # 結果画面にリダイレクト
                    return redirect('result')  # text-processからresultに変更
                    
                except json.JSONDecodeError as e:
                    print("\nJSON Parse Error:", str(e))
                    print("Raw content:", content)
                    messages.error(self.request, f"GPTの応答をJSONとして解析できませんでした: {str(e)}")
                    return redirect('process-text')
                    
            except Exception as e:
                print("\nGeneral Error:", str(e))
                messages.error(self.request, f"エラーが発生しました: {str(e)}")
                return redirect('process-text')
        except Exception as e:
            messages.error(self.request, f'エラーが発生しました: {str(e)}')
            return self.form_invalid(form)

    def process_text_with_gpt(self, text, categories):
        client = OpenAI()
        
        # プロンプトの構築
        prompt = f"""
        以下のテキストから、各カテゴリーに関連する情報を抽出してください。
        テキストに該当する情報がない場合は「情報なし」と記入してください。

        カテゴリー:
        {', '.join(categories)}

        テキスト:
        {text}

        回答は以下のJSON形式で返してください:
        {{
            "カテゴリー1": "抽出された情報1",
            "カテゴリー2": "抽出された情報2",
            ...
        }}
        """

        # GPTに問い合わせ（GPT-4を使用）
        response = client.chat.completions.create(
            model="gpt-4",  # GPT-3.5からGPT-4に変更
            messages=[
                {"role": "system", "content": "あなたは与えられたテキストから情報を抽出する専門家です。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )

class ConfirmNewKeysView(CreateView):
    template_name = 'textsmap/confirm_new_keys.html'
    
    def get(self, request, *args, **kwargs):
        temp_response = request.session.get('temp_response', {})
        suggested_keys = temp_response.get('suggested_new_keys', [])
        return render(request, self.template_name, {
            'suggested_keys': suggested_keys,
        })
    
    def post(self, request, *args, **kwargs):
        selected_keys = request.POST.getlist('selected_keys')
        current_keys = request.session.get('current_keys', INITIAL_KEYS.copy())
        current_keys.extend(selected_keys)
        request.session['current_keys'] = current_keys
        
        instance = MappedText(input_text=request.session['temp_form_data'])
        instance.save()
        
        del request.session['temp_form_data']
        del request.session['temp_response']
        
        return redirect('process-text')

class TextDetailView(DetailView):
    model = MappedText
    template_name = 'textsmap/mappedtext_detail.html'
    context_object_name = 'text'

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
    template_name = 'textsmap/adjust_categories.html'
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
    def get(self, request):
        # 最新の処理結果を取得
        latest_result = ProcessedText.objects.order_by('-created_at').first()
        
        if not latest_result:
            messages.error(request, 'テキスト処理の結果が見つかりません。')
            return redirect('text-process')

        context = {
            'original_text': latest_result.original_text,
            'processed_data': latest_result.processed_data,
            'tokens_info': {
                'prompt_tokens': latest_result.prompt_tokens,
                'completion_tokens': latest_result.completion_tokens,
                'total_tokens': latest_result.total_tokens,
                'cost_usd': latest_result.cost_usd
            }
        }
        
        return render(request, 'textsmap/result.html', context)
