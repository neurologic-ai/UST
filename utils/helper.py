from odmantic import AIOEngine
# from models.db import AssociationCollection, PopularCollection


# Define async functions for each recommendation source

async def get_association_recommendations(engine: AIOEngine, cart_items: list, top_n: int, collection_name):
    assoc_products = {}
    if cart_items:
        for product in cart_items:
            assoc_recommendation = await engine.find_one(collection_name, collection_name.product == product)
            if assoc_recommendation:
                assoc_products.update(assoc_recommendation.associate_products)
    return list(assoc_products.keys())[:top_n]


async def get_popular_recommendation(engine: AIOEngine, top_n: int, collection_name):
    popular_recommendation = await engine.find_one(collection_name)
    return list(popular_recommendation.popular_data.keys())[:top_n] if popular_recommendation else []