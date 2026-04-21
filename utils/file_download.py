import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from io import BytesIO
from urllib.parse import urlparse
from configs.manager import settings
from loguru import logger


def _get_s3_client():
    return boto3.client(
        's3',
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name='us-east-2'
    )


def download_file_from_s3(url):
    try:
        bucket, key = parse_s3_url(url)
        file_buffer = BytesIO()
        _get_s3_client().download_fileobj(bucket, key, file_buffer)
        file_buffer.seek(0)
        logger.debug(f"File downloaded successfully from {url}")
        return file_buffer

    except NoCredentialsError:
        logger.error("AWS credentials are not configured")
        return None
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code in ("InvalidClientTokenId", "AuthFailure", "SignatureDoesNotMatch"):
            logger.error("AWS credentials are invalid or expired")
        elif code == "AccessDenied":
            logger.error(f"Access denied downloading {url}")
        elif code == "NoSuchKey":
            logger.error(f"File not found in S3: {url}")
        else:
            logger.error(f"S3 ClientError [{code}] downloading {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error downloading file from S3: {e}")
        return None


def parse_s3_url(url):
    if url.startswith("s3://"):
        path = url[5:]
        bucket, key = path.split('/', 1)
        return bucket, key
    elif url.startswith("https://"):
        parsed_url = urlparse(url)
        bucket = parsed_url.hostname.split('.')[0]
        key = parsed_url.path.lstrip('/')
        return bucket, key
    else:
        raise ValueError("URL is not a valid S3 URL.")
