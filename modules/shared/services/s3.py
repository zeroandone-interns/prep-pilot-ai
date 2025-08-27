import boto3
from botocore.exceptions import ClientError
from extensions import get_logger


class S3Service:
    def __init__(self):
        self.client = boto3.client("s3", region_name="us-east-1")
        self.head_bucket_name = "instructor-documents-store"
        self.logger = get_logger('[S3Service]')

    def get_object_from_s3(self, object_key):
        try:
            return self.client.get_object(Bucket=self.head_bucket_name, Key=object_key)
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                self.logger.error(
                    f"[S3] Object '{object_key}' does not exist in bucket '{self.head_bucket_name}'"
                )
                raise ValueError(
                    f"[S3] Object '{object_key}' does not exist in bucket '{self.head_bucket_name}'"
                )
            raise

    def read_file_from_s3(self, s3_key):
        obj = self.get_object_from_s3(s3_key)
        body = obj["Body"].read()
        content_type = obj["ContentType"]
        self.logger.info(f"[S3] Read file from S3: {s3_key} with type: {content_type}")

        # Decode only for text formats
        if content_type.startswith("text/") or content_type in {
            "application/json",
            "application/xml",
        }:
            body = body.decode("utf-8", errors="ignore")

        # For PDFs, DOCX, images, keep as bytes
        return body, content_type
