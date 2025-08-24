from flask import request
from modules.course import controller


def register_course_routes(app):
    app.add_url_rule(
        "/generate_content",
        view_func=controller.course_content_controller,
        methods=["POST"],
    )
    app.add_url_rule(
        "/generate_quiz",
        view_func=controller.quiz_controller,
        methods=["POST"],
    )
