import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from fastapi import HTTPException
from configs.manager import settings
from loguru import logger

def upload_file_to_s3(file, csv_type, tenant_id, location_id, store_ids=None):
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

    except NoCredentialsError:
        raise HTTPException(status_code=502, detail="AWS credentials are not configured")
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code in ("InvalidClientTokenId", "AuthFailure", "SignatureDoesNotMatch"):
            raise HTTPException(status_code=502, detail="AWS credentials are invalid or expired")
        if code == "AccessDenied":
            raise HTTPException(status_code=502, detail="AWS credentials do not have permission to upload to S3")
        if code == "NoSuchBucket":
            raise HTTPException(status_code=502, detail=f"S3 bucket '{settings.bucket_name}' does not exist")
        logger.error(f"S3 ClientError [{code}]: {e}")
        raise HTTPException(status_code=502, detail=f"S3 upload failed: {code}")
    except Exception as e:
        logger.error(f"Unexpected S3 upload error: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload file to S3")
