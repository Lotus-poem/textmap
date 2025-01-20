from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from datetime import datetime
import os
import logging

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# テスト用のサンプルデータ
sample_job_data = {
    '企業名': 'PwCアドバイザリー合同会社',
    'ポジション': '社内契約手続きサポート【Deals EPC】(J-00001986)',
    '特徴': '年収500万円以下,法務/人事などその他バックオフィス系',
    '職種': '管理->法務・コンプライアンス',
    '業務内容': 'PwCアドバイザリー合同会社にて、コンサルタント等とコミュニケーションをとりながら、クライアントへのサービス提供に必要な契約手続きや社内手続きのアシスタント業務をお願いします。\n\n＜主な業務内容＞\n(1) 契約書、押印手続き\n(2) 社内システムへの情報入力\n(3) 各種問い合わせ対応、関係部署の担当者との連携',
    '応募資格(詳細)': '■必須条件\n・社会人経験3年以上\n・コミュニケーション能力\n・PCの基本的な操作が可能な方',
    '給与(詳細)': '面談時にご確認ください',
    '勤務地': '関東->東京都',
    '勤務地(詳細)': '東京',
    'リモートワークの可否': '一部OK',
    '待遇・福利厚生': '各種社会保険完備、退職金制度あり',
    '休日休暇': '完全週休2日制、祝日、年末年始',
    '雇用形態': '契約社員',
    '雇用形態(詳細)': '契約社員スタート。評価次第で正社員登用の可能性あり',
    '選考プロセス': '書類選考→面接→内定',
    '年収': '350万円 - 420万円'
}

def generate_test_pdf(job_data):
    try:
        # 日本語フォントの設定
        pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
        
        # 出力ディレクトリの作成
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        
        # PDFファイル名の設定
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = os.path.join(output_dir, f"test_求人情報_{timestamp}.pdf")

        # PDFドキュメントの作成
        doc = SimpleDocTemplate(
            pdf_filename,
            pagesize=A4,
            rightMargin=30,
            leftMargin=30,
            topMargin=50,
            bottomMargin=30
        )

        # スタイルの設定
        styles = getSampleStyleSheet()
        
        # 会社名用スタイル
        styles.add(ParagraphStyle(
            name='CompanyTitle',
            fontName='HeiseiKakuGo-W5',
            fontSize=16,
            leading=18,
            spaceAfter=20,
            textColor=colors.black,
            bulletIndent=0,
            leftIndent=0,
            bold=True
        ))
        
        # ポジション名用スタイル
        styles.add(ParagraphStyle(
            name='PositionTitle',
            fontName='HeiseiKakuGo-W5',
            fontSize=14,
            leading=16,
            spaceAfter=20,
            textColor=colors.black,
            bulletIndent=0,
            leftIndent=0,
            bold=True
        ))
        
        # 見出しスタイル
        styles.add(ParagraphStyle(
            name='CustomHeading',
            fontName='HeiseiKakuGo-W5',
            fontSize=11,
            leading=13,
            spaceAfter=10,
            backColor=colors.Color(0.9, 0.9, 1),
            textColor=colors.black,
            bulletIndent=0,
            leftIndent=0,
            bold=True
        ))
        
        # 本文スタイル
        styles.add(ParagraphStyle(
            name='CustomNormal',
            fontName='HeiseiKakuGo-W5',
            fontSize=10,
            leading=14,
            spaceAfter=10,
            bulletIndent=0,
            leftIndent=0
        ))

        elements = []
        
        # タイトル部分の追加
        elements.append(Paragraph(
            job_data['企業名'],
            styles['CompanyTitle']
        ))
        elements.append(Paragraph(
            job_data['ポジション'],
            styles['PositionTitle']
        ))

        # 表示順序の定義
        display_order = [
            '特徴',
            '業務内容',
            '職種',
            '応募資格(詳細)',
            '給与(詳細)',
            '勤務地',
            '勤務地(詳細)',
            'リモートワークの可否',
            '待遇・福利厚生',
            '休日休暇',
            '雇用形態',
            '雇用形態(詳細)',
            '選考プロセス',
            '年収'
        ]

        # 詳細情報の追加
        for key in display_order:
            if key in job_data and job_data[key]:
                elements.append(Paragraph(
                    f"■{key}",
                    styles['CustomHeading']
                ))
                content = str(job_data[key]).replace('\n', '<br/>')
                elements.append(Paragraph(
                    content,
                    styles['CustomNormal']
                ))

        # PDFの生成
        doc.build(elements)
        logger.info(f"テストPDFを作成しました: {pdf_filename}")
        
        return pdf_filename

    except Exception as e:
        logger.error(f"PDF生成中にエラーが発生しました: {e}")
        raise

if __name__ == "__main__":
    generate_test_pdf(sample_job_data) 