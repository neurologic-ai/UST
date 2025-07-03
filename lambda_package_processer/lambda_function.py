import asyncio
import time
import boto3
import traceback
import pandas as pd
import base64
import zipfile
import io
from loguru import logger
import json

from category_generate import generate_category_df_from_processed
from setup import run_models_and_store_outputs

s3_client = boto3.client('s3')

def decode_and_decompress_payload(encoded: str) -> dict:
    zipped_bytes = base64.b64decode(encoded)
    buffer = io.BytesIO(zipped_bytes)
    with zipfile.ZipFile(buffer, 'r') as zip_file:
        payload_json = zip_file.read("payload.json").decode('utf-8')
    return json.loads(payload_json)

async def async_lambda_handler(event):
    try:
        compressed_payload = event["compressed_payload"]
        payload = decode_and_decompress_payload(compressed_payload)

        df_processed = pd.DataFrame(payload["df_processed"])
        tenant_id = payload["tenant_id"]
        location_id = payload["location_id"]

        logger.debug(f"Tenant: {tenant_id}, Location: {location_id}")

        tasks = [
            generate_category_df_from_processed(df_processed, tenant_id, location_id),
            run_models_and_store_outputs(tenant_id, location_id, df_processed)
        ]

        start_time = time.time()
        await asyncio.gather(*tasks)
        end_time = time.time()

        logger.debug(f"Time taken for chunk process: {end_time - start_time:.2f}s")
        logger.debug("Both tasks completed successfully.")
    except Exception:
        logger.debug("Exception occurred during processing")
        logger.debug(traceback.format_exc())
        raise

def lambda_handler(event, context):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(async_lambda_handler(event))
