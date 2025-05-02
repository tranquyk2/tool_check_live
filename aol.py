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
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
import undetected_chromedriver as uc
from fake_useragent import UserAgent
import requests
from threading import Lock
import json

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProxyManager:
    def __init__(self):
        self.proxy_list = []
        self.current_proxy_index = 0
        self.lock = Lock()
        self.last_proxy_refresh = 0
        self.proxy_refresh_interval = 3600  # 1 hour
        
    def get_free_proxies(self):
        """Fetch fresh proxies from free sources"""
        try:
            # Get proxies from multiple free sources
            sources = [
                "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
                "https://www.proxy-list.download/api/v1/get?type=http",
                "https://api.proxyscrape.com/?request=displayproxies&protocol=http"
            ]
            
            proxies = set()
            for url in sources:
                try:
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        proxies.update(response.text.splitlines())
                except:
                    continue
            
            return list(proxies)
        except Exception as e:
            logger.error(f"Error fetching proxies: {str(e)}")
            return []
    
    def refresh_proxies_if_needed(self):
        """Refresh proxy list if empty or stale"""
        current_time = time.time()
        if not self.proxy_list or (current_time - self.last_proxy_refresh) > self.proxy_refresh_interval:
            with self.lock:
                if not self.proxy_list or (current_time - self.last_proxy_refresh) > self.proxy_refresh_interval:
                    logger.info("Refreshing proxy list...")
                    self.proxy_list = self.get_free_proxies()
                    self.current_proxy_index = 0
                    self.last_proxy_refresh = current_time
                    logger.info(f"Got {len(self.proxy_list)} fresh proxies")
    
    def get_next_proxy(self):
        """Get next available proxy with rotation"""
        self.refresh_proxies_if_needed()
        
        with self.lock:
            if not self.proxy_list:
                return None
            
            proxy = self.proxy_list[self.current_proxy_index]
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_list)
            return proxy

