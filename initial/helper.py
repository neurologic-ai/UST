from meteostat import Point, Hourly
from geopy.geocoders import Nominatim
import pandas as pd, numpy as np
from datetime import timedelta
from initial.constant import SHOP_LOCATION, DATE_COL

# Function to check if a date is a holiday
def get_holiday_name(date, holidays_obj):
    return holidays_obj.get(date.date(), None)  # Returns holiday name or None

def geolocation(loc:str) -> Point:
    getLoc = Nominatim(user_agent = 'GetLoc', timeout = 10).geocode(loc)
    return Point(getLoc.latitude, getLoc.longitude)

def get_weather_data(df:pd.DataFrame)-> pd.DataFrame:
    df['hrs'] = pd.to_datetime(df[DATE_COL]).dt.floor('h') #'2023-04-11 17:30' becomes to '2023-04-11 17:00'
    df.sort_values(by = DATE_COL, inplace = True)
    df.reset_index(inplace = True, drop = True)
    # We will get hourly data
    weather_data = pd.DataFrame(Hourly(geolocation(SHOP_LOCATION),
                                      df[DATE_COL].min() - timedelta(days = 1),
                                      df[DATE_COL].max() + timedelta(days =1)).fetch()
                              )
    weather_data.reset_index(inplace = True)
    #time is of floor format like '2023-04-11 17:00'
    df = pd.merge(df, weather_data, left_on = 'hrs', right_on = 'time', how = 'left')
    df.drop(columns = ['hrs','time'], inplace = True)
    return df

def calculate_feels_like(temp, rhum):
    try:
         # For temperature above 27°C (80°F) and relative humidity above 40%, feels like temparature defers
        #Below these thresholds, the perceived temperature is usually the same as the actual temperature.
        if (temp > 27) and (rhum > 40) :
            # Constants
            c1 = -8.784695
            c2 = 1.61139411
            c3 = 2.338549
            c4 = -0.14611605
            c5 = -0.01230809
            c6 = -0.01642482
            c7 = 0.00221173
            c8 = 0.00072546
            c9 = -0.00000358
            
            # Apply the heat index formula
            feels_like = (c1 + (c2 * temp) + (c3 * rhum) + (c4 * temp * rhum) + 
                        (c5 * temp**2) + (c6 * rhum**2) + 
                        (c7 * temp**2 * rhum) + (c8 * temp * rhum**2) + 
                        (c9 * temp**2 * rhum**2))
        else:
            feels_like = temp 
    except:
        feels_like = np.nan
    return feels_like


def categorize_temperature(temp):
    try:
        if temp < 0:
            return 'Extreme cold'
        elif 0 <= temp < 10:
            return 'Cold'
        elif 10 <= temp < 20:
            return 'Moderate'
        elif 20 <= temp < 30:
            return 'Hot'
        elif temp > 30:
            return 'Extreme Hot'
    except:
        return np.nan