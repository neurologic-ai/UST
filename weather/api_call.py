import redis
import requests
import json

# Connect to Redis server (default localhost:6379)
r = redis.Redis(host='localhost', port=6379, db=0)

def get_weather_data(location):
    redis_key = f"weather:{location.lower()}"
    
    # Try to get data from Redis
    cached_data = r.get(redis_key)
    if cached_data:
        print(f"Cache HIT for {location}")
        # Load from Redis cache
        return json.loads(cached_data)
    else:
        print(f"Cache MISS for {location}, calling API")
        # Call the weather API
        url = f"https://api.tomorrow.io/v4/weather/forecast?location={location}&timesteps=1d&apikey=fmVOCPe2gv1FUcvGlNYYCQQ3j3U9rVJn"
        headers = {
            "accept": "application/json",
            "accept-encoding": "deflate, gzip, br"
        }
        response = requests.get(url, headers=headers)
        
        # Save to Redis with expiry of 5 days (432000 seconds)
        if response.status_code == 200:
            r.setex(redis_key, 432000, response.text)
            return response.json()
        else:
            print("API Error:", response.status_code)
            return None

# Usage
data = get_weather_data("new york")
print(data)