class AOLEmailChecker:
    def __init__(self, headless=True, use_proxy=True):
        self.headless = headless
        self.use_proxy = use_proxy
        self.proxy_manager = ProxyManager() if use_proxy else None
        self.results = []
        self.die_emails = []
        self.output_file = None
        self.die_output_file = None
        self.ua = UserAgent()
        self.driver = None
        self.last_driver_creation = 0
        self.driver_refresh_interval = 300  # 5 minutes
        logger.warning("Automated email checking may violate AOL's Terms of Service. Use responsibly.")

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
        """Save only DIE emails to file"""
        try:
            os.makedirs(os.path.dirname(self.die_output_file) or '.', exist_ok=True)
            
            # Save DIE emails (clean format)
            with open(self.die_output_file, 'w', encoding='utf-8') as file:
                for email in self.die_emails:
                    clean_email = email.split(":")[0].strip()
                    file.write(clean_email + '\n')
            logger.info(f"DIE emails saved to {self.die_output_file}")
            
            # Save all results with status (for reference)
            with open(self.output_file, 'w', encoding='utf-8') as file:
                for result in self.results:
                    file.write(result + '\n')
                        
        except IOError as e:
            logger.error(f"Error writing to output files: {str(e)}")
            raise

    def optimized_delay(self, min_sec=0.05, max_sec=0.3):
        """Minimal random delay time for faster checking"""
        time.sleep(random.uniform(min_sec, max_sec))

    def setup_driver(self, proxy=None):
        """Setup driver with anti-detection measures and optional proxy"""
        # Refresh driver if it's been used for too long
        current_time = time.time()
        if self.driver and (current_time - self.last_driver_creation) > self.driver_refresh_interval:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
        
        if self.driver:
            return self.driver
        
        chrome_options = uc.ChromeOptions()
        
        if self.headless:
            chrome_options.add_argument('--headless=new')
        
        # Enhanced anti-detection measures
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--disable-infobars')
        chrome_options.add_argument('--disable-notifications')
        chrome_options.add_argument('--disable-popup-blocking')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--log-level=3')
        chrome_options.add_argument('--silent')
        chrome_options.add_argument('--lang=vi-VN,vi,en-US,en')
        
        # Randomize various browser parameters
        chrome_options.add_argument(f'--window-size={random.randint(1000,1400)},{random.randint(700,900)}')
        
        # Add proxy if specified
        if proxy:
            chrome_options.add_argument(f'--proxy-server={proxy}')
        
        try:
            # Random user agent to mimic real browser
            user_agent = self.ua.random
            chrome_options.add_argument(f'user-agent={user_agent}')
            
            # Create driver with randomized options
            driver = uc.Chrome(
                options=chrome_options,
                use_subprocess=True,
                suppress_welcome=True
            )
            
            # Enhanced script to hide automation markers
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5],
                        enumerable: true
                    });
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['vi-VN', 'vi', 'en-US', 'en'],
                        enumerable: true
                    });
                    window.navigator.chrome = {
                        runtime: {},
                        app: { isInstalled: false },
                        webstore: { onInstallStageChanged: {}, onDownloadProgress: {} }
                    };
                    window.chrome = {
                        runtime: {},
                        app: { isInstalled: false },
                        webstore: { onInstallStageChanged: {}, onDownloadProgress: {} }
                    };
                    Object.defineProperty(navigator, 'platform', {
                        get: () => 'Win32',
                        enumerable: true
                    });
                    Object.defineProperty(navigator, 'hardwareConcurrency', {
                        get: () => 4,
                        enumerable: true
                    });
                '''
            })
            
            # Set random viewport size
            driver.set_window_size(
                random.randint(1000, 1400),
                random.randint(700, 900)
            )
            
            # Randomize timezone
            driver.execute_cdp_cmd('Emulation.setTimezoneOverride', {
                'timezoneId': random.choice(['America/New_York', 'Europe/London', 'Asia/Ho_Chi_Minh'])
            })
            
            # Randomize geolocation
            driver.execute_cdp_cmd('Emulation.setGeolocationOverride', {
                'latitude': random.uniform(-90, 90),
                'longitude': random.uniform(-180, 180),
                'accuracy': random.uniform(1, 100)
            })
            
            logger.info(f"Created driver with user-agent: {user_agent}")
            self.last_driver_creation = time.time()
            self.driver = driver
            return driver
        
        except Exception as e:
            logger.error(f"Failed to create undetected_chromedriver: {str(e)}")
            raise

    def fast_input(self, element, text, clear_first=True):
        """Fast input with minimal random delay and human-like typing"""
        if clear_first:
            element.clear()
        
        # Simulate human typing with random delays between characters
        for char in text:
            element.send_keys(char)
            self.optimized_delay(0.02, 0.1)  # Very short delay between chars
        
        self.optimized_delay(0.3, 0.7)  # Final delay after typing

    def quick_click(self, driver, element):
        """Human-like click with random delay before and after"""
        self.optimized_delay(0.2, 0.5)  # Delay before click
        try:
            driver.execute_script("arguments[0].click();", element)
        except:
            try:
                element.click()
            except Exception as e:
                logger.error(f"Click failed: {str(e)}")
                raise
        self.optimized_delay(0.2, 0.5)  # Delay after click

    def rotate_proxy_and_restart(self):
        """Rotate to next proxy and restart driver"""
        if not self.use_proxy:
            return
            
        proxy = self.proxy_manager.get_next_proxy()
        if proxy:
            logger.info(f"Rotating to new proxy: {proxy}")
            try:
                if self.driver:
                    self.driver.quit()
                self.driver = None
                return self.setup_driver(proxy=proxy)
            except Exception as e:
                logger.error(f"Failed to rotate proxy: {str(e)}")
                return None
        return None

    def check_aol_account(self, email, driver):
        """Check if an AOL account exists using sign-in form with enhanced detection avoidance"""
        # Direct AOL login URL
        login_url = "https://login.aol.com/"
        
        try:
            # Clear cookies and cache before checking each email
            driver.delete_all_cookies()
            
            # Access page with random delay
            self.optimized_delay(0.5, 1.5)
            driver.get(login_url)
            
            # Random wait before interacting
            self.optimized_delay(0.5, 1.0)
            
            # Wait for email input field with multiple fallbacks
            try:
                email_input = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.ID, "login-username"))
                )
            except TimeoutException:
                # Try alternative selectors
                try:
                    email_input = driver.find_element(By.CSS_SELECTOR, "input[name='username']")
                except NoSuchElementException:
                    try:
                        email_input = driver.find_element(By.CSS_SELECTOR, "input[type='email']")
                    except NoSuchElementException:
                        return f"{email}: ERROR (No input field)"

            # Enter email address with human-like typing
            self.fast_input(email_input, email)
            
            # Find and click Next/Continue button
            try:
                next_button = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.ID, "login-signin"))
                )
                self.quick_click(driver, next_button)
            except TimeoutException:
                try:
                    next_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                    self.quick_click(driver, next_button)
                except:
                    return f"{email}: ERROR (No submit button)"

            # Wait for response with dynamic timeout based on page load
            start_time = time.time()
            while time.time() - start_time < 5:  # Max 5 seconds wait
                current_url = driver.current_url
                if current_url != login_url:
                    break
                time.sleep(0.1)
            
            # Get current URL and page source after submission
            current_url = driver.current_url
            page_source = driver.page_source
            
            # ======= ENHANCED DETECTION LOGIC =======
            
            # 1. First check for DIE account error messages (optimized list)
            error_texts_die = [
                "Rất tiếc, chúng tôi không nhận ra email này",
                "không nhận dạng được",
                "don't recognize",
                "không nhận ra email",
                "Sorry, we don't recognize this email",
                "We can't find this AOL account"
            ]
            
            # Check for specific error element first
            try:
                error_element = driver.find_element(By.ID, "username-error")
                if error_element.is_displayed():
                    error_text = error_element.text
                    for text in error_texts_die:
                        if text.lower() in error_text.lower():
                            return f"{email}: DIE"
            except NoSuchElementException:
                pass

            # Look for error message in the page source as fallback
            for text in error_texts_die:
                if text.lower() in page_source.lower():
                    return f"{email}: DIE"
            
            # 2. Check for LIVE account indicators (quick checks)
            
            # Check for password field
            try:
                password_field = driver.find_element(By.ID, "login-passwd")
                if password_field.is_displayed():
                    return f"{email}: LIVE"
            except NoSuchElementException:
                pass
            
            # Check URL patterns that indicate LIVE account
            live_url_patterns = ["challenge/", "p=", ".pwd", "account/challenge"]
            for pattern in live_url_patterns:
                if pattern in current_url:
                    return f"{email}: LIVE"
            
            # Check if URL changed (sign of LIVE) or still on login page (DIE)
            if login_url == current_url or "challenge/username" in current_url:
                return f"{email}: DIE"
            else:
                return f"{email}: LIVE"

        except Exception as e:
            logger.error(f"Error checking {email}: {str(e)}")
            return f"{email}: ERROR"

    def run(self, batch_size=15, delay_between_batches=30):
        """Run email checker with proxy rotation and enhanced anti-detection"""
        input_file = self.select_input_file()
        if not input_file:
            logger.error("No file selected. Exiting.")
            return

        output_dir = os.path.dirname(input_file) or '.'
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.output_file = os.path.join(output_dir, f"aol_results_{timestamp}.txt")
        self.die_output_file = os.path.join(output_dir, f"aol_die_emails_{timestamp}.txt")

        emails = self.read_emails(input_file)
        if not emails:
            logger.error("No emails to check.")
            return

        try:
            total_emails = len(emails)
            start_time = time.time()
            last_proxy_rotation = 0
            proxy_rotation_interval = 30  # Rotate proxy every 30 emails
            
            # Initial driver setup
            proxy = self.proxy_manager.get_next_proxy() if self.use_proxy else None
            self.setup_driver(proxy=proxy)
            
            for i, email in enumerate(emails, 1):
                # Rotate proxy periodically
                if self.use_proxy and i % proxy_rotation_interval == 0:
                    if not self.rotate_proxy_and_restart():
                        logger.warning("Failed to rotate proxy, continuing with current")
                
                result = self.check_aol_account(email, self.driver)
                self.results.append(result)
                
                # Only track DIE emails
                if "DIE" in result:
                    self.die_emails.append(result)
                
                # Simplified logging
                print(f"[{i}/{total_emails}] {result}")
                
                # Calculate time per email
                if i % 10 == 0:
                    elapsed = time.time() - start_time
                    speed = elapsed / i
                    remaining = (total_emails - i) * speed
                    print(f"Speed: {speed:.2f} sec/email | Estimated remaining: {remaining/60:.1f} min")
                
                # Random delay between emails (0.5-1.5s average)
                delay = random.uniform(0.3, 1.7)
                time.sleep(delay)
                
                # Refresh driver periodically to avoid detection
                if i % 50 == 0:
                    try:
                        self.driver.quit()
                        self.driver = None
                        proxy = self.proxy_manager.get_next_proxy() if self.use_proxy else None
                        self.setup_driver(proxy=proxy)
                    except Exception as e:
                        logger.error(f"Error refreshing driver: {str(e)}")
                        continue

        except Exception as e:
            print(f"Error during execution: {str(e)}")
            # Save results already collected even if there's an error
            if self.results:
                self.save_results()
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                    print("Driver closed successfully")
                except Exception as e:
                    print(f"Error closing driver: {str(e)}")

        # Save final results
        if self.results:
            self.save_results()
        
        # Log counts
        total_checked = len(self.results)
        die_count = len(self.die_emails)
        
        print(f"\nSummary:")
        print(f"Total emails checked: {total_checked}")
        print(f"DIE emails found: {die_count}")
        print(f"DIE emails saved to {self.die_output_file}")

        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo("Completed", 
                           f"Checked {total_checked} AOL emails.\n"
                           f"Found {die_count} DIE emails.\n"
                           f"DIE emails saved at:\n{self.die_output_file}")
        root.destroy()

if __name__ == "__main__":
    # Run with proxy rotation and optimized settings
    checker = AOLEmailChecker(headless=True, use_proxy=True)
    checker.run(batch_size=15, delay_between_batches=30)