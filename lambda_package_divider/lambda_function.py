import asyncio
import json
import os
import boto3
from loguru import logger
import pandas as pd
import math
import io
import zipfile
import base64
import traceback
from singleton import create_index, delete_documents_for_tenant_location

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

s3_client = boto3.client('s3')

LAMBDA_FUNCTION_NAME = os.environ.get("LAMBDA_FUNCTION_NAME")
CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE"))
DELAY_BETWEEN_BATCHES = float(os.environ.get("DELAY_BETWEEN_BATCHES", 2.0))
CHUNKS_PER_BATCH = int(os.environ.get("CHUNKS_PER_BATCH", 500))

REQUIRED_COLUMNS = ['Session_id', 'Datetime', 'Product_name', 'UPC', 'Quantity', 'location_id', 'store_id']

def normalize_key(name: str) -> str:
    if not isinstance(name, str):
        return ""
    return name.replace('\xa0', ' ').replace('.', '').strip().lower()

def compress_and_encode_payload(payload: dict) -> str:
    raw_bytes = json.dumps(payload).encode('utf-8')
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("payload.json", raw_bytes)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')

async def async_lambda_handler(event):
    logger.debug(f"Received event: {event}")
    try:
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']
        parts = key.split('/')
        tenant_id = parts[0]
        location_id = parts[1]
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
            dtype={"UPC": str, "store_id": str, "location_id": str}
        )

        lambda_client = boto3.client('lambda')
        batch_count = 0
        for df_processed in df_processed_chunks:
            df_processed['Product_name'] = df_processed['Product_name'].map(normalize_key)

            payload = {
                "df_processed": df_processed.to_dict(orient="records"),
                "tenant_id": tenant_id,
                "location_id": location_id
            }
            payload = clean_json(payload)
            compressed_payload = compress_and_encode_payload(payload)

            response = lambda_client.invoke(
                FunctionName=LAMBDA_FUNCTION_NAME,
                InvocationType='Event',
                Payload=json.dumps({"compressed_payload": compressed_payload}).encode('utf-8')
            )
            logger.debug(response['StatusCode'])
            logger.debug("Lamda Invoked")
            if response['StatusCode'] != 202:
                logger.warning(f"Chunk failed to invoke: {response}")

            batch_count += 1
            if batch_count % CHUNKS_PER_BATCH == 0:
                logger.debug(f"Sleeping for {DELAY_BETWEEN_BATCHES} seconds after {batch_count} chunks...")
                await asyncio.sleep(DELAY_BETWEEN_BATCHES)

        logger.debug(f"Completed processing for Tenant {tenant_id}, Location {location_id}")
    except Exception as e:
        logger.exception("Error occurred")
        logger.debug("Full traceback:", traceback.format_exc())
        raise

def lambda_handler(event, context):
    return asyncio.run(async_lambda_handler(event))
