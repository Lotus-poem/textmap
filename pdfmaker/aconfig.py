from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging
import pass_info as pass_data

# ロギングの設定
logger = logging.getLogger(__name__)

class LoginError(Exception):
    """ログイン処理に関するカスタム例外"""
    pass

def login(driver):
    """
    ログイン処理を実行する関数
    
    Args:
        driver: Seleniumのwebdriverインスタンス
    
    Raises:
        LoginError: ログイン処理に失敗した場合
    """
    try:
        logger.info("ログイン情報を入力中...")
        
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
        
        logger.info("ログインに成功しました")
        
    except Exception as e:
        logger.error(f"ログイン処理中にエラーが発生しました: {e}")
        raise LoginError(f"ログインに失敗しました: {str(e)}") 