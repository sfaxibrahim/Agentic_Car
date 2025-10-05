import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import re
import time
import random
import json

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

class CarSearchParams:
    def __init__(
        self,
        make: str,
        model: Optional[str] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        price_max: Optional[int] = None,
        mileage_max: Optional[int] = None,
        fuel_type: Optional[str] = None,
        transmission: Optional[str] = None,
    ):
        self.make = make
        self.model = model
        self.year_from = year_from
        self.year_to = year_to
        self.price_max = price_max
        self.mileage_max = mileage_max
        self.fuel_type = fuel_type
        self.transmission = transmission

    def build_url(self) -> str:
        """
        Build an AutoScout24 URL.
        Note: keep model optional — we will try it, but retriever can relax later.
        """
        base = f"https://www.autoscout24.com/lst/{self.make.lower()}"
        if self.model:
            base += f"/{self.model.lower()}"

        params = []
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
            code = trans_map.get(self.transmission.lower()) if self.transmission else None
            if code:
                params.append(f"gear={code}")

        if params:
            base += "?" + "&".join(params)
        return base


def _clean_price(raw: str) -> Optional[int]:
    if not raw:
        return None
    # Keep the euro sign and numbers, remove thousands separators and text
    m = re.search(r'€\s?([\d\.\s,]+)', raw)
    if not m:
        # sometimes price appears like "EUR 34,900"
        m = re.search(r'([\d\.\s,]+)\s*(€|EUR)', raw)
    if not m:
        return None
    num = m.group(1)
    # remove spaces and dots that are thousand separators; keep digits and commas as decimal if any
    num = num.replace(" ", "").replace(".", "").replace(",", "")
    try:
        return int(num)
    except:
        return None


def _clean_km(raw: str) -> Optional[int]:
    if not raw:
        return None
    m = re.search(r'([\d\.\s,]+)\s*km', raw, re.IGNORECASE)
    if not m:
        return None
    num = m.group(1).replace(" ", "").replace(".", "").replace(",", "")
    try:
        return int(num)
    except:
        return None
    
