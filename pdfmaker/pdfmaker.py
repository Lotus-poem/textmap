from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.firefox import GeckoDriverManager
from datetime import datetime
import aconfig
import logging
from contextlib import contextmanager
import time
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, 
    Paragraph, 
    Spacer, 
    Image, 
    PageBreak,
    Frame,
)
from reportlab.platypus.doctemplate import PageTemplate
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.utils import ImageReader
import os
import argparse
import sys

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WebScraper:
    def __init__(self, url):
        self.url = url
        self.driver = None
        self.job_data = {}
        
        # 日本語フォントの設定（MS Gothic を使用する場合）
        try:
            # まずIPAexフォントを試す
            font_path = "fonts/ipaexg.ttf"
            pdfmetrics.registerFont(TTFont('CustomFont', font_path))
        except:
            try:
                # Windows の場合、MS Gothic を使用
                font_path = "C:/Windows/Fonts/msgothic.ttc"
                pdfmetrics.registerFont(TTFont('CustomFont', font_path))
            except:
                # Mac の場合、Hiragino を使用
                font_path = "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"
                pdfmetrics.registerFont(TTFont('CustomFont', font_path))

    def setup_driver(self):
        firefox_options = webdriver.FirefoxOptions()
        firefox_options.accept_insecure_certs = True
        firefox_options.add_argument('--no-sandbox')
        firefox_options.add_argument('--disable-dev-shm-usage')
        firefox_options.add_argument('--headless')
        
        # geckodriverの場所を直接指定
        geckodriver_path = r"C:\Users\worth\.wdm\drivers\geckodriver\win64\v0.35.0\geckodriver.exe"
        service = FirefoxService(geckodriver_path)
        return webdriver.Firefox(service=service, options=firefox_options)

    @contextmanager
    def browser_session(self):
        try:
            self.driver = self.setup_driver()
            logger.info("ブラウザを起動しました")
            yield self.driver
        except Exception as e:
            logger.error(f"ブラウザセッション中にエラーが発生しました: {e}")
            raise
        finally:
            if self.driver:
                self.driver.quit()
                logger.info("ブラウザを終了しました")

    def analyze_page_content(self, driver):
        """ページ内の要素を解析してコンソールに出力する"""
        try:
            # ページの読み込みを待機
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            logger.info("=== ページ構造の解析を開始 ===")
            
            # 主要な見出し要素を取得
            headings = driver.find_elements(By.CSS_SELECTOR, "h1, h2, h3, h4, h5, h6")
            logger.info("\n【見出し要素】")
            for heading in headings:
                logger.info(f"{heading.tag_name}: {heading.text}")
            
            # 主要なコンテンツエリアを特定
            main_content = driver.find_elements(By.CSS_SELECTOR, "main, article, .content, .main")
            logger.info("\n【メインコンテンツ】")
            for content in main_content:
                logger.info(f"クラス名: {content.get_attribute('class')}")
                logger.info(f"内容: {content.text[:200]}...") # 最初の200文字のみ表示
            
            # フォーム要素やテーブルの特定
            forms = driver.find_elements(By.TAG_NAME, "form")
            tables = driver.find_elements(By.TAG_NAME, "table")
            logger.info(f"\n【フォーム数】: {len(forms)}")
            logger.info(f"【テーブル数】: {len(tables)}")
            
        except Exception as e:
            logger.error(f"ページ解析中にエラーが発生しました: {e}")

    def extract_job_info(self, driver):
        """求人情報を抽出する"""
        try:
            # ページの読み込みを待機
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "item"))
            )

            # 基本情報の取得
            try:
                number = driver.find_element(
                    By.XPATH, "//p[contains(@class, 'heading__sub')]"
                ).text
                title = driver.find_element(
                    By.XPATH, "//h2[contains(@class, 'heading__title')]"
                ).text
                subinfo_left = driver.find_element(
                    By.XPATH, "//div[contains(@class, 'subinfoLeft')]"
                ).text
                subinfo_right = driver.find_element(
                    By.XPATH, "//div[contains(@class, 'subinfoRight')]"
                ).text

                self.job_data["求人番号"] = number
                self.job_data["職種名"] = title
                self.job_data["会社情報"] = subinfo_left
                self.job_data["更新日"] = subinfo_right.replace("更新日：", "").strip()
            except Exception as e:
                logger.warning(f"基本情報の取得に失敗: {e}")

            # 詳細情報の取得
            contents = driver.find_elements(By.XPATH, "//div[@class='item']")
            for content in contents:
                try:
                    label = content.find_element(
                        By.XPATH, ".//h3[@class='label']"
                    ).text
                    content_text = content.find_element(
                        By.XPATH, ".//div[@class='content']//p"
                    ).text
                    self.job_data[label] = content_text
                except Exception as e:
                    logger.warning(f"項目「{label}」の取得に失敗: {e}")
                    continue

            logger.info("求人情報の抽出が完了しました")
            logger.info(f"取得した項目: {list(self.job_data.keys())}")
            return True

        except Exception as e:
            logger.error(f"求人情報の抽出中にエラーが発生しました: {e}")
            return False

    def run(self):
        with self.browser_session() as driver:
            try:
                logger.info("ログインページにアクセスしています...")
                driver.get(self.url)
                aconfig.login(driver)
                
                wait = WebDriverWait(driver, 20)
                wait.until(lambda driver: driver.current_url != self.url)
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                time.sleep(7)
                
                if self.extract_job_info(driver):
                    return self.job_data  # job_dataを返す（PDF生成は行わない）
                return None
                
            except Exception as e:
                logger.error(f"処理中にエラーが発生しました: {e}")
                return None

