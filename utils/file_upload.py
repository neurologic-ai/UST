import traceback
import boto3
from botocore.exceptions import NoCredentialsError
from configs.manager import settings

from loguru import logger

def upload_file_to_s3(file, csv_type, tenant_id, location_id, store_ids=None):
    """
    Uploads a file to AWS S3 and returns the file's URL, creating a destination name 
    using tenant_id, location_id, csv type, and store_ids.

    :param file: The file object to be uploaded.
    :param csv_type: Type/category of the CSV file (e.g., "processed", "categories").
    :param tenant_id: The tenant ID.
    :param location_id: The location ID.
    :param store_ids: Optional list of store IDs to append to filename.
    :return: The URL of the uploaded file.
    """
    logger.debug(f"access_key_id: {settings.aws_access_key_id}")
    logger.debug(f"secret_access_key: {settings.aws_secret_access_key}")

    s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name='us-east-2'
    )

    # Build filename with optional store_ids
    store_suffix = f"_{'_'.join(store_ids)}" if store_ids else ""
    dest_name = f"{tenant_id}/{location_id}/{csv_type}{store_suffix}.csv"

    try:
        s3_client.upload_fileobj(file, settings.bucket_name, dest_name)
        file_url = f"https://{settings.bucket_name}.s3.amazonaws.com/{dest_name}"
        return file_url

    except NoCredentialsError as e:
        raise RuntimeError("AWS credentials not available") from e
    except Exception as e:
        raise RuntimeError("Failed to upload file to S3") from e
