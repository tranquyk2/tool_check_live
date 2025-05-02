import time
import random
import logging
import tkinter as tk
from tkinter import filedialog, messagebox
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, WebDriverException
import undetected_chromedriver as uc
from fake_useragent import UserAgent

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FastEmailChecker:
    def __init__(self, headless=True, use_proxy=False, proxy=None):
        self.headless = headless
        self.use_proxy = use_proxy
        self.proxy = proxy
        self.results = []
        self.output_file = None
        self.ua = UserAgent()
        logger.warning("Automated email checking may violate Facebook's Terms of Service. Use responsibly.")

    def select_input_file(self):
        """Mở hộp thoại để chọn file txt chứa email"""
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(
            title="Chọn file chứa danh sách email",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        root.destroy()
        return file_path

    def read_emails(self, file_path):
        """Đọc danh sách email từ file txt"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                emails = [line.strip() for line in file if line.strip()]
            return emails
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            return []

    def save_results(self):
        """Lưu kết quả vào file"""
        try:
            os.makedirs(os.path.dirname(self.output_file) or '.', exist_ok=True)
            with open(self.output_file, 'w', encoding='utf-8') as file:
                for result in self.results:
                    file.write(result + '\n')
        except IOError as e:
            logger.error(f"Error writing to output file {self.output_file}: {str(e)}")
            raise

    def optimized_delay(self, min_sec=0.1, max_sec=1.5):
        """Giảm thời gian delay để tăng tốc độ"""
        time.sleep(random.uniform(min_sec, max_sec))

    def setup_driver(self):
        """Thiết lập driver với các tối ưu tốc độ"""
        chrome_options = uc.ChromeOptions()
        
        if self.headless:
            chrome_options.add_argument('--headless=new')
        
        # Tối ưu hiệu suất và giảm tải
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--disable-infobars')
        chrome_options.add_argument('--disable-notifications')
        chrome_options.add_argument('--disable-popup-blocking')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--allow-running-insecure-content')
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--log-level=3')
        chrome_options.add_argument('--silent')
        
        # User agent ngẫu nhiên
        user_agent = self.ua.random
        chrome_options.add_argument(f'user-agent={user_agent}')
        
        # Thêm proxy nếu được chỉ định
        if self.use_proxy and self.proxy:
            chrome_options.add_argument(f'--proxy-server={self.proxy}')
        
        try:
            driver = uc.Chrome(
                options=chrome_options,
                use_subprocess=True,
                suppress_welcome=True
            )
            
            # Thực thi script để ẩn automation
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                    Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                    window.navigator.chrome = { runtime: {}, app: { isInstalled: false } };
                '''
            })
            
            # Đặt kích thước cửa sổ cố định để tăng tốc
            driver.set_window_size(1200, 800)
            
            logger.info(f"Created driver with user-agent: {user_agent}")
            return driver
        
        except Exception as e:
            logger.error(f"Failed to create undetected_chromedriver: {str(e)}")
            raise

    def fast_input(self, element, text):
        """Nhập text nhanh nhưng vẫn có độ trễ ngẫu nhiên nhỏ"""
        element.clear()
        # Nhập toàn bộ text cùng lúc nhưng có delay ngắn
        self.optimized_delay(0.05, 0.2)
        element.send_keys(text)
        self.optimized_delay(0.1, 0.5)

    def quick_click(self, driver, element):
        """Click nhanh với ít kiểm tra hơn"""
        try:
            driver.execute_script("arguments[0].click();", element)
        except:
            try:
                element.click()
            except Exception as e:
                logger.error(f"Click failed: {str(e)}")
                raise

    def check_facebook_account(self, email, driver):
        """Phiên bản kiểm tra nhanh"""
        initial_url = "https://www.facebook.com/login/identify/?ctx=recover"
        
        try:
            # Truy cập trang với delay ngắn
            self.optimized_delay(0.5, 1.5)
            driver.get(initial_url)
            
            try:
                # Giảm thời gian chờ xuống
                email_input = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.ID, "identify_email"))
                )
            except TimeoutException:
                return f"Email {email}: Không thể tải trang quên mật khẩu"

            # Nhập email nhanh
            self.fast_input(email_input, email)
            
            try:
                search_button = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[name='did_submit'], button[type='submit']"))
                )
                self.quick_click(driver, search_button)
            except TimeoutException:
                logger.error(f"Search button not found for {email}")
                return f"Email {email}: Không thể tìm thấy nút tìm kiếm"

            # Giảm thời gian chờ kết quả
            self.optimized_delay(2, 4)
            
            page_source = driver.page_source
            current_url = driver.current_url

            # Kiểm tra kết quả nhanh
            no_results_texts = [
                "Không tìm thấy kết quả nào",
                "No search results",
                "We couldn't find any matches"
            ]
            
            if any(text in page_source for text in no_results_texts):
                return f"Email {email}: Không liên kết với Facebook"
            
            if current_url != initial_url or "recover/initiate" in current_url or "reset_action" in page_source:
                return f"Email {email}: Có liên kết với Facebook"
            
            return f"Email {email}: Không xác định được"

        except Exception as e:
            logger.error(f"Error checking {email}: {str(e)}")
            return f"Email {email}: Lỗi - {str(e)}"

    def run(self, batch_size=20, delay_between_batches=30):
        """Chạy kiểm tra email với tốc độ cao"""
        input_file = self.select_input_file()
        if not input_file:
            logger.error("No file selected. Exiting.")
            return

        output_dir = os.path.dirname(input_file) or '.'
        self.output_file = os.path.join(output_dir, f"fast_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

        emails = self.read_emails(input_file)
        if not emails:
            logger.error("No emails to check.")
            return

        driver = None
        try:
            driver = self.setup_driver()
            total_emails = len(emails)
            
            for i, email in enumerate(emails, 1):
                result = self.check_facebook_account(email, driver)
                self.results.append(result)
                logger.info(f"[{i}/{total_emails}] {result}")
                
                # Nghỉ ngơi sau mỗi batch email
                if i % batch_size == 0:
                    logger.info(f"Completed {i} emails. Taking a short break...")
                    time.sleep(delay_between_batches)
                else:
                    self.optimized_delay(0.5, 2)  # Delay rất ngắn giữa các email

        except Exception as e:
            logger.error(f"Error during execution: {str(e)}")
            raise
        finally:
            if driver:
                try:
                    driver.quit()
                    logger.info("Driver closed successfully")
                except Exception as e:
                    logger.error(f"Error closing driver: {str(e)}")

        self.save_results()
        logger.info(f"Results saved to {self.output_file}")

        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo("Completed", f"Checked {len(emails)} emails.\nResults saved at:\n{self.output_file}")
        root.destroy()

if __name__ == "__main__":
    # Sử dụng chế độ headless mặc định để tăng tốc độ
    checker = FastEmailChecker(headless=True)
    checker.run(batch_size=30, delay_between_batches=20)  # Có thể điều chỉnh tham số
    