"""
Webcar.eu Scraper - Correctly extracts individual car cards

Structure: Each car is an <a class="vehicle-card"> containing:
- Title in: <div class="card-title card-list-title">
- Date in: <svg icon-calendar> + text "04/2024"
- Mileage in: <svg icon-gauge> + text "52.900 km"
- Fuel in: <svg icons-fuel-*> + text "Diesel"
- Price in: <div class="card-list-title card-title"> € 36.776
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
import re
import json
from typing import List, Dict, Optional

class WebcarSearchParams:
    def __init__(
        self,
        make: str,
        model: Optional[str] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        make_id: Optional[int] = None,
        model_id: Optional[int] = None,
    ):
        self.make = make
        self.model = model
        self.year_from = year_from
        self.year_to = year_to
        self.make_id = make_id
        self.model_id = model_id
    
    def build_url(self) -> str:
        """
        Build webcar.eu URL with proper filter IDs
        All filters are optional - only add what's provided
        
        Common make IDs:
        - BMW: 15
        - Audi: 10
        - Mercedes: 45
        """
        base = "https://www.webcar.eu/eu-en/used-and-new-cars?"
        params = []
        
        # Add make filter (optional)
        if self.make_id:
            params.append(f"filter%5Bmake%5D%5B1%5D={self.make_id}")
        
        # Add model filter (optional - only if make is also provided)
        if self.model_id and self.make_id:
            params.append(f"filter%5Bmodel%5D%5B1%5D={self.model_id}")
        
        # Add year filters (optional)
        if self.year_from:
            params.append(f"filter%5Bregistered_on%5D%5Bfrom%5D={self.year_from}")
        if self.year_to:
            params.append(f"filter%5Bregistered_on%5D%5Bto%5D={self.year_to}")
        
        # Always add these
        params.append("formSubmitted=true")
        params.append("sort=created_at-desc")
        
        # Add make_model for URL readability (optional)
        if self.make and self.model:
            params.append(f"make_model={self.make.lower()}-{self.model.lower()}")
        elif self.make:
            params.append(f"make_model={self.make.lower()}")
        
        return base + "&".join(params)


def extract_ids_from_url(url: str) -> tuple:
    """
    Extract make_id and model_id from a webcar.eu URL
    
    Example URL:
    https://www.webcar.eu/eu-en/used-and-new-cars?filter%5Bmake%5D%5B1%5D=15&filter%5Bmodel%5D%5B1%5D=201&...
    
    Returns: (make_id, model_id)
    """
    make_id = None
    model_id = None
    
    # Extract make ID
    make_match = re.search(r'filter%5Bmake%5D%5B1%5D=(\d+)', url)
    if make_match:
        make_id = int(make_match.group(1))
    
    # Extract model ID
    model_match = re.search(r'filter%5Bmodel%5D%5B1%5D=(\d+)', url)
    if model_match:
        model_id = int(model_match.group(1))
    
    return make_id, model_id


def setup_driver(headless: bool = False):
    """Setup Selenium WebDriver"""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=chrome_options)
    except:
        return webdriver.Chrome(options=chrome_options)


def extract_car_from_html(card_html: str, link: str) -> Dict:
    """
    Extract car data from a single vehicle-card HTML
    Structure based on actual webcar.eu HTML
    """
    soup = BeautifulSoup(card_html, 'html.parser')
    
    # Extract title from card-title
    title = "N/A"
    title_div = soup.find('div', class_='card-title')
    if title_div:
        title = title_div.get_text(strip=True)
    
    # Extract date (MM/YYYY format)
    year = "N/A"
    # Find the div with calendar icon, then get next text
    calendar_divs = soup.find_all('div', class_='card-caption-content')
    for div in calendar_divs:
        svg = div.find('svg')
        if svg and 'icon-calendar' in str(svg):
            date_text = div.get_text(strip=True)
            # Extract year from MM/YYYY
            match = re.search(r'(\d{2})/(\d{4})', date_text)
            if match:
                year = int(match.group(2))
                break
    
    # Extract mileage
    mileage = None
    for div in calendar_divs:
        svg = div.find('svg')
        if svg and 'icon-gauge' in str(svg):
            mileage_text = div.get_text(strip=True)
            # Extract number with dots: "52.900 km"
            match = re.search(r'([\d.]+)\s*km', mileage_text)
            if match:
                try:
                    mileage = int(match.group(1).replace('.', ''))
                except:
                    pass
            break
    
    # Extract fuel type
    fuel = "N/A"
    for div in calendar_divs:
        svg = div.find('svg')
        if svg and 'icons-fuel' in str(svg):
            fuel = div.get_text(strip=True)
            break
    
    # Extract price - IMPROVED with multiple methods
    price = None
    
    # Method 1: Look in col-4 (right column where price usually is)
    col4 = soup.find('div', class_='col-4')
    if col4:
        # Find all text in col-4 and search for price
        col4_text = col4.get_text()
        # Look for € followed by number with dots
        price_matches = re.findall(r'€\s*([\d.]+)', col4_text)
        if price_matches:
            # Take first price found (usually the main price)
            try:
                price = int(price_matches[0].replace('.', ''))
            except:
                pass
    
    # Method 2: Find divs with specific classes
    if price is None:
        all_divs = soup.find_all('div')
        for div in all_divs:
            classes = div.get('class', [])
            # Look for card-list-title or similar price containers
            if any(cls in ['card-list-title', 'card-title', 'text-right'] for cls in classes):
                text = div.get_text(strip=True)
                if '€' in text:
                    match = re.search(r'€\s*([\d.]+)', text)
                    if match:
                        try:
                            price = int(match.group(1).replace('.', ''))
                            break
                        except:
                            pass
    
    # Method 3: Fallback - search entire card HTML for price pattern
    if price is None:
        all_text = soup.get_text()
        price_matches = re.findall(r'€\s*([\d.]+)', all_text)
        if price_matches:
            # Filter out unlikely prices (too small or too large)
            for match in price_matches:
                try:
                    potential_price = int(match.replace('.', ''))
                    # Car prices typically between 1,000 and 500,000
                    if 1000 <= potential_price <= 500000:
                        price = potential_price
                        break
                except:
                    pass
    
    # Extract transmission from card-paragraph
    transmission = "N/A"
    paragraph = soup.find('div', class_='card-paragraph')
    if paragraph:
        text = paragraph.get_text()
        if 'Automatic gear' in text or 'Automatic' in text:
            transmission = "Automatic"
        elif 'Manual gear' in text or 'Manual' in text:
            transmission = "Manual"
        elif 'Semi-automatic' in text:
            transmission = "Semi-automatic"
    
    return {
        "title": title,
        "price": price,
        "mileage": mileage,
        "year": year,
        "fuel": fuel,
        "transmission": transmission,
        "link": link,
    }


def fetch_webcar_listings(params: WebcarSearchParams, headless: bool = False, max_results: int = 30) -> List[Dict]:
    """Fetch listings from webcar.eu using Selenium"""
    driver = setup_driver(headless=headless)
    if not driver:
        return []
    
    try:
        url = params.build_url()
        print(f"🌐 Navigating to: {url}\n")
        
        driver.get(url)
        time.sleep(3)
        
        # Scroll to load all content
        print("📜 Scrolling to load content...")
        for i in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)
        
        # Wait for vehicle cards to load
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.vehicle-card"))
            )
            print("✅ Vehicle cards loaded\n")
        except:
            print("⚠️ Timeout waiting for cards\n")
        
        # Find all vehicle card elements
        vehicle_cards = driver.find_elements(By.CSS_SELECTOR, "a.vehicle-card")
        print(f"🔍 Found {len(vehicle_cards)} vehicle cards\n")
        
        results = []
        
        for idx, card_element in enumerate(vehicle_cards[:max_results], 1):
            try:
                # Get the link
                link = card_element.get_attribute('href')
                
                # Get the innerHTML of the card
                card_html = card_element.get_attribute('innerHTML')
                
                # Extract data from HTML
                data = extract_car_from_html(card_html, link)
                
                if data.get('title') != "N/A":
                    results.append(data)
                    print(f"   ✅ {idx}. {data.get('title')[:60]}...")
                
            except Exception as e:
                print(f"   ❌ Error extracting card {idx}: {e}")
                continue
        
        return results
    
    finally:
        driver.quit()
        print("\n✅ Browser closed")


def print_results(listings: List[Dict]):
    """Print extracted listings"""
    if not listings:
        print("\nNo listings to display.")
        return
    
    print(f"\n{'='*80}")
    print(f"📊 FOUND {len(listings)} LISTINGS")
    print(f"{'='*80}\n")
    
    for i, car in enumerate(listings, 1):
        print("-" * 70)
        print(f"Listing {i}")
        print(f"Title       : {car.get('title')}")
        print(f"Price       : €{car.get('price'):,}" if car.get('price') else "Price: N/A")
        print(f"Year        : {car.get('year')}")
        print(f"Mileage     : {car.get('mileage'):,} km" if car.get('mileage') else "Mileage: N/A")
        print(f"Fuel        : {car.get('fuel')}")
        print(f"Transmission: {car.get('transmission')}")
        print(f"Link        : {car.get('link')}")
    print("-" * 70)


if __name__ == "__main__":
    print("WEBCAR.EU SCRAPER\n")

    from car_id_mapper import WebcarIDMapper

    mapper = WebcarIDMapper()

    # User says: "BMW"
    make_id = mapper.get_make_id("BMW")  # Returns: 15

    # Use it:
    params = WebcarSearchParams(
        make="bmw",
        make_id=make_id, 
        year_from=2020
    )
        
    # # Example 1: Only BMW (no model) - gets all BMW cars
    # params = WebcarSearchParams(
    #     make="bmw",
    #     make_id=15,        # BMW's ID
    #     year_from=2020,
    # )
    
    # Example 2: BMW 320 specifically
    # params = WebcarSearchParams(
    #     make="bmw",
    #     model="320",
    #     make_id=15,      # BMW's ID
    #     model_id=201,    # 320's ID
    #     year_from=2020,
    #     year_to=2025
    # )
    
    # manual_url = "https://www.webcar.eu/eu-en/used-and-new-cars?filter%5Bmake%5D%5B1%5D=15&filter%5Bregistered_on%5D%5Bfrom%5D=2020&sort=created_at-desc"
    # make_id, model_id = extract_ids_from_url(manual_url)
    # params = WebcarSearchParams(
    #     make="bmw",
    #     make_id=make_id,
    #     model_id=model_id,  # Will be None if not in URL
    #     year_from=2020,
    # )
    
    results = fetch_webcar_listings(params, headless=False, max_results=30)
    
    print_results(results)
    
    if results:
        with open("webcar_results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print("\nSaved results to webcar_results.json")