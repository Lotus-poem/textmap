from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from datetime import datetime
import os
import json
import logging

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def generate_test_pdf(job_data):
    # 日本語フォントの設定
    pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
    
    # 出力ファイル名の設定
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    pdf_filename = os.path.join(output_dir, f"test_求人情報_{timestamp}.pdf")
    
    # PDFドキュメントの設定
    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )
    
    # スタイルの設定
    styles = getSampleStyleSheet()
    
    # ヘッダータイトル用スタイル
    styles.add(ParagraphStyle(
        name='CompanyTitle',
        fontName='HeiseiKakuGo-W5',
        fontSize=18,
        leading=22,
        spaceAfter=20,
        textColor=colors.HexColor('#0B2A5B'),  # RVの濃紺
        alignment=1  # 中央揃え
    ))
    
    # サブタイトル用スタイル
    styles.add(ParagraphStyle(
        name='PositionTitle',
        fontName='HeiseiKakuGo-W5',
        fontSize=16,
        leading=19,
        spaceAfter=30,
        textColor=colors.HexColor('#0B2A5B'),  # RVの濃紺
        alignment=1  # 中央揃え
    ))
    
    # セクションヘッダー用スタイル
    styles.add(ParagraphStyle(
        name='SectionHeader',
        fontName='HeiseiKakuGo-W5',
        fontSize=14,
        leading=18,
        spaceBefore=20,
        spaceAfter=12,
        textColor=colors.white,
        backColor=colors.HexColor('#0B2A5B'),  # RVの濃紺
        borderPadding=(8, 12, 8, 12),
        alignment=0  # 左揃え
    ))
    
    # 本文用スタイル
    styles.add(ParagraphStyle(
        name='ContentText',
        fontName='HeiseiKakuGo-W5',
        fontSize=10,
        leading=15,
        spaceBefore=5,
        spaceAfter=15,
        leftIndent=10,
        textColor=colors.black
    ))

    elements = []
    
    # ロゴの追加（Real Valueのロゴ）
    logo_path = "assets/logo.png"
    if os.path.exists(logo_path):
        logo = Image(logo_path)
        logo.drawHeight = 30
        logo.drawWidth = 100
        elements.append(logo)
        elements.append(Spacer(1, 20))

    # 会社名/企業名の追加
    company_name = job_data.get('会社情報') or job_data.get('企業名', '')
    if company_name:
        elements.append(Paragraph(company_name, styles['CompanyTitle']))
    
    # 職種名/ポジションの追加
    position = job_data.get('職種名') or job_data.get('ポジション', '')
    if position:
        elements.append(Paragraph(position, styles['PositionTitle']))
    
    # 主要項目の表示順序
    main_items = ['職務内容', '業務内容', '必要なスキル・経験', '応募資格(詳細)']
    for item in main_items:
        if item in job_data and job_data[item]:
            elements.append(Paragraph(
                f"■{item}",
                styles['SectionHeader']
            ))
            elements.append(Paragraph(
                job_data[item].replace('\n', '<br/>'),
                styles['ContentText']
            ))
    
    # その他の情報をグループ化して表示
    other_info = {
        "待遇・労働条件": ['給与', '手当', '賞与', '雇用形態', '勤務地', '就業時間', '休日'],
        "福利厚生・制度": ['社会保険', '制度・福利厚生', '試用期間'],
        "選考情報": ['選考', '年齢', '学歴']
    }
    
    for group_title, items in other_info.items():
        has_content = False
        group_content = []
        
        for item in items:
            if item in job_data and job_data[item]:
                has_content = True
                group_content.append(f"<b>{item}</b><br/>{job_data[item]}<br/><br/>")
        
        if has_content:
            elements.append(Paragraph(
                f"■{group_title}",
                styles['SectionHeader']
            ))
            elements.append(Paragraph(
                ''.join(group_content),
                styles['ContentText']
            ))

    # PDFの生成
    doc.build(elements)
    logger.info(f"テストPDFを作成しました: {pdf_filename}")
    return pdf_filename

def main():
    # JSONファイルからデータを読み込む
    try:
        with open('agent_navi_data.json', 'r', encoding='utf-8') as f:
            job_data = json.load(f)
        generate_test_pdf(job_data)
    except Exception as e:
        logger.error(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()