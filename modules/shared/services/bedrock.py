import json
import base64
import boto3
from extensions import get_logger


class BedrockService:

    def __init__(
        self,
        model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
    ):
        self.model_id = model_id
        self.client = boto3.client("bedrock-runtime", region_name="us-east-1")
        self.logger = get_logger()

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
        print("Region:", self.client.meta.region_name)
        print("Model ID:", model_id)
        print("Payload size (bytes):", len(json.dumps(payload)))
        response = self.client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            body=json.dumps(payload),
        )

        result = json.loads(response["body"].read())
        return result.get("content", [{}])[0].get("text", "")

    def invoke_image(
        self,
        file_bytes,
        content_type,
        image_prompt,
        model_id="anthropic.claude-3-haiku-20240307-v1:0",
        max_tokens=1000,
    ):
        if not isinstance(file_bytes, (bytes, bytearray)):
            raise TypeError("file_bytes must be bytes-like object")

        encoded_image = base64.b64encode(file_bytes).decode("utf-8")

        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": content_type,
                                "data": encoded_image,
                            },
                        },
                        {
                            "type": "text",
                            "text": image_prompt,
                        },
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

    def invoke_document(self, doc_bytes, file_key, prompt):
        file_name = file_key.split("/")[-1]  # Get the file name
        name, ext = file_name.rsplit(".", 1) if "." in file_name else (file_name, "")
        name = name.replace(" ", "_")
        self.logger.info(f"Invoking document with name: {name}, ext: {ext}")
        doc_message = {
            "role": "user",
            "content": [
                {
                    "document": {
                        "name": name,
                        "format": ext,
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

    def invoke_model_with_stream(self, prompt, temperature=0.5, max_tokens=1024):
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": prompt}]}
            ],
        }
        response = self.client.invoke_model_with_response_stream(
            modelId=self.model_id,
            body=json.dumps(body),
        )

        for event in response["body"]:
            if "chunk" in event and "bytes" in event["chunk"]:
                chunk_data = json.loads(event["chunk"]["bytes"])
                if chunk_data.get("type") == "content_block_delta":
                    yield chunk_data["delta"].get("text", "")

    def invoke_model_streaming(self, prompt, temperature=0.5, max_tokens=1024):
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": prompt}]}
            ],
        }
        response = self.client.invoke_model_with_response_stream(
            modelId=self.model_id,
            body=json.dumps(body),
        )

        collected_text = []
        for event in response["body"]:
            if "chunk" in event and "bytes" in event["chunk"]:
                chunk_data = json.loads(event["chunk"]["bytes"])
                if chunk_data.get("type") == "content_block_delta":
                    collected_text.append(chunk_data["delta"].get("text", ""))

        return "".join(collected_text)
