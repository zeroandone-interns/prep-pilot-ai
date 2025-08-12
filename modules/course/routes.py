from flask import request
from modules.course import controller


def register_course_routes(app):
    app.add_url_rule(
        "/generate_content",
        view_func=controller.generate_course_content,
        methods=["POST"],
    )
