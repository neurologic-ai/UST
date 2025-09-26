# category_generate.py

from typing import Dict, List
import pandas as pd
from pymongo import UpdateOne
from pymongo.errors import BulkWriteError
from db.singleton import category_cache_collection
from configs.manager import settings
from utils.make_category_csv import ClassificationService

GEMINI_PROJECT = settings.GEMINI_PROJECT
GEMINI_LOCATION = settings.GEMINI_LOCATION
GEMINI_SERVICE_ACCOUNT_PATH = settings.GEMINI_SERVICE_ACCOUNT_PATH


async def generate_categories_for_chunk_per_store(
    processed_df: pd.DataFrame,
    tenant_id: str,
    location_id: str,
) -> None:
    """
    Classify unique product names ONCE for the whole chunk, then upsert per-store docs.

    Writes one document per (tenant_id, location_id, store_id), merging dynamic keys under:
      data.<normalized_product_name> : {name, category, subcategory, timing}
    """
    if processed_df is None or processed_df.empty:
        return

    # 0) Normalize once
    df = processed_df.copy()
    # df = df[df["Product_name"].notna() & (df["Product_name"] != "")]
    if df.empty:
        return

    if "store_id" not in df.columns:
        return
    df["store_id"] = df["store_id"].astype(str)

    # 1) Unique products across the entire chunk
    unique_products: List[str] = df["Product_name"].dropna().unique().tolist()
    if not unique_products:
        return

    # 2) One Gemini client + one classification pass (service batches internally)
    svc = ClassificationService(
        project=GEMINI_PROJECT,
        location=GEMINI_LOCATION,
        service_account_path=GEMINI_SERVICE_ACCOUNT_PATH, 
    )
    classified = svc.classify(unique_products)

    # 3) Build global mapping: name -> classification payload
    global_cat_map: Dict[str, Dict] = {
        item.product: {
            "name": item.product,
            "category": (item.category or "").strip().lower(),
            "subcategory": ((item.subcategory or "").strip().lower() if item.subcategory else ""),
            "timing": item.timing.value.strip().lower(),
        }
        for item in classified
    }

    # 4) Fan-out per store: dynamic $set keys under data.<name>
    ops: List[UpdateOne] = []
    filters: List[Dict] = []     # parallel arrays for retry construction
    set_docs: List[Dict] = []

    for sid, df_store in df.groupby("store_id", dropna=False):
        if not sid or str(sid).strip().lower() in ("", "nan"):
            continue
        sid = str(sid)

        names_in_store = set(df_store["Product_name"].tolist())
        if not names_in_store:
            continue

        store_cat_map = {n: global_cat_map[n] for n in names_in_store if n in global_cat_map}
        if not store_cat_map:
            continue

        filt = {"tenant_id": tenant_id, "location_id": location_id, "store_id": sid}
        set_fields = {f"data.{k}": v for k, v in store_cat_map.items()}

        filters.append(filt)
        set_docs.append(set_fields)

        ops.append(
            UpdateOne(
                filt,
                {
                    "$setOnInsert": {"tenant_id": tenant_id, "location_id": location_id, "store_id": sid},
                    "$set": set_fields,
                },
                upsert=True,
            )
        )

    if not ops:
        return

    # 5) Bulk write (unordered, so one error doesn't stop others)
    try:
        await category_cache_collection.bulk_write(ops, ordered=False)
    except BulkWriteError as bwe:
        # Retry only duplicate-key losers as plain updates (upsert=False)
        write_errors = (bwe.details or {}).get("writeErrors", [])
        retry_ops: List[UpdateOne] = []
        other_errors = []

        for err in write_errors:
            code = err.get("code")
            idx = err.get("index")
            if code == 11000 and idx is not None:
                retry_ops.append(
                    UpdateOne(
                        filters[idx],
                        {"$set": set_docs[idx]},
                        upsert=False,   # doc exists now; just merge fields
                    )
                )
            else:
                other_errors.append(err)

        if retry_ops:
            await category_cache_collection.bulk_write(retry_ops, ordered=False)

        # Surface non-duplicate errors (if any)
        if other_errors:
            raise

    # Done


# ---------------------------------------------------------------------------
# Backward-compat alias so existing Lambda import/call keeps working unchanged.
# Your second lambda calls: generate_category_df_from_processed(df, tenant, location)
# ---------------------------------------------------------------------------
async def generate_category_df_from_processed(
    processed_df: pd.DataFrame,
    tenant_id: str,
    location_id: str,
) -> None:
    return await generate_categories_for_chunk_per_store(processed_df, tenant_id, location_id)
