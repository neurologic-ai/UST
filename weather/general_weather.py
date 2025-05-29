import json
from datetime import datetime

def generate_weather_recommendation(json_data):
    recommendations = []
    daily_data = json_data['data']['timelines'][0]['intervals']
    
    for day in daily_data:
        date_str = day['startTime']
        date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ").strftime("%d %B %Y")
        values = day['values']
        
        temp = values['temperature']
        humidity = values['humidity']
        uv_index = values['uvIndex']
        wind_speed = values['windSpeed']
        precip_prob = values['precipitationProbability']
        
        # General Weather Description Logic
        if temp >= 41:
            general_weather = "Scorching heat"
        elif 38 <= temp < 41:
            general_weather = "Very hot"
        else:
            general_weather = "Hot"
        
        # Recommendation Logic
        if uv_index >= 11:
            uv_warning = "UV index is extremely high. Avoid direct sunlight."
        elif uv_index >= 8:
            uv_warning = "UV index is high. Use sunscreen if outdoors."
        else:
            uv_warning = "UV index is moderate."
        
        if precip_prob > 20:
            rain_advice = "Carry an umbrella just in case."
        else:
            rain_advice = "No rain expected."
        
        rec = f"""
📅 {date}
- General Weather: {general_weather}, {rain_advice}
- Details: Temperature around {temp}°C, Humidity {humidity}%, Wind {wind_speed} km/h.
- {uv_warning}
- Recommendation: Stay hydrated, avoid outdoor activities during midday, wear light clothing. Best time for outdoor plans: early morning or late evening.
"""
        recommendations.append(rec.strip())
    
    return "\n\n".join(recommendations)
s
# Example usage
# Assuming your JSON is stored in 'json_data'
# json_data = <your JSON here>
# print(generate_weather_recommendation(json_data))