def _extract_from_listing_tag(tag) -> Dict:
    """Extract clean structured data from one listing card using data-* attributes."""
    text = tag.get_text(" ", strip=True)

    # PRIORITY 1: Extract from data-* attributes (most reliable)
    data_attrs = tag.attrs
    
    # Link - Build from data-guid attribute
    link = "N/A"
    guid = data_attrs.get('data-guid') or data_attrs.get('id')
    if guid:
        # AutoScout24 listing URLs follow pattern: /lst/{make}/{model}--{guid}
        link = f"https://www.autoscout24.com/offers/{guid}"
    
    # Year - Extract from data-first-registration
    year = "N/A"
    first_reg = data_attrs.get('data-first-registration')
    if first_reg:
        # data-first-registration might be like "2024-03" or "202403" or "2024"
        m = re.search(r'(19|20)\d{2}', str(first_reg))
        if m:
            try:
                year = int(m.group(0))
            except:
                pass
    
    # Mileage - Extract from data-mileage
    mileage = None
    data_mileage = data_attrs.get('data-mileage')
    if data_mileage:
        try:
            # data-mileage is usually just a number
            mileage = int(str(data_mileage).replace(",", "").replace(".", ""))
        except:
            pass
    
    # Price - Extract from data-price
    price = None
    data_price = data_attrs.get('data-price')
    if data_price:
        try:
            price = int(str(data_price).replace(",", "").replace(".", ""))
        except:
            pass
    
    # Fuel - Extract from data-fuel-type
    fuel = data_attrs.get('data-fuel-type', 'N/A')
    if fuel != 'N/A':
        # Capitalize first letter
        fuel = fuel.capitalize() if fuel else 'N/A'
    
    # PRIORITY 2: Extract from visible text (fallback)
    
    # Title
    title = None
    for sel in ["[data-testid='listing-title']", "h2 a", "h2"]:
        el = tag.select_one(sel)
        if el and el.get_text(strip=True):
            title = el.get_text(strip=True)
            break
    title = title or "N/A"

    # Price (fallback if data-price not available)
    price_raw = None
    if price:
        price_raw = f"€ {price:,}".replace(",", ".")
    else:
        el = tag.select_one("[data-testid='regular-price']") or tag.select_one(".cldt-price")
        if el:
            price_raw = el.get_text(strip=True)
        else:
            m = re.search(r'€\s?[\d\.,]+', text)
            price_raw = m.group(0) if m else None
        price = _clean_price(price_raw)

    # Year (fallback if data-first-registration not available)
    if year == "N/A":
        # Look for year in text patterns
        year_patterns = [
            r'\(First Registration\)\s*(\d{4})',  # (First Registration) 2023
            r'First Registration\s*[:\-]?\s*(\d{4})',  # First Registration: 2023
            r'(\d{1,2})/(\d{4})',  # MM/YYYY format
        ]
        
        for pattern in year_patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                try:
                    year_str = m.group(2) if len(m.groups()) > 1 else m.group(1)
                    year = int(year_str)
                    break
                except:
                    continue

    # Mileage (fallback if data-mileage not available)
    if mileage is None:
        mileage_el = tag.select_one("[data-testid='mileage']") or tag.select_one(".mileage")
        if mileage_el:
            mileage_text = mileage_el.get_text(strip=True)
            mileage = _clean_km(mileage_text)
        
        # Try to find mileage in text
        if mileage is None:
            mileage_patterns = [
                r'(\d[\d\.\s,]*)\s*km\b',
            ]
            
            for pattern in mileage_patterns:
                m = re.search(pattern, text, re.IGNORECASE)
                if m:
                    mileage = _clean_km(m.group(0))
                    if mileage is not None:
                        break

    # Fuel (fallback if data-fuel-type not available)
    if fuel == 'N/A':
        fuel_el = tag.select_one("[data-testid='fuel']")
        if fuel_el:
            fuel = fuel_el.get_text(strip=True)
        else:
            fuel_patterns = {
                "Diesel": r'\bdiesel\b',
                "Petrol": r'\bpetrol\b',
                "Gasoline": r'\bgasoline\b|\bbenzin\b',
                "Electric": r'\belectric\b',
                "Hybrid": r'\bhybrid\b'
            }
            for fuel_type, pattern in fuel_patterns.items():
                if re.search(pattern, text, re.IGNORECASE):
                    fuel = fuel_type
                    break

    # Transmission
    transmission = "N/A"
    trans_el = tag.select_one("[data-testid='transmission']")
    if trans_el:
        transmission = trans_el.get_text(strip=True)
    else:
        trans_patterns = {
            "Manual": r'\bmanual\b',
            "Automatic": r'\bautomatic\b',
            "Semi-automatic": r'\bsemi-automatic\b'
        }
        for trans_type, pattern in trans_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                transmission = trans_type
                break

    # Location
    location = "N/A"
    loc_el = tag.select_one("[data-testid='seller-location']")
    if loc_el:
        location = loc_el.get_text(" ", strip=True)
    else:
        # Extract from data-listing-zip-code if available
        zip_code = data_attrs.get('data-listing-zip-code')
        if zip_code:
            # Try to find city name after zip code in text
            m = re.search(rf'{zip_code}\s+([A-Za-zÄÖÜäöüß\-\s]+?)(?:\s*•|\s*\+|$)', text)
            if m:
                location = f"{zip_code} {m.group(1).strip()}"
            else:
                location = str(zip_code)
        else:
            # Fallback to regex patterns
            m = re.search(r'DE-(\d{4,5})\s+([A-Za-zÄÖÜäöüß\-\s]+)', text)
            if m:
                location = f"{m.group(1)} {m.group(2).strip()}"
            else:
                m = re.search(r'(\d{4,5})\s+([A-Za-zÄÖÜäöüß\-\s]+?)(?:\s*•|$)', text)
                if m:
                    location = f"{m.group(1)} {m.group(2).strip()}"

    return {
        "title": title,
        "price_raw": price_raw or "N/A",
        "price": price,
        "year": year,
        "mileage_raw": f"{mileage} km" if mileage is not None else "N/A",
        "mileage": mileage,
        "fuel": fuel,
        "transmission": transmission,
        "location": location,
        "link": link,
        "snippet": text[:300],
    }

def _find_listing_containers(soup: BeautifulSoup) -> List:
    """
    Find listing containers - prioritize articles with data-guid attribute.
    """
    # First try to find articles with data-guid (most reliable)
    articles_with_guid = soup.find_all('article', attrs={'data-guid': True})
    if articles_with_guid:
        print(f"  ✅ Found {len(articles_with_guid)} articles with data-guid attribute")
        return articles_with_guid
    
    # Fallback to other selectors
    selectors = [
        "article.cldt-summary-full-item",
        "article.ListItem_article__qyYw7",
        "article[data-testid='listing-summary-container']",
        "article",
    ]
    
    for sel in selectors:
        try:
            found = soup.select(sel)
            if found:
                # Filter to only include elements that look like car listings
                filtered = []
                for element in found:
                    text = element.get_text(" ", strip=True)
                    # Check if this looks like a car listing
                    if (re.search(r'€\s?[\d\.,]+', text) and 
                        (re.search(r'\b(km|BMW|Audi|Mercedes|Volkswagen|Automatic|Manual)\b', text, re.IGNORECASE) or
                         re.search(r'\b(19|20)\d{2}\b', text))):
                        filtered.append(element)
                
                if filtered:
                    print(f"  ✅ Found {len(filtered)} listings with selector: {sel}")
                    return filtered
        except Exception as e:
            continue
    
    return []


