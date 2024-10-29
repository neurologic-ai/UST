from odmantic import AIOEngine
from models.db import Association_collection, Calendar_collection, Popular_collection, Time_collection, Weather_collection


def insert_data(collection_name, inp_data, many = True, dataset_name = ''):
    collection_name.delete_many({})
    if many:
        collection_name.insert_many(inp_data)
    else:
        collection_name.insert_one(inp_data)
    print(f"{dataset_name} data stored successfully!")


# Define async functions for each recommendation source
async def get_time_recommendation(engine: AIOEngine, current_hr: int, current_dayofweek: int, top_n: int):
    time_recommendation = await engine.find_one(Time_collection, 
                                                    Time_collection.hour == current_hr,
                                                    Time_collection.dayofweek == current_dayofweek)
    return time_recommendation.recommended_products[:top_n] if time_recommendation else []

async def get_weather_recommendation(engine: AIOEngine, current_weather_category: str, top_n: int):
    weather_recommendation = await engine.find_one(Weather_collection, 
                                                    Weather_collection.category == current_weather_category)
    return weather_recommendation.products[:top_n] if weather_recommendation else []

async def get_calendar_recommendation(engine: AIOEngine, current_holiday: str, top_n: int):
    calendar_recommendation = await engine.find_one(Calendar_collection, 
                                                        Calendar_collection.holiday == current_holiday)
    return calendar_recommendation.products[:top_n] if calendar_recommendation else []

async def get_association_recommendations(engine: AIOEngine, cart_items: list, top_n: int):
    assoc_products = {}
    if cart_items:
        for product in cart_items:
            assoc_recommendation = await engine.find_one(Association_collection, 
                                                            Association_collection.product == product)
            if assoc_recommendation:
                assoc_products.update(assoc_recommendation.associate_products)
    return list(assoc_products.keys())[:top_n]

async def get_popular_recommendation(engine: AIOEngine, top_n: int):
    popular_recommendation = await engine.find_one(Popular_collection)
    return list(popular_recommendation.popular_data.keys())[:top_n] if popular_recommendation else []   