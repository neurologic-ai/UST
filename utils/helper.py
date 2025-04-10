from odmantic import AIOEngine
import pandas as pd
import json
import os

LOOKUP_DIR = "lookup_data"
os.makedirs(LOOKUP_DIR, exist_ok=True)


# Define async functions for each recommendation source

async def get_association_recommendations(engine: AIOEngine, cart_items: list, top_n: int, collection_name):
    assoc_products = {}
    if cart_items:
        for product in cart_items:
            assoc_recommendation = await engine.find_one(collection_name, {"product": product})
            if assoc_recommendation:
                assoc_products.update(assoc_recommendation.associate_products)
    return list(assoc_products.keys())[:top_n]


async def get_popular_recommendation(engine: AIOEngine, top_n: int, collection_name):
    popular_recommendation = await engine.find_one(collection_name)
    return list(popular_recommendation.popular_data.keys())[:top_n] if popular_recommendation else []


def build_lookup_dicts(df: pd.DataFrame) -> tuple[dict, dict]:
    df["Product_name"] = df["Product_name"].astype(str).str.strip().str.lower()
    df["UPC"] = df["UPC"].astype(str).str.strip()

    df_grouped = (
        df.groupby(["Product_name", "UPC"])["Quantity"]
        .sum()
        .reset_index()
    )

    name_to_upc_map = (
        df_grouped
        .sort_values("Quantity", ascending=False)
        .drop_duplicates("Product_name")
        .set_index("Product_name")["UPC"]
        .to_dict()
    )

    upc_to_name_map = (
        df.drop_duplicates("UPC")
        .set_index("UPC")["Product_name"]
        .to_dict()
    )

    return name_to_upc_map, upc_to_name_map


def save_lookup_dicts(name_to_upc_map: dict, upc_to_name_map: dict):
    with open(os.path.join(LOOKUP_DIR, "name_to_upc.json"), "w") as f:
        json.dump(name_to_upc_map, f)

    with open(os.path.join(LOOKUP_DIR, "upc_to_name.json"), "w") as f:
        json.dump(upc_to_name_map, f)
    print("✅ Lookup JSON files saved.")

def load_lookup_dicts() -> tuple[dict, dict]:
    with open(os.path.join(LOOKUP_DIR, "name_to_upc.json"), "r") as f1:
        name_to_upc_map = json.load(f1)

    with open(os.path.join(LOOKUP_DIR, "upc_to_name.json"), "r") as f2:
        upc_to_name_map = json.load(f2)

    return name_to_upc_map, upc_to_name_map
