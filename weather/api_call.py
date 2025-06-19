import json
from datetime import datetime, timezone
from loguru import logger
import redis
import requests
from configs.manager import settings

# --- Get weather forecast from Tomorrow.io ---
def get_weather_forecast(lat, lon):
    url = settings.WEATHER_URL
    params = {
        "location": f"{lat},{lon}",
        "apikey": settings.WEATHER_APIKEY,
        "timesteps": "1h"
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        logger.debug(response.json())
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return None

# --- Classify and cache only the "feels like" map ---
def get_or_set_feels_like_map(lat, lon, redis_client: redis.Redis):
    redis_key = f"Weather:{lat}:{lon}"
    logger.debug(redis_key)
    cached = redis_client.get(redis_key)

    if cached:
        return json.loads(cached)

    # Fetch and process fresh data
    weather_data = get_weather_forecast(lat, lon)
    logger.debug(weather_data)
    if not weather_data:
        return None

    feels_like_map = {}

    for entry in weather_data.get("timelines", {}).get("hourly", []):
        timestamp = entry.get("time")  # This is already in UTC ISO format
        temp_apparent = entry.get("values", {}).get("temperatureApparent")

        if temp_apparent is None:
            continue

        if temp_apparent <= 15:
            feel = "cold"
        elif temp_apparent < 25:
            feel = "moderate"
        else:
            feel = "hot"

        feels_like_map[timestamp] = feel

    # Cache for 5 days
    redis_client.setex(redis_key, 432000, json.dumps(feels_like_map))
    return feels_like_map

# --- Main function: get "feel" for a given datetime ---
def get_weather_feel(lat, lon, dt: datetime, redis_client: redis.Redis):
    dt_utc = dt.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    timestamp_key = dt_utc.isoformat().replace("+00:00", "Z")  # Match Tomorrow.io format

    feels_like_map = get_or_set_feels_like_map(lat, lon, redis_client)
    # logger.debug(feels_like_map)
    if not feels_like_map:
        return "moderate"

    return feels_like_map.get(timestamp_key, "moderate")

