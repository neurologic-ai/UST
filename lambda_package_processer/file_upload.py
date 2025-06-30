import boto3
from botocore.exceptions import NoCredentialsError
from datetime import datetime
from manager import settings

from loguru import logger

def upload_file_to_s3(file, csv_type, tenant_id, location_id):
    """
    Uploads a file to AWS S3 and returns the file's URL, creating a destination name 
    using tenant_id, location_id, current datetime, csv type, and a fixed file name.

    :param file: The file object to be uploaded.
    :param csv_type: Type/category of the CSV file (e.g., "processed", "categories").
    :param tenant_id: The tenant ID.
    :param location_id: The location ID.
    :return: The URL of the uploaded file.
    """
    s3_client = boto3.client('s3')

    try:
        dest_name = f"{tenant_id}/{location_id}/{csv_type}.csv"
        s3_client.upload_fileobj(file, settings.bucket_name, dest_name)
        file_url = f"https://{settings.bucket_name}.s3.amazonaws.com/{dest_name}"
        return file_url
    except NoCredentialsError:
        print("Credentials not available.")
        return None
    except Exception as e:
        print(f"Error uploading file: {e}")
        return None
