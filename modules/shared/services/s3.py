import boto3
import tempfile, os
from urllib.parse import urlparse


class S3Client:
    def __init__(self, region_name="us-east-1"):
        self.client = boto3.client("s3", region_name=region_name)

    def download_file_from_s3_uri(self, s3_uri):
        parsed = urlparse(s3_uri)
        bucket = parsed.netloc
        key = parsed.path.lstrip("/")
        ext = os.path.splitext(key)[1].lower()

        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            temp_path = tmp.name

        self.client.download_file(bucket, key, temp_path)
        return temp_path
