from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import logging
import json
import time

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class JobScraper:
    def __init__(self):
        self.job_data = {}

    def login(self, driver, username, password):
        """ログイン処理"""
        try:
            # ログインページにアクセス
            driver.get("https://jobsearch.w3hr.jp/login/")
            
            # ユーザー名とパスワードを入力
            username_input = driver.find_element(By.NAME, "username")
            password_input = driver.find_element(By.NAME, "password")
            
            username_input.send_keys(username)
            password_input.send_keys(password)
            
            # ログインボタンをクリック
            login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            
            # ログイン後のページ読み込みを待機
            time.sleep(3)  # 必要に応じて調整
            
            logger.info("ログインに成功しました")
            return True
            
        except Exception as e:
            logger.error(f"ログイン中にエラーが発生: {e}")
            return False

    def extract_job_info(self, driver):
        """求人情報を抽出する"""
        try:
            # ページの読み込みを待機
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.text-gray-500"))
            )

            # 基本情報の取得
            try:
                company_row = driver.find_element(
                    By.XPATH, "//tr[.//th[contains(text(), '企業名')]]"
                )
                position_row = driver.find_element(
                    By.XPATH, "//tr[.//th[contains(text(), 'ポジション')]]"
                )

                self.job_data["企業名"] = company_row.find_element(By.TAG_NAME, "td").text.strip()
                self.job_data["ポジション"] = position_row.find_element(By.TAG_NAME, "td").text.strip()

            except Exception as e:
                logger.warning(f"基本情報の取得に失敗: {e}")

            # 詳細情報の取得
            rows = driver.find_elements(By.CSS_SELECTOR, "table.text-gray-500 tr")
            for row in rows:
                try:
                    header = row.find_element(By.TAG_NAME, "th").text.strip()
                    try:
                        value = row.find_element(By.TAG_NAME, "pre").text.strip()
                    except NoSuchElementException:
                        value = row.find_element(By.TAG_NAME, "td").text.strip()
                    
                    if header and value:
                        self.job_data[header] = value
                except Exception as e:
                    logger.warning(f"項目の取得に失敗: {e}")
                    continue

            logger.info("求人情報の抽出が完了しました")
            logger.info(f"取得した項目: {list(self.job_data.keys())}")
            return True

        except Exception as e:
            logger.error(f"求人情報の抽出中にエラーが発生しました: {e}")
            return False

def main():
    # WebDriverの初期化
    driver = webdriver.Chrome()  # または他のブラウザドライバー
    
    try:
        scraper = JobScraper()
        
        # ログイン処理
        if not scraper.login(driver, "yoshinaga.hibiki@r-value.jp", ""):
            logger.error("ログインに失敗しました")
            return
        
        # 求人詳細ページにアクセス
        job_id = "33444"  # テスト用の求人ID
        url = f"https://jobsearch.w3hr.jp/detail/?job_id={job_id}"
        driver.get(url)
        
        # スクレイピング実行
        success = scraper.extract_job_info(driver)
        
        if success:
            # 結果を確認するためにJSONとして保存
            with open('job_data.json', 'w', encoding='utf-8') as f:
                json.dump(scraper.job_data, f, ensure_ascii=False, indent=2)
            logger.info("データをjob_data.jsonに保存しました")
        
    except Exception as e:
        logger.error(f"実行中にエラーが発生: {e}")
    
    finally:
        driver.quit()

if __name__ == "__main__":
    main()