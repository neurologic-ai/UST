from odmantic import AIOEngine
import pandas as pd
import json
import os

# LOOKUP_DIR = "lookup_data"
# os.makedirs(LOOKUP_DIR, exist_ok=True)

# async def get_association_recommendations(engine: AIOEngine, cart_items: list, top_n: int, model, filters: dict):
#     assoc_products = {}
#     if cart_items:
#         for product in cart_items:
#             filters_with_product = filters.copy()
#             filters_with_product['product'] = product
#             doc = await engine.find_one(model, filters_with_product)
#             if doc:
#                 assoc_products.update(doc.associate_products)
#     return list(assoc_products.keys())[:top_n]


# async def get_popular_recommendation(engine: AIOEngine, top_n: int, model, filters: dict):
#     doc = await engine.find_one(model, filters)
#     return list(doc.popular_data.keys())[:top_n] if doc else []


# def build_lookup_dicts(df: pd.DataFrame) -> tuple[dict, dict]:
#     df["Product_name"] = df["Product_name"].astype(str).str.strip().str.lower()
#     df["UPC"] = df["UPC"].astype(str).str.strip()

#     df_grouped = (
#         df.groupby(["Product_name", "UPC"])["Quantity"]
#         .sum()
#         .reset_index()
#     )

#     name_to_upc_map = (
#         df_grouped
#         .sort_values("Quantity", ascending=False)
#         .drop_duplicates("Product_name")
#         .set_index("Product_name")["UPC"]
#         .to_dict()
#     )

#     upc_to_name_map = (
#         df.drop_duplicates("UPC")
#         .set_index("UPC")["Product_name"]
#         .to_dict()
#     )

#     return name_to_upc_map, upc_to_name_map


# def save_lookup_dicts(name_to_upc_map: dict, upc_to_name_map: dict):
#     with open(os.path.join(LOOKUP_DIR, "name_to_upc.json"), "w") as f:
#         json.dump(name_to_upc_map, f)

#     with open(os.path.join(LOOKUP_DIR, "upc_to_name.json"), "w") as f:
#         json.dump(upc_to_name_map, f)
#     print("✅ Lookup JSON files saved.")

# def load_lookup_dicts() -> tuple[dict, dict]:
#     with open(os.path.join(LOOKUP_DIR, "name_to_upc.json"), "r") as f1:
#         name_to_upc_map = json.load(f1)

#     with open(os.path.join(LOOKUP_DIR, "upc_to_name.json"), "r") as f2:
#         upc_to_name_map = json.load(f2)

#     return name_to_upc_map, upc_to_name_map


### without name to upc map:

# async def get_popular_recommendation(engine: AIOEngine, top_n: int, model, filters: dict):
#     doc = await engine.find_one(model, filters)
#     if not doc or not doc.popular_data:
#         return {}, []

#     # Sort items by count
#     sorted_items = sorted(
#         doc.popular_data.items(),
#         key=lambda item: item[1].get("count", 0),
#         reverse=True
#     )
#     top_names = [name for name, _ in sorted_items[:top_n]]
#     return doc.popular_data, top_names


# async def get_association_recommendations(engine: AIOEngine, cart_items: list, top_n: int, model, filters: dict):
#     combined_assocs = {}
#     for product in cart_items:
#         filters_with_product = filters.copy()
#         filters_with_product['product'] = product
#         doc = await engine.find_one(model, filters_with_product)
#         if doc and doc.associate_products:
#             for name, val in doc.associate_products.items():
#                 if name not in combined_assocs:
#                     combined_assocs[name] = val.copy()
#                 else:
#                     combined_assocs[name]["count"] += val.get("count", 0)

#     # Sort
#     sorted_items = sorted(combined_assocs.items(), key=lambda x: x[1].get("count", 0), reverse=True)
#     top_names = [name for name, _ in sorted_items[:top_n]]
#     return combined_assocs, top_names

async def get_popular_recommendation(engine: AIOEngine, top_n: int, model, filters: dict):
    print(f"[Popular] Filters: {filters}")
    # docs = await engine.find(model)
    # print(f"[Debug] All docs for {model.__name__}:")
    # for d in docs:
    #     print(d.dict())

    doc = await engine.find_one(model, filters)
    # print(f"[Popular] Found doc: {doc}")
    
    if not doc or not doc.popular_data:
        print("[Popular] No doc or no popular_data")
        return {}, []

    # print(f"[Popular] Raw popular_data: {doc.popular_data}")

    # sorted_items = sorted(
    #     doc.popular_data.items(),
    #     key=lambda item: item[1].get("count", 0),
    #     reverse=True
    # )
    sorted_items = sorted(
        doc.popular_data.items(),
        key=lambda item: getattr(item[1], "count", 0),
        reverse=True
    )

    top_names = [name for name, _ in sorted_items[:top_n]]
    return doc.popular_data, top_names

async def get_association_recommendations(engine: AIOEngine, cart_items: list, top_n: int, model, filters: dict):
    print(f"[Association] Base filters: {filters}")
    combined_assocs = {}
    # docs = await engine.find(model)
    # print(f"[Debug] All docs for {model.__name__}:")
    # for d in docs:
    #     print(d.dict())

    for product in cart_items:
        filters_with_product = filters.copy()
        filters_with_product['product'] = product
        # print(f"[Association] Searching with: {filters_with_product}")

        doc = await engine.find_one(model, filters_with_product)
        # print(f"[Association] Found doc for {product}: {doc}")

        if doc and doc.associate_products:
            # print(f"[Association] associate_products for {product}: {doc.associate_products}")
            for name, val in doc.associate_products.items():
                if name not in combined_assocs:
                    combined_assocs[name] = val.copy()
                else:
                    combined_assocs[name]["count"] += val.get("count", 0)

    # sorted_items = sorted(combined_assocs.items(), key=lambda x: x[1].get("count", 0), reverse=True)
    sorted_items = sorted(combined_assocs.items(), key=lambda x: getattr(x[1], "count", 0), reverse=True)


    top_names = [name for name, _ in sorted_items[:top_n]]
    return combined_assocs, top_names
