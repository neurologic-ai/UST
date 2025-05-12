import boto3
from botocore.exceptions import NoCredentialsError
from datetime import datetime
from configs.manager import settings

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
    # s3_client = boto3.client('s3')
    s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name='us-east-2'
    )

    current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    dest_name = f"{tenant_id}/{location_id}/{current_datetime}/{csv_type}.csv"

    try:
        s3_client.upload_fileobj(file, settings.bucket_name, dest_name)
        # file_url = f"https://{settings.bucket_name}.s3.amazonaws.com/{dest_name}"
        # return file_url
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': settings.bucket_name, 'Key': dest_name},
            ExpiresIn=3600
        )

        return presigned_url

    except NoCredentialsError:
        print("Credentials not available.")
        return None
    except Exception as e:
        print(f"Error uploading file: {e}")
        return None
