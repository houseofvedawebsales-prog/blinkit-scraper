"""
scraper.py — Blinkit Selenium scraper
Extracted from fast.py and wrapped into run_scrape(keyword, pincode) -> List[dict]
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException, TimeoutException,
    ElementClickInterceptedException, StaleElementReferenceException
)
from time import sleep
import logging

logger = logging.getLogger("blinkit-scraper")


def _make_driver() -> webdriver.Chrome:
    """Create and return a configured Chrome driver."""
    opts = Options()
    opts.add_argument("--headless=new")           # headless for server deployment
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-web-security")
    opts.add_argument("--allow-running-insecure-content")
    opts.add_argument("--remote-debugging-port=0")
    opts.add_argument("--disable-blink-features=AutomationControlled")

    # Try webdriver-manager first, fall back to system chromedriver
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())
    except Exception:
        service = Service()   # expects chromedriver on PATH

    return webdriver.Chrome(service=service, options=opts)


def run_scrape(keyword: str, pincode: str) -> list:
    """
    Scrape Blinkit for `keyword` at delivery location `pincode`.
    Returns a list of up to 10 product dicts.
    """
    browser = None
    product_details = []

    try:
        browser = _make_driver()
        logger.info("Browser started.")

        browser.get("https://blinkit.com/")
        wait = WebDriverWait(browser, 15)
        logger.info("Loaded Blinkit homepage.")

        # ── 1. Enter PIN code ───────────────────────────────────
        logger.info(f"Entering PIN code: {pincode}")
        location_box = wait.until(
            EC.presence_of_element_located((By.XPATH, '//input[@placeholder="search delivery location"]'))
        )
        location_box.clear()
        location_box.send_keys(pincode)

        # ── 2. Select 2nd location suggestion ───────────────────
        logger.info("Selecting location suggestion...")
        location_container = wait.until(
            EC.element_to_be_clickable((By.XPATH, '(//div[contains(@class,"LocationSearchList__LocationDetailContainer")])[2]'))
        )
        location_container.click()

        # ── 3. Wait for overlay to dismiss ──────────────────────
        wait.until(EC.invisibility_of_element_located(
            (By.XPATH, '//div[contains(@class,"LocationDropDown__LocationOverlay") or contains(@class,"bLgtGp")]')
        ))
        sleep(3)
        try:
            browser.execute_script("document.querySelector('body').click();")
            sleep(1)
        except Exception:
            pass

        # ── 4. Open search bar ──────────────────────────────────
        logger.info("Opening search bar...")
        initial_search_wrapper = wait.until(
            EC.presence_of_element_located((By.XPATH, '//div[contains(@class,"SearchBar__AnimationWrapper")]'))
        )
        browser.execute_script("arguments[0].scrollIntoView({block:'center'});", initial_search_wrapper)
        sleep(1)
        for attempt in range(3):
            try:
                initial_search_wrapper.click()
                break
            except ElementClickInterceptedException:
                browser.execute_script("arguments[0].click();", initial_search_wrapper)
                break
            except Exception:
                sleep(1)
                initial_search_wrapper = browser.find_element(By.XPATH, '//div[contains(@class,"SearchBar__AnimationWrapper")]')
        sleep(1)

        # ── 5. Type keyword and search ──────────────────────────
        logger.info(f"Searching for '{keyword}'...")
        search_input = wait.until(
            EC.visibility_of_element_located((By.XPATH, '//input[contains(@class,"SearchBarContainer__Input")]'))
        )
        search_input.clear()
        search_input.send_keys(keyword)
        search_input.send_keys(Keys.ENTER)
        sleep(5)

        # ── 6. Wait for product cards ───────────────────────────
        CARD_XPATH = '//div[contains(@class,"categories-table")]//div[contains(@class,"tw-relative tw-flex tw-h-full tw-flex-col")]'
        wait.until(EC.presence_of_element_located((By.XPATH, CARD_XPATH)))
        all_cards = browser.find_elements(By.XPATH, CARD_XPATH)
        logger.info(f"Found {len(all_cards)} cards initially. Processing top 10...")

        # ── 7. Loop through top 10 ──────────────────────────────
        for rank in range(1, 11):
            logger.info(f"--- Processing Rank {rank} ---")

            current_card = None
            for retry in range(5):
                try:
                    current_card = wait.until(EC.presence_of_element_located(
                        (By.XPATH, f'({CARD_XPATH})[position()={rank}]')
                    ))
                    name_elem = current_card.find_element(By.XPATH, './/div[contains(@class,"tw-text-300 tw-font-semibold")]')
                    if name_elem and name_elem.text.strip():
                        break
                    raise NoSuchElementException("No valid name")
                except (TimeoutException, NoSuchElementException, StaleElementReferenceException):
                    sleep(2)

            if not current_card:
                logger.warning(f"Could not find valid card for rank {rank}. Skipping.")
                continue

            # Defaults
            product_name     = "N/A"
            unit_quantity    = "N/A"
            selling_price    = "N/A"
            delivery_time    = "N/A"
            listing_type     = "Organic"
            available_inventory = 0

            try:
                # Product Name
                try:
                    name_elem    = current_card.find_element(By.XPATH, './/div[contains(@class,"tw-text-300 tw-font-semibold tw-line-clamp-2")]')
                    product_name = name_elem.text.strip()
                except NoSuchElementException:
                    try:
                        name_elem    = current_card.find_element(By.XPATH, './/div[contains(@class,"tw-font-semibold") and contains(@class,"tw-text-300")]')
                        product_name = name_elem.text.strip()
                    except NoSuchElementException:
                        continue

                # Unit Quantity
                try:
                    unit_elem     = current_card.find_element(By.XPATH, './/div[contains(@class,"tw-text-200 tw-font-medium") and (contains(text(),"g") or contains(text(),"ml") or contains(text(),"kg") or contains(text(),"L"))]')
                    unit_quantity = unit_elem.text.strip()
                except NoSuchElementException:
                    pass

                # Price
                try:
                    price_elem    = current_card.find_element(By.XPATH, './/div[contains(@class,"tw-text-200 tw-font-semibold") and not(contains(@class,"tw-line-through")) and starts-with(text(),"₹")]')
                    selling_price = price_elem.text.strip()
                except NoSuchElementException:
                    pass

                # Delivery Time
                try:
                    delivery_elem = current_card.find_element(By.XPATH, './/div[contains(@class,"tw-text-050 tw-font-bold") and contains(text(),"mins")]')
                    delivery_time = delivery_elem.text.strip()
                except NoSuchElementException:
                    pass

                # Ad detection
                try:
                    current_card.find_element(By.XPATH, './/img[contains(@src,"ad_without_bg.png")]')
                    listing_type = "Ad"
                except NoSuchElementException:
                    listing_type = "Organic"

                # ── Inventory check ─────────────────────────────
                logger.info(f"  Checking inventory for: {product_name}")
                browser.execute_script("arguments[0].scrollIntoView({block:'center'});", current_card)
                sleep(1.5)

                add_div = None
                for retry_add in range(3):
                    try:
                        add_div = current_card.find_element(By.XPATH, './/div[contains(text(),"ADD") and @data-pf="reset"]')
                        browser.execute_script("arguments[0].click();", add_div)
                        sleep(0.5)
                        break
                    except (NoSuchElementException, ElementClickInterceptedException, StaleElementReferenceException):
                        current_card = wait.until(EC.presence_of_element_located((By.XPATH, f'({CARD_XPATH})[position()={rank}]')))
                        sleep(0.3)

                if not add_div:
                    raise Exception("Could not click initial ADD div")

                # Click + until stuck
                PLUS_SELECTORS = [
                    './/button[.//span[contains(@class,"icon-plus")]]',
                    './/span[contains(@class,"icon-plus")]/parent::button',
                    './/button[contains(@class,"tw-flex") and @data-pf="reset"]',
                    './/*[contains(@class,"icon-plus")]',
                    './/button[contains(@class,"plus") or contains(@class,"increment")]',
                    './/*[@aria-label="increase quantity" or @aria-label="add one more"]',
                    './/div[@data-pf="reset"]/following-sibling::*[1][@role="button"]',
                    './/div[@data-pf="reset" and translate(text(),"0123456789","")=""]',
                ]

                last_qty = 0
                current_qty = 0
                for attempt in range(100):
                    current_card = wait.until(EC.presence_of_element_located((By.XPATH, f'({CARD_XPATH})[position()={rank}]')))
                    try:
                        qty_div = current_card.find_element(By.XPATH, './/div[@data-pf="reset" and string-length(text())>0 and not(contains(text(),"ADD")) and translate(text(),"0123456789","")=""]')
                        display = qty_div.text.strip()
                        if display.isdigit():
                            current_qty = int(display)
                        else:
                            break
                    except NoSuchElementException:
                        break

                    if current_qty == last_qty and current_qty > 0:
                        logger.info(f"    Qty stuck at {current_qty} — max inventory reached!")
                        break

                    plus_elem = None
                    for sel in PLUS_SELECTORS:
                        try:
                            e = current_card.find_element(By.XPATH, sel)
                            if e.is_displayed() and e.size['height'] > 0:
                                plus_elem = e
                                break
                        except NoSuchElementException:
                            continue

                    if not plus_elem:
                        break

                    browser.execute_script("arguments[0].click();", plus_elem)
                    sleep(0.3)
                    last_qty = current_qty

                available_inventory = current_qty
                logger.info(f"  Inventory: {available_inventory}")

                # ── Reset quantity back to 0 ─────────────────────
                MINUS_SELECTORS = [
                    './/button[.//span[contains(@class,"icon-minus")]]',
                    './/span[contains(@class,"icon-minus")]/parent::button',
                    './/button[contains(@class,"tw-flex") and @data-pf="reset" and not(.//span[contains(@class,"icon-plus")])]',
                    './/*[contains(@class,"icon-minus")]',
                    './/button[contains(@class,"minus") or contains(@class,"decrement")]',
                    './/*[@aria-label="decrease quantity" or @aria-label="remove one"]',
                ]
                reset_attempts = 0
                while reset_attempts < available_inventory + 10:
                    current_card = wait.until(EC.presence_of_element_located((By.XPATH, f'({CARD_XPATH})[position()={rank}]')))
                    try:
                        qty_div = current_card.find_element(By.XPATH, './/div[@data-pf="reset" and string-length(text())>0 and not(contains(text(),"ADD")) and translate(text(),"0123456789","")=""]')
                        if qty_div.text.strip().isdigit() and int(qty_div.text.strip()) == 0:
                            break
                    except NoSuchElementException:
                        break

                    minus_elem = None
                    for sel in MINUS_SELECTORS:
                        try:
                            e = current_card.find_element(By.XPATH, sel)
                            if e.is_displayed() and e.size['height'] > 0:
                                minus_elem = e
                                break
                        except NoSuchElementException:
                            continue

                    if minus_elem:
                        browser.execute_script("arguments[0].click();", minus_elem)
                    else:
                        break
                    sleep(0.3)
                    reset_attempts += 1

                try:
                    browser.execute_script("arguments[0].click();", browser.find_element(By.TAG_NAME, "body"))
                except Exception:
                    pass
                sleep(0.5)

            except Exception as e:
                logger.warning(f"  Error at rank {rank}: {e}")
                available_inventory = 0
                try:
                    sleep(0.5)
                    browser.execute_script("arguments[0].click();", browser.find_element(By.TAG_NAME, "body"))
                except Exception:
                    pass

            product_details.append({
                "Rank": len(product_details) + 1,
                "Product Name": product_name,
                "Unit Quantity": unit_quantity,
                "Selling Price": selling_price,
                "Delivery Time": delivery_time,
                "Listing Type": listing_type,
                "Available Inventory": available_inventory,
            })

    except Exception as e:
        logger.error(f"Fatal scrape error: {e}", exc_info=True)
        raise
    finally:
        if browser:
            browser.quit()
            logger.info("Browser closed.")

    return product_details
