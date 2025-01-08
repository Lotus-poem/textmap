from django import forms
from .models import MappedText

class TextProcessForm(forms.ModelForm):
    class Meta:
        model = MappedText
        fields = ['input_text']
        widgets = {
            'input_text': forms.Textarea(attrs={'rows': 10, 'cols': 60})
        } 

class CategoryAdjustmentForm(forms.Form):
    def __init__(self, new_categories=None, existing_categories=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # new_categoriesがNoneの場合は空の辞書を使用
        new_categories = new_categories or {}
        
        # existing_categoriesがNoneの場合はデフォルト値を使用
        existing_categories = existing_categories or ['氏名', '会社名']
        
        # 各新カテゴリーに対してフィールドを作成
        for category in new_categories.keys():
            self.fields[f'action_{category}'] = forms.ChoiceField(
                choices=[
                    ('add', '追加'),
                    ('rename', '名前を変更'),
                    ('merge', '既存カテゴリーと統合'),
                    ('ignore', '無視')
                ],
                initial='add',
                widget=forms.RadioSelect
            )
            
            self.fields[f'rename_{category}'] = forms.CharField(
                required=False,
                widget=forms.TextInput(attrs={'class': 'form-control'})
            )
            
            self.fields[f'merge_{category}'] = forms.ChoiceField(
                choices=[(c, c) for c in existing_categories],
                required=False,
                widget=forms.Select(attrs={'class': 'form-control'})
            ) 