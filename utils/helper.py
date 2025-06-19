from loguru import logger
from odmantic import AIOEngine
import pandas as pd
import json
import os

async def get_popular_recommendation(engine: AIOEngine, top_n: int, model, filters: dict):
    print(f"[Popular] Filters: {filters}")
    doc = await engine.find_one(model, filters)
    # print(f"[Popular] Found doc: {doc}")
    
    if not doc or not doc.popular_data:
        print("[Popular] No doc or no popular_data")
        return {}, []
    print(f"[DEBUG] type(doc.popular_data) = {type(doc.popular_data)}")
    # print(f"[Popular] Raw popular_data: {doc.popular_data}")
    sorted_items = sorted(
        doc.popular_data.items(),
        key=lambda item: item[1].count,
        reverse=True
    )

    top_names = [name for name, _ in sorted_items[:top_n]]
    return doc.popular_data, top_names

async def get_association_recommendations(engine: AIOEngine, cart_items: list, top_n: int, model, filters: dict):
    print(f"[Association] Base filters: {filters}")
    combined_assocs = {}

    for product in cart_items:
        filters_with_product = filters.copy()
        filters_with_product['product'] = product
        # print(f"[Association] Searching with: {filters_with_product}")

        doc = await engine.find_one(model, filters_with_product)
        # print(f"[Association] Found doc for {product}: {doc}")

        if doc and doc.associate_products:
            logger.debug(doc.associate_products)
            # print(f"[Association] associate_products for {product}: {doc.associate_products}")
            for name, val in doc.associate_products.items():
                # logger.debug(val)
                # print(f"[DEBUG] type(val) = {type(val)}")

                if name not in combined_assocs:
                    combined_assocs[name] = val
                else:
                    combined_assocs[name].count += val.count
                
    sorted_items = sorted(combined_assocs.items(), key=lambda x: x[1].count, reverse=True)


    top_names = [name for name, _ in sorted_items[:top_n]]
    return combined_assocs, top_names
