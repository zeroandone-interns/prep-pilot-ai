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
        self.logger = get_logger("[BedrockService]")

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

        try:
            response = self.client.invoke_model(
                modelId=model_id,
                contentType="application/json",
                body=json.dumps(payload),
            )
        except Exception as e:
            self.logger.error(f"Error invoking model: {e}")
            return {"error": str(e)}

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

        try:
            response = self.client.invoke_model(
                modelId=model_id,
                contentType="application/json",
                body=json.dumps(payload),
            )
        except Exception as e:
            self.logger.error(f"Error invoking image model: {e}")
            return {"error": str(e)}

        result = json.loads(response["body"].read())
        return result.get("content", [{}])[0].get("text", "")

    def invoke_document(self, doc_bytes, file_name, file_extension, prompt):
        if not file_name or not isinstance(file_name, str) or len(file_name) < 1:
            raise ValueError("file_name must be a non-empty string")

        doc_message = {
            "role": "user",
            "content": [
                {
                    "document": {
                        "name": file_name,
                        "format": file_extension[1:],
                        "source": {"bytes": doc_bytes},
                    }
                },
                {"text": prompt},
            ],
        }

        try:
            response = self.client.converse(
                modelId="anthropic.claude-3-sonnet-20240229-v1:0",
                messages=[doc_message],
                inferenceConfig={
                    "maxTokens": 2000,
                    "temperature": 0,
                },
            )
        except Exception as e:
            self.logger.error(f"Error invoking document model: {e}")
            return {"error": str(e)}

        return response["output"]["message"]["content"][0]["text"]

    def generate_embedding(self, text, model_id="amazon.titan-embed-text-v2:0"):
        if not text or not isinstance(text, str) or len(text) < 1:
            raise ValueError("text must be a non-empty string")

        payload = {"inputText": text}
        try:
            response = self.client.invoke_model(
                modelId=model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(payload),
            )
        except Exception as e:
            self.logger.error(f"Error generating embedding: {e}")
            return {"error": str(e)}

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

        try:
            response = self.client.invoke_model_with_response_stream(
                modelId=self.model_id,
                body=json.dumps(body),
            )
        except Exception as e:
            self.logger.error(f"Error invoking model with stream: {e}")
            return []

        for event in response["body"]:
            if "chunk" in event and "bytes" in event["chunk"]:
                chunk_data = json.loads(event["chunk"]["bytes"])
                if chunk_data.get("type") == "content_block_delta":
                    yield chunk_data["delta"].get("text", "")

    def invoke_model_streaming(
        self, prompt, model_id, temperature=0.5, max_tokens=10000
    ):
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": prompt}]}
            ],
        }
        try:
            response = self.client.invoke_model_with_response_stream(
                modelId=model_id,
                body=json.dumps(body),
            )
        except Exception as e:
            self.logger.error(f"Error invoking model streaming: {e}")
            return []

        collected_text = []
        for event in response["body"]:
            if "chunk" in event and "bytes" in event["chunk"]:
                chunk_data = json.loads(event["chunk"]["bytes"])
                if chunk_data.get("type") == "content_block_delta":
                    collected_text.append(chunk_data["delta"].get("text", ""))

        return "".join(collected_text)

    def invoke_model_with_texttt(self, prompt):
        max_tokens = 10000
        temperature = 0.5
        model_id = "amazon.nova-pro-v1:0"
        conversation = [{"role": "user", "content": [{"text": prompt}]}]

        try:
            # Nova/Nova Lite models require converse and inferenceConfig
            inference_config = {"maxTokens": max_tokens, "temperature": temperature}
            response = self.client.converse(
                modelId=model_id,
                messages=conversation,
                inferenceConfig=inference_config,
            )
            return response["output"]["message"]["content"][0]["text"]

        except Exception as e:
            self.logger.error(f"Error invoking model: {e}")
            return {"error": str(e)}
