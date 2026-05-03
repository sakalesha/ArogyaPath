import os
import logging
import requests
import googlemaps
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class MapsClient:
    """
    Multi-Provider Maps Client.
    Prioritizes OpenStreetMap (Free) with Google Maps as a backup.
    """

    def __init__(self, google_api_key: Optional[str] = None):
        self.google_key = google_api_key or os.getenv("GOOGLE_MAPS_API_KEY")
        self.google_client = None
        
        if self.google_key and "YOUR_API_KEY" not in self.google_key:
            try:
                self.google_client = googlemaps.Client(key=self.google_key)
                logger.info("Google Maps Client initialized (Backup).")
            except Exception as e:
                logger.warning(f"Failed to init Google Maps: {e}")

    def is_active(self) -> bool:
        # OSM is always "active" because it's free/no key, 
        # but we'll return True to ensure the engine uses it.
        return True

    def find_hospitals(self, city: str, query: str = "hospital", coords: Optional[Dict] = None) -> List[Dict]:
        """
        Discovery entry point. Tries OSM first, falls back to Google.
        """
        logger.info(f"Starting Global Discovery for hospitals in {city}...")
        
        # 1. Try OpenStreetMap (Free, No Key required)
        osm_results = self._find_osm_hospitals(city, coords)
        if osm_results:
            logger.info(f"Found {len(osm_results)} hospitals via OpenStreetMap.")
            return [self._transform_osm_to_arogyapath(h) for h in osm_results]

        # 2. Fallback to Google Maps if OSM fails and key is present
        if self.google_client:
            logger.info("OSM returned no results. Trying Google Maps backup...")
            try:
                search_query = f"{query} in {city}"
                places_result = self.google_client.places(query=search_query, type="hospital")
                google_results = places_result.get("results", [])
                if google_results:
                    return [self._transform_google_to_arogyapath(h) for h in google_results]
            except Exception as e:
                logger.error(f"Google Maps fallback failed: {e}")

        return []

    # ── OpenStreetMap (OSM) Logic ──────────────────────────────────────────

    def _find_osm_hospitals(self, city: str, coords: Optional[Dict] = None) -> List[Dict]:
        """
        Uses Nominatim (Geocoding) + Overpass API (Search).
        """
        try:
            # Step A: Get City Coordinates (Either passed in or via Nominatim)
            if coords and "lat" in coords and "lng" in coords:
                lat, lon = coords["lat"], coords["lng"]
                logger.info(f"Using provided coordinates for {city}: {lat}, {lon}")
            else:
                # Use a more unique User-Agent to avoid blocks
                headers = {"User-Agent": "ArogyaPath_Hackathon_Research_Project/2.0 (ronad@example.com)"}
                geo_url = f"https://nominatim.openstreetmap.org/search?city={city}&format=json&limit=1"
                
                logger.info(f"Geocoding city: {city} via Nominatim...")
                geo_resp = requests.get(geo_url, headers=headers, timeout=15)
                
                if geo_resp.status_code != 200:
                    logger.error(f"Nominatim error: {geo_resp.status_code} {geo_resp.text}")
                    return []

                geo_data = geo_resp.json()
                if not geo_data:
                    return []
                lat, lon = geo_data[0]["lat"], geo_data[0]["lon"]

            # Step B: Search Hospitals via Overpass API (radius 15km)
            overpass_url = "https://overpass-api.de/api/interpreter"
            overpass_query = f"""
            [out:json][timeout:25];
            (
              node["amenity"="hospital"](around:15000,{lat},{lon});
              way["amenity"="hospital"](around:15000,{lat},{lon});
              relation["amenity"="hospital"](around:15000,{lat},{lon});
            );
            out center;
            """
            
            headers = {"User-Agent": "ArogyaPath_Hackathon_Research_Project/2.0 (ronad@example.com)"}
            ov_resp = requests.post(overpass_url, data={"data": overpass_query}, headers=headers, timeout=20)
            ov_data = ov_resp.json()
            
            return ov_data.get("elements", [])

        except Exception as e:
            logger.error(f"OSM discovery error: {e}")
            return []

    def _transform_osm_to_arogyapath(self, osm_element: Dict) -> Dict:
        tags = osm_element.get("tags", {})
        # OSM sometimes puts coords in 'center' (for ways/relations) or 'lat'/'lon' (for nodes)
        lat = osm_element.get("lat") or osm_element.get("center", {}).get("lat")
        lon = osm_element.get("lon") or osm_element.get("center", {}).get("lon")

        name = tags.get("name", "Unnamed Medical Centre")
        
        # Basic heuristic for type
        h_type = "private"
        if any(x in name.lower() for x in ["government", "district", "gh", "civil"]):
            h_type = "government"

        return {
            "id": f"osm_{osm_element.get('id')}",
            "name": name,
            "city": tags.get("addr:city", ""),
            "state": tags.get("addr:state", ""),
            "lat": lat,
            "lng": lon,
            "type": h_type,
            "rating": 3.5, # OSM doesn't have ratings, we use a neutral default
            "review_count": 10,
            "nabh_accredited": False,
            "cost_category": "medium",
            "cost_multiplier": 1.0,
            "icu_available": True,
            "emergency": True,
            "bed_count": "Unknown",
            "phone": tags.get("phone", tags.get("contact:phone", "N/A")),
            "tradeoff_tags": ["osm_data", "verified_location"],
            "procedures": []
        }

    # ── Google Maps Logic ──────────────────────────────────────────────────

    def _transform_google_to_arogyapath(self, google_place: Dict) -> Dict:
        location = google_place.get("geometry", {}).get("location", {})
        return {
            "id": google_place.get("place_id"),
            "name": google_place.get("name"),
            "city": "", 
            "state": "",
            "lat": location.get("lat"),
            "lng": location.get("lng"),
            "type": "private", 
            "rating": google_place.get("rating", 3.0),
            "review_count": google_place.get("user_ratings_total", 0),
            "nabh_accredited": False,
            "cost_category": "medium",
            "cost_multiplier": 1.0,
            "icu_available": True,
            "emergency": True,
            "bed_count": "Unknown",
            "phone": "Available in details",
            "distance_km": 0.0, # Will be calculated by engine
            "tradeoff_tags": ["google_data"],
            "procedures": []
        }
