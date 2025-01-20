from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import logging
import json
import time
import pass_info as pass_data

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AgentNaviScraper:
    def __init__(self):
        self.job_data = {}

    def login(self, driver):
        """ログイン処理"""
        try:
            logger.info("ログイン処理を開始します...")
            
            # 要素を待機して取得
            wait = WebDriverWait(driver, 20)
            
            # メールアドレス入力
            email_field = wait.until(
                EC.presence_of_element_located((By.ID, 'inputEmail'))
            )
            email_field.clear()
            email_field.send_keys(pass_data.LOGIN_EMAIL)
            
            # パスワード入力
            password_field = wait.until(
                EC.presence_of_element_located((By.ID, 'inputPassword'))
            )
            password_field.clear()
            password_field.send_keys(pass_data.LOGIN_PASSWORD)
            
            # ログインボタンクリック
            login_button = wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, 'button.btn.btn-primary.btn-block')
                )
            )
            logger.info("ログインボタンをクリックします...")
            login_button.click()
            
            time.sleep(3)  # ログイン後の待機
            
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
                # "※媒体掲載NG" という文言を削除
                title = title.replace("※媒体掲載NG", "").strip()
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

def main():
    # WebDriverの初期化
    driver = webdriver.Chrome()
    
    try:
        scraper = AgentNaviScraper()
        
        # まず求人詳細ページにアクセス
        url = "https://agent-navigation.jp/job/29653"
        logger.info(f"求人ページにアクセス: {url}")
        driver.get(url)
        
        # ログイン処理
        if not scraper.login(driver):
            logger.error("ログインに失敗しました")
            return
        
        # スクレイピング実行
        success = scraper.extract_job_info(driver)
        
        if success:
            # 結果を確認するためにJSONとして保存
            with open('agent_navi_data.json', 'w', encoding='utf-8') as f:
                json.dump(scraper.job_data, f, ensure_ascii=False, indent=2)
            logger.info("データをagent_navi_data.jsonに保存しました")
        
    except Exception as e:
        logger.error(f"実行中にエラーが発生: {e}")
    
    finally:
        driver.quit()

if __name__ == "__main__":
    main() 