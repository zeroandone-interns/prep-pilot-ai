from flask import request
from modules.document import controller


def register_document_routes(app):
    app.add_url_rule(
        "/process_documents",
        view_func=controller.document_processing_controller,
        methods=["POST"],
    )
    app.add_url_rule(
        "/document",
        view_func=controller.transcribe,
        methods=["GET"],
    )
