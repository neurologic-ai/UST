import json

def extract_weather_summary(json_data):
    summaries = []
    for day in json_data['timelines']['daily']:
        date = day['time'][:10]
        values = day['values']
        summary = {
            'date': date,
            'temperature_min': values.get('temperatureMin'),
            'temperature_max': values.get('temperatureMax'),
            'humidity_min': values.get('humidityMin'),
            'humidity_max': values.get('humidityMax'),
            'uv_index_max': values.get('uvIndexMax'),
            'precipitation_probability_max': values.get('precipitationProbabilityMax'),
            'wind_speed_avg': values.get('windSpeedAvg'),
        }
        summaries.append(summary)
    return summaries

# Example usage
# data = <your JSON data>
# print(extract_weather_summary(data))
