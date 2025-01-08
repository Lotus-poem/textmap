from django.db import models
from django.utils import timezone
import json

class MappedText(models.Model):
    input_text = models.TextField(verbose_name='入力テキスト')
    mapped_data = models.JSONField(verbose_name='マッピング結果', default=dict)
    created_at = models.DateTimeField(default=timezone.now, verbose_name='作成日時')
    used_keys = models.JSONField(verbose_name='使用した軸', default=list)
    prompt_tokens = models.IntegerField(default=0, verbose_name='入力トークン数')
    completion_tokens = models.IntegerField(default=0, verbose_name='出力トークン数')
    total_tokens = models.IntegerField(default=0, verbose_name='合計トークン数')
    cost_usd = models.DecimalField(max_digits=10, decimal_places=6, default=0, verbose_name='概算コスト(USD)')

    class Meta:
        verbose_name = 'マッピングテキスト'
        verbose_name_plural = 'マッピングテキスト'

    def __str__(self):
        return f"Mapped Text {self.id}"

    def get_mapped_data(self):
        if isinstance(self.mapped_data, str):
            return json.loads(self.mapped_data)
        return self.mapped_data

class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name='軸名', unique=True)
    created_at = models.DateTimeField(default=timezone.now, verbose_name='作成日時')
    is_active = models.BooleanField(default=True, verbose_name='有効')

    class Meta:
        verbose_name = '分類軸'
        verbose_name_plural = '分類軸'

    def __str__(self):
        return self.name

class ProcessedText(models.Model):
    original_text = models.TextField()
    processed_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    prompt_tokens = models.IntegerField(default=0)
    completion_tokens = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)
    cost_usd = models.DecimalField(max_digits=10, decimal_places=6, default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'処理済みテキスト {self.id} ({self.created_at})'
