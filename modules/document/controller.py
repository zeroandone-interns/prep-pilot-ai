from flask import request, jsonify
from modules.document.services import DocumentProcessingService
from modules.document.schema import validate_request
from extensions import get_logger
from modules.shared.services.transcrible import TranscribeService

logger = get_logger()
document_service = DocumentProcessingService()
transcribe_service = TranscribeService()

def document_processing_controller():
    data = request.get_json()

    valid, error = validate_request(data)
    if not valid:
        return jsonify({"error": error}), 400

    results = document_service.process_documents(data["course_id"], data["documents"])

    return jsonify({"results": results})


def transcribe():
    try:
        response = transcribe_service.transcribe_file(
            job_name=f"transcribe-test-1",
            media_uri=f"s3://instructor-documents-store/test/test_mp4.mp4",
            media_format="mp4",
            language_code="en-US"
        )
        if not response:
            return jsonify({"error": "Transcription failed"}), 500
        return jsonify({"transcription": response}), 200
    except Exception as e:
        logger.error(f"Error retrieving document: {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500
