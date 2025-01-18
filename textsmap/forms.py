from django import forms
from .models import MappedText
from django.conf import settings
import os

class TextProcessForm(forms.ModelForm):
    class Meta:
        model = MappedText
        fields = ['input_text']
        widgets = {
            'input_text': forms.Textarea(attrs={'rows': 10, 'cols': 60})
        } 

class CategoryAdjustmentForm(forms.Form):
    def __init__(self, *args, **kwargs):
        # new_categoriesとexisting_dataを取得
        new_categories = kwargs.pop('new_categories', {})
        existing_data = kwargs.pop('existing_data', {})
        super().__init__(*args, **kwargs)
        
        print("\n=== CategoryAdjustmentForm: 初期化 ===")
        print(f"新規カテゴリー: {list(new_categories.keys())}")
        print(f"既存データのキー: {list(existing_data.keys())}")
        
        # 各新カテゴリーに対してフィールドを作成
        for category, value in new_categories.items():
            # アクション選択フィールド
            action_field = f'action_{category}'
            self.fields[action_field] = forms.ChoiceField(
                choices=[
                    ('add', 'このまま追加'),
                    ('rename', '名前を変更して追加'),
                    ('merge', '既存カテゴリーに統合')
                ],
                initial='add',
                widget=forms.RadioSelect,
                label=f'「{category}」({value}) の処理方法'  # 値も表示
            )
            
            # 名前変更用フィールド
            rename_field = f'rename_{category}'
            self.fields[rename_field] = forms.CharField(
                required=False,
                widget=forms.TextInput(attrs={
                    'class': 'form-control',
                    'placeholder': '新しいカテゴリー名を入力'
                }),
                label='→ 新しい名前'
            )
            
            # 統合先選択フィールド
            merge_field = f'merge_{category}'
            existing_choices = [(k, f'{k}: {v}') for k, v in existing_data.items()]
            self.fields[merge_field] = forms.ChoiceField(
                choices=[('', '選択してください')] + existing_choices,  # 空の選択肢を追加
                required=False,
                widget=forms.Select(attrs={
                    'class': 'form-control'
                }),
                label='→ 統合先のカテゴリー'
            ) 

class AudioUploadForm(forms.Form):
    audio_file = forms.FileField(
        label='音声ファイル',
        help_text='対応形式: MP3, M4A, WAV, AAC (最大25MB)',
        required=True
    )

    def clean_audio_file(self):
        audio_file = self.cleaned_data.get('audio_file')
        if audio_file:
            # ファイルサイズチェック
            if audio_file.size > settings.FILE_UPLOAD_MAX_MEMORY_SIZE:
                raise forms.ValidationError('ファイルサイズは25MB以下にしてください。')
            
            # 拡張子チェック
            ext = os.path.splitext(audio_file.name)[1].lower()
            if ext not in settings.ALLOWED_AUDIO_EXTENSIONS:
                raise forms.ValidationError('対応していないファイル形式です。')
            
        return audio_file 