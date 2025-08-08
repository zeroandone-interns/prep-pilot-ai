import os
from flask import request, jsonify
from modules.document.services import (
    download_file_from_s3_uri,
    extract_text,
    analyze_image_with_bedrock,
)


def document_processing():
    data = request.get_json()
    if not data or "s3_url" not in data:
        return jsonify({"error": "Missing required field: s3_url"}), 400

    s3_url = data["s3_url"]
    try:
        downloaded_file = download_file_from_s3_uri(s3_url)
        ext = os.path.splitext(downloaded_file)[1].lower()

        if ext in [".pdf", ".docx", ".txt"]:
            result = extract_text(downloaded_file)
        elif ext in [".jpg", ".jpeg", ".png"]:
            result = analyze_image_with_bedrock(downloaded_file)
        else:
            return jsonify({"error": f"Unsupported file extension: {ext}"}), 400

        return jsonify({"result": result})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if "downloaded_file" in locals() and os.path.exists(downloaded_file):
            os.remove(downloaded_file)
