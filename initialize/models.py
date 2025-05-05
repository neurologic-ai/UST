import pandas as pd
from collections import defaultdict
from configs.constant import QUANTITY_COL, PRODUCT_NAME_COL, SESSION_COL


# def popular_based(df, top_n = 100):
#     # Group by product name and sum quantities, then get top_n popular products
#     df_popular = df.groupby(PRODUCT_NAME_COL)[QUANTITY_COL].sum().nlargest(top_n)

#     # Create a dictionary of popular products and their quantities
#     return [{'popular_data': df_popular.to_dict()}]


# def association_based(df: pd.DataFrame, top_n = 100) -> list:
#     association_cache = defaultdict(lambda: defaultdict(int))

#     # Group by session and process associations
#     for _, session_data in df.groupby(SESSION_COL):
#         products = session_data[PRODUCT_NAME_COL].astype(str).tolist()
#         quantities = session_data[QUANTITY_COL].tolist()

#         # Create associations between products within the session
#         for idx, product in enumerate(products):
#             for jdx, associated_product in enumerate(products):
#                 if idx != jdx:
#                     association_cache[product][associated_product] += quantities[jdx]

#     # Sort associated products and keep top_n recommendations
#     sorted_association_cache = {
#         product: dict(sorted(associates.items(), key = lambda item: item[1], reverse = True)[:top_n])
#         for product, associates in association_cache.items()
#     }

#     # Prepare output in the desired format
#     return [{'product': product, 'associate_products': associates} 
#             for product, associates in sorted_association_cache.items()]


def popular_based(df, top_n=100):
    results = []

    for (location_id, store_id), group in df.groupby(['location_id', 'store_id']):
        df_popular = group.groupby(PRODUCT_NAME_COL)[QUANTITY_COL].sum().nlargest(top_n)

        results.append({
            "location_id": location_id,
            "store_id": store_id,
            "popular_data": df_popular.to_dict()
        })

    return results


def association_based(df: pd.DataFrame, top_n=100, timing=None) -> list:
    full_result = []

    # Group by location and store
    for (location_id, store_id), store_group in df.groupby(["location_id", "store_id"]):
        association_cache = defaultdict(lambda: defaultdict(int))

        # Group by session within each store
        for _, session_data in store_group.groupby(SESSION_COL):
            products = session_data[PRODUCT_NAME_COL].astype(str).tolist()
            quantities = session_data[QUANTITY_COL].tolist()

            # Create associations
            for idx, product in enumerate(products):
                for jdx, associated_product in enumerate(products):
                    if idx != jdx:
                        association_cache[product][associated_product] += quantities[jdx]

        # Sort and limit top N
        sorted_association_cache = {
            product: dict(sorted(associates.items(), key=lambda item: item[1], reverse=True)[:top_n])
            for product, associates in association_cache.items()
        }

        # Prepare output for this store-location
        full_result.extend([
            {
                "location_id": location_id,
                "store_id": store_id,
                "product": product,
                "associate_products": associates
            }
            for product, associates in sorted_association_cache.items()
        ])

    return full_result