class NumberedCanvas(Canvas):
    """全ページにロゴを描画するためのカスタムキャンバス"""
    def __init__(self, *args, **kwargs):
        self.logo_path = kwargs.pop('logo_path', None)
        Canvas.__init__(self, *args, **kwargs)
        self.pages = []

    def showPage(self):
        """ページ描画完了時に呼ばれる"""
        self.pages.append(dict(self.__dict__))
        self._drawLogo()
        Canvas.showPage(self)

    def save(self):
        """PDFの保存時に呼ばれる"""
        Canvas.save(self)

    def _drawLogo(self):
        """ロゴを描画する"""
        try:
            logo = ImageReader(self.logo_path)
            logo_width = 25 * mm
            logo_height = logo_width * 0.3
            
            x = self._pagesize[0] - logo_width - 15
            y = self._pagesize[1] - logo_height - 10
            
            self.setFillColor(colors.white)
            self.setStrokeColor(colors.white)
            self.rect(x, y, logo_width, logo_height, fill=1, stroke=0)
            
            self.drawImage(
                self.logo_path,
                x, y,
                width=logo_width,
                height=logo_height,
                preserveAspectRatio=True,
                mask='auto'
            )
            logger.info(f"ロゴを配置しました")
        except Exception as e:
            logger.error(f"ロゴの描画中にエラーが発生しました: {e}")

def get_urls_interactively():
    """ユーザーから対話的にURLを取得する"""
    urls = []
    print("\n=== 求人情報URLの入力 ===")
    print("URLを1行ずつ入力してください。")
    print("入力を終了する場合は、空行のまま Enter を押してください。")
    
    while True:
        url = input("\n求人情報のURL（終了は空行）: ").strip()
        if not url:
            if not urls:
                print("少なくとも1つのURLを入力してください。")
                continue
            break
        
        if url.startswith('https://agent-navigation.jp/job/'):
            urls.append(url)
        else:
            print("無効なURLです。'https://agent-navigation.jp/job/' で始まるURLを入力してください。")
    
    return urls

