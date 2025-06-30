import asyncio
import time
import boto3
from loguru import logger
import pandas as pd
from category_generate import generate_category_df_from_processed
from setup import run_models_and_store_outputs
import traceback


s3_client = boto3.client(
        's3'
    )

async def async_lambda_handler(event):
    # logger.debug(f"Received event: {event}")
    try:
        df_processed = pd.DataFrame(event["df_processed"])
        tenant_id = event["tenant_id"]
        location_id = event["location_id"]      
        logger.debug(tenant_id)
        logger.debug(location_id)
        tasks = [
            generate_category_df_from_processed(df_processed, tenant_id, location_id),
            run_models_and_store_outputs(tenant_id, location_id, df_processed)
        ]

        try:
            start_time = time.time()
            df_categories, _ = await asyncio.gather(*tasks)
            end_time = time.time()
            time_elapsed = end_time - start_time
            logger.debug(f"Time taken for chunk process: {time_elapsed}")
        except Exception:
            logger.debug(traceback.format_exc())
            return {"Error": "Failed to complete setup tasks."}
        
        logger.debug("Both tasks completed successfully.")
        logger.debug(f"Processed file for Tenant {tenant_id}, Location {location_id}")
        
    except Exception as e:
        logger.debug(f"Error occurred: {str(e)}")
        logger.debug(f"Full traceback:\n{traceback.format_exc()}")
        raise  # Re-raise the exception to see it in CloudWatch
    


# Wrapper to support sync lambda_handler
def lambda_handler(event, context):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(async_lambda_handler(event))