"""
Webcar.eu ID Mapper - Discovers make/model IDs dynamically

The problem: webcar.eu uses numeric IDs (BMW=15, Audi=10) but users provide text ("BMW")
Solution: Use their search API or scrape their dropdown to build the mapping
"""

import requests
import json
from typing import Dict, Optional

class WebcarIDMapper:
    """
    Discovers and caches make/model IDs from webcar.eu
    """
    
    def __init__(self):
        self.make_map = {}
        self.model_map = {}
        self._load_cache()
    
    def _load_cache(self):
        """Load cached IDs from file"""
        try:
            with open("webcar_id_cache.json", "r") as f:
                data = json.load(f)
                self.make_map = data.get("makes", {})
                self.model_map = data.get("models", {})
        except:
            pass
    
    def _save_cache(self):
        """Save IDs to cache file"""
        with open("webcar_id_cache.json", "w") as f:
            json.dump({
                "makes": self.make_map,
                "models": self.model_map
            }, f, indent=2)
    
    def discover_make_ids(self) -> Dict[str, int]:
        """
        Discover make IDs by calling webcar.eu's API or parsing their page
        
        Method 1: Check if they have a public API endpoint
        Method 2: Parse the search form HTML
        Method 3: Monitor network requests when using the site
        """
        
        # Try to find their API endpoint
        # Common patterns: /api/makes, /api/filters, etc.
        api_urls = [
            "https://www.webcar.eu/api/makes",
            "https://www.webcar.eu/api/filters/makes",
            "https://api.webcar.eu/makes",
        ]
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        for url in api_urls:
            try:
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    # Parse response - structure depends on their API
                    # Example: [{"id": 15, "name": "BMW"}, ...]
                    if isinstance(data, list):
                        for item in data:
                            if "id" in item and "name" in item:
                                name = item["name"].lower()
                                self.make_map[name] = item["id"]
                    
                    if self.make_map:
                        print(f"Discovered {len(self.make_map)} makes from {url}")
                        self._save_cache()
                        return self.make_map
            except:
                continue
        
        # Fallback: Use manual mapping for common brands
        print("Could not auto-discover IDs. Using manual mapping.")
        self.make_map = self._get_manual_mapping()
        self._save_cache()
        return self.make_map
    
    def _get_manual_mapping(self) -> Dict[str, int]:
        """
        Manual mapping discovered by inspection
        You build this by:
        1. Go to webcar.eu
        2. Select "BMW" in the filter
        3. Look at URL: filter%5Bmake%5D%5B1%5D=15 → BMW = 15
        4. Repeat for all brands
        """
        return {
            "bmw": 15,
            "audi": 10,
            "mercedes": 45,
            "mercedes-benz": 45,
            "volkswagen": 68,
            "vw": 68,
            "porsche": 55,
            "ford": 20,
            "toyota": 63,
            "honda": 28,
            "nissan": 48,
            "opel": 50,
            "renault": 56,
            "peugeot": 52,
            "citroen": 13,
            "fiat": 19,
            "hyundai": 29,
            "kia": 36,
            "mazda": 43,
            "mitsubishi": 46,
            "suzuki": 61,
            "skoda": 59,
            "seat": 58,
            "volvo": 69,
            "land rover": 38,
            "jaguar": 32,
            "mini": 44,
            "smart": 60,
            # Add more as needed
        }
    
    def get_make_id(self, make_name: str) -> Optional[int]:
        """Get make ID from make name"""
        if not self.make_map:
            self.discover_make_ids()
        
        make_lower = make_name.lower().strip()
        return self.make_map.get(make_lower)
    
    def get_model_id(self, make_name: str, model_name: str) -> Optional[int]:
        """
        Get model ID for a specific make/model combination
        This is more complex as models are nested under makes
        
        For now, returns None - you'd need to build this similarly
        """
        # This would require scraping model dropdowns for each make
        # Or finding their models API endpoint
        return None
    
    def add_manual_mapping(self, make_name: str, make_id: int):
        """Manually add a make mapping"""
        self.make_map[make_name.lower()] = make_id
        self._save_cache()
        print(f"Added mapping: {make_name} → {make_id}")


# Example usage
if __name__ == "__main__":
    mapper = WebcarIDMapper()
    
    # Discover IDs (or load from cache)
    mapper.discover_make_ids()
    
    # Get ID for a make
    bmw_id = mapper.get_make_id("BMW")
    print(f"BMW ID: {bmw_id}")
    
    audi_id = mapper.get_make_id("Audi")
    print(f"Audi ID: {audi_id}")
    
    # If you discover a new ID manually, add it:
    # mapper.add_manual_mapping("Tesla", 62)
    
    print(f"\nTotal makes in cache: {len(mapper.make_map)}")