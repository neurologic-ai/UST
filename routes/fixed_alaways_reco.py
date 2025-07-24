from datetime import datetime
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from odmantic import AIOEngine
from auth.api_key import get_api_key
from db.singleton import get_engine
from models.fixed_always_reco import AlwaysRecommendProduct, FixedProduct, ProductType
from repos.fixed_always_product import parse_upload, validate_df
from utils.error_codes import UPLOAD_ERRORS, UPLOAD_SUCCESS
from utils.helper import load_lookup_dicts



router = APIRouter(
    prefix="/api/v1",  # version prefix
    tags=["Recommendation V1"],
    dependencies=[Depends(get_api_key)]
)


@router.post("/upload-products")
async def upload_products(
    productType: ProductType,
    file: UploadFile = File(...),
    db: AIOEngine = Depends(get_engine)
):
    # 1️ Parse + validate
    df = await parse_upload(file)
    await validate_df(df)

    # 2️ Clean
    df["UPC"] = df["UPC"].astype(str).str.strip()
    df["Product Name"] = df["Product Name"].astype(str).str.strip()

    # 3️ Load your UPC lookup map
    _, upc_to_name_map = load_lookup_dicts()

    # 4️ Filter valid vs invalid
    valid_products = []
    skipped_upcs = []

    for _, row in df.iterrows():
        upc = row["UPC"]
        if upc in upc_to_name_map:
            valid_products.append({
                "UPC": upc,
                "Product Name": row["Product Name"]
            })
        else:
            skipped_upcs.append(upc)
    if not valid_products:
        raise HTTPException(status_code=400, detail=UPLOAD_ERRORS["ALL_UPCS_INVALID"])

    now = datetime.utcnow()

    # 5️ Save only valid ones
    if productType == ProductType.fixed:
        config = await db.find_one(FixedProduct)
        if not config:
            config = FixedProduct(products=valid_products, created_at=now)
        else:
            config.products = valid_products
            config.updated_at = now
        await db.save(config)

    elif productType == ProductType.always:
        config = await db.find_one(AlwaysRecommendProduct)
        if not config:
            config = AlwaysRecommendProduct(products=valid_products, created_at=now)
        else:
            config.products = valid_products
            config.updated_at = now
        await db.save(config)

    if skipped_upcs:
        message = f"Products uploaded, but {len(skipped_upcs)} unknown UPCs were skipped."
        error_code = UPLOAD_SUCCESS["PARTIAL"]
    else:
        message = "Products uploaded successfully."
        error_code = UPLOAD_SUCCESS["ALL_VALID"]

    return {
        "detail": {
            "errorCode": error_code,
            "message": message,
            "skippedUpcs": skipped_upcs,
            "uploadedCount": len(valid_products)
        }
    }


@router.put("/reset-products")
async def clear_products(
    productType: ProductType,
    db: AIOEngine = Depends(get_engine)
):
    now = datetime.utcnow()

    if productType == ProductType.fixed:
        config = await db.find_one(FixedProduct)
    elif productType == ProductType.always:
        config = await db.find_one(AlwaysRecommendProduct)
    else:
        raise HTTPException(status_code=400, detail="Invalid product type.")

    if not config:
        raise HTTPException(status_code=404, detail=f"No {productType.value} products found to clear.")

    config.products = []
    config.updated_at = now
    await db.save(config)

    return {
        "message": f"{productType.value.capitalize()} products cleared successfully."
    }



