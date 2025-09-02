import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import re

class AutoScout24Scraper:
    def __init__(self, headless=True):
        self.setup_driver(headless)
        self.listings = []
    
    def setup_driver(self, headless):
        """Setup Chrome driver with anti-detection measures"""
        chrome_options = Options()
        
        if headless:
            chrome_options.add_argument("--headless")
        
        # Anti-detection measures
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            print("✅ Chrome driver initialized")
        except Exception as e:
            print(f"❌ Failed to initialize Chrome driver: {e}")
            print("Make sure ChromeDriver is installed: https://chromedriver.chromium.org/")
            raise
    
    def scrape_listings(self, search_url, max_pages=3):
        """Scrape car listings from AutoScout24"""
        print(f"🚀 Starting scrape of: {search_url}")
        
        try:
            self.driver.get(search_url)
            time.sleep(3)
            
            # Accept cookies if popup appears
            self.handle_cookie_popup()
            
            page = 1
            while page <= max_pages:
                print(f"📄 Scraping page {page}...")
                
                # Scrape current page
                page_listings = self.scrape_current_page()
                if not page_listings:
                    print("No listings found on this page, stopping...")
                    break
                
                self.listings.extend(page_listings)
                print(f"Found {len(page_listings)} listings on page {page}")
                
                # Try to go to next page
                if page < max_pages:
                    if not self.go_to_next_page():
                        print("No more pages available")
                        break
                    time.sleep(2)
                
                page += 1
            
            print(f"✅ Scraping completed. Total listings: {len(self.listings)}")
            
        except Exception as e:
            print(f"❌ Error during scraping: {e}")
        
        return self.listings
    
    def handle_cookie_popup(self):
        """Handle cookie consent popup"""
        try:
            # Common cookie button selectors
            cookie_selectors = [
                "[data-testid='cookie-consent-accept']",
                "button[id*='cookie']",
                "button[class*='cookie']",
                ".cookie-accept",
                "#cookie-accept",
                "[id*='CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll']",
                "button[onclick*='cookie']"
            ]
            
            for selector in cookie_selectors:
                try:
                    cookie_btn = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    cookie_btn.click()
                    print("✅ Accepted cookies")
                    time.sleep(1)
                    return
                except TimeoutException:
                    continue
                    
        except Exception as e:
            print("No cookie popup found or already handled")
    
    def scrape_current_page(self):
        """Scrape listings from current page"""
        listings = []
        
        # Wait for listings to load
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='listing-summary-container'], .listing-item, .cldt-summary-full-item"))
            )
        except TimeoutException:
            print("⚠️ Timeout waiting for listings to load")
            return listings
        
        # Try different selectors for listing containers
        listing_selectors = [
            "[data-testid='listing-summary-container']",
            ".listing-item",
            ".cldt-summary-full-item",
            "[data-testid='listing-item']",
            "article[data-testid='listing-summary-container']"
        ]
        
        listing_elements = []
        for selector in listing_selectors:
            listing_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            if listing_elements:
                print(f"Found {len(listing_elements)} listings using selector: {selector}")
                break
        
        if not listing_elements:
            print("⚠️ No listing elements found")
            return listings
        
        for i, element in enumerate(listing_elements):
            try:
                print(f"Processing listing {i+1}...")
                listing_data = self.extract_listing_data(element)
                if listing_data:
                    listings.append(listing_data)
            except Exception as e:
                print(f"Error extracting listing {i+1} data: {e}")
                continue
        
        return listings
    
    def extract_listing_data(self, element):
        """Extract data from a single listing element"""
        try:
            listing = {}
            
            # Get all text content from the element to parse data from it
            full_text = element.text
            
            # Title/Model - More comprehensive selectors for AutoScout24
            title_selectors = [
                ".cldt-summary-makemodel",
                ".cldt-summary-version", 
                "h2 a",
                "h3 a",
                "a[data-testid='listing-title']",
                "[data-testid='listing-title']",
                ".listing-title",
                ".cldt-summary-titles h2",
                ".vehicle-title",
                "span[data-testid='make-model']",
                "h2",
                "h3"
            ]
            title = self.get_text_by_selectors(element, title_selectors)
            
            # If no title found, try getting it from link text or attribute
            if not title:
                try:
                    link_element = element.find_element(By.CSS_SELECTOR, "a")
                    title = link_element.get_attribute('title') or link_element.get_attribute('aria-label') or link_element.text.strip()
                except:
                    pass
            
            listing['title'] = title or "N/A"
            
            # Price - Updated selectors for AutoScout24
            price_selectors = [
                ".cldt-price",
                "[data-testid='regular-price']",
                "[data-testid='price-summary']", 
                ".price-block",
                ".listing-price",
                "span[data-testid='price']",
                "[class*='price']",
                ".cldt-price span"
            ]
            price = self.get_text_by_selectors(element, price_selectors)
            
            # Try to extract price from full text if not found
            if not price and full_text:
                price_match = re.search(r'€\s?[\d,.\s]+', full_text)
                if price_match:
                    price = price_match.group().strip()
            
            listing['price'] = price or "N/A"
            
            # Extract data from full text using regex patterns
            if full_text:
                # Mileage patterns (km, kilometers)
                mileage_patterns = [
                    r'([\d,.\s]+)\s*km',
                    r'([\d,.\s]+)\s*kilometers',
                    r'([\d,.\s]+)\s*KM'
                ]
                mileage = None
                for pattern in mileage_patterns:
                    match = re.search(pattern, full_text, re.IGNORECASE)
                    if match:
                        mileage = match.group().strip()
                        break
                
                # Year patterns (4 digits, first registration)
                year_patterns = [
                    r'\b(19|20)\d{2}\b',  # 4-digit years
                    r'(\d{2}/\d{4})',     # MM/YYYY format
                    r'(\d{1,2}/\d{1,2}/\d{4})'  # Full date
                ]
                year = None
                for pattern in year_patterns:
                    matches = re.findall(pattern, full_text)
                    if matches:
                        # Take the first reasonable year found
                        for match in matches:
                            if isinstance(match, tuple):
                                match = match[0] if len(match[0]) == 4 else match[1] if len(match) > 1 else match[0]
                            try:
                                year_num = int(match) if len(str(match)) == 4 else int(match.split('/')[-1])
                                if 1990 <= year_num <= 2025:  # Reasonable year range
                                    year = str(year_num)
                                    break
                            except:
                                continue
                        if year:
                            break
                
                # Fuel type patterns
                fuel_patterns = [
                    r'\b(Gasoline|Petrol|Benzin|Diesel|Electric|Hybrid|LPG|CNG)\b'
                ]
                fuel = None
                for pattern in fuel_patterns:
                    match = re.search(pattern, full_text, re.IGNORECASE)
                    if match:
                        fuel = match.group().strip()
                        break
                
                # Transmission patterns
                transmission_patterns = [
                    r'\b(Manual|Automatic|Semi-automatic|Schaltgetriebe|Automatik)\b'
                ]
                transmission = None
                for pattern in transmission_patterns:
                    match = re.search(pattern, full_text, re.IGNORECASE)
                    if match:
                        transmission = match.group().strip()
                        break
                
                # Location patterns (postal code + city)
                location_patterns = [
                    r'\b(\d{5})\s+([A-Za-zäöüß\s]+)\b',  # German postal code + city
                    r'\b([A-Za-zäöüß\s]+)\s+\((\d{5})\)'  # City (postal code)
                ]
                location = None
                for pattern in location_patterns:
                    match = re.search(pattern, full_text)
                    if match:
                        if len(match.groups()) == 2:
                            location = f"{match.group(1)} {match.group(2)}".strip()
                        break
                
                # If regex didn't work, try specific CSS selectors
                if not mileage:
                    mileage_selectors = [
                        ".cldt-summary-mileage",
                        "[data-testid='mileage']",
                        ".listing-mileage",
                        "[class*='mileage']",
                        ".vehicle-data span",
                        "span[data-testid='vehicle-mileage']"
                    ]
                    mileage = self.get_text_by_selectors(element, mileage_selectors)
                
                if not year:
                    year_selectors = [
                        ".cldt-summary-registration",
                        "[data-testid='year']",
                        "[data-testid='first-registration']",
                        ".listing-year",
                        "[class*='year']",
                        "span[data-testid='vehicle-registration']"
                    ]
                    year = self.get_text_by_selectors(element, year_selectors)
                
                if not location:
                    location_selectors = [
                        ".cldt-summary-seller-contact-zip-city",
                        "[data-testid='dealer-location']",
                        "[data-testid='seller-location']",
                        ".listing-location",
                        ".dealer-location",
                        "[class*='location']"
                    ]
                    location = self.get_text_by_selectors(element, location_selectors)
                
                if not fuel:
                    fuel_selectors = [
                        ".cldt-summary-fuel", 
                        "[data-testid='fuel-type']"
                    ]
                    fuel = self.get_text_by_selectors(element, fuel_selectors)
                
                if not transmission:
                    transmission_selectors = [
                        ".cldt-summary-transmission",
                        "[data-testid='transmission']"
                    ]
                    transmission = self.get_text_by_selectors(element, transmission_selectors)
            
            listing['mileage'] = mileage or "N/A"
            listing['year'] = year or "N/A"
            listing['location'] = location or "N/A"
            listing['fuel'] = fuel or "N/A"
            listing['transmission'] = transmission or "N/A"
            
            # Link extraction
            try:
                link_selectors = [
                    "a[href*='/offers/']",
                    "a[href*='/details/']", 
                    "a[data-testid='listing-link']",
                    "a[href*='/offer/']",
                    "a"
                ]
                link = None
                for selector in link_selectors:
                    try:
                        link_element = element.find_element(By.CSS_SELECTOR, selector)
                        href = link_element.get_attribute('href')
                        if href and ('offer' in href or 'details' in href):
                            link = href if href.startswith('http') else f"https://www.autoscout24.com{href}"
                            break
                    except NoSuchElementException:
                        continue
                listing['link'] = link or "N/A"
            except:
                listing['link'] = "N/A"
            
            # Debug output with more details
            print(f"✅ Extracted: Title='{listing['title'][:50]}...', Price='{listing['price']}', Mileage='{listing['mileage']}', Year='{listing['year']}', Location='{listing['location']}'")
            
            # Return if we got at least a title OR price
            if listing.get('title', 'N/A') != 'N/A' or listing.get('price', 'N/A') != 'N/A':
                return listing
            else:
                print("❌ No title or price found, skipping listing")
                return None
            
        except Exception as e:
            print(f"Error extracting listing data: {e}")
            import traceback
            traceback.print_exc()
        
        return None
    
    def get_text_by_selectors(self, element, selectors):
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
    
    def go_to_next_page(self):
        """Navigate to next page"""
        next_selectors = [
            "[data-testid='pagination-next']",
            ".pagination-next",
            "a[aria-label*='Next']",
            ".next-page",
            "[class*='next'][class*='page']",
            "a[title*='next']",
            "button[aria-label*='next']"
        ]
        
        for selector in next_selectors:
            try:
                next_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                if next_btn.is_enabled() and next_btn.is_displayed():
                    self.driver.execute_script("arguments[0].click();", next_btn)
                    time.sleep(3)
                    return True
            except NoSuchElementException:
                continue
        
        return False
    
    def save_to_csv(self, filename="autoscout_listings.csv"):
        """Save listings to CSV"""
        if not self.listings:
            print("No listings to save")
            return
        
        df = pd.DataFrame(self.listings)
        
        # Clean up data
        for col in df.columns:
            if col in ['price', 'mileage']:
                # Clean price and mileage columns
                df[col] = df[col].astype(str).str.replace(r'[^\d,.]', '', regex=True)
        
        df.to_csv(filename, index=False)
        print(f"✅ {len(self.listings)} listings saved to {filename}")
        print(f"Columns: {list(df.columns)}")
        print("\nSample data:")
        print(df.head())
        
        # Show data completeness
        print("\n📊 Data Completeness:")
        for col in df.columns:
            non_empty = len(df[df[col] != 'N/A'])
            percentage = (non_empty / len(df)) * 100
            print(f"{col}: {non_empty}/{len(df)} ({percentage:.1f}%)")
    
    def close(self):
        """Close the driver"""
        if hasattr(self, 'driver'):
            self.driver.quit()
            print("✅ Driver closed")

def main():
    # Configuration
    search_url = "https://www.autoscout24.com/lst/bmw/3-series"
    max_pages = 2  # Start with 2 pages for testing
    
    scraper = AutoScout24Scraper(headless=False)  # Set to True to run in background
    
    try:
        listings = scraper.scrape_listings(search_url, max_pages)
        if listings:
            scraper.save_to_csv("bmw_complete_data.csv")
        else:
            print("No listings found")
            
    except Exception as e:
        print(f"❌ Scraping failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        scraper.close()

if __name__ == "__main__":
    main()