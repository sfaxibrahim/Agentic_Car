# services/car_deal_service.py
from .autoscout_service import CarSearchParams, fetch_listings_with_fallback
from langchain_community.chat_models import ChatOllama
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from pydantic import BaseModel, Field
from typing import Optional
from config.settings import settings
import json


class CarSearchCriteria(BaseModel):
    """Structured car search criteria extracted from user query."""
    make: str = Field(description="Car manufacturer (e.g., BMW, Mercedes, Toyota)")
    model: Optional[str] = Field(None, description="Specific car model (e.g., X5, C-Class, Corolla)")
    year_from: Optional[int] = Field(None, description="Minimum year (e.g., 2020)")
    year_to: Optional[int] = Field(None, description="Maximum year (e.g., 2024)")
    price_max: Optional[int] = Field(None, description="Maximum price in EUR")
    price_min: Optional[int] = Field(None, description="Minimum price in EUR")
    mileage_max: Optional[int] = Field(None, description="Maximum mileage in kilometers")
    fuel_type: Optional[str] = Field(None, description="Fuel type: diesel, petrol, electric, hybrid, lpg")
    transmission: Optional[str] = Field(None, description="Transmission: manual, automatic, semi-automatic")
    location: Optional[str] = Field(None, description="Preferred location or country")


def extract_car_details(query: str) -> CarSearchCriteria:
    """
    Use LLM with structured output to extract car search criteria from user query.
    Returns a validated Pydantic model.
    """
    # Initialize LLM
    llm = ChatOllama(
        model=settings.OLLAMA_MODEL,
        temperature=0,  # Make it deterministic
        format="json",  # Force JSON output
        verbose=False
    )
    
    # Create prompt template with clear instructions
    prompt = PromptTemplate(
        template="""Extract car search criteria from this query: "{query}"

CRITICAL RULES:
1. Return ONLY valid JSON - no comments, no markdown, no explanations
2. Use null for missing values, NOT comments
3. Do not wrap in code blocks

Examples:
Query: "BMW X5 from 2020"
{{"make": "BMW", "model": "X5", "year_from": 2020, "year_to": null, "price_max": null, "price_min": null, "mileage_max": null, "fuel_type": null, "transmission": null, "location": null}}

Query: "Mercedes under 50000 euros"
{{"make": "Mercedes", "model": null, "year_from": null, "year_to": null, "price_max": 50000, "price_min": null, "mileage_max": null, "fuel_type": null, "transmission": null, "location": null}}

Query: "2020 Audi A4 under €50,000"
{{"make": "Audi", "model": "A4", "year_from": 2020, "year_to": null, "price_max": 50000, "price_min": null, "mileage_max": null, "fuel_type": null, "transmission": null, "location": null}}

Now extract from: "{query}"

Return only the JSON:""",
        input_variables=["query"]
    )
    
    try:
        # Get response from LLM
        chain = prompt | llm
        response = chain.invoke({"query": query})
        
        # Extract content
        json_str = response.content if hasattr(response, 'content') else str(response)
        
        # Clean the response - remove markdown code blocks and extra text
        json_str = json_str.strip()
        if "```" in json_str:
            # Extract JSON from markdown code blocks
            import re
            match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', json_str, re.DOTALL)
            if match:
                json_str = match.group(1)
        
        # Remove any text before first { or after last }
        start = json_str.find('{')
        end = json_str.rfind('}')
        if start != -1 and end != -1:
            json_str = json_str[start:end+1]
        
        # Parse JSON and create Pydantic model
        import json
        data = json.loads(json_str)
        result = CarSearchCriteria(**data)
        
        print(f"✅ Successfully extracted criteria: {result}")
        return result
        
    except Exception as e:
        print(f"⚠️ Error extracting criteria: {e}")
        print(f"Raw LLM output: {json_str if 'json_str' in locals() else 'N/A'}")
        
        # Fallback: try to extract make at minimum
        make = _extract_make_fallback(query)
        
        # Try to extract other basic info from query using regex
        import re
        fallback_data = {"make": make}
        
        # Extract year
        year_match = re.search(r'\b(20\d{2})\b', query)
        if year_match:
            fallback_data["year_from"] = int(year_match.group(1))
        
        # Extract price
        price_match = re.search(r'(?:under|max|maximum|up to|€|euro[s]?)\s*[€]?\s*([\d,\.]+)(?:k|000)?', query, re.IGNORECASE)
        if price_match:
            price_str = price_match.group(1).replace(',', '').replace('.', '')
            price = int(price_str)
            if 'k' in query.lower() or (price < 1000 and 'euro' in query.lower()):
                price *= 1000
            fallback_data["price_max"] = price
        
        # Extract model (words after make)
        query_lower = query.lower()
        if make.lower() in query_lower:
            idx = query_lower.index(make.lower()) + len(make)
            remaining = query[idx:].strip()
            # Get first 1-2 words after make as potential model
            words = remaining.split()[:2]
            if words and not any(w.lower() in ['from', 'under', 'with', 'in', 'at'] for w in words[:1]):
                potential_model = ' '.join(words).strip(',.;')
                if potential_model and len(potential_model) > 1:
                    fallback_data["model"] = potential_model
        
        print(f"📦 Using fallback extraction: {fallback_data}")
        return CarSearchCriteria(**fallback_data)


