import os
import json
import base64
import tempfile
from urllib.parse import urlparse
import boto3
import pdfplumber
from docx import Document

model_id = "anthropic.claude-3-haiku-20240307-v1:0"

image_prompt = """
You are an expert assistant skilled in both image captioning and text extraction (OCR).
Please perform the following tasks on the provided image:

1. Extract all readable text from the image accurately.
2. Provide a clear and concise descriptive caption summarizing the main content, objects, or scene in the image.

Format your response clearly with two sections:
Extracted text: [Insert all extracted text here]
Image caption: [Insert descriptive caption here]

Make sure the caption complements the extracted text and helps a person who cannot see the image understand its contents.
"""


s3_client = boto3.client("s3")
bedrock_runtime_client = boto3.client("bedrock-runtime", region_name="us-east-1")


def download_file_from_s3_uri(s3_uri):
    parsed = urlparse(s3_uri)
    bucket = parsed.netloc
    key = parsed.path.lstrip("/")
    ext = os.path.splitext(key)[1].lower()

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        temp_path = tmp.name

    s3_client.download_file(bucket, key, temp_path)
    return temp_path


def extract_text_from_pdf(file_path):
    full_text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"
    return full_text.strip()


def extract_text_from_docx(file_path):
    doc = Document(file_path)
    return "\n".join(para.text for para in doc.paragraphs).strip()


def extract_text_from_txt(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read().strip()


def extract_text(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext == ".docx":
        return extract_text_from_docx(file_path)
    elif ext == ".txt":
        return extract_text_from_txt(file_path)
    else:
        raise ValueError(f"Unsupported text file type: {ext}")


def analyze_image_with_bedrock(file_path):
    with open(file_path, "rb") as image_file:
        encoded_image = base64.b64encode(image_file.read()).decode()

    ext = os.path.splitext(file_path)[1].lower()
    if ext in [".jpg", ".jpeg"]:
        media_type = "image/jpeg"
    elif ext == ".png":
        media_type = "image/png"
    else:
        media_type = "application/octet-stream"

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
                    {"type": "text", "text": image_prompt},
                ],
            }
        ],
        "max_tokens": 1000,
        "anthropic_version": "bedrock-2023-05-31",
    }

    response = bedrock_runtime_client.invoke_model(
        modelId=model_id,
        contentType="application/json",
        body=json.dumps(payload),
    )

    output_binary = response["body"].read()
    output_json = json.loads(output_binary)
    return output_json.get("content", [{}])[0].get("text", "[No response text]")
