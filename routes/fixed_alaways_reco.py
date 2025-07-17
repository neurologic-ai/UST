from datetime import datetime
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from odmantic import AIOEngine
from auth.api_key import get_api_key
from db.singleton import get_engine
from models.fixed_always_reco import AlwaysRecommendProduct, FixedProduct, ProductType
from repos.fixed_always_product import parse_upload, validate_df



router = APIRouter(
    prefix="/api/v1",  # version prefix
    tags=["Recommendation V1"],
    dependencies=[Depends(get_api_key)]
)


@router.post("/upload-products")
async def upload_products(
    product_type: ProductType,
    file: UploadFile = File(...),
    db: AIOEngine = Depends(get_engine)
):
    df = await parse_upload(file)
    await validate_df(df)

    df["UPC"] = df["UPC"].astype(str).str.strip()
    df["Product Name"] = df["Product Name"].astype(str).str.strip()
    now = datetime.utcnow()

    product_list = df.to_dict(orient="records")

    if product_type == ProductType.fixed:
        config = await db.find_one(FixedProduct)
        if not config:
            config = FixedProduct(products=product_list, created_at=now)
        else:
            config.products = product_list
            config.updated_at = now
        await db.save(config)

    elif product_type == ProductType.always:
        config = await db.find_one(AlwaysRecommendProduct)
        if not config:
            config = AlwaysRecommendProduct(products=product_list, created_at=now)
        else:
            config.products = product_list
            config.updated_at = now
        await db.save(config)
    return {"message": f"{product_type.value.capitalize()} products uploaded."}
