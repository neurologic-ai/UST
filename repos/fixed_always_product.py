from io import BytesIO
from fastapi import HTTPException, UploadFile
import pandas as pd


REQUIRED_COLUMNS = {"UPC", "Product Name"}

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
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing columns: {missing}")
    if df[REQUIRED_COLUMNS].isnull().any().any():
        raise HTTPException(status_code=400, detail="Empty UPC or Product Name values found.")
