import json
import base64
import boto3


class BedrockService:

    def __init__(
        self,
        model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
    ):
        self.model_id = model_id
        self.client = boto3.client("bedrock-runtime", region_name="us-east-1")

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

    def invoke_document(self, doc_bytes, file_key, prompt, ext):
        name = file_key.split("/")[-1].rsplit(".", 1)[0].replace(" ", "_")
        ext = ext
        format_map = {
            ".pdf": "pdf",
            ".docx": "docx",
            ".doc": "doc",
            ".md": "md",
            ".txt": "txt",
            ".html": "html",
        }

        if ext not in format_map:
            raise ValueError(f"Unsupported document format: {ext}")
        doc_message = {
            "role": "user",
            "content": [
                {
                    "document": {
                        "name": name,
                        "format": format_map[ext],
                        "source": {"bytes": doc_bytes},
                    }
                },
                {"text": prompt},
            ],
        }

        response = self.client.converse(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            messages=[doc_message],
            inferenceConfig={
                "maxTokens": 2000,
                "temperature": 0,
            },
        )

        return response["output"]["message"]["content"][0]["text"]
