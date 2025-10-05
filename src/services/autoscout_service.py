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

    def _normalize_for_url(self, text: str) -> str:
        """Normalize make/model names for URL construction."""
        if not text:
            return ""
        # Convert to lowercase, replace spaces and special chars with hyphens
        text = text.lower()
        text = re.sub(r'[^a-z0-9]+', '-', text)
        text = text.strip('-')
        return text

    def build_url(self) -> str:
        """
        Build an AutoScout24 URL.
        Simple path-based approach: /lst/{make}/{model}
        Keep it simple and let the fallback mechanism handle relaxing constraints.
        """
        # Normalize make for URL
        make_normalized = self.make.lower().replace(' ', '-')
        
        # Special handling for common make names
        make_map = {
            'mercedes': 'mercedes-benz',
            'mercedes-benz': 'mercedes-benz',
            'vw': 'volkswagen',
            'beemer': 'bmw',
            'benz': 'mercedes-benz'
        }
        make_normalized = make_map.get(make_normalized, make_normalized)
        
        # Start with make
        base = f"https://www.autoscout24.com/lst/{make_normalized}"
        
        # Add model if specified
        if self.model:
            model_normalized = self.model.lower().replace(' ', '-')
            base += f"/{model_normalized}"
        
        # Build query parameters
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
    m = re.search(r'€\s?([\d\.\s,]+)', raw)
    if not m:
        m = re.search(r'([\d\.\s,]+)\s*(€|EUR)', raw)
    if not m:
        return None
    num = m.group(1)
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


def _matches_make(title: str, make: str) -> bool:
    """Check if the listing title matches the requested make."""
    if not title or not make:
        return False
    # Normalize both for comparison
    title_lower = title.lower()
    make_lower = make.lower()
    
    # Direct match
    if make_lower in title_lower:
        return True
    
    # Handle common abbreviations
    abbreviations = {
        'mercedes': ['mercedes', 'mercedes-benz', 'merc', 'mb'],
        'bmw': ['bmw'],
        'volkswagen': ['volkswagen', 'vw'],
        'audi': ['audi'],
    }
    
    for key, variants in abbreviations.items():
        if make_lower in variants or make_lower == key:
            return any(variant in title_lower for variant in variants)
    
    return False
    

