from flask import request
from modules.document import controller


def register_document_routes(app):
    app.add_url_rule(
        "/process_document",
        view_func=controller.document_processing,
        methods=["POST"],
    )
