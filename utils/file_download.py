import asyncio
import boto3
from botocore.exceptions import NoCredentialsError
from io import BytesIO
from urllib.parse import urlparse
import requests
from configs.manager import settings

# Initialize s3 client

# Initialize s3 client
s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name='us-east-2'
    )

def download_file_from_s3(url):
    """
    Downloads a file from S3 and returns a BytesIO object.

    :param url: The S3 URL of the file.
    :return: BytesIO object containing the file data.
    """
    try:
        bucket, key = parse_s3_url(url)

        file_buffer = BytesIO()
        s3_client.download_fileobj(bucket, key, file_buffer)
        file_buffer.seek(0)
        print(f"File downloaded successfully from {url}")
        return file_buffer

    except NoCredentialsError:
        print("Credentials not available.")
        return None
    except Exception as e:
        print(f"Error downloading file: {e}")
        return None


def parse_s3_url(url):
    """
    Parses the S3 URL and extracts the bucket name and key.
    """
    if url.startswith("s3://"):
        path = url[5:]
        bucket, key = path.split('/', 1)
        print(bucket)
        print(key)
        return bucket, key
    elif url.startswith("https://"):
        parsed_url = urlparse(url)
        bucket = parsed_url.hostname.split('.')[0]
        key = parsed_url.path.lstrip('/')
        print(bucket)
        print(key)
        return bucket, key
    else:
        raise ValueError("URL is not a valid S3 URL.")