def _extract_from_listing_tag(tag) -> Dict:
    """Extract clean structured data from one listing card using data-* attributes."""
    text = tag.get_text(" ", strip=True)
    data_attrs = tag.attrs
    
    # Link
    link = "N/A"
    guid = data_attrs.get('data-guid') or data_attrs.get('id')
    if guid:
        link = f"https://www.autoscout24.com/offers/{guid}"
    
    # Year
    year = "N/A"
    first_reg = data_attrs.get('data-first-registration')
    if first_reg:
        m = re.search(r'(19|20)\d{2}', str(first_reg))
        if m:
            try:
                year = int(m.group(0))
            except:
                pass
    
    # Mileage
    mileage = None
    data_mileage = data_attrs.get('data-mileage')
    if data_mileage:
        try:
            mileage = int(str(data_mileage).replace(",", "").replace(".", ""))
        except:
            pass
    
    # Price
    price = None
    data_price = data_attrs.get('data-price')
    if data_price:
        try:
            price = int(str(data_price).replace(",", "").replace(".", ""))
        except:
            pass
    
    # Fuel
    fuel = data_attrs.get('data-fuel-type', 'N/A')
    if fuel != 'N/A':
        fuel = fuel.capitalize() if fuel else 'N/A'
    
    # Title
    title = None
    for sel in ["[data-testid='listing-title']", "h2 a", "h2"]:
        el = tag.select_one(sel)
        if el and el.get_text(strip=True):
            title = el.get_text(strip=True)
            break
    title = title or "N/A"

    # Price fallback
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

    # Year fallback
    if year == "N/A":
        year_patterns = [
            r'\(First Registration\)\s*(\d{4})',
            r'First Registration\s*[:\-]?\s*(\d{4})',
            r'(\d{1,2})/(\d{4})',
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

    # Mileage fallback
    if mileage is None:
        mileage_el = tag.select_one("[data-testid='mileage']") or tag.select_one(".mileage")
        if mileage_el:
            mileage_text = mileage_el.get_text(strip=True)
            mileage = _clean_km(mileage_text)
        
        if mileage is None:
            m = re.search(r'(\d[\d\.\s,]*)\s*km\b', text, re.IGNORECASE)
            if m:
                mileage = _clean_km(m.group(0))

    # Fuel fallback
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
        zip_code = data_attrs.get('data-listing-zip-code')
        if zip_code:
            m = re.search(rf'{zip_code}\s+([A-Za-zÄÖÜäöüß\-\s]+?)(?:\s*•|\s*\+|$)', text)
            if m:
                location = f"{zip_code} {m.group(1).strip()}"
            else:
                location = str(zip_code)
        else:
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
    """Find listing containers - prioritize articles with data-guid attribute."""
    articles_with_guid = soup.find_all('article', attrs={'data-guid': True})
    if articles_with_guid:
        print(f"  ✅ Found {len(articles_with_guid)} articles with data-guid attribute")
        return articles_with_guid
    
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
                filtered = []
                for element in found:
                    text = element.get_text(" ", strip=True)
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
    IMPORTANT: Also filters results to only include cars matching the requested make.
    """
    attempts = []

    # Ordering: full -> without model -> without year_from -> make-only
    attempts.append(params)
    if params.model:
        p2 = CarSearchParams(
            make=params.make, model=None, year_from=params.year_from, year_to=params.year_to,
            price_max=params.price_max, mileage_max=params.mileage_max, 
            fuel_type=params.fuel_type, transmission=params.transmission
        )
        attempts.append(p2)
    if params.year_from:
        p3 = CarSearchParams(
            make=params.make, model=None, year_from=None, year_to=params.year_to,
            price_max=params.price_max, mileage_max=params.mileage_max, 
            fuel_type=params.fuel_type, transmission=params.transmission
        )
        attempts.append(p3)

    p_make_only = CarSearchParams(make=params.make)
    attempts.append(p_make_only)

    for i, attempt in enumerate(attempts, 1):
        url = attempt.build_url()
        print(f"\nAttempt {i}: Fetching {url}")
        if pause:
            time.sleep(random.uniform(1.0, 2.2))
        
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"  ❌ HTTP {resp.status_code} — skipping this attempt")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

        with open(f"debug_attempt_{i}.html", "w", encoding="utf-8") as f:
            f.write(resp.text)
        print(f"  💾 Saved HTML to debug_attempt_{i}.html")

        cards = _find_listing_containers(soup)
        
        if not cards:
            print("  ⚠️ No listing containers found on page.")
            continue

        print(f"  🔍 Found {len(cards)} potential listing cards")
        parsed = []
        for j, tag in enumerate(cards[:max_results]):
            try:
                item = _extract_from_listing_tag(tag)
                
                # CRITICAL: Verify the make matches what was requested
                if not _matches_make(item.get('title', ''), params.make):
                    print(f"    ⚠️ Skipped card {j+1} - wrong make: {item.get('title')[:50]}...")
                    continue
                
                # Only add if it has basic car data
                if item.get('price') or item.get('title') != "N/A":
                    parsed.append(item)
                    print(f"    ✅ Parsed card {j+1}: {item.get('title')[:50]}...")
                else:
                    print(f"    ⚠️ Skipped card {j+1} - insufficient data")
            except Exception as e:
                print(f"    ❌ Error parsing card {j+1}: {e}")
                continue

        if parsed:
            print(f"  ✅ Successfully parsed {len(parsed)} {params.make} listings on attempt {i}")
            return parsed
        else:
            print(f"  ⚠️ No valid {params.make} listings found — trying next fallback.")

    print(f"❌ No {params.make} listings found after all fallback attempts.")
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
    print("-" * 60)


if __name__ == "__main__":
    # Test with Mercedes C-Class
    params = CarSearchParams(
        make="Mercedes",
        model="C-Class",
        year_from=2020,
        price_max=50000
    )

    results = fetch_listings_with_fallback(params, max_results=20)
    print(f"\nFound {len(results)} Mercedes listings total.")
    print_cards(results)

    with open("autoscout_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\nSaved results to autoscout_results.json")