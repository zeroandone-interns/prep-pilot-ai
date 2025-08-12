from flask import request, jsonify
from modules.document.services import DocumentProcessingService


def document_processing_controller():
    data = request.get_json()

    service = DocumentProcessingService()

    valid, error = service.validate_request(data)
    if not valid:
        return jsonify({"error": error}), 400

    results = service.process_documents(data["course_id"], data["documents"])

    return jsonify({"results": results})
