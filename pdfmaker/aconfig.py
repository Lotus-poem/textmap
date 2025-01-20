from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging
import pass_info as pass_data
import time

# ロギングの設定
logger = logging.getLogger(__name__)

class LoginError(Exception):
    """ログイン処理に関するカスタム例外"""
    pass

def login_agent_navi(driver):
    """
    agent-navigation用のログイン処理を実行する関数
    
    Args:
        driver: Seleniumのwebdriverインスタンス
    
    Raises:
        LoginError: ログイン処理に失敗した場合
    """
    try:
        logger.info("agent-navigationにログイン中...")
        
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
        
        logger.info("agent-navigationのログインに成功しました")
        
    except Exception as e:
        logger.error(f"agent-navigationのログイン処理中にエラーが発生しました: {e}")
        raise LoginError(f"ログインに失敗しました: {str(e)}")

def login_w3hr(driver):
    """
    W3HR用のログイン処理を実行する関数
    """
    try:
        logger.info("W3HRにログイン中...")
        
        # ログインページに直接アクセス
        driver.get("https://jobsearch.w3hr.jp/login/")
        
        # メールアドレス入力
        username_input = driver.find_element(By.NAME, "username")
        username_input.clear()
        username_input.send_keys(pass_data.W3HR_LOGIN_EMAIL)
        
        # パスワード入力
        password_input = driver.find_element(By.NAME, "password")
        password_input.clear()
        password_input.send_keys(pass_data.W3HR_LOGIN_PASSWORD)
        
        # ログインボタンクリック
        login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        logger.info("ログインボタンをクリックします...")
        login_button.click()
        
        # ログイン後の待機
        time.sleep(3)
        
        logger.info("W3HRのログインに成功しました")
        
    except Exception as e:
        logger.error(f"W3HRのログイン処理中にエラーが発生しました: {e}")
        raise LoginError(f"ログインに失敗しました: {str(e)}")

# 後方互換性のために残す
def login(driver):
    """
    既存のログイン処理（agent-navigation用）
    """
    return login_agent_navi(driver) 