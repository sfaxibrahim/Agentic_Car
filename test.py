import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WebcarProfessionalScraper:
    def __init__(self, headless=False):
        self.driver = self.setup_driver(headless)
        self.listings = []
        
    def setup_driver(self, headless):
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        driver = webdriver.Chrome(options=chrome_options)
        return driver

    def analyze_website_structure(self):
        """Analyze the website structure to understand the layout"""
        logger.info("🔍 Analyzing website structure...")
        
        self.driver.get("https://www.webcar.eu/eu-en/car-search")
        time.sleep(5)
        
        # Handle cookies
        self.handle_cookies()
        
        # Fill basic search
        self.fill_search_form()
        time.sleep(5)
        
        # Analyze page structure
        structure_info = {}
        
        # Look for main content containers
        containers = [
            "main", "section", ".container", ".content", ".main-content",
            ".search-results", ".results", ".listings", ".vehicles"
        ]
        
        for container in containers:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, container)
                if elements:
                    structure_info[container] = len(elements)
                    logger.info(f"Found {len(elements)} elements with selector: {container}")
            except:
                pass
        
        # Look for individual listing elements
        listing_selectors = [
            ".vehicle-card", ".car-item", ".listing-item", ".result-item",
            ".card", ".item", "[data-testid*='vehicle']", "[class*='vehicle']",
            "[class*='car']", "[class*='listing']", "[class*='result']"
        ]
        
        for selector in listing_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    structure_info[selector] = len(elements)
                    logger.info(f"Found {len(elements)} listing elements with: {selector}")
                    
                    # Print sample of first listing
                    if elements:
                        sample_text = elements[0].text.replace('\n', ' | ')[:200]
                        logger.info(f"Sample listing text: {sample_text}...")
            except:
                pass
        
        # Save page source for analysis
        with open("page_structure.html", "w", encoding="utf-8") as f:
            f.write(self.driver.page_source)
        
        logger.info("💾 Saved page structure to page_structure.html")
        return structure_info

    def handle_cookies(self):
        """Handle cookie consent"""
        try:
            selectors = [
                "button#acceptCookies",
                "button[onclick*='cookie']",
                "button[class*='cookie']",
                "button[class*='accept']",
                ".cookie-accept-all",
                "#cookie-accept-all"
            ]
            
            for selector in selectors:
                try:
                    button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    button.click()
                    logger.info("✅ Accepted cookies")
                    time.sleep(2)
                    break
                except:
                    continue
        except:
            pass

    def fill_search_form(self):
        """Fill the search form systematically"""
        try:
            # Wait for form to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "form, select, input"))
            )
            
            # Fill brand
            brand_selectors = ["select[name='brand']", "select[id*='brand']", "#brand"]
            for selector in brand_selectors:
                try:
                    brand_select = self.driver.find_element(By.CSS_SELECTOR, selector)
                    select = Select(brand_select)
                    
                    # Try to select Audi
                    for option in select.options:
                        if 'audi' in option.text.lower():
                            select.select_by_visible_text(option.text)
                            logger.info(f"✅ Selected brand: {option.text}")
                            time.sleep(2)
                            break
                    break
                except:
                    continue
            
            # Fill model  
            model_selectors = ["select[name='model']", "select[id*='model']", "#model"]
            for selector in model_selectors:
                try:
                    model_select = self.driver.find_element(By.CSS_SELECTOR, selector)
                    select = Select(model_select)
                    
                    # Try to select A4
                    for option in select.options:
                        if 'a4' in option.text.lower():
                            select.select_by_visible_text(option.text)
                            logger.info(f"✅ Selected model: {option.text}")
                            time.sleep(2)
                            break
                    break
                except:
                    continue
            
            # Submit search
            submit_selectors = [
                "button[type='submit']",
                "input[type='submit']", 
                "button[class*='search']",
                ".btn-search",
                "#search-button"
            ]
            
            for selector in submit_selectors:
                try:
                    submit_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if submit_btn.is_enabled():
                        submit_btn.click()
                        logger.info("✅ Submitted search form")
                        time.sleep(3)
                        return True
                except:
                    continue
                    
        except Exception as e:
            logger.warning(f"⚠️ Search form filling failed: {e}")
        
        return False

    def scrape_with_proper_selectors(self):
        """Scrape using proper CSS selectors based on website analysis"""
        logger.info("🎯 Starting professional scraping...")
        
        # Common listing selectors for car websites
        listing_selectors = [
            # Webcar specific
            ".vehicle-card",
            "[data-testid*='vehicle']",
            # Generic car listing patterns
            ".car-listing",
            ".vehicle-item", 
            ".listing-card",
            ".result-item",
            # Grid items
            ".grid-item",
            ".col[class*='vehicle']",
            ".col[class*='car']",
            # Fallbacks
            "article",
            "section > div",
            ".card"
        ]
        
        all_listings = []
        
        for selector in listing_selectors:
            try:
                listings = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if listings and len(listings) > 2:  # Need multiple results
                    logger.info(f"✅ Found {len(listings)} listings with: {selector}")
                    all_listings = listings
                    break
            except:
                continue
        
        if not all_listings:
            logger.warning("❌ No listings found with standard selectors")
            return []
        
        extracted_data = []
        
        for i, listing in enumerate(all_listings[:20]):  # Limit to first 20
            try:
                data = self.extract_listing_data_advanced(listing)
                if data:
                    extracted_data.append(data)
                    logger.info(f"✅ Extracted listing {i+1}: {data.get('price', 'N/A')}")
            except Exception as e:
                logger.debug(f"⚠️ Failed to extract listing {i+1}: {e}")
                continue
        
        return extracted_data

    def extract_listing_data_advanced(self, listing_element):
        """Advanced data extraction with multiple fallback methods"""
        try:
            # Method 1: Try to find specific data elements
            data = {}
            
            # Price - look in specific elements first
            price_selectors = [
                ".price", "[class*='price']", ".vehicle-price", ".car-price",
                "span[class*='price']", "div[class*='price']", "strong"
            ]
            
            for selector in price_selectors:
                try:
                    price_elem = listing_element.find_element(By.CSS_SELECTOR, selector)
                    price_text = price_elem.text.strip()
                    if '€' in price_text:
                        data['price'] = price_text
                        break
                except:
                    continue
            
            # Title
            title_selectors = [
                ".title", "[class*='title']", ".vehicle-title", ".car-title",
                "h2", "h3", "h4", ".name", "[class*='name']"
            ]
            
            for selector in title_selectors:
                try:
                    title_elem = listing_element.find_element(By.CSS_SELECTOR, selector)
                    title_text = title_elem.text.strip()
                    if title_text and len(title_text) > 3:
                        data['title'] = title_text
                        break
                except:
                    continue
            
            # Method 2: Parse all text if specific elements not found
            if not data:
                full_text = listing_element.text
                lines = [line.strip() for line in full_text.split('\n') if line.strip()]
                
                if lines:
                    # Price is usually a line with €
                    for line in lines:
                        if '€' in line:
                            data['price'] = line
                            break
                    
                    # Title is usually first meaningful line without €
                    for line in lines:
                        if line and '€' not in line and len(line) > 5:
                            data['title'] = line
                            break
            
            # Extract additional details from text
            full_text = listing_element.text
            
            # Year
            year_match = re.search(r'\b(20\d{2}|19\d{2})\b', full_text)
            if year_match:
                data['year'] = year_match.group()
            
            # Mileage
            mileage_match = re.search(r'(\d{1,3}(?:[.,]\d{3})*)\s*km', full_text, re.IGNORECASE)
            if mileage_match:
                data['mileage'] = mileage_match.group()
            
            # Fuel type
            fuel_types = ['petrol', 'diesel', 'electric', 'hybrid', 'gasoline']
            for fuel in fuel_types:
                if fuel in full_text.lower():
                    data['fuel_type'] = fuel.title()
                    break
            
            # Link
            try:
                link_elem = listing_element.find_element(By.CSS_SELECTOR, "a")
                href = link_elem.get_attribute("href")
                if href:
                    data['link'] = href
            except:
                pass
            
            # Validate we have meaningful data
            if data.get('price') or data.get('title'):
                return data
            
            return None
            
        except Exception as e:
            logger.debug(f"Extraction error: {e}")
            return None

    def save_results(self, data, filename="webcar_professional_results.csv"):
        """Save results professionally"""
        if not data:
            logger.warning("No data to save")
            return
        
        df = pd.DataFrame(data)
        
        # Reorder columns logically
        preferred_order = ['title', 'price', 'year', 'mileage', 'fuel_type', 'link']
        existing_columns = [col for col in preferred_order if col in df.columns]
        other_columns = [col for col in df.columns if col not in preferred_order]
        
        df = df[existing_columns + other_columns]
        
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        logger.info(f"💾 Saved {len(data)} listings to {filename}")
        
        # Print summary
        print(f"\n{'='*50}")
        print("📊 SCRAPING SUMMARY")
        print(f"{'='*50}")
        print(f"Total listings: {len(data)}")
        if len(data) > 0:
            print(f"With prices: {sum(1 for x in data if x.get('price'))}")
            print(f"With years: {sum(1 for x in data if x.get('year'))}")
            print(f"\nSample data:")
            for i, item in enumerate(data[:3]):
                print(f"{i+1}. {item.get('title', 'No title')} - {item.get('price', 'No price')}")
        print(f"{'='*50}")

    def close(self):
        self.driver.quit()

def main():
    """Main execution with proper error handling"""
    scraper = WebcarProfessionalScraper(headless=False)
    
    try:
        # Step 1: Analyze structure
        structure = scraper.analyze_website_structure()
        
        # Step 2: Scrape data
        data = scraper.scrape_with_proper_selectors()
        
        # Step 3: Save results
        if data:
            scraper.save_results(data, "professional_webcar_results.csv")
        else:
            logger.error("❌ No data extracted")
            logger.info("💡 Check page_structure.html to see the actual page structure")
            
    except Exception as e:
        logger.error(f"❌ Scraping failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        scraper.close()

if __name__ == "__main__":
    main()