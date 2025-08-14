import boto3
import tempfile
import os
from urllib.parse import urlparse
from botocore.exceptions import ClientError


class S3Client:
    def __init__(self, region_name="us-east-1"):
        self.client = boto3.client("s3", region_name=region_name)

    def _check_bucket_exists(self, bucket_name):
        try:
            self.client.head_bucket(Bucket=bucket_name)
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code in ("404", "403"):
                raise ValueError(
                    f"Bucket '{bucket_name}' does not exist or access is denied"
                )
            raise

    def download_file_from_s3_uri(self, s3_uri):
        parsed = urlparse(s3_uri)
        bucket = parsed.netloc
        key = parsed.path.lstrip("/")
        ext = os.path.splitext(key)[1].lower()

        self._check_bucket_exists(bucket)

        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            temp_path = tmp.name

        try:
            self.client.download_file(bucket, key, temp_path)
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise ValueError(f"Object '{key}' does not exist in bucket '{bucket}'")
            raise

        return temp_path