def _extract_make_fallback(query: str) -> str:
    """Fallback method to extract car make using simple pattern matching."""
    query_lower = query.lower()
    
    # Common car makes
    makes = [
        "bmw", "mercedes", "mercedes-benz", "audi", "volkswagen", "vw",
        "toyota", "honda", "ford", "chevrolet", "nissan", "mazda",
        "hyundai", "kia", "volvo", "porsche", "ferrari", "lamborghini",
        "tesla", "lexus", "jaguar", "land rover", "mini", "fiat",
        "peugeot", "renault", "citroen", "seat", "skoda", "opel"
    ]
    
    for make in makes:
        if make in query_lower:
            return make.title()
    
    # Default if nothing found
    return "BMW"


def _rank_listings(listings: list, criteria: CarSearchCriteria) -> list:
    """
    Rank listings based on how well they match user criteria.
    Returns top 3 best matches with scores.
    """
    if not listings:
        return []
    
    def score_listing(listing):
        score = 0
        reasons = []
        
        # Price matching (prefer lower prices if max specified)
        if criteria.price_max and listing.get('price'):
            if listing['price'] <= criteria.price_max:
                score += 10
                reasons.append(f"Within budget (€{listing['price']:,})")
                # Bonus for being well under budget
                price_ratio = listing['price'] / criteria.price_max
                score += (1 - price_ratio) * 5
                if price_ratio < 0.8:
                    reasons.append(f"Great value ({int((1-price_ratio)*100)}% under budget)")
        
        # Price minimum matching
        if criteria.price_min and listing.get('price'):
            if listing['price'] >= criteria.price_min:
                score += 5
        
        # Year matching (prefer newer if year_from specified)
        if criteria.year_from and listing.get('year') and listing['year'] != 'N/A':
            if listing['year'] >= criteria.year_from:
                score += 10
                reasons.append(f"Newer model ({listing['year']})")
                # Bonus for newer cars
                year_diff = listing['year'] - criteria.year_from
                score += min(year_diff, 5)
        
        # Year maximum matching
        if criteria.year_to and listing.get('year') and listing['year'] != 'N/A':
            if listing['year'] <= criteria.year_to:
                score += 5
        
        # Mileage matching (prefer lower mileage if max specified)
        if criteria.mileage_max and listing.get('mileage'):
            if listing['mileage'] <= criteria.mileage_max:
                score += 8
                reasons.append(f"Low mileage ({listing['mileage']:,} km)")
                # Bonus for lower mileage
                mileage_ratio = listing['mileage'] / criteria.mileage_max
                score += (1 - mileage_ratio) * 4
        
        # Fuel type exact match
        if criteria.fuel_type and listing.get('fuel') != 'N/A':
            if criteria.fuel_type.lower() in listing['fuel'].lower():
                score += 5
                reasons.append(f"Matches fuel type ({listing['fuel']})")
        
        # Transmission exact match
        if criteria.transmission and listing.get('transmission') != 'N/A':
            if criteria.transmission.lower() in listing['transmission'].lower():
                score += 5
                reasons.append(f"Matches transmission ({listing['transmission']})")
        
        # Model exact match bonus
        if criteria.model and listing.get('title'):
            if criteria.model.lower() in listing['title'].lower():
                score += 8
                reasons.append(f"Exact model match")
        
        return score, reasons
    
    # Score and sort listings
    scored = []
    for listing in listings:
        score, reasons = score_listing(listing)
        listing['match_score'] = score
        listing['match_reasons'] = reasons
        scored.append((score, listing))
    
    scored.sort(key=lambda x: x[0], reverse=True)
    
    # Return top 3
    return [listing for score, listing in scored[:3]]


