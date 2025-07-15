from datetime import datetime
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from odmantic import AIOEngine
from auth.api_key import get_api_key
from db.singleton import get_engine
from models.fixed_always_reco import RecommendationConfig
from repos.fixed_always_product import parse_upload, validate_df



router = APIRouter(
    prefix="/api/v1",  # version prefix
    tags=["Recommendation V1"],
    dependencies=[Depends(get_api_key)]
)

@router.post("/upload-products")
async def upload_products(
    file: UploadFile = File(...),
    product_type: str = Form(...),
    db: AIOEngine = Depends(get_engine)
):
    df = await parse_upload(file)
    await validate_df(df)

    # Clean up
    df["UPC"] = df["UPC"].astype(str).str.strip()
    df["Product Name"] = df["Product Name"].astype(str).str.strip()

    product_list = df.to_dict(orient="records")

    # Upsert logic
    config = await db.find_one(
        RecommendationConfig
    )
    if not config:
        config = RecommendationConfig()

    if product_type == "fixed":
        config.fixed_products = product_list
    elif product_type == "always":
        config.always_recommend = product_list
    else:
        raise HTTPException(status_code=400, detail="Invalid product_type. Must be 'fixed' or 'always'.")

    config.updated_at = datetime.utcnow()
    await db.save(config)

    return {"message": f"✅ {product_type.capitalize()} products uploaded."}
