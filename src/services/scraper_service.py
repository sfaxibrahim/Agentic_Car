"""
Car listing scraper service for AutoScout24
"""
import time
import re
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class CarSearchParams:
    """Parameters for car search"""
    def __init__(self, make: str = None, model: str = None, 
                 year_from: int = None, year_to: int = None,
                 price_max: int = None, mileage_max: int = None,
                 fuel_type: str = None, transmission: str = None):
        self.make = make
        self.model = model  # keep for local filtering only
        self.year_from = year_from
        self.year_to = year_to
        self.price_max = price_max
        self.mileage_max = mileage_max
        self.fuel_type = fuel_type
        self.transmission = transmission

    def to_url(self) -> str:
        """Convert search parameters to a broad AutoScout24 URL"""
        base_url = "https://www.autoscout24.com/lst"
        params = []

        if self.make:
            params.append(f"make={self.make.capitalize()}")  # safe, guaranteed
        if self.year_from:
            params.append(f"fregfrom={self.year_from}")
        if self.year_to:
            params.append(f"fregto={self.year_to}")
        if self.price_max:
            params.append(f"priceto={self.price_max}")
        if self.mileage_max:
            params.append(f"kmto={self.mileage_max}")
        if self.fuel_type:
            params.append(f"fuel={self.fuel_type.upper()}")
        if self.transmission:
            trans_map = {"manual": "M", "automatic": "A", "semi-automatic": "S"}
            code = trans_map.get(self.transmission.lower())
            if code:
                params.append(f"gear={code}")

        url = base_url
        if params:
            url += "?" + "&".join(params)
        return url



class AutoScout24Scraper:
    """Scraper for AutoScout24 car listings"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None
    
    def _setup_driver(self):
        """Setup Chrome driver with anti-detection measures"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless")
        
        # Anti-detection measures
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
    
    def _handle_cookie_popup(self):
        """Handle cookie consent popup"""
        try:
            cookie_selectors = [
                "[data-testid='listing-summary-container']",
                "button[id*='cookie']",
                "#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll"
            ]
            
            for selector in cookie_selectors:
                try:
                    cookie_btn = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    cookie_btn.click()
                    time.sleep(1)
                    return
                except TimeoutException:
                    continue
        except Exception:
            pass
    
    def _extract_listing_data(self, element) -> Optional[Dict]:
        """Extract data from a single listing element"""
        try:
            listing = {}
            full_text = element.text
            
            # Title
            title_selectors = [
                ".cldt-summary-makemodel",
                "h2 a", "h3 a",
                "[data-testid='listing-title']"
            ]
            title = self._get_text_by_selectors(element, title_selectors)
            listing['title'] = title or "N/A"
            
            # Price
            price_selectors = [
                ".cldt-price",
                "[data-testid='regular-price']"
            ]
            price = self._get_text_by_selectors(element, price_selectors)
            if not price and full_text:
                price_match = re.search(r'€\s?[\d,.\s]+', full_text)
                if price_match:
                    price = price_match.group().strip()
            listing['price'] = price or "N/A"
            
            # Mileage
            mileage_match = re.search(r'([\d,.\s]+)\s*km', full_text, re.IGNORECASE)
            listing['mileage'] = mileage_match.group().strip() if mileage_match else "N/A"
            
            # Year
            year_match = re.search(r'\b(19|20)\d{2}\b', full_text)
            listing['year'] = year_match.group() if year_match else "N/A"
            
            # Fuel type
            fuel_match = re.search(
                r'\b(Gasoline|Petrol|Benzin|Diesel|Electric|Hybrid)\b',
                full_text, re.IGNORECASE
            )
            listing['fuel'] = fuel_match.group().strip() if fuel_match else "N/A"
            
            # Transmission
            trans_match = re.search(
                r'\b(Manual|Automatic|Semi-automatic)\b',
                full_text, re.IGNORECASE
            )
            listing['transmission'] = trans_match.group().strip() if trans_match else "N/A"
            
            # Location
            location_match = re.search(r'\b(\d{5})\s+([A-Za-zäöüß\s]+)\b', full_text)
            listing['location'] = (
                f"{location_match.group(1)} {location_match.group(2)}"
                if location_match else "N/A"
            )
            
            # Link
            try:
                link_elem = element.find_element(By.CSS_SELECTOR, "a[href*='/offers/']")
                href = link_elem.get_attribute('href')
                listing['link'] = href if href.startswith('http') else f"https://www.autoscout24.com{href}"
            except:
                listing['link'] = "N/A"
            
            return listing if listing.get('title') != 'N/A' else None
            
        except Exception as e:
            print(f"Error extracting listing: {e}")
            return None
    
    def _get_text_by_selectors(self, element, selectors: List[str]) -> Optional[str]:
        """Try multiple selectors to get text"""
        for selector in selectors:
            try:
                sub_element = element.find_element(By.CSS_SELECTOR, selector)
                text = sub_element.text.strip()
                if text:
                    return text
            except NoSuchElementException:
                continue
        return None
    
    def scrape_listings(self, search_params: CarSearchParams, 
                       max_results: int = 10) -> List[Dict]:
        """
        Scrape car listings based on search parameters
        
        Args:
            search_params: CarSearchParams object with search criteria
            max_results: Maximum number of results to return
            
        Returns:
            List of dictionaries containing car listing data
        """
        listings = []
        
        try:
            self._setup_driver()
            search_url = search_params.to_url()
            
            print(f"🔍 Scraping: {search_url}")
            self.driver.get(search_url)
            time.sleep(3)
            
            self._handle_cookie_popup()
            
            # Wait for listings
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "[data-testid='listing-summary-container']"
                ))
            )
            
            # Get listing elements
            listing_elements = self.driver.find_elements(
                By.CSS_SELECTOR,
                "[data-testid='listing-summary-container']"
            )
            
            print(f"✅ Found {len(listing_elements)} listings")
            
            # Extract data from each listing
            for element in listing_elements[:max_results]:
                listing_data = self._extract_listing_data(element)
                if listing_data:
                    listings.append(listing_data)
            
            print(f"✅ Extracted {len(listings)} valid listings")
            
        except Exception as e:
            print(f"❌ Scraping error: {e}")
        
        finally:
            if self.driver:
                self.driver.quit()
        
        return listings
    
    def close(self):
        """Close the driver"""
        if self.driver:
            self.driver.quit()