def car_search(query: str) -> str:
    """
    Main tool function for LangChain agent.
    Returns a formatted string with top 3 car recommendations.
    """
    print(f"\n🔍 Car search query: {query}")
    
    # Extract search criteria using structured LLM
    criteria = extract_car_details(query)
    print(f"📋 Extracted criteria:")
    print(f"   Make: {criteria.make}")
    print(f"   Model: {criteria.model}")
    print(f"   Year: {criteria.year_from}-{criteria.year_to}")
    print(f"   Price: €{criteria.price_min or 0}-{criteria.price_max or '∞'}")
    print(f"   Mileage: ≤{criteria.mileage_max or '∞'} km")
    print(f"   Fuel: {criteria.fuel_type or 'Any'}")
    print(f"   Transmission: {criteria.transmission or 'Any'}")
    
    # Build search parameters
    params = CarSearchParams(
        make=criteria.make,
        model=criteria.model,
        year_from=criteria.year_from,
        year_to=criteria.year_to,
        price_max=criteria.price_max,
        mileage_max=criteria.mileage_max,
        fuel_type=criteria.fuel_type,
        transmission=criteria.transmission,
    )
    
    # Fetch listings
    listings = fetch_listings_with_fallback(params, max_results=20, pause=True)
    
    if not listings:
        return f"No {criteria.make} listings found matching your criteria. Try broadening your search parameters."
    
    print(f"✅ Found {len(listings)} total {criteria.make} listings")
    
    # Rank and select top 3
    top_3 = _rank_listings(listings, criteria)
    
    if not top_3:
        top_3 = listings[:3]  # fallback to first 3 if ranking fails
    
    print(f"🏆 Selected top 3 listings")
    
    # Format response as readable text
    result = f"Found {len(listings)} {criteria.make} listings"
    if criteria.model:
        result += f" ({criteria.model})"
    result += ". Here are the top 3 matches:\n\n"
    
    for i, car in enumerate(top_3, 1):
        title = car.get('title', 'N/A').replace('\n', ' ').replace('•', '').strip()
        price = car.get('price_raw', 'N/A')
        year = car.get('year', 'N/A')
        mileage = car.get('mileage_raw', 'N/A')
        fuel = car.get('fuel', 'N/A')
        transmission = car.get('transmission', 'N/A')
        location = car.get('location', 'N/A')
        link = car.get('link', 'N/A')

        result += f"**Option {i}:**\n"
        result += f"  • {title}\n"
        result += f"  • Price: {price}\n"
        result += f"  • Year: {year}\n"
        result += f"  • Mileage: {mileage}\n"
        result += f"  • Fuel: {fuel}\n"
        result += f"  • Transmission: {transmission}\n"
        result += f"  • Location: {location}\n"
        result += f"  • Link: {link}\n\n"

        
    
    # Save detailed results as JSON
    with open("car_search_results.json", "w", encoding="utf-8") as f:
        json.dump({
            "query": query,
            "criteria": criteria.dict(),
            "total_found": len(listings),
            "top_3": top_3,
            "all_listings": listings
        }, f, ensure_ascii=False, indent=2)
    
    print("💾 Saved detailed results to car_search_results.json")
    
    return result