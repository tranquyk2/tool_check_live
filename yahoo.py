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
from selenium.common.exceptions import TimeoutException, WebDriverException
import undetected_chromedriver as uc
from fake_useragent import UserAgent

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MicrosoftEmailChecker:
    def __init__(self, headless=True, use_proxy=False, proxy=None):
        self.headless = headless
        self.use_proxy = use_proxy
        self.proxy = proxy
        self.results = []
        self.die_emails = []  # New list to track only DIE emails
        self.output_file = None
        self.die_output_file = None  # New file to store only DIE emails
        self.ua = UserAgent()
        logger.warning("Automated email checking may violate Microsoft's Terms of Service. Use responsibly.")

    def select_input_file(self):
        """Open dialog to select txt file containing emails"""
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(
            title="Select file with email list",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        root.destroy()
        return file_path

    def read_emails(self, file_path):
        """Read email list from txt file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                emails = [line.strip() for line in file if line.strip()]
            return emails
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            return []

    def save_results(self):
        """Save all results to a file and DIE emails to a separate file"""
        try:
            os.makedirs(os.path.dirname(self.output_file) or '.', exist_ok=True)
            
            # Save only DIE emails to the dedicated file
            with open(self.die_output_file, 'w', encoding='utf-8') as file:
                for email in self.die_emails:
                    # Extract just the email address without the DIE status
                    clean_email = email.split(":")[0].strip()
                    file.write(clean_email + '\n')
            logger.info(f"DIE emails saved to {self.die_output_file}")
            
            # Save all results to the original file (for reference)
            with open(self.output_file, 'w', encoding='utf-8') as file:
                for result in self.results:
                    file.write(result + '\n')
            logger.info(f"All results saved to {self.output_file}")
                        
        except IOError as e:
            logger.error(f"Error writing to output files: {str(e)}")
            raise

    def optimized_delay(self, min_sec=0.1, max_sec=1.5):
        """Reduced delay time to increase speed"""
        time.sleep(random.uniform(min_sec, max_sec))

    def setup_driver(self):
        """Setup driver with speed optimizations"""
        chrome_options = uc.ChromeOptions()
        
        if self.headless:
            chrome_options.add_argument('--headless=new')
        
        # Performance optimizations
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
        
        # Random user agent
        user_agent = self.ua.random
        chrome_options.add_argument(f'user-agent={user_agent}')
        
        # Add proxy if specified
        if self.use_proxy and self.proxy:
            chrome_options.add_argument(f'--proxy-server={self.proxy}')
        
        try:
            driver = uc.Chrome(
                options=chrome_options,
                use_subprocess=True,
                suppress_welcome=True
            )
            
            # Execute script to hide automation
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                    Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                    window.navigator.chrome = { runtime: {}, app: { isInstalled: false } };
                '''
            })
            
            # Set fixed window size for consistent results
            driver.set_window_size(1200, 800)
            
            logger.info(f"Created driver with user-agent: {user_agent}")
            return driver
        
        except Exception as e:
            logger.error(f"Failed to create undetected_chromedriver: {str(e)}")
            raise

    def fast_input(self, element, text):
        """Fast input with minimal random delay"""
        element.clear()
        self.optimized_delay(0.05, 0.2)
        element.send_keys(text)
        self.optimized_delay(0.1, 0.5)

    def quick_click(self, driver, element):
        """Fast click with minimal checks"""
        try:
            driver.execute_script("arguments[0].click();", element)
        except:
            try:
                element.click()
            except Exception as e:
                logger.error(f"Click failed: {str(e)}")
                raise

    def check_microsoft_account(self, email, driver):
        """Fast version of Microsoft account checking with improved detection"""
        initial_url = "https://login.microsoftonline.com/"
        
        try:
            # Access page with short delay
            self.optimized_delay(0.5, 1.5)
            driver.get(initial_url)
            
            try:
                # Reduced wait time
                email_input = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.NAME, "loginfmt"))
                )
            except TimeoutException:
                return f"{email}: ERROR - Cannot load login page"

            # Fast email input
            self.fast_input(email_input, email)
            
            try:
                # Find and click Next button
                next_button = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.ID, "idSIButton9"))
                )
                self.quick_click(driver, next_button)
            except TimeoutException:
                logger.error(f"Next button not found for {email}")
                return f"{email}: ERROR - Cannot find next button"

            # Short wait for result
            self.optimized_delay(2, 4)
            
            page_source = driver.page_source
            current_url = driver.current_url
            
            # Check for password input - indicates LIVE account
            try:
                password_input = driver.find_element(By.NAME, "passwd")
                if password_input.is_displayed():
                    return f"{email}: LIVE - Account exists"
            except:
                pass
                
            # Check for specific URLs that indicate a LIVE account
            if "login.live.com/ppsecure" in current_url or "login.microsoftonline.com/common/SAS" in current_url:
                return f"{email}: LIVE - Account exists"
                
            # Fast result checking for DIE accounts
            error_texts = [
                "Chúng tôi không tìm được tài khoản có tên người dùng đó", 
                "We couldn't find an account with that username",
                "No account found with that username",
                "tài khoản có tên người dùng đó",
                "Hãy thử dùng một tên người dùng khác",
                "không tìm được",
                "không tìm thấy",
                "couldn't find",
                "can't find",
                "doesn't exist"
            ]
            
            if any(text.lower() in page_source.lower() for text in error_texts):
                return f"{email}: DIE - Account not found"
            
            # If we remain on the same page with the email input field still visible
            try:
                error_element = driver.find_element(By.ID, "usernameError")
                if error_element.is_displayed():
                    return f"{email}: DIE - Account not found"
            except:
                pass
                
            try:
                # If we're still on the email input page after clicking Next, account likely doesn't exist
                email_input = driver.find_element(By.NAME, "loginfmt")
                if email_input.is_displayed():
                    return f"{email}: DIE - Account not found"
            except:
                pass
            
            # Final check for account existence - if URL changed but we didn't match any patterns above
            if initial_url != current_url and not any(text.lower() in page_source.lower() for text in ["password", "mật khẩu"]):
                return f"{email}: DIE - Account not found (URL changed)"
                
            # If we get here and URL has changed or contains "IfExistsResult", account likely exists
            if "IfExistsResult" in current_url:
                return f"{email}: LIVE - Account exists"
                
            # Last resort - check if any password-related elements or text exist on the page
            if any(text.lower() in page_source.lower() for text in ["password", "passwd", "mật khẩu"]):
                return f"{email}: LIVE - Account exists (password prompt)"
                
            # Default to DIE if we couldn't definitively determine it's LIVE
            return f"{email}: DIE - Account not found (default case)"

        except Exception as e:
            logger.error(f"Error checking {email}: {str(e)}")
            return f"{email}: ERROR - {str(e)}"

    def run(self, batch_size=20, delay_between_batches=30):
        """Run email checker with high speed"""
        input_file = self.select_input_file()
        if not input_file:
            logger.error("No file selected. Exiting.")
            return

        output_dir = os.path.dirname(input_file) or '.'
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.output_file = os.path.join(output_dir, f"microsoft_results_{timestamp}.txt")
        self.die_output_file = os.path.join(output_dir, f"microsoft_die_emails_{timestamp}.txt")

        emails = self.read_emails(input_file)
        if not emails:
            logger.error("No emails to check.")
            return

        driver = None
        try:
            driver = self.setup_driver()
            total_emails = len(emails)
            
            for i, email in enumerate(emails, 1):
                result = self.check_microsoft_account(email, driver)
                self.results.append(result)
                
                # Check if this is a DIE email and add to die_emails list if so
                if "DIE" in result:
                    self.die_emails.append(result)
                
                logger.info(f"[{i}/{total_emails}] {result}")
                
                # Rest after each batch
                if i % batch_size == 0:
                    logger.info(f"Completed {i} emails. Taking a short break...")
                    time.sleep(delay_between_batches)
                else:
                    self.optimized_delay(0.5, 2)  # Very short delay between emails

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
        
        # Log counts
        total_checked = len(self.results)
        die_count = len(self.die_emails)
        
        logger.info(f"Total emails checked: {total_checked}")
        logger.info(f"DIE emails found: {die_count}")
        logger.info(f"DIE emails saved to {self.die_output_file}")

        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo("Completed", 
                           f"Checked {total_checked} emails.\n"
                           f"Found {die_count} DIE emails.\n"
                           f"DIE emails saved at:\n{self.die_output_file}\n"
                           f"All results saved at:\n{self.output_file}")
        root.destroy()

if __name__ == "__main__":
    # Use headless mode by default for speed
    checker = MicrosoftEmailChecker(headless=True)
    checker.run(batch_size=30, delay_between_batches=20)  # Adjustable parameters