def generate_combined_pdf(all_job_data):
    try:
        # 日本語フォントの設定
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
        
        # 出力ディレクトリの作成
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        
        # PDFファイル名の設定
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = os.path.join(output_dir, f"求人情報一覧_{timestamp}.pdf")

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
        
        # 会社名用スタイル（サイズアップ、太字）
        styles.add(ParagraphStyle(
            name='CompanyTitle',
            fontName='HeiseiKakuGo-W5',
            fontSize=16,  # 14から16に
            leading=18,
            spaceAfter=20,
            textColor=colors.black,
            bulletIndent=0,
            leftIndent=0,
            bold=True  # 太字を追加
        ))
        
        # ポジション名用スタイル（太字）
        styles.add(ParagraphStyle(
            name='PositionTitle',
            fontName='HeiseiKakuGo-W5',
            fontSize=14,
            leading=16,
            spaceAfter=20,
            textColor=colors.black,
            bulletIndent=0,
            leftIndent=0,
            bold=True  # 太字を追加
        ))
        
        # 見出しスタイル（太字）
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
            bold=True  # 太字を追加
        ))
        
        # 本文スタイル（既存）
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
        
        # 各求人情報をPDFに追加
        for i, job_data in enumerate(all_job_data):
            if i > 0:
                elements.append(PageBreak())
            
            # 会社名を追加（CompanyTitleスタイルを使用）
            if '会社情報' in job_data:
                elements.append(Paragraph(
                    job_data['会社情報'],
                    styles['CompanyTitle']  # 新しいスタイルを適用
                ))
            
            # 職種名を追加（PositionTitleスタイルを使用）
            if '職種名' in job_data:
                elements.append(Paragraph(
                    job_data['職種名'],
                    styles['PositionTitle']  # 新しいスタイルを適用
                ))

            # その他の情報を追加
            display_order = [
                '職務内容', '雇用形態', '業種', '職種', '勤務地', 
                '就業時間', '社会保険', '制度・福利厚生', '試用期間',
                '休日', '給与', '手当', '必要なスキル・経験',
                '年齢', '学歴', '選考'
            ]

            for key in display_order:
                if key in job_data and job_data[key]:
                    # 見出し（背景色付き）
                    elements.append(Paragraph(
                        f"■{key}",
                        styles['CustomHeading']
                    ))
                    
                    # 改行を保持して本文を表示
                    content = str(job_data[key]).replace('\n', '<br/>')
                    elements.append(Paragraph(
                        content,
                        styles['CustomNormal']
                    ))
            
            logger.info(f"求人情報 {i+1} を追加しました")

        # PDFの生成
        current_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(current_dir, "images", "logo.png")
        
        def make_canvas(*args, **kwargs):
            return NumberedCanvas(*args, logo_path=logo_path, **kwargs)
        
        doc.build(elements, canvasmaker=make_canvas)
        logger.info(f"PDFを作成しました: {pdf_filename}")
        
        return pdf_filename

    except Exception as e:
        logger.error(f"PDF生成中にエラーが発生しました: {e}")
        raise

def process_urls(urls):
    """複数のURLを処理する"""
    all_job_data = []
    total = len(urls)
    
    for i, url in enumerate(urls, 1):
        try:
            print(f"\n処理中 ({i}/{total}): {url}")
            scraper = WebScraper(url)
            job_data = scraper.run()
            if job_data:
                all_job_data.append(job_data)
                print(f"情報取得完了: {url}")
            else:
                print(f"情報取得失敗: {url}")
        except Exception as e:
            print(f"エラー ({url}): {e}")
            continue

    if all_job_data:
        print("\nPDFを生成中...")
        pdf_file = generate_combined_pdf(all_job_data)
        print(f"PDFを生成しました: {pdf_file}")
    else:
        print("有効な求人情報が取得できませんでした。")

def main():
    # コマンドライン引数のパーサーを設定
    parser = argparse.ArgumentParser(description='求人情報をPDFに変換するツール')
    parser.add_argument(
        'urls', 
        nargs='*', 
        help='求人情報のURL（複数指定可）'
    )
    parser.add_argument(
        '-i', 
        '--interactive', 
        action='store_true',
        help='対話モードで実行'
    )
    
    args = parser.parse_args()
    
    # URLの取得
    if args.interactive or not args.urls:
        # 対話モードが指定されているか、URLが指定されていない場合
        urls = get_urls_interactively()
    else:
        # コマンドライン引数からURLを取得
        urls = [url for url in args.urls if url.startswith('https://agent-navigation.jp/job/')]
        if not urls:
            print("有効なURLが指定されていません。")
            sys.exit(1)
    
    # 処理開始
    print(f"\n{len(urls)}件の求人情報を処理します...")
    process_urls(urls)
    print("\nすべての処理が完了しました。")

if __name__ == "__main__":
    main() 