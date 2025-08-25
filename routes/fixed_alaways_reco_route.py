from datetime import datetime
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from odmantic import AIOEngine, ObjectId
from auth.tenant_user_verify import check_user_role_and_status
from db.singleton import get_engine
from initialize.helper import load_lookup_dicts
from models.db import Tenant
from models.fixed_always_reco import AlwaysRecommendProduct, FixedProduct, ProductType
from repos.fixed_always_product import parse_upload, validate_df
from routes.user_route import PermissionChecker
from utils.error_codes import UPLOAD_ERRORS, UPLOAD_SUCCESS




router = APIRouter(
    prefix="/api/v2",  # version prefix
    tags=["Recommendation V2"]
)



@router.post("/upload-products")
async def upload_products(
    tenantId: str,
    locationId: str,
    storeId: str,
    productType: ProductType,
    file: UploadFile = File(...),
    authorize: bool = Depends(PermissionChecker(['items:write'])),
    db: AIOEngine = Depends(get_engine)
):
    if not ObjectId.is_valid(tenantId):
        raise HTTPException(status_code=400, detail="Invalid tenant ID")
    
    check_user_role_and_status(authorize, tenantId)

    tenant = await db.find_one(Tenant, Tenant.id == ObjectId(tenantId))
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    location = next((loc for loc in tenant.locations if loc.location_id == locationId), None)
    if not location:
        raise HTTPException(status_code=404, detail=f"Location '{locationId}' not found for this tenant")
    
    store = next((s for s in location.stores if s.store_id == storeId), None)
    if not store:
        raise HTTPException(status_code=400, detail=f"Invalid store_id: {storeId}")
    # 1️ Parse + validate
    df = await parse_upload(file)
    await validate_df(df)

    # 2️ Clean
    df["UPC"] = df["UPC"].astype(str).str.strip()
    df["Product Name"] = df["Product Name"].astype(str).str.strip()

    # 3️ Load your UPC lookup map
    _, upc_to_name_map = await load_lookup_dicts(tenantId, locationId, storeId)

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
        config = await db.find_one(
            FixedProduct,
            FixedProduct.tenant_id == tenantId,
            FixedProduct.location_id == locationId,
            FixedProduct.store_id == storeId
        )
        if not config:
            config = FixedProduct(
                tenant_id=tenantId,
                location_id=locationId,
                store_id=storeId,
                products=valid_products,
                created_at=now
            )
        else:
            config.products = valid_products
            config.updated_at = now
        await db.save(config)

    elif productType == ProductType.always:
        config = await db.find_one(
            AlwaysRecommendProduct,
            AlwaysRecommendProduct.tenant_id == tenantId,
            AlwaysRecommendProduct.location_id == locationId,
            AlwaysRecommendProduct.store_id == storeId
        )
        if not config:
            config = AlwaysRecommendProduct(
                tenant_id=tenantId,
                location_id=locationId,
                store_id=storeId,
                products=valid_products,
                created_at=now
            )
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
    tenantId: str,
    locationId: str,
    storeId: str,
    productType: ProductType,
    db: AIOEngine = Depends(get_engine)
):
    now = datetime.utcnow()

    if productType == ProductType.fixed:
        config = await db.find_one(
            FixedProduct,
            FixedProduct.tenant_id == tenantId,
            FixedProduct.location_id == locationId,
            FixedProduct.store_id == storeId
        )
    elif productType == ProductType.always:
        config = await db.find_one(
            AlwaysRecommendProduct,
            AlwaysRecommendProduct.tenant_id == tenantId,
            AlwaysRecommendProduct.location_id == locationId,
            AlwaysRecommendProduct.store_id == storeId
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid product type.")

    if not config:
        raise HTTPException(
            status_code=404,
            detail=f"No {productType.value} products found to clear for tenant={tenantId}, location={locationId}, store={storeId}."
        )

    config.products = []
    config.updated_at = now
    await db.save(config)

    return {
        "message": f"{productType.value.capitalize()} products cleared successfully for tenant={tenantId}, location={locationId}, store={storeId}."
    }