import asyncio
import json
import os
import boto3
from loguru import logger
import pandas as pd

from singleton import create_index, delete_documents_for_tenant_location

import math

def clean_json(obj):
    """Recursively replace NaN, inf, -inf with None."""
    if isinstance(obj, dict):
        return {k: clean_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_json(v) for v in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
    return obj



s3_client = boto3.client(
        's3'
    )

LAMBDA_FUNCTION_NAME = os.environ.get("LAMBDA_FUNCTION_NAME")
CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE"))

# List of required columns
REQUIRED_COLUMNS = ['Session_id', 'Datetime', 'Product_name','UPC','Quantity','location_id','store_id']  




def normalize_key(name: str) -> str:
    if not isinstance(name, str):
        return ""
    return name.replace('\xa0', ' ').replace('.', '').strip().lower()

async def async_lambda_handler(event):
    logger.debug(f"Received event: {event}")
    try:
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']
        logger.debug(f"bucket: {bucket}, key: {key}")

        parts = key.split('/')
        tenant_id = parts[0]
        location_id = parts[1]

        logger.debug(f"Tenant ID: {tenant_id}, Location ID: {location_id}")

        logger.debug("Attempting to get object from S3...")
        response = s3_client.get_object(Bucket=bucket, Key=key)
        logger.debug("Successfully got object from S3")
        await create_index()
        await delete_documents_for_tenant_location(tenant_id, location_id)
        logger.debug("Attempting to read CSV...")
        df_processed_chunks = pd.read_csv(
            response['Body'],
            chunksize=CHUNK_SIZE,
            usecols=REQUIRED_COLUMNS,
            dtype={"UPC": str, "store_id": str}  # ✅ forcing store_id and UPC to be strings
        )

        for df_processed in df_processed_chunks:
            logger.debug("Chunking happens") 
            df_processed['Product_name'] = df_processed['Product_name'].map(normalize_key)
            logger.debug("Normalize the Producat Names")
            lambda_client = boto3.client('lambda')
            payload = {
                "df_processed": df_processed.to_dict(orient="records"),
                "location_id": location_id,
                "tenant_id": tenant_id
            }
            payload = clean_json(payload)
            logger.debug("Lambda Payload Created")
            response = lambda_client.invoke(
                FunctionName=LAMBDA_FUNCTION_NAME,
                InvocationType='Event',
                Payload=json.dumps(payload).encode('utf-8')
            )
            logger.debug(response['StatusCode'])
            logger.debug("Lamda Invoked")
            if response['StatusCode'] != 202:
                logger.warning(f"Chunk failed to invoke: {response}")

        logger.debug(f"Processed file divided in chunks for Tenant {tenant_id}, Location {location_id}")
    except Exception as e:
        logger.debug("Error occurred:", str(e))
        import traceback
        logger.debug("Full traceback:", traceback.format_exc())
        raise  # Re-raise the exception to see it in CloudWatch
    
def lambda_handler(event, context):
    return asyncio.run(async_lambda_handler(event))