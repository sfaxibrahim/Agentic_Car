"""
Detailed diagnostic for webcar.eu - inspects individual car card structure
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
import re

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
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except:
        driver = webdriver.Chrome(options=chrome_options)
        return driver


def detailed_card_analysis(url: str):
    """
    Analyze individual car cards in detail
    """
    driver = setup_driver(headless=False)
    
    try:
        print("="*80)
        print(f"🔍 DETAILED WEBCAR.EU CARD ANALYSIS")
        print("="*80)
        print(f"\n🌐 URL: {url}\n")
        
        driver.get(url)
        time.sleep(3)
        
        # Scroll to load content
        print("📜 Scrolling...")
        for i in range(2):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)
        
        # Get rendered HTML
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        
        # Save full HTML
        with open("webcar_full_debug.html", "w", encoding="utf-8") as f:
            f.write(soup.prettify())
        print("💾 Saved full HTML to webcar_full_debug.html\n")
        
        # Try to find individual car cards (not the container)
        print("🔍 SEARCHING FOR INDIVIDUAL CAR CARDS...\n")
        
        # Strategy 1: Find all links to /vehicle/
        vehicle_links = soup.find_all('a', href=re.compile(r'/vehicle/'))
        print(f"✅ Found {len(vehicle_links)} links to /vehicle/\n")
        
        if vehicle_links:
            print("="*80)
            print("📋 ANALYZING FIRST 3 VEHICLE LINKS")
            print("="*80)
            
            for idx, link in enumerate(vehicle_links[:3], 1):
                print(f"\n{'='*80}")
                print(f"VEHICLE LINK {idx}")
                print(f"{'='*80}")
                
                # Get the link's parent (this is likely the car card)
                card = link.parent
                
                # Try to find the actual card container
                # Walk up the tree to find a containing div with substantial content
                for _ in range(5):  # Try up to 5 levels up
                    if card and card.name == 'div':
                        card_text = card.get_text(" ", strip=True)
                        # Check if this div contains a full car listing (price + mileage + year)
                        has_price = re.search(r'€\s*\d', card_text)
                        has_km = re.search(r'\d+\s*km', card_text)
                        has_year = re.search(r'20\d{2}', card_text)
                        
                        if has_price and has_km and has_year and len(card_text) > 100:
                            break  # Found the card!
                    card = card.parent if card else None
                
                if not card:
                    print("⚠️ Could not find card container")
                    continue
                
                print(f"\n1. CARD CONTAINER:")
                print(f"   Tag: {card.name}")
                print(f"   Classes: {card.get('class', [])}")
                print(f"   ID: {card.get('id', 'None')}")
                
                # Get all text from card
                card_text = card.get_text(" ", strip=True)
                print(f"\n2. FULL CARD TEXT:")
                print(f"   {card_text}")
                print(f"\n   Length: {len(card_text)} characters")
                
                # Analyze structure
                print(f"\n3. CARD STRUCTURE:")
                
                # Find all divs in card
                all_divs = card.find_all('div', recursive=False)
                print(f"   Direct child divs: {len(all_divs)}")
                for i, div in enumerate(all_divs[:5], 1):
                    div_classes = div.get('class', [])
                    div_text = div.get_text(" ", strip=True)[:80]
                    print(f"      Div {i}: classes={div_classes}")
                    print(f"              text='{div_text}...'")
                
                # Find images
                images = card.find_all('img')
                print(f"\n   Images: {len(images)}")
                for img in images[:2]:
                    print(f"      src: {img.get('src', 'N/A')[:80]}")
                    print(f"      alt: {img.get('alt', 'N/A')[:80]}")
                
                # Find all spans
                spans = card.find_all('span')
                print(f"\n   Spans: {len(spans)}")
                for i, span in enumerate(spans[:10], 1):
                    span_text = span.get_text(strip=True)
                    if span_text:
                        print(f"      Span {i}: '{span_text}'")
                
                # Find all strong/b tags
                strong_tags = card.find_all(['strong', 'b', 'h1', 'h2', 'h3', 'h4', 'h5'])
                print(f"\n   Bold/Heading elements: {len(strong_tags)}")
                for i, tag in enumerate(strong_tags[:5], 1):
                    print(f"      {tag.name}: '{tag.get_text(strip=True)}'")
                
                print(f"\n4. DATA EXTRACTION TEST:")
                
                # Try to extract price
                price_patterns = [
                    (r'€\s*(\d{1,3}(?:\.\d{3})*)\s', "European format with dots"),
                    (r'€\s*(\d+(?:,\d{3})*)', "US format with commas"),
                    (r'(\d{1,3}(?:\.\d{3})*)\s*€', "Price after symbol"),
                ]
                
                for pattern, desc in price_patterns:
                    match = re.search(pattern, card_text)
                    if match:
                        print(f"   ✅ Price ({desc}): {match.group(0)}")
                        break
                else:
                    print(f"   ❌ Price not found")
                
                # Try to extract mileage
                mileage_match = re.search(r'(\d{1,3}(?:\.\d{3})*)\s*km', card_text, re.IGNORECASE)
                if mileage_match:
                    print(f"   ✅ Mileage: {mileage_match.group(0)}")
                else:
                    print(f"   ❌ Mileage not found")
                
                # Try to extract year
                year_match = re.search(r'(\d{2})/(\d{4})', card_text)
                if year_match:
                    print(f"   ✅ Year (MM/YYYY): {year_match.group(0)}")
                else:
                    year_match = re.search(r'\b(20\d{2})\b', card_text)
                    if year_match:
                        print(f"   ✅ Year: {year_match.group(0)}")
                    else:
                        print(f"   ❌ Year not found")
                
                # Try to extract title
                title_match = re.search(r'((?:Audi|BMW|Mercedes|Volkswagen|Renault|Cupra|VW|Porsche|Skoda)\s+[A-Z0-9][^\n€]+?)(?:\s+\*|\s+€|$)', card_text, re.IGNORECASE)
                if title_match:
                    print(f"   ✅ Title: {title_match.group(1).strip()}")
                else:
                    print(f"   ❌ Title not found")
                
                # Extract link
                print(f"   ✅ Link: {link.get('href')}")
                
                # Save individual card HTML
                with open(f"webcar_card_{idx}.html", "w", encoding="utf-8") as f:
                    f.write(card.prettify())
                print(f"\n💾 Saved card HTML to webcar_card_{idx}.html")
        
        else:
            print("❌ No vehicle links found!")
        
        print("\n" + "="*80)
        print("✅ ANALYSIS COMPLETE")
        print("="*80)
        print("\nCheck the saved HTML files:")
        print("  - webcar_full_debug.html (full page)")
        print("  - webcar_card_1.html, webcar_card_2.html, etc. (individual cards)")
        
    finally:
        driver.quit()


# Run the analysis
if __name__ == "__main__":
    # Use the correct URL from user
    url = "https://www.webcar.eu/eu-en/used-and-new-cars?filter%5Bregistered_on%5D%5Bfrom%5D=2021&filter%5Bregistered_on%5D%5Bto%5D=2025&filter%5Bmake%5D%5B1%5D=10&filter%5Bmodel%5D%5B1%5D=96&formSubmitted=true&make_model=audi-a4"
    
    detailed_card_analysis(url)