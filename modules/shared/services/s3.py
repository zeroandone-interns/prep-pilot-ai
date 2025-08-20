import boto3
from botocore.exceptions import ClientError
from extensions import get_logger


class S3Service:
    def __init__(self):
        self.client = boto3.client("s3", region_name="us-east-1")
        self.head_bucket_name = "instructor-documents-store"
        self.logger = get_logger()

    def check_if_bucket_exists(self):
        return self.client.head_bucket(Bucket=self.head_bucket_name)

    # Check if folder exists
    def check_if_folder_exists(self, folder_prefix):
        if not folder_prefix.endswith("/"):
            folder_prefix += "/"

        response = self.client.list_objects_v2(
            Bucket=self.head_bucket_name, Prefix=folder_prefix, MaxKeys=1
        )
        contents = response["Contents"][0]["Key"]

        return contents

    def check_if_folder_has_files(self, folder_name):
        if not folder_name.endswith("/"):
            folder_name += "/"

        response = self.client.list_objects_v2(
            Bucket=self.head_bucket_name, Prefix=folder_name
        )
        contents = response.get("Contents", [])

        keys = [obj["Key"] for obj in contents]
        self.logger.info(f"Keys: {keys if keys else 'No keys found'}")

        return keys

    def get_object_from_s3(self, object_key):
        try:
            return self.client.get_object(Bucket=self.head_bucket_name, Key=object_key)
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                self.logger.error(
                    f"[S3] Object '{object_key}' does not exist in bucket '{self.head_bucket_name}'"
                )
                raise ValueError(
                    f"Object '{object_key}' does not exist in bucket '{self.head_bucket_name}'"
                )
            raise

    def read_file_from_s3(self, object_key):
        obj = self.get_object_from_s3(object_key)
        body = obj["Body"].read()
        content_type = obj["ContentType"]
        self.logger.info(f"Read file from S3: {object_key} with type: {content_type}")

        # Decode only for text formats
        if content_type.startswith("text/") or content_type in {
            "application/json",
            "application/xml",
        }:
            body = body.decode("utf-8", errors="ignore")

        # For PDFs, DOCX, images, keep as bytes
        return body, content_type
