import os
import boto3
import json

class SecretsDBService:
    def __init__(self, region_name=None, host_secret="Preppilot_Secret", pass_secret="rds!db-abdcda1d-dab5-4011-8bdc-b40ef6122df3"):
        self.region_name = region_name or os.getenv("AWS_REGION", "us-east-1")
        self.host_secret = host_secret
        self.pass_secret = pass_secret
        self.client = boto3.client("secretsmanager", region_name=self.region_name)
        self.host_info = None
        self.credentials = None

    def fetch_host_info(self):
        response = self.client.get_secret_value(SecretId=self.host_secret)
        self.host_info = json.loads(response["SecretString"])
        return self.host_info

    def fetch_credentials(self):
        response = self.client.get_secret_value(SecretId=self.pass_secret)
        self.credentials = json.loads(response["SecretString"])
        return self.credentials

    def get_db_url(self):
        if not self.host_info:
            self.fetch_host_info()
        if not self.credentials:
            self.fetch_credentials()

        host = self.host_info.get("host")
        port = self.host_info.get("port", 5432)
        dbname = self.host_info.get("dbname") or self.host_info.get("db_name")
        username = self.credentials.get("username") or self.credentials.get("db_user")
        password = self.credentials.get("password") or self.credentials.get("db_pass")

        return f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{dbname}"
