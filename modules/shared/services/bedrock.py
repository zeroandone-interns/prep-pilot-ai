import json
import base64
import boto3


class Bedrock:

    def __init__(
        self,
        model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
        region_name="us-east-1",
    ):
        self.model_id = model_id
        self.client = boto3.client("bedrock-runtime", region_name=region_name)

    def invoke_model_with_text(
        self,
        prompt,
        model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
        temperature=0.5,
        max_tokens=2048,
    ):
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}],
                }
            ],
        }

        response = self.client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            body=json.dumps(payload),
        )

        result = json.loads(response["body"].read())
        return result.get("content", [{}])[0].get("text", "")

    def invoke_image(
        self,
        image_path,
        prompt,
        model_id="anthropic.claude-3-haiku-20240307-v1:0",
        max_tokens=1000,
    ):
        with open(image_path, "rb") as img:
            encoded_image = base64.b64encode(img.read()).decode()

        ext = image_path.split(".")[-1].lower()
        media_type = "image/jpeg" if ext in ["jpg", "jpeg"] else "image/png"

        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": encoded_image,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            "max_tokens": max_tokens,
            "anthropic_version": "bedrock-2023-05-31",
        }

        response = self.client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            body=json.dumps(payload),
        )

        result = json.loads(response["body"].read())
        return result.get("content", [{}])[0].get("text", "")

    def generate_embedding(self, text, model_id="amazon.titan-embed-text-v2:0"):
        """Generate text embeddings from Bedrock."""
        payload = {"inputText": text}
        response = self.client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload),
        )
        result = json.loads(response["body"].read())
        return result.get("embedding", [])

    def invoke_pdf(self):
        pass
    