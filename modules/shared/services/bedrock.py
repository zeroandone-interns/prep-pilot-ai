import json
import boto3


class Bedrock:
    def __init__(
        self, model_id="anthropic.claude-3-haiku-20240307-v1:0", region_name="us-east-1"
    ):
        self.model_id = model_id
        self.client = boto3.client("bedrock-runtime", region_name=region_name)

    def invoke_model_with_request(self, prompt):
        model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"

        native_request = {
            "anthropic_version": "bedrock-2023-05-31",
            "temperature": 0.5,
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}],
                }
            ],
        }

        request = json.dumps(native_request)

        response = self.client.invoke_model(modelId=model_id, body=request)

        model_response = json.loads(response["body"].read())
        response_text = model_response["content"][0]["text"]

        return response_text
