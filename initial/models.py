import pandas as pd
from collections import defaultdict
from initial.constant import US_HOLIDAYS, DATE_COL
from initial.helper import get_holiday_name, get_weather_data, calculate_feels_like, categorize_temperature

def popular_based(df, top_n = 100):
    # Group by product name and sum quantities, then get top_n popular products
    df_popular = df.groupby('Product_name')['Quantity'].sum().nlargest(top_n)

    # Create a dictionary of popular products and their quantities
    return [{'popular_data': df_popular.to_dict()}]


def time_based(df, top_n = 100):
    # Convert to datetime and extract hour and day of week
    df['Date_time'] = pd.to_datetime(df['Date_time'])
    df['hour'] = df['Date_time'].dt.hour
    df['dayofweek'] = df['Date_time'].dt.dayofweek

    recommendations_combination = []

    # Loop over all hour and dayofweek combinations
    for hour in range(24):
        for dayofweek in range(7):
            # Filter DataFrame and get top_n products by quantity
            filtered_df = df[(df['hour'] == hour) & (df['dayofweek'] == dayofweek)]
            top_products = (filtered_df.groupby('Product_name')['Quantity'].sum().nlargest(top_n).index.tolist())

            # Store the combination
            recommendations_combination.append({
                'hour': hour,
                'dayofweek': dayofweek,
                'recommended_products': top_products
            })

    return recommendations_combination


def calendar_based(df, top_n = 100):
    # Convert 'Date_time' to datetime and extract holiday names
    df['Date_time'] = pd.to_datetime(df['Date_time'])
    df['holiday'] = df['Date_time'].apply(lambda x: get_holiday_name(x, US_HOLIDAYS))

    # Filter out rows without holidays
    df_holidays = df[df['holiday'].notna()]

    # Dictionary to store top products for each holiday
    holiday_recommendations = {}

    # Group data by holiday and calculate top_n products for each
    for holiday_name, group in df_holidays.groupby('holiday'):
        top_products = group.groupby('Product_name')['Quantity'].sum().nlargest(top_n)
        holiday_recommendations[holiday_name] = top_products.index.tolist()

    # Prepare final recommendations
    return [{'holiday': holiday, 'products': products} for holiday, products in holiday_recommendations.items()]


def weather_based(df, top_n = 100):
    df[DATE_COL] = pd.to_datetime(df[DATE_COL])
    df_weather = get_weather_data(df)

    # Calculate 'flt' (feels like temperature) and categorize it
    df_weather['flt'] = df_weather.apply(lambda row: calculate_feels_like(row['temp'], row['rhum']), axis=1)
    df_weather['Category'] = df_weather['flt'].apply(categorize_temperature)

    # Create a dictionary to store product recommendations by weather category
    weather_dct = {}
    for category in ['Extreme cold', 'Cold', 'Moderate', 'Hot', 'Extreme Hot']:
        filtered_df = df_weather[df_weather['Category'] == category]

        # Get top_n products for each category
        top_products = (filtered_df.groupby('Product_name')['Quantity'].sum().nlargest(top_n).index.tolist())

        weather_dct[category] = top_products

    # Prepare final output
    return [{'category': category, 'products': products} for category, products in weather_dct.items()]


def association_based(df: pd.DataFrame, top_n = 100) -> list:
    association_cache = defaultdict(lambda: defaultdict(int))

    # Group by session and process associations
    for _, session_data in df.groupby('Session_id'):
        products = session_data['Product_name'].astype(str).tolist()
        quantities = session_data['Quantity'].tolist()

        # Create associations between products within the session
        for idx, product in enumerate(products):
            for jdx, associated_product in enumerate(products):
                if idx != jdx:
                    association_cache[product][associated_product] += quantities[jdx]

    # Sort associated products and keep top_n recommendations
    sorted_association_cache = {
        product: dict(sorted(associates.items(), key = lambda item: item[1], reverse = True)[:top_n])
        for product, associates in association_cache.items()
    }

    # Prepare output in the desired format
    return [{'product': product, 'associate_products': associates} 
            for product, associates in sorted_association_cache.items()]