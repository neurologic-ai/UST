from io import BytesIO
import random
import itertools
from fastapi import HTTPException, UploadFile
import pandas as pd
from typing import List, Set
from models.fixed_always_reco import AlwaysRecommendProduct, FixedProduct
from utils.error_codes import UPLOAD_ERRORS


REQUIRED_COLUMNS = ["UPC", "Product Name"]


async def parse_upload(file: UploadFile) -> pd.DataFrame:
    contents = await file.read()
    if file.filename.endswith(".csv"):
        df = pd.read_csv(BytesIO(contents))
    elif file.filename.endswith(".xlsx"):
        df = pd.read_excel(BytesIO(contents))
    else:
        raise HTTPException(status_code=400, detail=UPLOAD_ERRORS["INVALID_FILE_TYPE"])
    return df

async def validate_df(df: pd.DataFrame):
    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        err = UPLOAD_ERRORS["MISSING_COLUMNS"]
        raise HTTPException(status_code=400, detail={
            "errorCode": err["errorCode"],
            "message": f"{err['message']} Missing: {missing}"
        })
    if df[REQUIRED_COLUMNS].isnull().any().any():
        raise HTTPException(status_code=400, detail=UPLOAD_ERRORS["EMPTY_VALUES"])


def merge_final_recommendations(
    base_rec_upcs: List[str],
    fixed_products: List[dict],
    always_products: List[dict],
    final_top_n: int
) -> List[str]:
    """
    Safe, non-blocking version.
    - Adds ALL unique Always first (or samples N from Always if Always >= N)
    - Uses Fixed next: first those that overlap with Base (preserving Base order), then random from remaining Fixed
    - Fills any remaining slots ONLY from Base (unique, in order)
    - Never loops infinitely; may return < N if not enough unique UPCs exist
    """
    if final_top_n <= 0:
        return []

    fixed_upcs  = [fp["UPC"] for fp in (fixed_products or [])]
    always_upcs = [ap["UPC"] for ap in (always_products or [])]

    # If Always alone can fill the target, random sample and return
    if len(always_upcs) >= final_top_n:
        return random.sample(always_upcs, k=final_top_n)

    final_upcs: List[str] = []
    seen = set()

    # 1) Add ALL unique Always
    for u in always_upcs:
        if u not in seen:
            final_upcs.append(u)
            seen.add(u)

    slots_left = final_top_n - len(final_upcs)

    # 2) Bring in Fixed (overlap with Base first, preserving Base order)
    if slots_left > 0 and fixed_upcs:
        fixed_set = set(fixed_upcs)

        # 2a) Fixed that appear in Base (respect Base order)
        for u in base_rec_upcs:
            if slots_left == 0:
                break
            if u in fixed_set and u not in seen:
                final_upcs.append(u)
                seen.add(u)
                slots_left -= 1

        # 2b) If slots remain, top-up from remaining Fixed at random
        if slots_left > 0:
            remaining_fixed = [u for u in fixed_upcs if u not in seen]
            if remaining_fixed:
                k = min(slots_left, len(remaining_fixed))
                if k > 0:
                    picks = random.sample(remaining_fixed, k=k)
                    final_upcs.extend(picks)
                    seen.update(picks)
                    slots_left -= k

    # 3) Fill remaining strictly from Base (unique, preserve order)
    if slots_left > 0:
        for u in base_rec_upcs:
            if slots_left == 0:
                break
            if u not in seen:
                final_upcs.append(u)
                seen.add(u)
                slots_left -= 1

    # Return up to N (may be fewer if not enough unique UPCs exist)
    return final_upcs[:final_top_n]