def fetch_listings_with_fallback(params: CarSearchParams, max_results: int = 20, pause: bool = True) -> List[Dict]:
    """
    Try fetching with the given params. If no results, relax filters.
    Returns structured listing dicts.
    """
    attempts = []

    # ordering of attempts: full -> without model -> without year_from -> make-only
    attempts.append(params)
    if params.model:
        p2 = CarSearchParams(
            make=params.make, model=None, year_from=params.year_from, year_to=params.year_to,
            price_max=params.price_max, mileage_max=params.mileage_max, fuel_type=params.fuel_type, transmission=params.transmission
        )
        attempts.append(p2)
    if params.year_from:
        p3 = CarSearchParams(
            make=params.make, model=None, year_from=None, year_to=params.year_to,
            price_max=params.price_max, mileage_max=params.mileage_max, fuel_type=params.fuel_type, transmission=params.transmission
        )
        attempts.append(p3)

    # always end with just make-only if none above worked
    p_make_only = CarSearchParams(make=params.make)
    attempts.append(p_make_only)

    for i, attempt in enumerate(attempts, 1):
        url = attempt.build_url()
        print(f"\nAttempt {i}: Fetching {url}")
        if pause:
            time.sleep(random.uniform(1.0, 2.2))  # polite pause
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"  ❌ HTTP {resp.status_code} — skipping this attempt")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

        # Debug: Save HTML for inspection
        with open(f"debug_attempt_{i}.html", "w", encoding="utf-8") as f:
            f.write(resp.text)
        print(f"  💾 Saved HTML to debug_attempt_{i}.html for inspection")

        # find listing containers robustly
        cards = _find_listing_containers(soup)
        
        if not cards:
            print("  ⚠️ No listing containers found on page.")
            continue

        print(f"  🔍 Found {len(cards)} potential listing cards")
        parsed = []
        for j, tag in enumerate(cards[:max_results]):
            try:
                item = _extract_from_listing_tag(tag)
                # Only add if it has basic car-like data
                if item.get('price') or item.get('title') != "N/A":
                    parsed.append(item)
                    print(f"    ✅ Parsed card {j+1}: {item.get('title')[:50]}... | Link: {item.get('link')[:50]}...")
                else:
                    print(f"    ⚠️ Skipped card {j+1} - insufficient data")
            except Exception as e:
                print(f"    ❌ Error parsing card {j+1}: {e}")
                continue

        if parsed:
            print(f"  ✅ Successfully parsed {len(parsed)} listings on attempt {i}")
            return parsed
        else:
            print("  ⚠️ No valid parsed listings found — trying next fallback.")

    # if we get here, nothing found
    print("❌ No listings found after all fallback attempts.")
    return []


def print_cards(listings: List[Dict]) -> None:
    if not listings:
        print("No listings to show.")
        return

    for i, car in enumerate(listings, 1):
        print("-" * 60)
        print(f"Card {i}")
        print(f"Title      : {car.get('title')}")
        print(f"Price      : {car.get('price_raw')} (normalized: {car.get('price')})")
        print(f"Year       : {car.get('year')}")
        print(f"Mileage    : {car.get('mileage_raw')}")
        print(f"Fuel       : {car.get('fuel')}")
        print(f"Transmission: {car.get('transmission')}")
        print(f"Location   : {car.get('location')}")
        print(f"Link       : {car.get('link')}")
        print(f"Snippet    : {car.get('snippet')}")
    print("-" * 60)


# Example usage
if __name__ == "__main__":
    params = CarSearchParams(
        make="Bmw",
        model="318",       # optional; retriever will relax if it yields nothing
        year_from=2025,
        price_max=50000
    )

    results = fetch_listings_with_fallback(params, max_results=20)
    print(f"\nFound {len(results)} listings total.")
    print_cards(results)

    # Optionally save to JSON
    with open("autoscout_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\nSaved results to autoscout_results.json")