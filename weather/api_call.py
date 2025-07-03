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
        logger.debug(response.status_code)
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return None

# --- Classify and cache only the "feels like" map ---
def get_or_set_feels_like_map(lat, lon, redis_client: redis.Redis):
    redis_key = f"Weather:{lat}:{lon}"
    logger.debug(f"Checking Redis key: {redis_key}")

    try:
        cached = redis_client.get(redis_key)
    except redis.RedisError as e:
        logger.warning(f"Redis GET failed for key {redis_key}: {e}")
        cached = None

    if cached:
        logger.info(f"Cache hit for {redis_key}")
        return json.loads(cached)

    logger.info(f"Cache miss for {redis_key}, fetching fresh data")
    weather_data = get_weather_forecast(lat, lon)
    if not weather_data:
        logger.warning(f"No weather data fetched for {lat}, {lon}")
        return None

    feels_like_map = {}
    for entry in weather_data.get("timelines", {}).get("hourly", []):
        timestamp = entry.get("time")
        temp_apparent = entry.get("values", {}).get("temperatureApparent")
        if temp_apparent is None:
            continue
        feel = (
            "cold" if temp_apparent <= 15
            else "moderate" if temp_apparent < 25
            else "hot"
        )
        feels_like_map[timestamp] = feel

    try:
        redis_client.setex(redis_key, 432000, json.dumps(feels_like_map))
        logger.info(f"Weather feel data cached under key {redis_key}")
    except redis.RedisError as e:
        logger.warning(f"Failed to set Redis cache for {redis_key}: {e}")

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

