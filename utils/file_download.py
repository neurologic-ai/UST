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



# Example usage
if __name__ == "__main__":
    # s3_url = "https://s3-replus-prd-use-01.s3.amazonaws.com/101/101/2025-05-20_14-58-08/processed.csv"
    # # s3_url = "https://s3-replus-prd-use-01.s3.amazonaws.com/2/10/2025-05-13_19-43-11/processed.csv?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIASHQJVI4CY6BH7G5Z%2F20250513%2Fus-east-2%2Fs3%2Faws4_request&X-Amz-Date=20250513T141319Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Signature=7693b1eb3d332a82a59e1e2e4475d32ccfd0b90563d97d010ceec720c12c6608"
    # download_file_from_s3(s3_url)
    s3_url = "https://s3-replus-prd-use-01.s3.amazonaws.com/682db0be29b7dee813deffc5/location_1/categories.csv"
    local_file_path = "downloads/6th_june_50.csv"

    download_file_from_s3(s3_url, local_file_path)

