from flask import app, request, jsonify
from modules.document.services import DocumentProcessingService
from modules.document.schema import validate_request
from extensions import get_logger
from modules.flashcard.service import FlashcardService
from modules.shared.services.transcrible import TranscribeService

logger = get_logger("[DocumentController]")
document_service = DocumentProcessingService()
transcribe_service = TranscribeService()


def document_processing_controller():
    try:
        data = request.get_json()

        valid, error = validate_request(data)
        if not valid:
            return jsonify({"success": False, "message": "Invalid request data"}), 400

        results = document_service.process_documents_for_course(data["s3_keys"])

        return jsonify({"success": bool(results)}), 200
    except Exception as e:
        logger.error(f"Error processing documents: {str(e)}")
        return jsonify({"success": False, "message": "Internal Server Error"}), 500
