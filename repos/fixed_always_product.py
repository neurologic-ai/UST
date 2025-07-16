from io import BytesIO
from fastapi import HTTPException, UploadFile
import pandas as pd
from typing import List, Set
from models.fixed_always_reco import AlwaysRecommendProduct, FixedProduct


REQUIRED_COLUMNS = ["UPC", "Product Name"]


async def parse_upload(file: UploadFile) -> pd.DataFrame:
    contents = await file.read()
    if file.filename.endswith(".csv"):
        df = pd.read_csv(BytesIO(contents))
    elif file.filename.endswith(".xlsx"):
        df = pd.read_excel(BytesIO(contents))
    else:
        raise HTTPException(status_code=400, detail="File must be .csv or .xlsx")
    return df

async def validate_df(df: pd.DataFrame):
    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing columns: {missing}")
    if df[REQUIRED_COLUMNS].isnull().any().any():
        raise HTTPException(status_code=400, detail="Empty UPC or Product Name values found.")


def merge_final_recommendations(
    base_rec_upcs: List[str],
    fixed_products: List[FixedProduct],
    always_products: List[AlwaysRecommendProduct],
    final_top_n: int
) -> List[str]:
    fixed_upcs = {fp["UPC"] for fp in fixed_products}
    always_upcs = {ap["UPC"] for ap in always_products}

    final_upcs = []

    # If always-recommend fully fills slots → no need for anything else
    if len(always_upcs) >= final_top_n:
        final_upcs = list(always_upcs)[:final_top_n]
        return final_upcs

    # Otherwise, start with always
    final_upcs.extend(always_upcs)
    slots_left = final_top_n - len(final_upcs)

    if fixed_upcs:
        # Find coincidences in base vs fixed
        matched_fixed = [upc for upc in base_rec_upcs if upc in fixed_upcs]
        remaining_fixed = [fp["UPC"] for fp in fixed_products if fp["UPC"] not in matched_fixed]

        if matched_fixed:
            # Some matches → fill with random fixed
            while len(matched_fixed) < slots_left and remaining_fixed:
                matched_fixed.append(remaining_fixed.pop())
            final_upcs.extend(matched_fixed[:slots_left])
            slots_left = final_top_n - len(final_upcs)
        else:
            # No matches → fill entirely with random fixed
            final_upcs.extend(remaining_fixed[:slots_left])
            slots_left = final_top_n - len(final_upcs)

    # Fill any remaining slots with fallback base recs
    fallback = [upc for upc in base_rec_upcs if upc not in final_upcs]
    final_upcs.extend(fallback[:slots_left])

    # Deduplicate
    final_upcs = list(dict.fromkeys(final_upcs))
    return final_upcs[:final_top_n]
